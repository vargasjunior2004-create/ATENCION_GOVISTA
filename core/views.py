import json
import logging
import os
import threading
import re
from urllib.parse import urlparse, parse_qs
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta
from django.db import IntegrityError, transaction
from django.conf import settings
from django.db.models import ProtectedError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Count, Max, Q, Sum
from django.http import FileResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .models import (
    User, Customer, Contract, CoverageZone, Role, Permission, RolePermission, UserRole,
    TemporaryFunction, TemporaryAssignment, Plan, Promotion, Sale, Backup, TipoSolicitud, Motivo,
    TarifaTraslado, TarifaTrasladoHistorial, SaleIdempotencyKey, AuditLog,
    InventarioMovimiento, CanalCaptacion, CustomerLocation, CustomerLocationHistory,
    UserSession,
)
from .serializers import (
    UserSerializer, UserWriteSerializer, PermissionSerializer, RoleSerializer,
    UserRoleSerializer, TemporaryFunctionSerializer, TemporaryAssignmentSerializer,
    PlanSerializer,
    PlanPublicSerializer, CustomerSerializer, ContractSerializer, SaleSerializer,
    SaleCreateSerializer, BackupSerializer,
    PromotionSerializer, PromotionWriteSerializer,
    TipoSolicitudPublicSerializer, MotivoSerializer, MotivoPublicSerializer,
    CoverageZoneSerializer, TarifaTrasladoSerializer, TarifaTrasladoHistorialSerializer,
    CanalCaptacionSerializer, CanalCaptacionPublicSerializer,
    CustomerLocationSerializer, CustomerLocationHistorySerializer,
)
from .domain import (
    request_type_mode, request_type_catalog,
    movement_status_for_request_type,
    MODO_RETIRO, MODO_CAMBIO_PLAN, MODO_ADICION,
    MODO_SIMPLE, MODO_TRASLADO,
)
from .reports import build_sales_pdf, build_sales_xlsx
from .rbac import can_supervise_productivity, has_permission, is_system_admin
from .audit import record_audit
from .location_storage import optimize_photo, upload_photo

# Evita que dos respaldos corran a la vez. Con gunicorn --workers 2 este
# lock es por proceso, lo cual es suficiente para el caso de un unico
# administrador y evita agotar la CPU del plan gratuito.
_backup_lock = threading.Lock()
_backup_in_progress = False
logger = logging.getLogger(__name__)


def _issue_session_token(user):
    """Crea una sesión persistente y emite un JWT asociado a ella."""
    access_lifetime = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
    session = UserSession.objects.create(
        user=user,
        expires_at=timezone.now() + access_lifetime,
    )
    refresh = RefreshToken.for_user(user)
    refresh['ver'] = user.token_version
    refresh['sid'] = str(session.session_id)
    return session, refresh


class _BackupFileResponse(FileResponse):
    """FileResponse que borra el archivo temporal cuando la respuesta
    termina de enviarse.

    Django captura file.close al construir la respuesta, asi que no se
    puede parchear el archivo: hay que sobrescribir close(), que el
    servidor WSGI invoca en el finally tras completar el streaming.
    """

    def __init__(self, *args, filepath=None, **kwargs):
        self._backup_filepath = filepath
        super().__init__(*args, **kwargs)

    def close(self):
        try:
            super().close()
        finally:
            path = self._backup_filepath
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass


def _stream_backup_file(filepath, filename, checksum=''):
    """Transmite el archivo al navegador; se elimina al terminar."""
    handle = open(filepath, 'rb')
    response = _BackupFileResponse(
        handle,
        content_type='application/octet-stream',
        as_attachment=True,
        filename=filename,
        filepath=filepath,
    )
    if checksum:
        response['X-Content-SHA256'] = checksum
    return response


def _user_payload(user):
    assignments = list(user.role_assignments.filter(
        active=True, role__active=True).select_related('role').prefetch_related(
            'role__role_permissions__permission'))
    roles = [{
        'id': assignment.role_id,
        'code': assignment.role.code,
        'name': assignment.role.name,
        'is_system_role': assignment.role.is_system_role,
        'grants_full_access': assignment.role.grants_full_access,
    } for assignment in assignments]
    permissions = sorted({
        role_permission.permission.code
        for assignment in assignments
        for role_permission in assignment.role.role_permissions.all()
        if role_permission.permission.active
    })
    return {'id': user.id, 'name': user.name,
            'role': user.role, 'active': user.active, 'roles': roles,
            'permissions': permissions,
            'mustChangePassword': user.must_change_password,
            'lastLoginAt': user.last_login_at,
            'isSystemAdmin': is_system_admin(user)}


class IsAdminMixin:
    permission_code = None

    def check_admin(self, request):
        user = request.user
        allowed = (
            user and getattr(user, 'active', True)
            and (has_permission(user, self.permission_code)
                 if self.permission_code else getattr(user, 'role', None) == 'admin')
        )
        if not allowed:
            return Response({'error': 'Se requieren permisos de administrador'},
                            status=status.HTTP_403_FORBIDDEN)
        return None


class PermissionMixin:
    permission_code = None

    def check_permission(self, request, code=None):
        if not has_permission(request.user, code or self.permission_code):
            return Response(
                {'error': 'No tienes permiso para realizar esta operación'},
                status=status.HTTP_403_FORBIDDEN)
        return None


class PermissionListView(PermissionMixin, APIView):
    permission_code = 'roles.permisos.view'

    def get(self, request):
        error = self.check_permission(request)
        if error:
            return error
        return Response(PermissionSerializer(
            Permission.objects.filter(active=True).order_by('module', 'action'),
            many=True).data)


class AuditLogListView(PermissionMixin, APIView):
    permission_code = 'auditoria.eventos.view'

    def get(self, request):
        error = self.check_permission(request)
        if error:
            return error
        events = AuditLog.objects.select_related('actor').all()
        actor = (request.query_params.get('actor') or '').strip()
        if actor:
            events = events.filter(actor__name__icontains=actor)
        action = (request.query_params.get('action') or '').strip()
        if action:
            events = events.filter(action=action)
        entity = (request.query_params.get('entity') or '').strip()
        if entity:
            events = events.filter(entity=entity)
        module = (request.query_params.get('module') or '').strip()
        if module:
            events = events.filter(module=module)
        entity_id = (request.query_params.get('entity_id') or '').strip()
        if entity_id:
            events = events.filter(entity_id=entity_id)
        outcome = (request.query_params.get('outcome') or '').strip()
        if outcome in ('success', 'failure'):
            events = events.filter(outcome=outcome)
        date_from = (request.query_params.get('from') or '').strip()
        date_to = (request.query_params.get('to') or '').strip()
        try:
            if date_from:
                events = events.filter(
                    created_at__date=date.fromisoformat(date_from))
            if date_to:
                events = events.filter(
                    created_at__date=date.fromisoformat(date_to))
        except ValueError:
            return Response({'error': 'Use fechas YYYY-MM-DD'},
                            status=status.HTTP_400_BAD_REQUEST)

        total = events.count()
        page, error = _query_int(request.query_params, 'page', 1)
        if error:
            return error
        page_size, error = _query_int(
            request.query_params, 'page_size', 50, maximum=200)
        if error:
            return error
        start = (page - 1) * page_size
        events = events[start:start + page_size]
        return Response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'results': [{
                'id': event.id,
                'action': event.action,
                'entity': event.entity,
                'entityId': event.entity_id,
                'module': event.module,
                'outcome': event.outcome,
                'requestId': event.request_id,
                'actor': event.actor.name if event.actor else 'Sistema',
                'before': event.before,
                'after': event.after,
                'ip': event.ip,
                'createdAt': event.created_at,
            } for event in events],
        })


class RoleListView(PermissionMixin, APIView):
    def get(self, request):
        error = self.check_permission(request, 'roles.roles.view')
        if error:
            return error
        roles = Role.objects.prefetch_related(
            'role_permissions__permission', 'user_assignments')
        include_inactive = request.query_params.get(
            'include_inactive', '').lower() in ('1', 'true', 'yes')
        if not include_inactive:
            roles = roles.filter(active=True)
        return Response(RoleSerializer(roles, many=True).data)

    def post(self, request):
        error = self.check_permission(request, 'roles.roles.create')
        if error:
            return error
        serializer = RoleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'fields': serializer.errors},
                            status=400)
        role = serializer.save(is_system_role=False, grants_full_access=False)
        try:
            self._set_permissions(role, request.data.get('permissionIds', []),
                                  request.user)
        except ValueError as exc:
            role.delete()
            return Response({'error': str(exc)}, status=400)
        record_audit(request, 'created', 'role', role.id, module='roles',
                     after={'code': role.code, 'name': role.name,
                            'permissions': sorted(
                                role.role_permissions.values_list(
                                    'permission__module',
                                    'permission__resource',
                                    'permission__action'))})
        return Response(RoleSerializer(role).data, status=201)

    @staticmethod
    def _set_permissions(role, permission_ids, actor=None):
        if permission_ids is None:
            return
        if role.is_system_role:
            raise ValueError('Los permisos de un rol protegido son de solo lectura.')
        permissions = list(Permission.objects.filter(
            id__in=permission_ids, active=True))
        if len(permissions) != len(set(permission_ids)):
            raise ValueError('Uno o más permisos no existen o están inactivos.')
        from .rbac import can_grant_permission
        if actor is not None:
            for permission in permissions:
                if not can_grant_permission(actor, permission):
                    raise ValueError(
                        f'No puedes asignar el permiso {permission.code}.')
        RolePermission.objects.filter(role=role).delete()
        for permission in permissions:
            RolePermission.objects.get_or_create(
                role=role, permission=permission)


class RoleDetailView(PermissionMixin, APIView):
    def get_object(self, pk):
        return Role.objects.filter(pk=pk).first()

    def get(self, request, pk):
        error = self.check_permission(request, 'roles.roles.view')
        if error:
            return error
        role = self.get_object(pk)
        if role is None:
            return Response({'error': 'Rol no encontrado'}, status=404)
        return Response(RoleSerializer(role).data)

    def put(self, request, pk):
        error = self.check_permission(request, 'roles.roles.change')
        if error:
            return error
        role = self.get_object(pk)
        if role is None:
            return Response({'error': 'Rol no encontrado'}, status=404)
        if role.is_system_role:
            return Response(
                {'error': 'El rol protegido no puede modificarse.'}, status=400)
        serializer = RoleSerializer(role, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'fields': serializer.errors},
                            status=400)
        before = {
            'name': role.name,
            'active': role.active,
            'permissions': sorted(role.role_permissions.values_list(
                'permission__module', 'permission__resource',
                'permission__action')),
        }
        try:
            role = serializer.save()
            RoleListView._set_permissions(
                role, request.data.get('permissionIds'), request.user)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=400)
        record_audit(
            request, 'updated', 'role', role.id, module='roles',
            before=before,
            after={
                'name': role.name,
                'active': role.active,
                'permissions': sorted(role.role_permissions.values_list(
                    'permission__module', 'permission__resource',
                    'permission__action')),
            })
        return Response(RoleSerializer(role).data)

    def delete(self, request, pk):
        error = self.check_permission(request, 'roles.roles.delete')
        if error:
            return error
        role = self.get_object(pk)
        if role is None:
            return Response({'error': 'Rol no encontrado'}, status=404)
        if role.is_system_role:
            return Response(
                {'error': 'El rol protegido no puede eliminarse.'}, status=400)
        if role.user_assignments.filter(active=True).exists():
            return Response(
                {'error': 'No se puede eliminar el rol porque tiene usuarios '
                          'asignados. Desactívelo en su lugar.'},
                status=status.HTTP_409_CONFLICT)
        role.active = False
        role.save(update_fields=['active', 'updated_at'])
        record_audit(request, 'deactivated', 'role', role.id, module='roles',
                     after={'active': False})
        return Response(status=status.HTTP_204_NO_CONTENT)


class TemporaryFunctionListView(PermissionMixin, APIView):
    def get(self, request):
        error = self.check_permission(request, 'temporary_assignments.view')
        if error:
            return error
        return Response(TemporaryFunctionSerializer(
            TemporaryFunction.objects.filter(active=True), many=True).data)


class UserRoleListView(PermissionMixin, APIView):
    def get(self, request, user_id):
        error = self.check_permission(request, 'roles.roles.view')
        if error:
            return error
        if not User.objects.filter(pk=user_id).exists():
            return Response({'error': 'Usuario no encontrado'}, status=404)
        assignments = UserRole.objects.filter(user_id=user_id).select_related('user', 'role')
        return Response(UserRoleSerializer(assignments, many=True).data)

    def post(self, request, user_id):
        error = self.check_permission(request, 'roles.roles.change')
        if error:
            return error
        user = User.objects.filter(pk=user_id).first()
        role = Role.objects.filter(pk=request.data.get('role'), active=True).first()
        if user is None or role is None:
            return Response({'error': 'Usuario o rol no encontrado'}, status=404)
        if role.is_system_role:
            return Response(
                {'error': 'Los roles protegidos se asignan mediante el flujo '
                          'especial de administración.'},
                status=status.HTTP_400_BAD_REQUEST)
        assignment, created = UserRole.objects.get_or_create(
            user=user, role=role, active=True,
            defaults={'assigned_by': request.user})
        if not created:
            return Response({'error': 'El usuario ya tiene ese rol activo'}, status=409)
        record_audit(request, 'assigned', 'user_role', assignment.id,
                     module='roles',
                     after={'user_id': user.id, 'role': role.code})
        return Response(UserRoleSerializer(assignment).data, status=201)


class UserRoleDetailView(PermissionMixin, APIView):
    def delete(self, request, pk):
        error = self.check_permission(request, 'roles.roles.change')
        if error:
            return error
        assignment = UserRole.objects.select_related('role', 'user').filter(pk=pk).first()
        if assignment is None:
            return Response({'error': 'Asignación de rol no encontrada'}, status=404)
        if assignment.role.grants_full_access:
            from .rbac import is_last_superadmin
            if is_last_superadmin(assignment.user):
                return Response(
                    {'error': 'No puedes revocar el acceso del último '
                              'administrador de sistemas activo.'},
                    status=status.HTTP_409_CONFLICT)
            if assignment.user_id == request.user.id:
                return Response(
                    {'error': 'No puedes revocar tu propio acceso total.'},
                    status=status.HTTP_400_BAD_REQUEST)
        assignment.active = False
        assignment.revoked_at = timezone.now()
        assignment.save(update_fields=['active', 'revoked_at'])
        assignment.user.bump_token_version()
        assignment.user.save(update_fields=['token_version', 'updated_at'])
        record_audit(request, 'revoked', 'user_role', assignment.id,
                     module='roles',
                     after={'user_id': assignment.user_id, 'role': assignment.role.code})
        return Response(status=204)


class TemporaryAssignmentListView(PermissionMixin, APIView):
    def get(self, request):
        error = self.check_permission(request, 'temporary_assignments.view')
        if error:
            return error
        assignments = TemporaryAssignment.objects.select_related(
            'user', 'function', 'assigned_by').all()
        return Response(TemporaryAssignmentSerializer(assignments, many=True).data)

    def post(self, request):
        error = self.check_permission(request, 'temporary_assignments.assign')
        if error:
            return error
        serializer = TemporaryAssignmentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=400)
        starts_at = serializer.validated_data['starts_at']
        ends_at = serializer.validated_data['ends_at']
        user = serializer.validated_data['user']
        function = serializer.validated_data['function']
        if starts_at >= ends_at:
            return Response({'error': 'El inicio debe ser anterior al fin'}, status=400)
        overlap = TemporaryAssignment.objects.filter(
            user=user, function=function,
            status__in=['scheduled', 'active'],
            starts_at__lt=ends_at, ends_at__gt=starts_at).exists()
        if overlap:
            return Response({'error': 'Existe una asignación temporal superpuesta'}, status=409)
        assignment = serializer.save(assigned_by=request.user)
        record_audit(request, 'created', 'temporary_assignment', assignment.id,
                     after={'user_id': user.id, 'function': function.code,
                            'starts_at': starts_at.isoformat(),
                            'ends_at': ends_at.isoformat()})
        return Response(TemporaryAssignmentSerializer(assignment).data, status=201)


class ExternalSellerListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        users = User.objects.filter(
            active=True,
            temporary_assignments__function__code='external_seller',
            temporary_assignments__function__active=True,
            temporary_assignments__status='active',
            temporary_assignments__starts_at__lte=now,
            temporary_assignments__ends_at__gte=now,
        ).distinct()
        return Response([
            {'id': user.id, 'name': user.name}
            for user in users.order_by('name', 'id')
        ])


class TemporaryAssignmentDetailView(PermissionMixin, APIView):
    def patch(self, request, pk):
        error = self.check_permission(request, 'temporary_assignments.assign')
        if error:
            return error
        assignment = TemporaryAssignment.objects.filter(pk=pk).first()
        if assignment is None:
            return Response({'error': 'Asignación no encontrada'}, status=404)
        new_status = request.data.get('status')
        if new_status not in {'finished', 'revoked'}:
            return Response({'error': 'Solo se puede finalizar o revocar'}, status=400)
        before = {'status': assignment.status}
        assignment.status = new_status
        assignment.finished_at = timezone.now()
        assignment.save(update_fields=['status', 'finished_at'])
        record_audit(request, new_status, 'temporary_assignment', assignment.id,
                     before=before, after={'status': new_status})
        return Response(TemporaryAssignmentSerializer(assignment).data)


@extend_schema(responses={200: dict})
class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'status': 'ok'})


@extend_schema(responses={200: dict, 503: dict})
class ReadyView(APIView):
    """Comprueba base y migraciones sin revelar detalles de infraestructura."""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            connection.ensure_connection()
            executor = MigrationExecutor(connection)
            if executor.migration_plan(executor.loader.graph.leaf_nodes()):
                return Response({'status': 'unavailable'}, status=503)
            return Response({'status': 'ok'})
        except Exception:
            return Response({'status': 'unavailable'}, status=503)


@extend_schema_view(
    post=extend_schema(request=dict, responses={200: dict, 400: dict, 401: dict}),
)
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        from .login_security import (
            client_ip, lockout_remaining, register_failure, register_success)
        from .models import normalize_user_name

        name = (request.data.get('name') or '').strip()
        password = request.data.get('password') or ''

        if not name:
            return Response({'error': 'Usuario requerido'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({'error': 'Contraseña requerida'},
                            status=status.HTTP_400_BAD_REQUEST)

        normalized = normalize_user_name(name)
        ip = client_ip(request)
        user = User.objects.filter(
            name_normalized=normalized, active=True).first()
        # Compatibilidad con usuarios creados/importados antes de que
        # ``name_normalized`` existiera o mediante una actualización directa.
        # No se usa una coincidencia parcial: el nombre sigue siendo exacto,
        # insensible a mayúsculas y espacios externos.
        if user is None:
            user = User.objects.filter(
                name__iexact=name, active=True).first()
            if user is not None and user.name_normalized != normalized:
                user.name_normalized = normalized
                user.save(update_fields=['name_normalized'])

        remaining = lockout_remaining(normalized, ip)
        if remaining:
            record_audit(
                request, 'login', 'user', user.pk if user else '', module='auth',
                outcome='failure', after={'reason': 'locked'})
            return Response(
                {'error': 'Demasiados intentos. Intente más tarde.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={'Retry-After': str(remaining)})

        if user is None or not user.check_password(password):
            register_failure(
                user, normalized, ip,
                request.META.get('HTTP_USER_AGENT', ''))
            record_audit(
                request, 'login', 'user', user.pk if user else '',
                module='auth', outcome='failure',
                after={'username': normalized})
            return Response({'error': 'Credenciales inválidas'},
                            status=status.HTTP_401_UNAUTHORIZED)

        register_success(
            user, normalized, ip, request.META.get('HTTP_USER_AGENT', ''))
        _, refresh = _issue_session_token(user)
        record_audit(
            request, 'login', 'user', user.pk, module='auth',
            actor=user, after={'username': user.name})
        return Response({
            'token': str(refresh.access_token),
            'user': _user_payload(user),
        })


@extend_schema(responses={200: dict, 401: dict})
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_id = request.auth.get('sid') if request.auth else None
        if session_id:
            updated = UserSession.objects.filter(
                session_id=session_id,
                user=request.user,
                revoked_at__isnull=True,
            ).update(
                revoked_at=timezone.now(),
                revoked_reason='logout',
            )
            return Response({'revoked': bool(updated)})
        # Tokens emitidos antes de las sesiones individuales siguen siendo
        # compatibles hasta expirar, pero nunca pueden revocar otra sesión.
        return Response({'revoked': False, 'legacy': True})


@extend_schema(responses={200: dict})
class MeView(APIView):
    def get(self, request):
        return Response({'user': _user_payload(request.user)})


@extend_schema_view(
    post=extend_schema(request=dict, responses={200: dict, 400: dict}),
)
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .passwords import (
            PasswordPolicyError, validate_password, validate_password_confirmation)

        current = request.data.get('current_password', '')
        new_password = request.data.get('new_password', '')
        confirmation = request.data.get(
            'new_password_confirm', request.data.get('confirm_password', ''))

        if not current or not new_password:
            return Response({'error': 'Completa ambos campos'},
                            status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user.check_password(current):
            return Response({'error': 'La contrasena actual es incorrecta'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password_confirmation(new_password, confirmation)
            validate_password(new_password, user)
        except PasswordPolicyError as exc:
            return Response({'error': str(exc)},
                            status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user.set_password(new_password)
            user.save(update_fields=[
                'password', 'password_changed_at', 'token_version',
                'must_change_password', 'updated_at'])
            UserSession.objects.filter(
                user=user, revoked_at__isnull=True).update(
                    revoked_at=timezone.now(),
                    revoked_reason='password_changed',
                )
            _, refresh = _issue_session_token(user)
        record_audit(
            request, 'password_changed', 'user', user.pk, module='auth',
            after={'must_change_password': False})
        return Response({
            'message': 'Contrasena actualizada correctamente',
            'token': str(refresh.access_token),
            'user': _user_payload(user),
        })


@extend_schema_view(
    get=extend_schema(responses={200: PlanSerializer(many=True)}),
    post=extend_schema(request=PlanSerializer, responses={201: PlanSerializer, 400: dict}),
)
class PlanListView(IsAdminMixin, APIView):
    permission_code = 'commercial_config.manage'
    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error
        return Response(PlanSerializer(Plan.objects.all().order_by('type', 'code'), many=True).data)

    def post(self, request):
        error = self.check_admin(request)
        if error:
            return error
        serializer = PlanSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': _first_error(serializer)}, status=status.HTTP_400_BAD_REQUEST)
        plan = serializer.save()
        from .audit import record_audit
        record_audit(request, 'created', 'plan', plan.id,
                     after={'code': plan.code, 'type': plan.type,
                            'active': plan.active, 'legacy': plan.legacy})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    put=extend_schema(request=PlanSerializer, responses={200: PlanSerializer, 400: dict, 404: dict}),
    delete=extend_schema(responses={204: None, 400: dict, 404: dict}),
)
class PlanDetailView(IsAdminMixin, APIView):
    permission_code = 'commercial_config.manage'
    def _get_plan(self, pk):
        try:
            return Plan.objects.get(id=pk)
        except Plan.DoesNotExist:
            return None

    def delete(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        plan = self._get_plan(pk)
        if not plan:
            return Response({'error': 'Plan no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        plan.active = False
        plan.save(update_fields=['active'])
        from .audit import record_audit
        record_audit(request, 'deactivated', 'plan', pk,
                     after={'active': False})
        return Response(status=status.HTTP_204_NO_CONTENT)

    def put(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        plan = self._get_plan(pk)
        if not plan:
            return Response({'error': 'Plan no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        serializer = PlanSerializer(plan, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'error': _first_error(serializer)}, status=status.HTTP_400_BAD_REQUEST)
        before = {'code': plan.code, 'type': plan.type,
                  'active': plan.active, 'legacy': plan.legacy}
        serializer.save()
        from .audit import record_audit
        record_audit(request, 'updated', 'plan', plan.id, before=before,
                     after={'code': plan.code, 'type': plan.type,
                            'active': plan.active, 'legacy': plan.legacy})
        return Response(serializer.data)


@extend_schema(responses={200: PlanPublicSerializer(many=True)})
class ActivePlansView(APIView):
    def get(self, request):
        plans = Plan.objects.filter(active=True).order_by('type', 'code')
        return Response(PlanPublicSerializer(plans, many=True).data)


class ActiveCoverageZoneListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        zones = CoverageZone.objects.all()
        if request.query_params.get('active', '').lower() in {'true', '1'}:
            zones = zones.filter(is_active=True)
        return Response(CoverageZoneSerializer(zones, many=True).data)


class CoverageZoneAdminListView(IsAdminMixin, APIView):
    permission_code = 'coverage.manage'

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error
        zones = CoverageZone.objects.all()
        return Response(CoverageZoneSerializer(zones, many=True).data)

    def post(self, request):
        if not has_permission(request.user, 'coverage.create'):
            return Response(
                {'error': 'No tienes permiso para realizar esta operación'},
                status=status.HTTP_403_FORBIDDEN)
        if not request.data.get('google_maps_url'):
            return Response(
                {'error': 'La URL de Google Maps es obligatoria'},
                status=status.HTTP_400_BAD_REQUEST)
        serializer = CoverageZoneSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': _first_error(serializer)},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            zone = serializer.save(created_by=request.user, is_active=True)
        except IntegrityError:
            return Response(
                {'error': 'Ya existe una zona con ese nombre'},
                status=status.HTTP_400_BAD_REQUEST)
        record_audit(
            request, 'created', 'coverage_zone', zone.id,
            after={
                'name': zone.name,
                'google_maps_url': zone.google_maps_url,
                'is_active': zone.is_active,
            })
        return Response(
            CoverageZoneSerializer(zone).data,
            status=status.HTTP_201_CREATED)


class CoverageZoneDetailView(IsAdminMixin, APIView):
    permission_code = 'coverage.manage'

    def patch(self, request, pk):
        permission_code = (
            'coverage.manage' if 'is_active' in request.data
            else 'coverage.change')
        if not (has_permission(request.user, permission_code)
                or has_permission(request.user, 'coverage.manage')):
            return Response(
                {'error': 'No tienes permiso para realizar esta operación'},
                status=status.HTTP_403_FORBIDDEN)
        try:
            zone = CoverageZone.objects.get(pk=pk)
        except CoverageZone.DoesNotExist:
            return Response(
                {'error': 'Zona de cobertura no encontrada'},
                status=status.HTTP_404_NOT_FOUND)

        before = {
            'name': zone.name,
            'google_maps_url': zone.google_maps_url,
            'is_active': zone.is_active,
        }
        serializer = CoverageZoneSerializer(
            zone, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'error': _first_error(serializer)},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            zone = serializer.save()
        except IntegrityError:
            return Response(
                {'error': 'Ya existe una zona con ese nombre'},
                status=status.HTTP_400_BAD_REQUEST)
        record_audit(
            request, 'updated', 'coverage_zone', zone.id,
            before=before,
            after={
                'name': zone.name,
                'google_maps_url': zone.google_maps_url,
                'is_active': zone.is_active,
            })
        return Response(CoverageZoneSerializer(zone).data)


@extend_schema(responses={200: TipoSolicitudPublicSerializer(many=True)})
class ActiveRequestTypesView(APIView):
    """Catalogo para el formulario de movimientos.

    Sin IsAdminMixin, igual que ActivePlansView: el operador registra
    movimientos y necesita los tipos, aunque no pueda administrarlos.
    """

    def get(self, request):
        return Response(TipoSolicitudPublicSerializer(
            TipoSolicitud.objects.filter(activo=True), many=True).data)


@extend_schema_view(
    get=extend_schema(responses={200: MotivoSerializer(many=True)}),
    post=extend_schema(request=MotivoSerializer, responses={201: MotivoSerializer, 400: dict}),
)
class MotivoListView(IsAdminMixin, APIView):
    permission_code = 'commercial_config.manage'
    """Catalogo administrable de motivos (solo administradores)."""

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error
        categoria = request.query_params.get('categoria')
        qs = Motivo.objects.all()
        if categoria:
            qs = qs.filter(categoria=categoria)
        return Response(MotivoSerializer(qs, many=True).data)

    def post(self, request):
        error = self.check_admin(request)
        if error:
            return error
        serializer = MotivoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': _first_error(serializer)},
                            status=status.HTTP_400_BAD_REQUEST)
        motivo = serializer.save()
        from .audit import record_audit
        record_audit(request, 'created', 'motivo', motivo.id,
                     after={'categoria': motivo.categoria,
                            'activo': motivo.activo})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(responses={200: MotivoPublicSerializer(many=True)})
class ActiveMotivosView(APIView):
    """Motivos activos para el formulario de movimientos.

    Sin IsAdminMixin: el operador necesita los motivos aunque no pueda
    administrarlos. `?categoria=cambio|retiro` filtra por formulario.
    """

    def get(self, request):
        qs = Motivo.objects.filter(activo=True)
        categoria = request.query_params.get('categoria')
        if categoria in ('cambio', 'retiro'):
            qs = qs.filter(categoria=categoria)
        return Response(MotivoPublicSerializer(qs, many=True).data)


@extend_schema_view(
    put=extend_schema(request=MotivoSerializer, responses={200: MotivoSerializer, 400: dict, 404: dict}),
    delete=extend_schema(responses={204: None, 400: dict, 404: dict}),
)
class MotivoDetailView(IsAdminMixin, APIView):
    permission_code = 'commercial_config.manage'
    def _get_motivo(self, pk):
        try:
            return Motivo.objects.get(id=pk)
        except Motivo.DoesNotExist:
            return None

    def delete(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        motivo = self._get_motivo(pk)
        if not motivo:
            return Response({'error': 'Motivo no encontrado'},
                            status=status.HTTP_404_NOT_FOUND)
        motivo.activo = False
        motivo.save(update_fields=['activo'])
        from .audit import record_audit
        record_audit(request, 'deactivated', 'motivo', pk,
                     after={'activo': False})
        return Response(status=status.HTTP_204_NO_CONTENT)

    def put(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        motivo = self._get_motivo(pk)
        if not motivo:
            return Response({'error': 'Motivo no encontrado'},
                            status=status.HTTP_404_NOT_FOUND)
        serializer = MotivoSerializer(motivo, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'error': _first_error(serializer)},
                            status=status.HTTP_400_BAD_REQUEST)
        before = {'categoria': motivo.categoria, 'activo': motivo.activo}
        serializer.save()
        from .audit import record_audit
        record_audit(request, 'updated', 'motivo', motivo.id, before=before,
                     after={'categoria': motivo.categoria,
                            'activo': motivo.activo})
        return Response(serializer.data)


@extend_schema_view(
    get=extend_schema(responses={200: CanalCaptacionSerializer(many=True)}),
    post=extend_schema(request=CanalCaptacionSerializer,
                       responses={201: CanalCaptacionSerializer, 400: dict}),
)
class CanalCaptacionListView(PermissionMixin, APIView):
    """Catalogo administrable de canales de captacion."""

    def get(self, request):
        error = self.check_permission(request, 'captacion.view')
        if error:
            return error
        return Response(CanalCaptacionSerializer(
            CanalCaptacion.objects.all(), many=True).data)

    def post(self, request):
        error = self.check_permission(request, 'captacion.manage')
        if error:
            return error
        serializer = CanalCaptacionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': _first_error(serializer)},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            canal = serializer.save()
        except IntegrityError:
            return Response(
                {'error': 'Ya existe un canal con ese nombre'},
                status=status.HTTP_400_BAD_REQUEST)
        record_audit(request, 'created', 'canal_captacion', canal.id,
                     after={'nombre': canal.nombre, 'activo': canal.activo})
        return Response(CanalCaptacionSerializer(canal).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(responses={200: CanalCaptacionPublicSerializer(many=True)})
class ActiveCanalesCaptacionView(APIView):
    """Canales activos para el selector "¿Como nos conocio?".

    Sin permisos administrativos: el operador que registra solicitudes
    necesita el catalogo aunque no pueda modificarlo.
    """

    def get(self, request):
        return Response(CanalCaptacionPublicSerializer(
            CanalCaptacion.objects.filter(activo=True), many=True).data)


@extend_schema_view(
    put=extend_schema(request=CanalCaptacionSerializer,
                      responses={200: CanalCaptacionSerializer, 400: dict, 404: dict}),
    patch=extend_schema(request=CanalCaptacionSerializer,
                        responses={200: CanalCaptacionSerializer, 400: dict, 404: dict}),
    delete=extend_schema(responses={204: None, 404: dict}),
)
class CanalCaptacionDetailView(PermissionMixin, APIView):
    """Edita o desactiva un canal. Nunca se borra fisicamente."""

    def _get_canal(self, pk):
        return CanalCaptacion.objects.filter(pk=pk).first()

    def put(self, request, pk):
        return self._update(request, pk, partial=False)

    def patch(self, request, pk):
        return self._update(request, pk, partial=True)

    def _update(self, request, pk, partial):
        error = self.check_permission(request, 'captacion.manage')
        if error:
            return error
        canal = self._get_canal(pk)
        if canal is None:
            return Response({'error': 'Canal de captacion no encontrado'},
                            status=status.HTTP_404_NOT_FOUND)
        serializer = CanalCaptacionSerializer(
            canal, data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response({'error': _first_error(serializer)},
                            status=status.HTTP_400_BAD_REQUEST)
        before = {'nombre': canal.nombre, 'activo': canal.activo,
                  'descripcion': canal.descripcion}
        try:
            canal = serializer.save()
        except IntegrityError:
            return Response(
                {'error': 'Ya existe un canal con ese nombre'},
                status=status.HTTP_400_BAD_REQUEST)
        record_audit(request, 'updated', 'canal_captacion', canal.id,
                     before=before,
                     after={'nombre': canal.nombre, 'activo': canal.activo,
                            'descripcion': canal.descripcion})
        return Response(CanalCaptacionSerializer(canal).data)

    def delete(self, request, pk):
        error = self.check_permission(request, 'captacion.manage')
        if error:
            return error
        canal = self._get_canal(pk)
        if canal is None:
            return Response({'error': 'Canal de captacion no encontrado'},
                            status=status.HTTP_404_NOT_FOUND)
        if not canal.activo:
            return Response(status=status.HTTP_204_NO_CONTENT)
        canal.activo = False
        canal.save(update_fields=['activo', 'updated_at'])
        record_audit(request, 'deactivated', 'canal_captacion', canal.id,
                     before={'activo': True}, after={'activo': False})
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    get=extend_schema(responses={200: PromotionSerializer(many=True)}),
    post=extend_schema(request=PromotionWriteSerializer, responses={201: PromotionSerializer, 400: dict}),
)
class PromotionListView(IsAdminMixin, APIView):
    permission_code = 'commercial_config.manage'
    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error
        plan_id = request.query_params.get('plan_id')
        qs = Promotion.objects.select_related('plan').all().order_by('-start_date', '-id')
        if plan_id:
            qs = qs.filter(plan_id=plan_id)
        return Response(PromotionSerializer(qs, many=True).data)

    def post(self, request):
        error = self.check_admin(request)
        if error:
            return error
        serializer = PromotionWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': _first_error(serializer)},
                            status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        plan = data.pop('plan')

        # Check for conflicting promotions
        conflict = Promotion.objects.filter(
            plan=plan, active=True,
            start_date__lte=data['end_date'],
            end_date__gte=data['start_date'],
        )
        if data.get('apply_installation'):
            conflict = conflict.filter(apply_installation=True)
        elif data.get('apply_monthly'):
            conflict = conflict.filter(apply_monthly=True)
        if conflict.exists():
            return Response(
                {'error': 'Ya existe una promocion activa para este concepto en el periodo seleccionado'},
                status=status.HTTP_400_BAD_REQUEST)

        promo = Promotion.objects.create(
            plan=plan,
            created_by=request.user,
            **data,
        )
        from .audit import record_audit
        record_audit(request, 'created', 'promotion', promo.id,
                     after={'plan_id': promo.plan_id, 'active': promo.active,
                            'start_date': promo.start_date.isoformat(),
                            'end_date': promo.end_date.isoformat()})
        return Response(PromotionSerializer(promo).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    put=extend_schema(request=PromotionWriteSerializer, responses={200: PromotionSerializer, 400: dict, 404: dict}),
    delete=extend_schema(responses={204: None, 400: dict, 404: dict}),
)
class PromotionDetailView(IsAdminMixin, APIView):
    permission_code = 'commercial_config.manage'
    def _get_promo(self, pk):
        try:
            return Promotion.objects.get(id=pk)
        except Promotion.DoesNotExist:
            return None

    def put(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        promo = self._get_promo(pk)
        if not promo:
            return Response({'error': 'Promocion no encontrada'},
                            status=status.HTTP_404_NOT_FOUND)

        data = request.data

        # Simple toggle (active only) — skip full serializer
        if set(data.keys()) <= {'active'}:
            before = {'active': promo.active}
            promo.active = data.get('active', promo.active)
            promo.save()
            from .audit import record_audit
            record_audit(request, 'updated', 'promotion', promo.id,
                         before=before, after={'active': promo.active})
            return Response(PromotionSerializer(promo).data)

        serializer = PromotionWriteSerializer(data=data, partial=True)
        if not serializer.is_valid():
            return Response({'error': _first_error(serializer)},
                            status=status.HTTP_400_BAD_REQUEST)
        data = serializer.validated_data
        plan = data.pop('plan', promo.plan)

        # Check conflicts excluding current promo
        start = data.get('start_date', promo.start_date)
        end = data.get('end_date', promo.end_date)
        apply_inst = data.get('apply_installation', promo.apply_installation)
        apply_month = data.get('apply_monthly', promo.apply_monthly)
        conflict = Promotion.objects.filter(
            plan=plan, active=True,
            start_date__lte=end, end_date__gte=start,
        ).exclude(id=promo.id)
        if apply_inst:
            conflict = conflict.filter(apply_installation=True)
        elif apply_month:
            conflict = conflict.filter(apply_monthly=True)
        if conflict.exists():
            return Response(
                {'error': 'Ya existe una promocion activa para este concepto en el periodo seleccionado'},
                status=status.HTTP_400_BAD_REQUEST)

        before = {'plan_id': promo.plan_id, 'active': promo.active,
                  'start_date': promo.start_date.isoformat(),
                  'end_date': promo.end_date.isoformat()}
        if 'name' in data:
            promo.name = data['name']
        promo.plan = plan
        if 'apply_installation' in data:
            promo.apply_installation = data['apply_installation']
        if 'apply_monthly' in data:
            promo.apply_monthly = data['apply_monthly']
        if 'installation_price' in data:
            promo.installation_price = data['installation_price']
        if 'monthly_price' in data:
            promo.monthly_price = data['monthly_price']
        if 'start_date' in data:
            promo.start_date = data['start_date']
        if 'end_date' in data:
            promo.end_date = data['end_date']
        if 'active' in data:
            promo.active = data['active']
        promo.save()
        from .audit import record_audit
        record_audit(request, 'updated', 'promotion', promo.id,
                     before=before,
                     after={'plan_id': promo.plan_id, 'active': promo.active,
                            'start_date': promo.start_date.isoformat(),
                            'end_date': promo.end_date.isoformat()})
        return Response(PromotionSerializer(promo).data)

    def delete(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        promo = self._get_promo(pk)
        if not promo:
            return Response({'error': 'Promocion no encontrada'},
                            status=status.HTTP_404_NOT_FOUND)
        promo.active = False
        promo.save(update_fields=['active'])
        from .audit import record_audit
        record_audit(request, 'deactivated', 'promotion', pk,
                     after={'active': False})
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(responses={200: PromotionSerializer(many=True), 400: dict})
class ActivePromotionsView(APIView):
    """Promociones vigentes para un plan (cualquier usuario autenticado)."""
    def get(self, request):
        plan_id = request.query_params.get('plan_id')
        if not plan_id:
            return Response({'error': 'plan_id requerido'},
                            status=status.HTTP_400_BAD_REQUEST)
        from django.utils import timezone as tz
        today = tz.localdate()
        promos = Promotion.objects.filter(
            plan_id=plan_id, active=True,
            plan__active=True, plan__legacy=False,
            start_date__lte=today, end_date__gte=today,
        ).order_by('-start_date')
        return Response(PromotionSerializer(promos, many=True).data)


@extend_schema(responses={200: TarifaTrasladoSerializer(many=True)})
class ActiveTransferTariffsView(APIView):
    """Tarifas vigentes para operadores y formularios comerciales."""
    def get(self, request):
        tariffs = TarifaTraslado.objects.filter(active=True)
        return Response(TarifaTrasladoSerializer(tariffs, many=True).data)


@extend_schema_view(
    get=extend_schema(responses={200: TarifaTrasladoSerializer(many=True)}),
    post=extend_schema(request=dict, responses={201: TarifaTrasladoSerializer, 400: dict}),
)
class TransferTariffListView(IsAdminMixin, APIView):
    permission_code = 'commercial_config.manage'
    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error
        return Response(TarifaTrasladoSerializer(
            TarifaTraslado.objects.all(), many=True).data)

    def post(self, request):
        error = self.check_admin(request)
        if error:
            return error
        data = request.data
        try:
            amount = Decimal(str(data.get('amount')))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'error': 'Importe no valido'}, status=400)
        if amount < 0:
            return Response({'error': 'El importe no puede ser negativo'}, status=400)
        if TarifaTraslado.objects.filter(service_type=data.get('service_type')).exists():
            return Response({'error': 'Ya existe una tarifa para este servicio'}, status=400)
        tariff = TarifaTraslado.objects.create(
            service_type=data.get('service_type'),
            name=data.get('name', ''),
            amount=amount,
            active=data.get('active', True),
            created_by=request.user,
            updated_by=request.user,
        )
        TarifaTrasladoHistorial.objects.create(
            tarifa=tariff, previous_amount=amount, new_amount=amount,
            previous_active=tariff.active, new_active=tariff.active,
            action='created', changed_by=request.user)
        from .audit import record_audit
        record_audit(request, 'created', 'transfer_tariff', tariff.id,
                     after={'service_type': tariff.service_type,
                            'amount': str(tariff.amount),
                            'active': tariff.active})
        return Response(TarifaTrasladoSerializer(tariff).data, status=201)


@extend_schema_view(
    get=extend_schema(responses={200: TarifaTrasladoSerializer, 400: dict, 404: dict}),
    put=extend_schema(request=dict, responses={200: TarifaTrasladoSerializer, 400: dict, 404: dict}),
)
class TransferTariffDetailView(IsAdminMixin, APIView):
    permission_code = 'commercial_config.manage'
    def _get(self, pk):
        try:
            return TarifaTraslado.objects.get(pk=pk)
        except TarifaTraslado.DoesNotExist:
            return None

    def put(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        tariff = self._get(pk)
        if tariff is None:
            return Response({'error': 'Tarifa no encontrada'}, status=404)
        data = request.data
        if 'name' in data and data.get('name') != tariff.name:
            return Response(
                {'error': 'El nombre de la tarifa no se puede modificar'},
                status=status.HTTP_400_BAD_REQUEST)
        try:
            amount = Decimal(str(data.get('amount', tariff.amount)))
        except (InvalidOperation, TypeError, ValueError):
            return Response({'error': 'Importe no valido'}, status=400)
        if amount < 0:
            return Response({'error': 'El importe no puede ser negativo'}, status=400)
        old_amount, old_active = tariff.amount, tariff.active
        tariff.name = data.get('name', tariff.name)
        tariff.amount = amount
        tariff.active = data.get('active', tariff.active)
        tariff.updated_by = request.user
        tariff.save()
        if old_amount != tariff.amount or old_active != tariff.active:
            TarifaTrasladoHistorial.objects.create(
                tarifa=tariff, previous_amount=old_amount,
                new_amount=tariff.amount, previous_active=old_active,
                new_active=tariff.active, action='updated',
                changed_by=request.user)
            from .audit import record_audit
            record_audit(
                request, 'updated', 'transfer_tariff', tariff.id,
                before={'amount': str(old_amount), 'active': old_active},
                after={'amount': str(tariff.amount), 'active': tariff.active})
        return Response(TarifaTrasladoSerializer(tariff).data)

    def get(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        tariff = self._get(pk)
        if tariff is None:
            return Response({'error': 'Tarifa no encontrada'}, status=404)
        return Response(TarifaTrasladoSerializer(tariff).data)


@extend_schema(responses={200: TarifaTrasladoHistorialSerializer(many=True), 404: dict})
class TransferTariffHistoryView(IsAdminMixin, APIView):
    permission_code = 'commercial_config.view'
    def get(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        if not TarifaTraslado.objects.filter(pk=pk).exists():
            return Response({'error': 'Tarifa no encontrada'}, status=404)
        history = TarifaTrasladoHistorial.objects.filter(tarifa_id=pk)
        return Response(TarifaTrasladoHistorialSerializer(history, many=True).data)


@extend_schema(responses={200: CustomerSerializer(many=True)})
class CustomerListView(APIView):
    """Busqueda de clientes por kardex o nombre (para autocompletar)."""
    def get(self, request):
        q = request.query_params.get('q', '').strip()
        qs = Customer.objects.all().order_by('name', 'code')
        if q:
            qs = qs.filter(
                Q(code__icontains=q) | Q(name__icontains=q)
                | Q(ci__icontains=q) | Q(phone__icontains=q)
                | Q(contracts__meter_number__icontains=q)
            ).distinct()
        return Response(CustomerSerializer(qs[:20], many=True).data)


def _maps_url_coordinates(value):
    """Extrae coordenadas de formatos comunes de Google Maps, si existen."""
    parsed = urlparse(value)
    host = (parsed.hostname or '').lower()
    valid_hosts = ('google.com', 'www.google.com', 'maps.google.com',
                   'goo.gl', 'maps.app.goo.gl')
    if parsed.scheme != 'https' or not any(host == item or host.endswith('.' + item) for item in valid_hosts):
        raise ValueError('La URL debe ser un enlace HTTPS válido de Google Maps')
    text = parsed.path + '?' + parsed.query
    patterns = [
        r'@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)',
        r'!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return Decimal(match.group(1)), Decimal(match.group(2))
    query = parse_qs(parsed.query).get('q', [])
    if query:
        match = re.match(r'^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)', query[0])
        if match:
            return Decimal(match.group(1)), Decimal(match.group(2))
    return None, None


def _location_values(data, current=None):
    """Valida la ubicación recibida y devuelve valores normalizados."""
    source = data.get('source') or (current.source if current else '')
    maps_url = (data.get('maps_url') if 'maps_url' in data else (current.maps_url if current else '')) or ''
    latitude = data.get('latitude') if 'latitude' in data else (current.latitude if current else None)
    longitude = data.get('longitude') if 'longitude' in data else (current.longitude if current else None)
    accuracy = data.get('accuracy_meters') if 'accuracy_meters' in data else (current.accuracy_meters if current else None)
    captured_at = data.get('captured_at') if 'captured_at' in data else (current.captured_at if current else None)
    if source == CustomerLocation.SOURCE_MAPS_URL:
        if not maps_url:
            raise ValueError('Pega una URL de Google Maps')
        url_lat, url_lng = _maps_url_coordinates(maps_url)
        latitude = latitude if latitude is not None else url_lat
        longitude = longitude if longitude is not None else url_lng
    elif source == CustomerLocation.SOURCE_GPS:
        if latitude in (None, '') or longitude in (None, ''):
            raise ValueError('La ubicación GPS está incompleta')
        try:
            latitude, longitude = Decimal(str(latitude)), Decimal(str(longitude))
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                raise ValueError
        except (InvalidOperation, ValueError):
            raise ValueError('Las coordenadas GPS no son válidas')
    else:
        raise ValueError('Indica si la ubicación proviene de GPS o Google Maps')
    if accuracy not in (None, ''):
        try:
            accuracy = Decimal(str(accuracy))
            if accuracy < 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            raise ValueError('La precisión GPS no es válida')
    if isinstance(captured_at, str):
        captured_at = parse_datetime(captured_at)
        if captured_at is None:
            raise ValueError('La fecha de captura no es válida')
    return {
        'source': source, 'maps_url': maps_url,
        'latitude': latitude, 'longitude': longitude,
        'accuracy_meters': accuracy, 'captured_at': captured_at,
    }


class CustomerLocationListView(PermissionMixin, APIView):
    permission_code = 'ubicaciones.clientes.view'

    def get(self, request):
        error = self.check_permission(request)
        if error:
            return error
        query = (request.query_params.get('q') or '').strip()
        customers = Customer.objects.filter(active=True)
        if query:
            customers = customers.filter(Q(code__icontains=query) | Q(name__icontains=query))
        locations = CustomerLocation.objects.filter(customer__in=customers).select_related(
            'customer', 'created_by', 'updated_by').order_by('-updated_at')[:20]
        return Response(CustomerLocationSerializer(locations, many=True).data)


class CustomerLocationDetailView(PermissionMixin, APIView):
    permission_code = 'ubicaciones.clientes.view'
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, pk, lock=False):
        qs = CustomerLocation.objects.select_related(
            'customer', 'created_by', 'updated_by')
        if lock:
            qs = qs.select_for_update()
        return qs.filter(pk=pk).first()

    def get(self, request, pk):
        error = self.check_permission(request)
        if error:
            return error
        location = self.get_object(pk)
        if location is None:
            return Response({'error': 'Ubicación no encontrada'}, status=404)
        return Response(CustomerLocationSerializer(location).data)

    def patch(self, request, pk):
        error = self.check_permission(request, 'ubicaciones.clientes.change')
        if error:
            return error
        with transaction.atomic():
            location = self.get_object(pk, lock=True)
            if location is None:
                return Response({'error': 'Ubicación no encontrada'}, status=404)
            try:
                values = _location_values(request.data, location)
                photo = request.FILES.get('photo')
                new_photo_path = location.photo_path
                if photo:
                    content, content_type = optimize_photo(photo)
                    new_photo_path = upload_photo(content, content_type, location.customer_id)
            except (ValueError, RuntimeError) as exc:
                return Response({'error': str(exc)}, status=400 if isinstance(exc, ValueError) else 503)
            before = CustomerLocationSerializer(location).data
            previous_photo_path = location.photo_path
            for key, value in values.items():
                setattr(location, key, value)
            location.photo_path = new_photo_path
            location.updated_by = request.user
            location.save()
            CustomerLocationHistory.objects.create(
                location=location, changed_by=request.user, change_type='updated',
                previous_photo_path=previous_photo_path,
                new_photo_path=new_photo_path,
                previous_latitude=before.get('latitude'), previous_longitude=before.get('longitude'),
                previous_accuracy_meters=before.get('accuracy_meters'), previous_maps_url=before.get('maps_url', ''),
                previous_source=before.get('source', ''), new_latitude=location.latitude,
                new_longitude=location.longitude, new_accuracy_meters=location.accuracy_meters,
                new_maps_url=location.maps_url, new_source=location.source)
            record_audit(request, 'updated', 'customer_location', location.id,
                         module='ubicaciones', before=before,
                         after={'customer_id': location.customer_id, 'source': location.source})
        return Response(CustomerLocationSerializer(location).data)


class CustomerLocationCreateView(PermissionMixin, APIView):
    permission_code = 'ubicaciones.clientes.create'
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        error = self.check_permission(request)
        if error:
            return error
        customer_id = request.data.get('customer')
        try:
            customer = Customer.objects.get(pk=customer_id, active=True)
        except (Customer.DoesNotExist, TypeError, ValueError):
            return Response({'error': 'Cliente no encontrado'}, status=404)
        if CustomerLocation.objects.filter(customer=customer).exists():
            return Response({'error': 'El cliente ya tiene una ubicación; usa actualizar'}, status=409)
        photo = request.FILES.get('photo')
        if not photo:
            return Response({'error': 'La fotografía de fachada es obligatoria'}, status=400)
        try:
            values = _location_values(request.data)
            content, content_type = optimize_photo(photo)
            photo_path = upload_photo(content, content_type, customer.id)
        except (ValueError, RuntimeError) as exc:
            return Response({'error': str(exc)}, status=400 if isinstance(exc, ValueError) else 503)
        with transaction.atomic():
            location = CustomerLocation.objects.create(
                customer=customer, photo_path=photo_path, created_by=request.user,
                updated_by=request.user, **values)
            CustomerLocationHistory.objects.create(
                location=location, changed_by=request.user, change_type='created',
                new_photo_path=photo_path, new_latitude=location.latitude,
                new_longitude=location.longitude, new_accuracy_meters=location.accuracy_meters,
                new_maps_url=location.maps_url, new_source=location.source)
            record_audit(request, 'created', 'customer_location', location.id,
                         module='ubicaciones', after={'customer_id': customer.id})
        return Response(CustomerLocationSerializer(location).data, status=201)


class CustomerLocationHistoryView(PermissionMixin, APIView):
    permission_code = 'ubicaciones.historial.view'

    def get(self, request, pk):
        error = self.check_permission(request)
        if error:
            return error
        if not CustomerLocation.objects.filter(pk=pk).exists():
            return Response({'error': 'Ubicación no encontrada'}, status=404)
        history = CustomerLocationHistory.objects.filter(location_id=pk).select_related('changed_by')
        return Response(CustomerLocationHistorySerializer(history, many=True).data)


class CustomerDetailView(APIView):
    """Ficha consolidada del cliente: contratos y movimientos reales."""

    def get_customer(self, pk):
        return Customer.objects.prefetch_related(
            'contracts__plan', 'contracts__sale', 'contracts__created_by',
            'contracts__meter_reviewed_by',
        ).filter(pk=pk).first()

    def get(self, request, pk):
        customer = self.get_customer(pk)
        if customer is None:
            return Response({'error': 'Cliente no encontrado'}, status=404)

        contracts = list(customer.contracts.all())
        meter_numbers = {c.meter_number for c in contracts if c.meter_number}
        matching = Contract.objects.filter(
            meter_number__in=meter_numbers
        ).exclude(customer_id=customer.id).select_related(
            'customer', 'plan')
        matches_by_meter = {}
        for contract in matching:
            matches_by_meter.setdefault(contract.meter_number, []).append({
                'id': contract.id,
                'number': contract.number,
                'customerId': contract.customer_id,
                'customerName': contract.customer.name,
                'status': contract.status,
            })

        contract_data = ContractSerializer(contracts, many=True).data
        for item in contract_data:
            item['meterMatches'] = matches_by_meter.get(item['meter_number'], [])

        sales = Sale.objects.filter(customer=customer).select_related(
            'plan', 'planFromId', 'createdBy', 'coverage_zone', 'canal_captacion'
        ).order_by('-date', '-id')
        timeline = SaleSerializer(
            sales, many=True, context={'catalog': request_type_catalog()}).data
        return Response({
            'customer': CustomerSerializer(customer).data,
            'summary': {
                'contracts': len(contracts),
                'meters': len({c.meter_number for c in contracts if c.meter_number}),
                'movements': sales.count(),
            },
            'contracts': contract_data,
            'timeline': timeline,
        })

    def put(self, request, pk):
        if not has_permission(request.user, 'customers.change'):
            return Response(
                {'error': 'Solo administradores pueden editar clientes'}, status=403)
        customer = self.get_customer(pk)
        if customer is None:
            return Response({'error': 'Cliente no encontrado'}, status=404)
        serializer = CustomerSerializer(customer, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=400)
        before = CustomerSerializer(customer).data
        customer = serializer.save()
        from .audit import record_audit
        record_audit(
            request, 'updated', 'customer', customer.id,
            before=before, after=CustomerSerializer(customer).data)
        return Response(CustomerSerializer(customer).data)


class ContractMeterReviewView(IsAdminMixin, APIView):
    """Registra la comprobación manual del medidor en el otro sistema."""

    def patch(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        contract = Contract.objects.filter(pk=pk).first()
        if contract is None:
            return Response({'error': 'Contrato no encontrado'}, status=404)
        review_status = request.data.get('meter_review_status')
        if review_status not in {'pendiente', 'verificado', 'observado'}:
            return Response(
                {'error': 'Estado de revisión inválido'}, status=400)
        notes = (request.data.get('meter_review_notes') or '').strip()
        before = {
            'meter_review_status': contract.meter_review_status,
            'meter_review_notes': contract.meter_review_notes,
        }
        contract.meter_review_status = review_status
        contract.meter_review_notes = notes
        contract.meter_reviewed_by = request.user
        contract.meter_reviewed_at = timezone.now()
        contract.save(update_fields=[
            'meter_review_status', 'meter_review_notes',
            'meter_reviewed_by', 'meter_reviewed_at',
        ])
        from .audit import record_audit
        record_audit(
            request, 'reviewed', 'contract', contract.id,
            before=before,
            after={
                'meter_review_status': contract.meter_review_status,
                'meter_review_notes': contract.meter_review_notes,
            })
        return Response(ContractSerializer(contract).data)


class ContractMeterUpdateView(APIView):
    """Permite que cualquier operador autenticado registre el medidor."""

    def patch(self, request, pk):
        contract = Contract.objects.filter(pk=pk).first()
        if contract is None:
            return Response({'error': 'Contrato no encontrado'}, status=404)
        meter_number = (request.data.get('meter_number') or '').strip() or None
        before = {'meter_number': contract.meter_number}
        contract.meter_number = meter_number
        # Un cambio de medidor requiere volver a verificarlo manualmente.
        contract.meter_review_status = 'pendiente'
        contract.meter_review_notes = ''
        contract.meter_reviewed_by = None
        contract.meter_reviewed_at = None
        contract.save(update_fields=[
            'meter_number', 'meter_review_status', 'meter_review_notes',
            'meter_reviewed_by', 'meter_reviewed_at',
        ])
        from .audit import record_audit
        record_audit(
            request, 'updated', 'contract', contract.id,
            before=before, after={'meter_number': contract.meter_number})
        return Response(ContractSerializer(contract).data)


class ContractDetailView(APIView):
    """Detalle de un contrato sin alterar el movimiento comercial original."""

    def get(self, request, pk):
        contract = Contract.objects.select_related(
            'customer', 'plan', 'created_by', 'meter_reviewed_by', 'sale').filter(
                pk=pk).first()
        if contract is None:
            return Response({'error': 'Contrato no encontrado'}, status=404)
        payload = ContractSerializer(contract).data
        payload['customer'] = CustomerSerializer(contract.customer).data
        payload['sale'] = SaleSerializer(
            contract.sale, context={'catalog': request_type_catalog()}).data \
            if contract.sale else None
        return Response(payload)


class EquipmentBySerialView(APIView):
    """Consulta de solo lectura de un equipo físico por número de serie."""
    permission_classes = [IsAuthenticated]

    def get(self, request, serie):
        normalized = (serie or '').strip()
        if not normalized:
            return Response({'error': 'Debe indicar un número de serie'}, status=400)

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT o.id_onu, o.serie,
                       c.codigo_item, c.descripcion, c.marca, c.modelo,
                       t.id_tipo_onu, t.nombre,
                       o.estado, o.ubicacion, o.actualizado_en
                FROM public.onu AS o
                INNER JOIN public.catalogo_item AS c
                    ON c.codigo_item = o.codigo_item
                INNER JOIN public.tipo_onu AS t
                    ON t.id_tipo_onu = c.id_tipo_onu
                WHERE LOWER(TRIM(o.serie)) = LOWER(TRIM(%s))
                LIMIT 1
                """,
                [normalized],
            )
            row = cursor.fetchone()

        if row is None:
            return Response(
                {'error': 'No se encontró un equipo con esa serie'}, status=404)

        return Response({
            'id': row[0],
            'serie': row[1],
            'articulo': {
                'codigo': row[2],
                'descripcion': row[3],
                'marca': row[4],
                'modelo': row[5],
                'tipo': {
                    'id': row[6],
                    'nombre': row[7],
                },
            },
            'estado': row[8],
            'ubicacion': row[9],
            'actualizadoEn': row[10],
        })


class InventoryPendingListView(IsAdminMixin, APIView):
    permission_code = 'inventory.manage'
    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error
        movements = InventarioMovimiento.objects.filter(
            estado=InventarioMovimiento.ESTADO_PENDIENTE
        ).select_related('sale', 'created_by').order_by('-created_at')
        return Response({
            'items': [{
                'id': movement.id,
                'serie': movement.serie,
                'tipo': movement.tipo,
                'estado': movement.estado,
                'saleId': movement.sale_id,
                'clientCode': movement.sale.clientCode,
                'clientName': movement.sale.clientName,
                'requestDate': movement.sale.date,
                'createdAt': movement.created_at,
                'createdBy': movement.created_by.name,
            } for movement in movements],
        })


class InventoryConfirmReceptionView(IsAdminMixin, APIView):
    permission_code = 'inventory.manage'
    def post(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        try:
            movement = InventarioMovimiento.objects.select_related('sale').get(
                id=pk, estado=InventarioMovimiento.ESTADO_PENDIENTE)
        except InventarioMovimiento.DoesNotExist:
            return Response({'error': 'Recepción pendiente no encontrada'}, status=404)

        now = timezone.now()
        with transaction.atomic():
            movement = InventarioMovimiento.objects.select_for_update().get(id=pk)
            if movement.estado != InventarioMovimiento.ESTADO_PENDIENTE:
                return Response({'error': 'La recepción ya fue confirmada'}, status=409)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE public.onu
                    SET estado = %s,
                        ubicacion = %s,
                        actualizado_en = now()
                    WHERE LOWER(TRIM(serie)) = LOWER(TRIM(%s))
                    """,
                    ['DEVUELTO', 'ALMACEN', movement.serie],
                )
                if cursor.rowcount != 1:
                    return Response(
                        {'error': 'El equipo ya no existe en inventario'}, status=409)
            movement.estado = InventarioMovimiento.ESTADO_CONFIRMADO
            movement.confirmed_by = request.user
            movement.confirmed_at = now
            movement.save(update_fields=['estado', 'confirmed_by', 'confirmed_at'])
        from .audit import record_audit
        record_audit(
            request, 'received', 'inventory_movement', movement.id,
            before={'estado': InventarioMovimiento.ESTADO_PENDIENTE,
                    'serie': movement.serie},
            after={'estado': movement.estado,
                   'sale_id': movement.sale_id},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


def _query_int(params, name, default, maximum=None):
    raw = params.get(name)
    if raw in (None, ''):
        return default, None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None, Response(
            {'error': {name: 'Debe ser un número entero'}},
            status=status.HTTP_400_BAD_REQUEST)
    if value < 1 or (maximum is not None and value > maximum):
        message = 'Debe ser mayor que cero'
        if maximum is not None:
            message = f'Debe estar entre 1 y {maximum}'
        return None, Response(
            {'error': {name: message}}, status=status.HTTP_400_BAD_REQUEST)
    return value, None


@extend_schema_view(
    get=extend_schema(responses={200: SaleSerializer(many=True), 400: dict}),
    post=extend_schema(request=SaleCreateSerializer, responses={201: dict, 400: dict}),
)
class SaleListView(APIView):
    def get(self, request):
        archived = request.query_params.get('archived', '').lower() == 'true'
        if archived and getattr(request.user, 'role', None) != 'admin':
            return Response({'error': 'Solo administradores pueden ver solicitudes archivadas'}, status=403)
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        rtype = request.query_params.get('requestType')
        stype = request.query_params.get('serviceType')
        stype_from = request.query_params.get('serviceTypeFrom')
        page, error = _query_int(request.query_params, 'page', 1)
        if error:
            return error
        page_size, error = _query_int(
            request.query_params, 'page_size', 25, maximum=100)
        if error:
            return error

        try:
            parsed_from = date.fromisoformat(from_date) if from_date else None
            parsed_to = date.fromisoformat(to_date) if to_date else None
        except ValueError:
            return Response(
                {'error': {'date': 'Use el formato YYYY-MM-DD'}},
                status=status.HTTP_400_BAD_REQUEST)
        if parsed_from and parsed_to and parsed_from > parsed_to:
            return Response(
                {'error': {'date': 'La fecha inicial no puede ser posterior a la final'}},
                status=status.HTTP_400_BAD_REQUEST)
        if parsed_from and parsed_to and (parsed_to - parsed_from).days > 366:
            return Response(
                {'error': {'date': 'El rango máximo permitido es de 366 días'}},
                status=status.HTTP_400_BAD_REQUEST)

        from .domain import SERVICE_TYPE_LABELS, SERVICE_TYPE_TO_PLAN_TYPE
        catalog = request_type_catalog()
        if rtype and rtype not in catalog:
            return Response(
                {'error': {'requestType': 'Tipo de solicitud desconocido'}},
                status=status.HTTP_400_BAD_REQUEST)
        if stype and stype not in SERVICE_TYPE_LABELS:
            return Response(
                {'error': {'serviceType': 'Tipo de servicio desconocido'}},
                status=status.HTTP_400_BAD_REQUEST)
        if stype_from and stype_from not in SERVICE_TYPE_TO_PLAN_TYPE:
            return Response(
                {'error': {'serviceTypeFrom': 'Tipo de servicio desconocido'}},
                status=status.HTTP_400_BAD_REQUEST)
        qs = Sale.objects.select_related(
            'plan', 'planFromId', 'createdBy', 'coverage_zone', 'canal_captacion'
        ).filter(deleted_at__isnull=not archived).order_by('-date', '-id')
        if from_date:
            qs = qs.filter(date__gte=from_date)
        if to_date:
            qs = qs.filter(date__lte=to_date)
        if rtype:
            qs = qs.filter(requestType=rtype)
        if stype:
            qs = qs.filter(serviceType=stype)
        if stype_from:
            # Busca por el servicio anterior registrado y, para los
            # movimientos antiguos que no lo tienen, por la familia del
            # plan anterior. Asi el filtro no pierde registros previos.
            from .domain import SERVICE_TYPE_TO_PLAN_TYPE
            if stype_from in SERVICE_TYPE_TO_PLAN_TYPE:
                qs = qs.filter(Q(serviceTypeFrom=stype_from)
                               | Q(serviceTypeFrom__isnull=True,
                                   planFromId__type=SERVICE_TYPE_TO_PLAN_TYPE[stype_from]))
            else:
                qs = qs.filter(serviceTypeFrom=stype_from)

        total = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = qs[start:end]
        total_pages = max(1, (total + page_size - 1) // page_size)

        serialized = SaleSerializer(
            items, many=True, context={'catalog': request_type_catalog()}).data
        if archived:
            ids = [str(item.id) for item in items]
            audit_events = AuditLog.objects.filter(
                entity='sale', entity_id__in=ids, action='deactivated'
            ).select_related('actor').order_by('created_at')
            archive_data = {}
            for event in audit_events:
                archive_data[event.entity_id] = {
                    'at': event.created_at,
                    'by': event.actor.name if event.actor else 'Sistema',
                }
            for item, sale in zip(serialized, items):
                event = archive_data.get(str(sale.id))
                item['archivedAt'] = event['at'] if event else sale.deleted_at
                item['archivedBy'] = event['by'] if event else '—'

        return Response({
            # El catalogo va en el context: sin esto, get_previousService y
            # get_isServiceChange lo pedirian una vez por cada venta de la pagina.
            'items': serialized,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
        })

    def post(self, request):
        import logging, traceback
        logger = logging.getLogger('core')
        data = request.data.copy()
        data['date'] = timezone.localdate().isoformat()
        idempotency_key = request.headers.get('Idempotency-Key', '').strip()
        if len(idempotency_key) > 128:
            return Response(
                {'error': 'Idempotency-Key no puede superar 128 caracteres'},
                status=status.HTTP_400_BAD_REQUEST)
        idempotency = None
        if idempotency_key:
            now = timezone.now()
            existing = SaleIdempotencyKey.objects.filter(
                user=request.user, key=idempotency_key).first()
            if existing and existing.expires_at <= now:
                existing.delete()
                existing = None
            if existing:
                if existing.status == 'processing':
                    return Response(
                        {'error': 'La solicitud con esta clave todavía está en proceso'},
                        status=status.HTTP_409_CONFLICT)
                response = Response(
                    existing.response_payload, status=existing.response_status)
                response['Idempotent-Replayed'] = 'true'
                return response
            try:
                idempotency = SaleIdempotencyKey.objects.create(
                    user=request.user, key=idempotency_key, status='processing',
                    expires_at=now + timedelta(hours=24))
            except IntegrityError:
                existing = SaleIdempotencyKey.objects.get(
                    user=request.user, key=idempotency_key)
                if existing.status == 'completed':
                    response = Response(
                        existing.response_payload, status=existing.response_status)
                    response['Idempotent-Replayed'] = 'true'
                    return response
                return Response(
                    {'error': 'La solicitud con esta clave está en proceso'},
                    status=status.HTTP_409_CONFLICT)
        logger.info(
            'Sale creation requested user_id=%s request_type=%s',
            getattr(request.user, 'id', None), data.get('requestType', 'nuevo_contrato'))
        try:
            serializer = SaleCreateSerializer(data=data, context={'user': request.user})
            if not serializer.is_valid():
                if idempotency:
                    idempotency.delete()
                return Response({'error': _first_error(serializer)}, status=status.HTTP_400_BAD_REQUEST)
            with transaction.atomic():
                sale = serializer.save()
                payload = json.loads(JSONRenderer().render(SaleSerializer(sale).data))
                if idempotency:
                    idempotency.status = 'completed'
                    idempotency.sale = sale
                    idempotency.response_payload = payload
                    idempotency.save(update_fields=[
                        'status', 'sale', 'response_payload'])
                from .audit import record_audit
                record_audit(
                    request, 'created', 'sale', sale.id,
                    after={'requestType': sale.requestType,
                           'serviceType': sale.serviceType,
                           'total': str(sale.total),
                           'version': sale.version})
            response = Response(payload, status=status.HTTP_201_CREATED)
            if idempotency:
                response['Idempotent-Replayed'] = 'false'
            return response
        except Exception as e:
            if idempotency:
                idempotency.delete()
            logger.error('SaleListView POST error: %s\n%s', e, traceback.format_exc())
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema_view(
    put=extend_schema(request=SaleCreateSerializer, responses={200: SaleSerializer, 400: dict, 404: dict, 409: dict}),
    delete=extend_schema(responses={204: None, 404: dict, 409: dict}),
)
class SaleDetailView(IsAdminMixin, APIView):
    permission_code = 'comercial.change'
    def delete(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        try:
            sale = Sale.objects.get(id=pk, deleted_at__isnull=True)
        except Sale.DoesNotExist:
            return Response({'error': 'Venta no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        before_audit = {
            'requestType': sale.requestType,
            'serviceType': sale.serviceType,
            'total': str(sale.total),
            'version': sale.version,
        }
        # La baja es lógica: no elimina la venta ni sus relaciones. Por eso
        # puede archivarse aunque tenga traslado o claves de idempotencia.
        sale.deleted_at = timezone.now()
        sale.save(update_fields=['deleted_at'])
        from .audit import record_audit
        record_audit(request, 'deactivated', 'sale', pk, before=before_audit,
                     after={'deleted_at': sale.deleted_at.isoformat()})
        return Response(status=status.HTTP_204_NO_CONTENT)

    def put(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        try:
            sale = Sale.objects.get(id=pk, deleted_at__isnull=True)
        except Sale.DoesNotExist:
            return Response({'error': 'Venta no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        from .domain import (
            SERVICE_TYPE_LABELS, SERVICE_TYPE_TO_PLAN_TYPE,
            motivo_categoria_de_modo, plan_is_selectable)
        from .serializers import (
            SaleSerializer, resolve_sale_prices, validate_cambio_plan,
            validate_adicion,
            resolve_motivo)

        data = request.data
        if 'status' in data:
            return Response(
                {'error': 'El estado se determina automáticamente según el tipo de solicitud.'},
                status=status.HTTP_400_BAD_REQUEST)
        if 'version' in data:
            try:
                requested_version = int(data['version'])
            except (TypeError, ValueError):
                return Response(
                    {'error': 'La version del registro no es valida'},
                    status=status.HTTP_400_BAD_REQUEST)
            if requested_version != sale.version:
                return Response(
                    {'error': 'El registro fue modificado por otro usuario',
                     'currentVersion': sale.version},
                    status=status.HTTP_409_CONFLICT)
        old_plan_id = sale.plan_id
        old_plan_from_id = sale.planFromId_id

        plan = sale.plan
        if data.get('planId'):
            plan = Plan.objects.filter(id=data['planId']).first()
            if not plan:
                return Response({'error': 'Plan no encontrado o inactivo'},
                                status=status.HTTP_400_BAD_REQUEST)

        service_type = data.get('serviceType', sale.serviceType)
        request_type = data.get('requestType', sale.requestType)
        catalog = request_type_catalog()
        tipo = catalog.get(request_type)
        if tipo is None:
            return Response({'error': 'Tipo de solicitud desconocido'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not tipo.activo:
            return Response({'error': 'El tipo de solicitud esta inactivo'},
                            status=status.HTTP_400_BAD_REQUEST)
        mode = tipo.modo
        mode_changed = mode != request_type_mode(sale.requestType, catalog)

        is_rehire = request_type == 'recontratacion'
        is_transfer = mode == MODO_TRASLADO
        transfer = getattr(sale, 'traslado_externo', None)
        if (request_type_mode(sale.requestType, catalog) == MODO_TRASLADO
                and not is_transfer):
            return Response(
                {'error': 'Un traslado externo no puede cambiarse a otro tipo '
                          'de solicitud.'},
                status=status.HTTP_400_BAD_REQUEST)
        if is_transfer:
            if transfer is None:
                return Response(
                    {'error': 'El traslado externo no tiene detalle asociado.'},
                    status=status.HTTP_409_CONFLICT)
            expected_family = SERVICE_TYPE_TO_PLAN_TYPE.get(service_type)
            if transfer.tariff.service_type != expected_family:
                return Response(
                    {'error': 'La tarifa del traslado no corresponde al servicio.'},
                    status=status.HTTP_400_BAD_REQUEST)
        if is_rehire:
            equipment_retained = data.get(
                'equipmentRetained', sale.equipment_retained)
            requires_technical_visit = data.get(
                'requiresTechnicalVisit', sale.requires_technical_visit)
            debt_applies = data.get('debtApplies', sale.debt_applies)
            debt_raw = data.get('debtAmount', sale.debt_amount)
            if equipment_retained is None:
                return Response(
                    {'error': 'Indique si conserva el router/ONU'},
                    status=status.HTTP_400_BAD_REQUEST)
            if requires_technical_visit is None:
                return Response(
                    {'error': 'Indique si requiere visita tecnica'},
                    status=status.HTTP_400_BAD_REQUEST)
            try:
                debt_amount = Decimal(str(debt_raw or 0))
            except (InvalidOperation, TypeError, ValueError):
                return Response(
                    {'error': 'El adeudo no es valido'},
                    status=status.HTTP_400_BAD_REQUEST)
            if debt_applies and debt_amount <= 0:
                return Response(
                    {'error': 'Ingrese un adeudo mayor que cero'},
                    status=status.HTTP_400_BAD_REQUEST)
            if not debt_applies and debt_amount != 0:
                return Response(
                    {'error': 'El adeudo debe ser cero si no aplica'},
                    status=status.HTTP_400_BAD_REQUEST)
        else:
            equipment_retained = None
            requires_technical_visit = None
            debt_applies = False
            debt_amount = Decimal('0')

        if service_type not in SERVICE_TYPE_LABELS:
            return Response({'error': 'Tipo de servicio no valido'},
                            status=status.HTTP_400_BAD_REQUEST)
        if plan.type != SERVICE_TYPE_TO_PLAN_TYPE.get(service_type):
            return Response(
                {'error': 'El plan no pertenece al tipo de servicio seleccionado'},
                status=status.HTTP_400_BAD_REQUEST)

        if (not plan_is_selectable(plan, mode, request_type)
                and not (plan.id == old_plan_id and not mode_changed)):
            return Response(
                {'error': ('El plan legacy no esta disponible para este tipo '
                           'de solicitud') if plan.legacy else
                          'El plan no esta disponible para este tipo de solicitud'},
                status=status.HTTP_400_BAD_REQUEST)

        plan_from = sale.planFromId
        if 'planFromId' in data:
            plan_from = None
            if data.get('planFromId'):
                plan_from = Plan.objects.filter(id=data['planFromId']).first()
                if not plan_from:
                    return Response({'error': 'Plan anterior no encontrado'},
                                    status=status.HTTP_400_BAD_REQUEST)

        service_type_from = data.get('serviceTypeFrom', sale.serviceTypeFrom) or None

        # Motivo: se conserva el historico (aunque este inactivo) cuando el
        # modo no cambio. Si cambia el tipo de movimiento, el motivo tiene
        # que corresponder a la nueva categoria o se exige uno nuevo.
        motivo = sale.motivo
        motivo_id = data.get('motivoId')
        expected_motive = motivo_categoria_de_modo(mode)

        if motivo_id and str(motivo_id) == str(sale.motivo_id):
            if (expected_motive and motivo is not None
                    and motivo.categoria != expected_motive):
                return Response(
                    {'error': 'El motivo no corresponde a este tipo de solicitud'},
                    status=status.HTTP_400_BAD_REQUEST)
            if expected_motive:
                change_reason = data.get('changeReason', sale.changeReason)
            else:
                motivo = None
                change_reason = ''
        elif motivo_id:
            motivo_errors = {}
            motivo, _ = resolve_motivo(motivo_id, mode, motivo_errors)
            if motivo_errors:
                return Response({'error': next(iter(motivo_errors.values()))},
                                status=status.HTTP_400_BAD_REQUEST)
            change_reason = motivo.nombre if motivo else ''
        elif mode_changed:
            motivo = None
            change_reason = data.get('changeReason', '') or ''
        else:
            change_reason = data.get('changeReason', sale.changeReason)

        if expected_motive:
            if motivo is None and mode_changed:
                etiqueta = ('del cambio' if expected_motive == 'cambio'
                            else 'del retiro')
                return Response(
                    {'error': f'Debe seleccionar el motivo {etiqueta}'},
                    status=status.HTTP_400_BAD_REQUEST)
            if motivo is not None and motivo.categoria != expected_motive:
                return Response(
                    {'error': 'El motivo no corresponde a este tipo de solicitud'},
                    status=status.HTTP_400_BAD_REQUEST)
        elif mode_changed:
            motivo = None
            change_reason = ''

        if mode == MODO_CAMBIO_PLAN:
            errors = validate_cambio_plan(
                plan=plan, plan_from=plan_from, service_type=service_type,
                service_type_from=service_type_from,
                change_reason=change_reason)
            if errors:
                return Response({'error': next(iter(errors.values()))},
                                status=status.HTTP_400_BAD_REQUEST)
        elif mode == MODO_ADICION:
            errors = validate_adicion(
                plan=plan, service_type=service_type,
                plan_from=plan_from,
                service_type_from=service_type_from,
                addition_type=data.get('additionType', sale.additionType))
            if errors:
                return Response({'error': next(iter(errors.values()))},
                                status=status.HTTP_400_BAD_REQUEST)
            plan_from = None
        else:
            service_type_from = None
            plan_from = None
            if mode != MODO_ADICION:
                data = {**data, 'additionType': ''}

        canal_captacion = None
        if request_type == 'nuevo_contrato':
            if 'canalCaptacionId' not in data:
                if sale.requestType == 'nuevo_contrato':
                    canal_captacion = sale.canal_captacion
                else:
                    return Response(
                        {'error': 'Seleccione cómo nos conoció para registrar el nuevo contrato'},
                        status=status.HTTP_400_BAD_REQUEST)
            elif data.get('canalCaptacionId') in (None, ''):
                return Response(
                    {'error': 'Seleccione cómo nos conoció para registrar el nuevo contrato'},
                    status=status.HTTP_400_BAD_REQUEST)
            elif str(data['canalCaptacionId']) == str(sale.canal_captacion_id):
                canal_captacion = sale.canal_captacion
            else:
                canal_captacion = CanalCaptacion.objects.filter(
                    id=data['canalCaptacionId'], activo=True).first()
                if canal_captacion is None:
                    return Response(
                        {'error': 'El canal de captacion no existe o esta inactivo'},
                        status=status.HTTP_400_BAD_REQUEST)
        elif data.get('canalCaptacionId') not in (None, ''):
            return Response(
                {'error': 'El canal de captación solo aplica a nuevos contratos'},
                status=status.HTTP_400_BAD_REQUEST)

        sale.date = data.get('date', sale.date)
        sale.clientCode = data.get('clientCode', sale.clientCode)
        sale.clientName = data.get('clientName', sale.clientName)
        sale.serviceType = service_type
        sale.requestType = request_type
        sale.status = movement_status_for_request_type(request_type, catalog)
        sale.additionType = data.get('additionType', sale.additionType)
        sale.changeReason = change_reason
        sale.motivo = motivo
        sale.notes = data.get('notes', sale.notes)
        sale.plan = plan
        if plan.id != old_plan_id or not sale.planName:
            sale.planName = plan.label
        sale.canal_captacion = canal_captacion
        sale.planFromId = plan_from
        if plan_from is None:
            sale.planFrom = ''
        elif plan_from.id != old_plan_from_id or not sale.planFrom:
            sale.planFrom = plan_from.label
        sale.serviceTypeFrom = service_type_from
        sale.totalFrom = plan_from.total if plan_from else None
        sale.equipment_retained = equipment_retained
        sale.requires_technical_visit = requires_technical_visit
        sale.debt_applies = debt_applies
        sale.debt_amount = debt_amount

        # Si el plan cambio, una promocion del plan anterior ya no aplica.
        # Se limpia para que el total se calcule con las condiciones nuevas.
        if (sale.promotion is not None
                and sale.promotion.plan_id != plan.id):
            sale.promotion = None
            sale.promotion_name = ''
        if plan.id != old_plan_id:
            if sale.promotion:
                sale.promotion_name = sale.promotion.name
            else:
                sale.promotion = None
                sale.promotion_name = ''

        # Solo admin puede llegar a esta vista. Permitir importes manuales
        # para este registro; si no vienen, se conserva el calculo vigente
        # derivado del plan y la promocion.
        manual_installation = data.get('appliedInstallation')
        manual_monthly = data.get('appliedMonthly')
        if (manual_installation is None) != (manual_monthly is None):
            return Response(
                {'error': 'Debe indicar instalación y mensualidad juntas'},
                status=status.HTTP_400_BAD_REQUEST)
        if manual_installation is not None:
            try:
                installation = Decimal(str(manual_installation))
                monthly = Decimal(str(manual_monthly))
            except (InvalidOperation, TypeError, ValueError):
                return Response(
                    {'error': 'Los importes no son validos'},
                    status=status.HTTP_400_BAD_REQUEST)
            if installation < 0 or monthly < 0:
                return Response(
                    {'error': 'Los importes no pueden ser negativos'},
                    status=status.HTTP_400_BAD_REQUEST)
            total = installation + monthly
        else:
            installation, monthly, total = resolve_sale_prices(
                plan, sale.promotion, request_type)
        if is_transfer:
            # El traslado se cobra con el snapshot de su tarifa, nunca con
            # los importes del plan asociado a Sale.
            installation = Decimal('0')
            monthly = Decimal('0')
            total = transfer.tariff_amount
        elif is_rehire:
            total += debt_amount
        sale.applied_installation = installation
        sale.applied_monthly = monthly
        sale.total = total

        before_audit = {
            'requestType': sale.requestType,
            'serviceType': sale.serviceType,
            'total': str(sale.total),
            'version': sale.version,
        }
        sale.lastEditedBy = request.user
        sale.lastEditedAt = timezone.now()
        sale.version += 1
        sale.save()
        from .audit import record_audit
        record_audit(
            request, 'updated', 'sale', sale.id,
            before=before_audit,
            after={'requestType': sale.requestType,
                   'serviceType': sale.serviceType,
                   'total': str(sale.total),
                   'version': sale.version})
        return Response(SaleSerializer(sale).data)


@extend_schema_view(
    get=extend_schema(responses={200: UserSerializer(many=True)}),
    post=extend_schema(request=UserWriteSerializer, responses={201: UserSerializer, 400: dict}),
)
class SaleRestoreView(IsAdminMixin, APIView):
    permission_code = 'comercial.change'
    def post(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        try:
            sale = Sale.objects.get(id=pk, deleted_at__isnull=False)
        except Sale.DoesNotExist:
            return Response({'error': 'Solicitud archivada no encontrada'}, status=404)

        archived_at = sale.deleted_at
        sale.deleted_at = None
        sale.save(update_fields=['deleted_at'])
        from .audit import record_audit
        record_audit(
            request, 'restored', 'sale', pk,
            before={'deleted_at': archived_at.isoformat()},
            after={'deleted_at': None},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


def _resolve_assignable_roles(role_ids):
    if len(role_ids) != len(set(role_ids)):
        return None, Response(
            {'error': {'roleIds': 'No repita roles'}},
            status=status.HTTP_400_BAD_REQUEST)
    roles = list(Role.objects.filter(
        pk__in=role_ids, active=True, is_system_role=False))
    if len(roles) != len(role_ids):
        return None, Response(
            {'error': {'roleIds': 'Uno o más roles no existen o no están disponibles'}},
            status=status.HTTP_400_BAD_REQUEST)
    return roles, None


def _sync_user_roles(user, roles, assigned_by):
    active_assignments = list(UserRole.objects.filter(
        user=user, active=True, role__is_system_role=False))
    role_ids = {role.id for role in roles}
    assigned_role_ids = {assignment.role_id for assignment in active_assignments}
    now = timezone.now()
    for assignment in active_assignments:
        if assignment.role_id not in role_ids:
            assignment.active = False
            assignment.revoked_at = now
            assignment.save(update_fields=['active', 'revoked_at'])
    for role in roles:
        if role.id not in assigned_role_ids:
            UserRole.objects.create(
                user=user, role=role, assigned_by=assigned_by)


class UserListView(IsAdminMixin, APIView):
    permission_code = 'users.manage'

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error
        users = User.objects.prefetch_related(
            'role_assignments__role').order_by('name', 'id')
        query = (request.query_params.get('q') or '').strip()
        if query:
            users = users.filter(
                Q(name__icontains=query) | Q(name_normalized__icontains=query))
        active = request.query_params.get('active')
        if active in ('true', 'false'):
            users = users.filter(active=(active == 'true'))
        role_code = request.query_params.get('role')
        if role_code:
            users = users.filter(
                role_assignments__active=True,
                role_assignments__role__code=role_code)

        total = users.count()
        page, error = _query_int(request.query_params, 'page', 1)
        if error:
            return error
        page_size, error = _query_int(
            request.query_params, 'page_size', 25, maximum=100)
        if error:
            return error
        start = (page - 1) * page_size
        page_items = users[start:start + page_size]
        return Response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'results': UserSerializer(
                page_items, many=True).data,
        })

    def post(self, request):
        error = self.check_admin(request)
        if error:
            return error
        serializer = UserWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': _first_error(serializer),
                             'fields': serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)
        if not request.data.get('password'):
            return Response({'error': 'La contraseña es requerida'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not request.data.get('password_confirm'):
            return Response(
                {'error': {'password_confirm': 'Confirme la contraseña.'}},
                status=status.HTTP_400_BAD_REQUEST)
        role_ids = serializer.validated_data.get('roleIds')
        if not role_ids:
            return Response(
                {'error': {'roleIds': 'Seleccione al menos un rol'}},
                status=status.HTTP_400_BAD_REQUEST)
        roles, error = _resolve_assignable_roles(role_ids)
        if error:
            return error
        with transaction.atomic():
            user = serializer.save()
            _sync_user_roles(user, roles, request.user)
            record_audit(
                request, 'created', 'user', user.id,
                after={
                    'role': user.role,
                    'active': user.active,
                    'roles': [role.name for role in roles or []],
                })
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    put=extend_schema(request=UserWriteSerializer, responses={200: UserSerializer, 400: dict, 404: dict}),
    delete=extend_schema(responses={204: None, 400: dict, 404: dict, 409: dict}),
)
class UserDetailView(IsAdminMixin, APIView):
    permission_code = 'users.manage'

    def _guard_deactivation(self, request, user, new_active):
        if new_active is False and user == request.user:
            return Response(
                {'error': 'No puedes desactivar tu propia cuenta.'},
                status=status.HTTP_400_BAD_REQUEST)
        if new_active is False:
            from .rbac import is_last_superadmin
            if is_last_superadmin(user):
                return Response(
                    {'error': 'No puedes desactivar al último administrador '
                              'de sistemas activo.'},
                    status=status.HTTP_409_CONFLICT)
        return None

    def delete(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        guard = self._guard_deactivation(request, user, False)
        if guard:
            return guard
        try:
            user.active = False
            user.bump_token_version()
            user.save(update_fields=['active', 'token_version', 'updated_at'])
        except ProtectedError:
            return Response(
                {'error': 'No se puede eliminar el usuario porque tiene '
                          'registros asociados.'},
                status=status.HTTP_409_CONFLICT)
        record_audit(request, 'deactivated', 'user', pk,
                     after={'active': False})
        return Response(status=status.HTTP_204_NO_CONTENT)

    def put(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)

        new_active = request.data.get('active')
        if new_active is not None:
            guard = self._guard_deactivation(
                request, user, new_active is True)
            if guard:
                return guard

        serializer = UserWriteSerializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'error': _first_error(serializer),
                             'fields': serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)
        role_ids = serializer.validated_data.get('roleIds')
        roles = None
        if role_ids is not None:
            if not role_ids:
                return Response(
                    {'error': {'roleIds': 'Seleccione al menos un rol'}},
                    status=status.HTTP_400_BAD_REQUEST)
            roles, error = _resolve_assignable_roles(role_ids)
            if error:
                return error
        before = {
            'role': user.role,
            'active': user.active,
            'roles': list(user.role_assignments.filter(
                active=True).values_list('role__code', flat=True)),
        }
        with transaction.atomic():
            was_active = user.active
            serializer.save()
            if was_active and not user.active:
                user.bump_token_version()
                user.save(update_fields=['token_version', 'updated_at'])
            if roles is not None:
                _sync_user_roles(user, roles, request.user)
            after_roles = list(user.role_assignments.filter(
                active=True).values_list('role__code', flat=True))
            record_audit(
                request, 'updated', 'user', user.id, before=before,
                after={
                    'role': user.role,
                    'active': user.active,
                    'roles': after_roles,
                })
        return Response(UserSerializer(user).data)


@extend_schema(responses={200: dict, 400: dict, 500: dict})
class DashboardStatsView(APIView):
    MOVEMENT_TYPES = {
        'all', 'nuevo_contrato', 'recontrataciones', 'instalaciones',
        'retiros', 'cambios_plan',
        'adiciones', 'traslados', 'otros',
    }

    @staticmethod
    def _parse_range(params, today):
        from_value = params.get('from')
        to_value = params.get('to')
        if bool(from_value) != bool(to_value):
            raise ValueError('Los parametros from y to deben enviarse juntos')

        if not from_value:
            return today, today

        try:
            from_date = date.fromisoformat(from_value)
            to_date = date.fromisoformat(to_value)
        except (TypeError, ValueError):
            raise ValueError('Las fechas deben usar el formato YYYY-MM-DD')

        if from_date > to_date:
            raise ValueError('La fecha inicial no puede superar la fecha final')
        return from_date, to_date

    @staticmethod
    def _category_codes(catalog):
        # Estos dos tipos comparten el modo "nuevo", pero son categorías
        # comerciales distintas y deben medirse por separado.
        categories = {
            'nuevo_contrato': [
                code for code in catalog if code == 'nuevo_contrato'],
            'recontrataciones': [
                code for code in catalog if code == 'recontratacion'],
        }
        classified = set(categories['nuevo_contrato']) | set(
            categories['recontrataciones'])
        # Una adición es un cambio de servicio con una etiqueta comercial
        # distinta. Se agrupa junto a cambios_plan para no duplicar métricas;
        # requestType sigue conservando "adicion" para reportes y auditoría.
        mode_groups = (
            ('retiros', (MODO_RETIRO,)),
            ('cambios_plan', (MODO_CAMBIO_PLAN, MODO_ADICION)),
            ('traslados', (MODO_TRASLADO,)),
        )
        for name, modes in mode_groups:
            categories[name] = [
                code for code, tipo in catalog.items()
                if code not in classified and tipo.modo in modes]
            classified.update(categories[name])
        # Se conserva la clave para clientes antiguos del endpoint, pero ya
        # no clasifica movimientos: las adiciones viven en cambios_plan.
        categories['adiciones'] = []
        # Compatibilidad para consumidores antiguos del endpoint. No se
        # expone como categoría nueva ni se incluye en el desglose.
        categories['instalaciones'] = (
            categories['nuevo_contrato'] + categories['recontrataciones'])
        categories['otros'] = [
            code for code, tipo in catalog.items()
            if code not in classified and tipo.modo == MODO_SIMPLE
        ]
        return categories

    @staticmethod
    def _amount(value):
        return float(value or 0)

    @classmethod
    def _summary(cls, queryset):
        data = queryset.aggregate(count=Count('id'), total=Sum('total'))
        return {
            'count': data['count'] or 0,
            'total': cls._amount(data['total']),
        }

    @staticmethod
    def _zone_rows(queryset, categories):
        zone_request_codes = (
            categories['nuevo_contrato']
            + categories['recontrataciones']
            + categories['traslados'])
        return list(
            queryset.filter(
                requestType__in=zone_request_codes,
                coverage_zone__isnull=False,
            ).values(
                'coverage_zone_id', 'coverage_zone__name'
            ).annotate(
                count=Count('id')
            ).order_by('-count', 'coverage_zone__name'))

    @staticmethod
    def _category_rows(queryset, categories, movement_type, from_date, to_date):
        """Aggregate only the category selected in the dashboard."""
        codes = categories.get(movement_type, [])
        selected = queryset.filter(requestType__in=codes)
        plans = list(selected.values(
            'planName', 'plan__label', 'plan__type'
        ).annotate(count=Count('id'), total=Sum('total'))
             .order_by('-count', 'planName', 'plan__label'))
        plan_type_labels = {
            'internet': 'Internet', 'tv': 'TV', 'combo': 'Combo',
        }
        plan_rows = [{
            'label': row['planName'] or row['plan__label'],
            'plan_name': row['planName'],
            'catalog_label': row['plan__label'],
            'type': row['plan__type'],
            'type_label': plan_type_labels.get(row['plan__type'], row['plan__type']),
            'count': row['count'],
            'total': float(row['total'] or 0),
        } for row in plans]

        motive_rows = list(selected.filter(motivo__isnull=False).values(
            'motivo_id', 'motivo__nombre'
        ).annotate(count=Count('id')).order_by('-count', 'motivo__nombre'))
        motives = [{
            'id': row['motivo_id'],
            'label': row['motivo__nombre'],
            'count': row['count'],
        } for row in motive_rows]

        transitions = []
        if movement_type == 'cambios_plan':
            from .domain import SERVICE_TYPE_FAMILY, SERVICE_FAMILY_LABELS

            transition_rows = selected.values(
                'serviceTypeFrom', 'serviceType',
                'planFromId__type', 'plan__type',
                'planFromId__label', 'planName', 'plan__label')
            transition_counts = {}
            for row in transition_rows:
                old_family = (SERVICE_TYPE_FAMILY.get(row['serviceTypeFrom'])
                              or row['planFromId__type'])
                new_family = SERVICE_TYPE_FAMILY.get(row['serviceType'])
                if old_family and new_family and old_family != new_family:
                    transition = (
                        SERVICE_FAMILY_LABELS.get(old_family, old_family),
                        SERVICE_FAMILY_LABELS.get(new_family, new_family))
                else:
                    transition = (
                        row['planFromId__label'] or 'Sin plan anterior',
                        row['planName'] or row['plan__label'] or 'Sin plan nuevo')
                transition_counts[transition] = transition_counts.get(transition, 0) + 1
            transitions = [{
                'from': old,
                'to': new,
                'count': count,
            } for (old, new), count in sorted(
                transition_counts.items(), key=lambda item: (-item[1], item[0]))]

        if movement_type == 'adiciones':
            addition_rows = selected.values('additionType').annotate(
                count=Count('id'), total=Sum('total')).order_by('additionType')
            services = [{
                'serviceType': row['additionType'],
                'label': {
                    'adicion_tv': 'TV cable adicionada',
                    'adicion_internet': 'Internet adicionado',
                }.get(row['additionType'], 'Adición'),
                'count': row['count'],
                'total': float(row['total'] or 0),
            } for row in addition_rows]
        else:
            service_rows = selected.values('serviceType').annotate(
                count=Count('id'), total=Sum('total')).order_by('serviceType')
            service_labels = {
                'internet': 'Internet',
                'tv': 'TV analógica',
                'tv_digital': 'TV digital',
                'combo_analog': 'Internet + TV analógica',
                'combo_digital': 'Internet + TV digital',
            }
            services = [{
                'serviceType': row['serviceType'],
                'label': service_labels.get(row['serviceType'], row['serviceType']),
                'count': row['count'],
                'total': float(row['total'] or 0),
            } for row in service_rows]

        zone_rows = []
        if movement_type in {'nuevo_contrato', 'recontrataciones', 'traslados'}:
            zone_rows = list(selected.filter(coverage_zone__isnull=False).values(
                'coverage_zone__name'
            ).annotate(count=Count('id')).order_by('-count', 'coverage_zone__name'))
        zone_total = sum(row['count'] for row in zone_rows)
        zones = [{
            'name': row['coverage_zone__name'],
            'count': row['count'],
            'percentage': round(row['count'] * 100 / zone_total, 1)
            if zone_total else 0,
        } for row in zone_rows]

        daily = selected.values('date').annotate(count=Count('id')).order_by('date')
        daily_by_date = {row['date']: row['count'] for row in daily}
        series = []
        current = from_date
        while current <= to_date:
            series.append({'date': current.isoformat(), 'count': daily_by_date.get(current, 0)})
            current += timedelta(days=1)

        return {
            'plans': plan_rows,
            'motivos': motives,
            'transiciones': transitions,
            'servicios': services,
            'zonas': zones,
            'series': series,
        }

    @staticmethod
    def _selected_sales(categories, from_date, to_date, movement_type):
        queryset = Sale.objects.filter(
            deleted_at__isnull=True,
            date__gte=from_date,
            date__lte=to_date,
        )
        if movement_type != 'all':
            queryset = queryset.filter(
                requestType__in=categories[movement_type])
        return queryset

    @classmethod
    def _analytics(cls, queryset, categories, from_date, to_date,
                   movement_type):
        category_querysets = {
            name: queryset.filter(requestType__in=codes)
            for name, codes in categories.items()
            if name != 'instalaciones'
        }
        summaries = {
            name: cls._summary(category_qs)
            for name, category_qs in category_querysets.items()
        }

        daily_rows = queryset.values('date').annotate(
            count=Count('id'),
            nuevo_contrato=Count(
                'id', filter=Q(requestType__in=categories['nuevo_contrato'])),
            recontrataciones=Count(
                'id', filter=Q(requestType__in=categories['recontrataciones'])),
            retiros=Count(
                'id', filter=Q(requestType__in=categories['retiros'])),
            cambios_plan=Count(
                'id', filter=Q(requestType__in=categories['cambios_plan'])),
            adiciones=Count(
                'id', filter=Q(requestType__in=categories['adiciones'])),
            otros=Count(
                'id', filter=Q(requestType__in=categories['otros'])),
        )
        daily_by_date = {row['date']: row for row in daily_rows}

        series = []
        current = from_date
        while current <= to_date:
            row = daily_by_date.get(current, {})
            series.append({
                'date': current.isoformat(),
                'movimientos': row.get('count', 0),
                'nuevo_contrato': row.get('nuevo_contrato', 0),
                'recontrataciones': row.get('recontrataciones', 0),
                'retiros': row.get('retiros', 0),
                'cambios_plan': row.get('cambios_plan', 0),
                'adiciones': row.get('adiciones', 0),
                'otros': row.get('otros', 0),
            })
            current += timedelta(days=1)

        # Resumen general por servicio. El análisis de una categoría tiene
        # su propia agregación en _category_rows, pero el dashboard general
        # también necesita este bloque.
        service_rows = queryset.values('serviceType').annotate(
            count=Count('id'), total=Sum('total')).order_by('serviceType')
        service_labels = {
            'internet': 'Internet',
            'tv': 'TV analógica',
            'tv_digital': 'TV digital',
            'combo_analog': 'Internet + TV analógica',
            'combo_digital': 'Internet + TV digital',
        }
        services = [{
            'serviceType': row['serviceType'],
            'label': service_labels.get(row['serviceType'], row['serviceType']),
            'count': row['count'],
            'total': cls._amount(row['total']),
        } for row in service_rows]

        channel_queryset = queryset.filter(
            requestType__in=categories['nuevo_contrato'])
        channel_rows = list(
            channel_queryset.values(
                'canal_captacion_id', 'canal_captacion__nombre'
            ).annotate(count=Count('id'))
        )
        channel_rows.sort(
            key=lambda row: (
                -row['count'],
                row['canal_captacion__nombre'] or 'Sin especificar',
            ))
        channel_total = sum(row['count'] for row in channel_rows)
        channels = [
            {
                'id': row['canal_captacion_id'],
                'key': (
                    f"channel-{row['canal_captacion_id']}"
                    if row['canal_captacion_id'] is not None
                    else 'channel-none'
                ),
                'name': row['canal_captacion__nombre'] or 'Sin especificar',
                'count': row['count'],
                'percentage': (
                    round(row['count'] * 100 / channel_total, 2)
                    if channel_total else 0
                ),
            }
            for row in channel_rows
        ]
        if channels:
            channels[-1]['percentage'] = round(
                channels[-1]['percentage']
                + 100
                - sum(channel['percentage'] for channel in channels),
                2,
            )

        daily_channel_rows = channel_queryset.values(
            'date', 'canal_captacion_id'
        ).annotate(count=Count('id'))
        daily_channel_counts = {
            (row['date'], row['canal_captacion_id']): row['count']
            for row in daily_channel_rows
        }
        channels_by_day = []
        current = from_date
        while current <= to_date:
            day = {'date': current.isoformat()}
            for channel in channels:
                day[channel['key']] = daily_channel_counts.get(
                    (current, channel['id']), 0)
            channels_by_day.append(day)
            current += timedelta(days=1)

        demand_codes = (
            categories['nuevo_contrato'] + categories['recontrataciones'])
        plan_rows = queryset.filter(
            requestType__in=demand_codes
        ).values(
            'planName', 'plan__label', 'plan__type'
        ).annotate(
            count=Count('id'), total=Sum('total')
        ).order_by('-count', 'planName', 'plan__label')
        plan_type_labels = {
            'internet': 'Internet',
            'tv': 'TV',
            'combo': 'Combo',
        }
        plans = [
            {
                'label': row['planName'] or row['plan__label'],
                'plan_name': row['planName'],
                'catalog_label': row['plan__label'],
                'type': row['plan__type'],
                'type_label': plan_type_labels.get(
                    row['plan__type'], row['plan__type']),
                'count': row['count'],
                'total': cls._amount(row['total']),
            }
            for row in plan_rows
        ]

        zone_rows = cls._zone_rows(queryset, categories)
        zone_request_total = sum(row['count'] for row in zone_rows)
        top_zone_rows = zone_rows
        zones = [
            {
                'name': row['coverage_zone__name'],
                'count': row['count'],
                'percentage': round(row['count'] * 100 / zone_request_total, 1),
            }
            for row in top_zone_rows
        ] if zone_request_total else []

        movement_breakdown = [
            {
                'type': name,
                'label': {
                    'nuevo_contrato': 'Nuevo contrato',
                    'recontrataciones': 'Recontrataciones',
                    'retiros': 'Retiros',
                    'cambios_plan': 'Cambios de plan',
                    'adiciones': 'Adiciones',
                    'otros': 'Otros',
                }[name],
                **summaries[name],
            }
            for name in ('nuevo_contrato', 'recontrataciones', 'retiros', 'cambios_plan',
                         'adiciones', 'otros')
        ]

        selected_summary = cls._summary(queryset)
        category_analysis = None
        if movement_type != 'all':
            category_analysis = cls._category_rows(
                queryset, categories, movement_type, from_date, to_date)

        return {
            'period': {
                'from': from_date.isoformat(),
                'to': to_date.isoformat(),
                'movement_type': movement_type,
                'granularity': 'day',
            },
            'nuevo_contrato': summaries['nuevo_contrato'],
            'recontrataciones': summaries['recontrataciones'],
            'retiros': summaries['retiros'],
            'cambios_plan': summaries['cambios_plan'],
            'balance_neto': (
                summaries['nuevo_contrato']['count']
                + summaries['recontrataciones']['count']
                - summaries['retiros']['count']
            ),
            'series': series,
            'comparativa': series,
            'servicios': services,
            'planes': plans,
            'zonas': zones,
            'canales_captacion': {
                'total': channel_total,
                'principal': channels[0] if channels else None,
                'items': channels,
                'series': channels_by_day,
            },
            'categorias': movement_breakdown,
            'selected': selected_summary,
            'category_analysis': category_analysis,
        }

    def get(self, request):
        try:
            today = timezone.localdate()
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)

            movement_type = request.query_params.get('movement_type', 'all')
            if movement_type not in self.MOVEMENT_TYPES:
                return Response({
                    'error': 'movement_type no valido',
                    'allowed': sorted(self.MOVEMENT_TYPES),
                }, status=status.HTTP_400_BAD_REQUEST)

            is_admin = can_supervise_productivity(request.user)
            if is_admin:
                try:
                    from_date, to_date = self._parse_range(
                        request.query_params, today)
                except ValueError as exc:
                    return Response({'error': str(exc)},
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                # El período personal siempre es hoy. No se confía en
                # from/to enviados por el cliente.
                from_date = to_date = today

            all_sales = Sale.objects.filter(deleted_at__isnull=True)
            if not is_admin:
                all_sales = all_sales.filter(createdBy=request.user)
            # Retiros y cambios se derivan del MODO del catálogo. Los dos
            # tipos de alta comerciales se separan por su código histórico.
            catalog = request_type_catalog()
            categories = self._category_codes(catalog)
            installations = all_sales.filter(
                requestType__in=categories['instalaciones'])
            new_contracts = all_sales.filter(
                requestType__in=categories['nuevo_contrato'])
            rehires = all_sales.filter(
                requestType__in=categories['recontrataciones'])
            retiro_codes = categories['retiros']

            def stats(qs, start_date, end_date):
                filtered = qs.filter(date__gte=start_date, date__lte=end_date)
                return self._summary(filtered)

            def retiros_stats(start_date, end_date):
                sale_retiros = all_sales.filter(requestType__in=retiro_codes,
                                               date__gte=start_date,
                                               date__lte=end_date)
                return self._summary(sale_retiros)

            empty = {'count': 0, 'total': 0}

            legacy = {
                'movimientos': {
                    'today': stats(all_sales, today, today),
                    'week': stats(all_sales, week_start, today) if is_admin else empty,
                    'month': stats(all_sales, month_start, today) if is_admin else empty,
                },
                'instalaciones': {
                    'today': stats(installations, today, today),
                    'week': stats(installations, week_start, today) if is_admin else empty,
                    'month': stats(installations, month_start, today) if is_admin else empty,
                },
                'nuevo_contrato': {
                    'today': stats(new_contracts, today, today),
                    'week': stats(new_contracts, week_start, today) if is_admin else empty,
                    'month': stats(new_contracts, month_start, today) if is_admin else empty,
                },
                'recontrataciones': {
                    'today': stats(rehires, today, today),
                    'week': stats(rehires, week_start, today) if is_admin else empty,
                    'month': stats(rehires, month_start, today) if is_admin else empty,
                },
                'retiros': {
                    'today': retiros_stats(today, today),
                    'week': retiros_stats(week_start, today) if is_admin else empty,
                    'month': retiros_stats(month_start, today) if is_admin else empty,
                },
                'role': request.user.role,
            }

            selected_sales = self._selected_sales(
                categories, from_date, to_date, movement_type)

            return Response({
                **legacy,
                'analytics': self._analytics(
                    selected_sales, categories, from_date, to_date,
                    movement_type),
            })
        except Exception:
            # No devolver ceros ante un fallo: el frontend debe distinguir un
            # error de consulta de un período sin movimientos.
            logger.exception('Error calculando estadisticas del dashboard')
            return Response(
                {'error': 'No se pudieron calcular las estadísticas'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(responses={200: dict, 400: dict, 500: dict})
class DashboardDrilldownView(APIView):
    INDICATOR_CATEGORIES = {
        'nuevo_contrato': ('nuevo_contrato',),
        'recontrataciones': ('recontrataciones',),
        'retiros': ('retiros',),
        'cambios_plan': ('cambios_plan',),
        'traslados': ('traslados',),
        'adiciones': ('adiciones',),
        'altas_comerciales': ('nuevo_contrato', 'recontrataciones'),
        'balance_neto': (
            'nuevo_contrato', 'recontrataciones', 'retiros'),
        'zone': (),
        'plan': (),
        'channel': (),
        'motive': (),
    }

    def get(self, request):
        indicator = request.query_params.get('indicator', '')
        if indicator not in self.INDICATOR_CATEGORIES:
            return Response(
                {'error': {'indicator': 'Indicador no válido'}},
                status=status.HTTP_400_BAD_REQUEST)

        dashboard = DashboardStatsView()
        movement_type = request.query_params.get('movement_type', 'all')
        if movement_type not in dashboard.MOVEMENT_TYPES:
            return Response({
                'error': 'movement_type no válido',
                'allowed': sorted(dashboard.MOVEMENT_TYPES),
            }, status=status.HTTP_400_BAD_REQUEST)

        page, error = _query_int(request.query_params, 'page', 1)
        if error:
            return error
        page_size, error = _query_int(
            request.query_params, 'page_size', 25, maximum=100)
        if error:
            return error

        search = request.query_params.get('search', '').strip()
        if len(search) > 100:
            return Response(
                {'error': {'search': 'No puede superar 100 caracteres'}},
                status=status.HTTP_400_BAD_REQUEST)

        today = timezone.localdate()
        if can_supervise_productivity(request.user):
            try:
                from_date, to_date = dashboard._parse_range(
                    request.query_params, today)
            except ValueError as exc:
                return Response(
                    {'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # El detalle respeta la misma regla que los indicadores: solo hoy.
            from_date = to_date = today

        try:
            catalog = request_type_catalog()
            categories = dashboard._category_codes(catalog)
            filtered_sales = dashboard._selected_sales(
                categories, from_date, to_date, movement_type)
            breakdown = []
            zone_count = None
            plan_count = None
            channel_count = None
            motive_count = None
            category = None
            if indicator == 'zone':
                zone_name = request.query_params.get('zone_name', '').strip()
                if not zone_name or len(zone_name) > 120:
                    return Response(
                        {'error': {'zone_name': 'Zona no válida'}},
                        status=status.HTTP_400_BAD_REQUEST)

                zone_rows = dashboard._zone_rows(filtered_sales, categories)
                zone_request_codes = (
                    categories['nuevo_contrato']
                    + categories['recontrataciones']
                    + categories['traslados'])
                if zone_name == 'Otros barrios':
                    other_rows = zone_rows[5:]
                    zone_ids = [row['coverage_zone_id'] for row in other_rows]
                    zone_count = sum(row['count'] for row in other_rows)
                    selected_sales = filtered_sales.filter(
                        requestType__in=zone_request_codes,
                        coverage_zone_id__in=zone_ids)
                else:
                    selected_zone = next(
                        (row for row in zone_rows
                         if row['coverage_zone__name'] == zone_name),
                        None)
                    zone_count = selected_zone['count'] if selected_zone else 0
                    selected_sales = (
                        filtered_sales.filter(
                            requestType__in=zone_request_codes,
                            coverage_zone_id=selected_zone['coverage_zone_id'])
                        if selected_zone else filtered_sales.none())
            elif indicator == 'plan':
                plan_name = request.query_params.get('plan_name', '')
                catalog_label = request.query_params.get(
                    'catalog_label', '').strip()
                plan_type = request.query_params.get('plan_type', '').strip()
                if (
                        len(plan_name) > 120
                        or not catalog_label or len(catalog_label) > 120
                        or plan_type not in {'internet', 'tv', 'combo'}):
                    return Response(
                        {'error': {'plan': 'Plan no válido'}},
                        status=status.HTTP_400_BAD_REQUEST)
                demand_codes = (
                    categories.get(movement_type)
                    if movement_type != 'all' else
                    categories['nuevo_contrato']
                    + categories['recontrataciones'])
                selected_sales = filtered_sales.filter(
                    requestType__in=demand_codes,
                    plan__type=plan_type,
                    planName=plan_name,
                    plan__label=catalog_label,
                )
                plan_count = selected_sales.count()
            elif indicator == 'channel':
                channel_key = request.query_params.get('channel_key', '')
                channel_codes = categories['nuevo_contrato']
                if channel_key == 'channel-none':
                    channel_name = 'Sin especificar'
                    selected_sales = filtered_sales.filter(
                        requestType__in=channel_codes,
                        canal_captacion__isnull=True)
                elif channel_key.startswith('channel-') and channel_key[8:].isdigit():
                    channel_id = int(channel_key[8:])
                    channel = CanalCaptacion.objects.filter(
                        id=channel_id).first()
                    if channel is None:
                        return Response(
                            {'error': {'channel_key': 'Canal no válido'}},
                            status=status.HTTP_400_BAD_REQUEST)
                    channel_name = channel.nombre
                    selected_sales = filtered_sales.filter(
                        requestType__in=channel_codes,
                        canal_captacion_id=channel_id)
                else:
                    return Response(
                        {'error': {'channel_key': 'Canal no válido'}},
                        status=status.HTTP_400_BAD_REQUEST)
                channel_count = selected_sales.count()
            elif indicator == 'motive':
                motive_id = request.query_params.get('motive_id', '').strip()
                if not motive_id.isdigit():
                    return Response(
                        {'error': {'motive_id': 'Motivo no válido'}},
                        status=status.HTTP_400_BAD_REQUEST)
                motive = Motivo.objects.filter(id=int(motive_id)).first()
                if motive is None:
                    return Response(
                        {'error': {'motive_id': 'Motivo no válido'}},
                        status=status.HTTP_400_BAD_REQUEST)
                selected_sales = filtered_sales.filter(motivo_id=motive.id)
                motive_count = selected_sales.count()
            else:
                relevant_categories = self.INDICATOR_CATEGORIES[indicator]
                category = request.query_params.get(
                    'category', relevant_categories[0])
                if category not in relevant_categories:
                    return Response(
                        {'error': {'category': 'Categoría no válida para el indicador'}},
                        status=status.HTTP_400_BAD_REQUEST)

                for name in relevant_categories:
                    summary = dashboard._summary(
                        filtered_sales.filter(requestType__in=categories[name]))
                    breakdown.append({
                        'category': name,
                        'label': {
                            'nuevo_contrato': 'Nuevos contratos',
                            'recontrataciones': 'Recontrataciones',
                            'retiros': 'Retiros',
                            'cambios_plan': 'Cambios de plan',
                            'traslados': 'Traslados externos',
                            'adiciones': 'Adiciones',
                        }[name],
                        **summary,
                    })

                selected_sales = filtered_sales.filter(
                    requestType__in=categories[category])

            if search:
                selected_sales = selected_sales.filter(
                    Q(clientName__icontains=search)
                    | Q(clientCode__icontains=search))

            total = selected_sales.count()
            start = (page - 1) * page_size
            items = selected_sales.select_related(
                'plan', 'planFromId', 'createdBy', 'coverage_zone',
                'canal_captacion', 'motivo', 'traslado_externo',
            ).order_by('-date', '-id')[start:start + page_size]

            serialized_items = SaleSerializer(
                items, many=True,
                context={'catalog': catalog}).data
            if indicator in {'zone', 'plan', 'channel'}:
                for item in serialized_items:
                    request_type = catalog.get(item['requestType'])
                    item['requestTypeLabel'] = (
                        request_type.nombre if request_type
                        else item['requestType'])

            if indicator == 'zone':
                indicator_count = zone_count
            elif indicator == 'plan':
                indicator_count = plan_count
            elif indicator == 'channel':
                indicator_count = channel_count
            elif indicator == 'motive':
                indicator_count = motive_count
            elif indicator == 'balance_neto':
                totals = {item['category']: item['count'] for item in breakdown}
                indicator_count = (
                    totals['nuevo_contrato'] + totals['recontrataciones']
                    - totals['retiros'])
            else:
                indicator_count = sum(item['count'] for item in breakdown)

            response_data = {
                'indicator': indicator,
                'category': category,
                'period': {
                    'from': from_date.isoformat(),
                    'to': to_date.isoformat(),
                    'movement_type': movement_type,
                },
                'indicator_count': indicator_count,
                'breakdown': breakdown,
                'items': serialized_items,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': max(1, (total + page_size - 1) // page_size),
            }
            if indicator == 'zone':
                response_data['zone_name'] = zone_name
                response_data['zone_count'] = zone_count
            elif indicator == 'plan':
                response_data['plan_name'] = plan_name
                response_data['catalog_label'] = catalog_label
                response_data['plan_type'] = plan_type
                response_data['plan_count'] = plan_count
            elif indicator == 'channel':
                response_data['channel_key'] = channel_key
                response_data['channel_name'] = channel_name
                response_data['channel_count'] = channel_count
            elif indicator == 'motive':
                response_data['motive_id'] = motive.id
                response_data['motive_name'] = motive.nombre
                response_data['motive_count'] = motive_count
            return Response(response_data)
        except Exception:
            logger.exception(
                'Error consultando detalle del dashboard comercial')
            return Response(
                {'error': 'No se pudo consultar el detalle comercial'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CommercialProductivityView(APIView):
    """Productividad comercial con alcance decidido exclusivamente en backend.

    ``Sale.createdBy`` representa quién registró la solicitud. El modelo no
    tiene una relación confiable de atención/completado, por lo que esas
    métricas se exponen explícitamente como no disponibles.
    """

    def get(self, request):
        user = request.user
        if not (
            has_permission(user, 'dashboard.view')
            or has_permission(user, 'comercial.view')
        ):
            return Response(
                {'error': 'No tienes permiso para consultar productividad'},
                status=status.HTTP_403_FORBIDDEN)

        today = timezone.localdate()
        if can_supervise_productivity(user):
            try:
                from_date, to_date = DashboardStatsView._parse_range(
                    request.query_params, today)
            except ValueError as exc:
                return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # La productividad personal no admite consultas históricas.
            from_date = to_date = today

        movement_type = request.query_params.get('movement_type', 'all')
        if movement_type not in DashboardStatsView.MOVEMENT_TYPES:
            return Response(
                {'error': 'movement_type no válido'},
                status=status.HTTP_400_BAD_REQUEST)
        page, error = _query_int(request.query_params, 'page', 1)
        if error:
            return error
        page_size, error = _query_int(
            request.query_params, 'page_size', 25, maximum=100)
        if error:
            return error

        catalog = request_type_catalog()
        categories = DashboardStatsView._category_codes(catalog)
        sales = Sale.objects.filter(
            deleted_at__isnull=True,
            created_at__date__gte=from_date,
            created_at__date__lte=to_date,
        )
        if movement_type != 'all':
            sales = sales.filter(requestType__in=categories[movement_type])

        supervisor = can_supervise_productivity(user)
        requested_user_id = request.query_params.get('user_id')
        if requested_user_id not in (None, ''):
            try:
                requested_user_id = int(requested_user_id)
            except (TypeError, ValueError):
                return Response({'error': 'user_id no válido'}, status=status.HTTP_400_BAD_REQUEST)
            if not supervisor and requested_user_id != user.id:
                return Response(
                    {'error': 'Solo puedes consultar tu propia productividad'},
                    status=status.HTTP_403_FORBIDDEN)
            sales = sales.filter(createdBy_id=requested_user_id)
        if not supervisor:
            # Nunca se toma un user_id enviado por el cliente: el alcance
            # personal siempre se deriva de request.user.
            sales = sales.filter(createdBy=user)

        grouped = list(sales.values(
            'createdBy_id', 'createdBy__name',
        ).annotate(
            registered=Count('id'),
            last_activity=Max('created_at'),
        ).order_by('-registered', 'createdBy__name', 'createdBy_id'))

        if not supervisor:
            # La respuesta personal no filtra por nombres del cliente ni por
            # IDs externos; solo devuelve la cuenta autenticada.
            grouped = [{
                'createdBy_id': user.id,
                'createdBy__name': user.name,
                'registered': grouped[0]['registered'] if grouped else 0,
                'last_activity': grouped[0]['last_activity'] if grouped else None,
            }]

        total_registered = sales.count()
        active_users = len([row for row in grouped if row['registered']])
        total = sales.count()
        start = (page - 1) * page_size
        items = sales.select_related(
            'plan', 'createdBy', 'motivo', 'customer',
        ).order_by('-created_at', '-id')[start:start + page_size]
        serialized = SaleSerializer(items, many=True, context={'catalog': catalog}).data
        for payload, item in zip(serialized, items):
            payload['createdAt'] = item.created_at.isoformat() if item.created_at else None
            payload['registeredBy'] = {
                'id': item.createdBy_id,
                'name': item.createdBy.name,
            }
            # No existe actualmente un responsable/fecha de atención fiable.
            payload['attendedBy'] = None
            payload['attendedAt'] = None

        def user_row(row):
            return {
                'userId': row['createdBy_id'],
                'userName': row['createdBy__name'],
                'registered': row['registered'],
                'attended': None,
                'lastActivity': (
                    row['last_activity'].isoformat()
                    if row['last_activity'] else None
                ),
            }

        rows = [user_row(row) for row in grouped]
        daily = sales.values('created_at__date').annotate(
            registered=Count('id'),
        ).order_by('created_at__date')
        daily_map = {row['created_at__date']: row['registered'] for row in daily}
        series = []
        current = from_date
        while current <= to_date:
            series.append({
                'date': current.isoformat(),
                'registered': daily_map.get(current, 0),
                'attended': None,
            })
            current += timedelta(days=1)

        return Response({
            'scope': 'general' if supervisor else 'personal',
            'viewer': {
                'id': user.id,
                'name': user.name,
                'role': user.role,
            },
            'period': {
                'from': from_date.isoformat(),
                'to': to_date.isoformat(),
                'movement_type': movement_type,
            },
            'summary': {
                'registered': total_registered,
                'activeUsers': active_users,
                'attended': None,
                'attendedAvailable': False,
            },
            'users': rows if supervisor else rows[:1],
            'series': series,
            'items': serialized,
            'page': page,
            'page_size': page_size,
            'total': total,
            'total_pages': max(1, (total + page_size - 1) // page_size),
        })


def _first_error(serializer):
    errors = serializer.errors
    if isinstance(errors, dict):
        for key, value in errors.items():
            if isinstance(value, list) and value:
                return str(value[0])
            return str(value)
    return 'Error de validación'


@extend_schema(exclude=True)
class BackupListView(PermissionMixin, APIView):
    permission_code = 'respaldos.backups.view'
    """Historial de respaldos. Solo metadatos: el archivo nunca se conserva."""

    def get(self, request):
        error = self.check_permission(request)
        if error:
            return error
        backups = Backup.objects.all()[:50]
        serializer = BackupSerializer(backups, many=True)
        return Response(serializer.data)

    def post(self, request):
        global _backup_in_progress
        error = self.check_permission(request, 'respaldos.backups.create')
        if error:
            return error

        # Mutex: la base de datos garantiza un unico respaldo 'running'
        # (restriccion backup_unico_en_proceso). Se usa eso en vez de un
        # bloqueo consultivo porque el transaction pooler de Supabase no
        # los soporta, y el mutex en memoria no sirve entre workers.
        with _backup_lock:
            if _backup_in_progress:
                return Response(
                    {'error': 'Ya hay un respaldo en proceso. Intente en un momento.'},
                    status=status.HTTP_409_CONFLICT)
            _backup_in_progress = True

        backup = None
        filepath = None
        response = None
        try:
            from .management.commands.backup_database import (
                create_backup, cleanup_old_backups, BackupError,
            )
            try:
                backup, filepath = create_backup(
                    backup_type='manual', user=request.user)
            except BackupError as e:
                # El mensaje ya viene saneado por el comando.
                if 'en proceso' in str(e):
                    return Response(
                        {'error': str(e)},
                        status=status.HTTP_409_CONFLICT)
                return Response({'error': str(e)},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except Exception:
                return Response(
                    {'error': 'No se pudo generar el respaldo. Intente nuevamente.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            cleanup_old_backups(keep=12)

            # El archivo se transmite y lo borra _BackupFileResponse al
            # terminar la respuesta: en el servidor no queda nada.
            record_audit(
                request, 'backup_created', 'backup', backup.id,
                module='respaldos',
                after={'filename': backup.filename, 'size': backup.size,
                       'checksum': backup.checksum})
            response = _stream_backup_file(
                filepath, backup.filename, backup.checksum)
            return response
        finally:
            # Si nunca se llego a construir la respuesta, el archivo se
            # elimina aqui para no dejar residuos.
            if response is None and filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except OSError:
                    pass
            if backup:
                backup.storage_path = ''
                backup.save(update_fields=['storage_path'])
            with _backup_lock:
                _backup_in_progress = False


@extend_schema(responses={204: None, 404: dict})
class BackupDeleteView(PermissionMixin, APIView):
    permission_code = 'respaldos.backups.delete'
    def delete(self, request, pk):
        error = self.check_permission(request)
        if error:
            return error
        try:
            backup = Backup.objects.get(id=pk)
        except Backup.DoesNotExist:
            return Response(
                {'error': 'Backup no encontrado'},
                status=status.HTTP_404_NOT_FOUND)

        if backup.storage_path and os.path.exists(backup.storage_path):
            try:
                os.remove(backup.storage_path)
            except OSError:
                pass
        record_audit(request, 'backup_deleted', 'backup', backup.id,
                     module='respaldos',
                     before={'filename': backup.filename,
                             'size': backup.size})
        backup.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
