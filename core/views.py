import json
import logging
import os
import threading
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta

from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Count, Q, Sum
from django.http import FileResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .models import (
    User, Customer, Plan, Promotion, Sale, Backup, TipoSolicitud, Motivo,
    TarifaTraslado, TarifaTrasladoHistorial, SaleIdempotencyKey,
)
from .serializers import (
    UserSerializer, UserWriteSerializer, PlanSerializer,
    PlanPublicSerializer, CustomerSerializer, SaleSerializer,
    SaleCreateSerializer, BackupSerializer,
    PromotionSerializer, PromotionWriteSerializer,
    TipoSolicitudPublicSerializer, MotivoSerializer, MotivoPublicSerializer,
    TarifaTrasladoSerializer, TarifaTrasladoHistorialSerializer,
)
from .domain import (
    request_type_mode, request_type_catalog,
    MODO_RETIRO, MODO_CAMBIO_PLAN, MODO_ADICION,
    MODO_SIMPLE, MODO_TRASLADO,
)
from .reports import build_sales_pdf, build_sales_xlsx

# Evita que dos respaldos corran a la vez. Con gunicorn --workers 2 este
# lock es por proceso, lo cual es suficiente para el caso de un unico
# administrador y evita agotar la CPU del plan gratuito.
_backup_lock = threading.Lock()
_backup_in_progress = False
logger = logging.getLogger(__name__)


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
    return {'id': user.id, 'name': user.name,
            'role': user.role, 'active': user.active}


class IsAdminMixin:
    def check_admin(self, request):
        user = request.user
        if not user or not getattr(user, 'active', True) or user.role != 'admin':
            return Response({'error': 'Se requieren permisos de administrador'},
                            status=status.HTTP_403_FORBIDDEN)
        return None


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
        name = (request.data.get('name') or '').strip()
        password = request.data.get('password') or ''

        if not name:
            return Response({'error': 'Usuario requerido'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({'error': 'Contraseña requerida'},
                            status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(name__iexact=name, active=True).first()
        if user and not user.check_password(password):
            user = None

        if user is None:
            return Response({'error': 'Credenciales inválidas'},
                            status=status.HTTP_401_UNAUTHORIZED)

        token = RefreshToken.for_user(user)
        return Response({'token': str(token.access_token), 'user': _user_payload(user)})


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
        current = request.data.get('current_password', '')
        new_password = request.data.get('new_password', '')

        if not current or not new_password:
            return Response({'error': 'Completa ambos campos'},
                            status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 6:
            return Response({'error': 'La nueva contrasena debe tener al menos 6 caracteres'},
                            status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user.check_password(current):
            return Response({'error': 'La contrasena actual es incorrecta'},
                            status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({'message': 'Contrasena actualizada correctamente'})


@extend_schema_view(
    get=extend_schema(responses={200: PlanSerializer(many=True)}),
    post=extend_schema(request=PlanSerializer, responses={201: PlanSerializer, 400: dict}),
)
class PlanListView(IsAdminMixin, APIView):
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
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    put=extend_schema(request=PlanSerializer, responses={200: PlanSerializer, 400: dict, 404: dict}),
    delete=extend_schema(responses={204: None, 400: dict, 404: dict}),
)
class PlanDetailView(IsAdminMixin, APIView):
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
        serializer.save()
        return Response(serializer.data)


@extend_schema(responses={200: PlanPublicSerializer(many=True)})
class ActivePlansView(APIView):
    def get(self, request):
        plans = Plan.objects.filter(active=True).order_by('type', 'code')
        return Response(PlanPublicSerializer(plans, many=True).data)


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
        serializer.save()
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
        serializer.save()
        return Response(serializer.data)


@extend_schema_view(
    get=extend_schema(responses={200: PromotionSerializer(many=True)}),
    post=extend_schema(request=PromotionWriteSerializer, responses={201: PromotionSerializer, 400: dict}),
)
class PromotionListView(IsAdminMixin, APIView):
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
        return Response(PromotionSerializer(promo).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    put=extend_schema(request=PromotionWriteSerializer, responses={200: PromotionSerializer, 400: dict, 404: dict}),
    delete=extend_schema(responses={204: None, 400: dict, 404: dict}),
)
class PromotionDetailView(IsAdminMixin, APIView):
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
            promo.active = data.get('active', promo.active)
            promo.save()
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
        return Response(TarifaTrasladoSerializer(tariff).data, status=201)


@extend_schema_view(
    get=extend_schema(responses={200: TarifaTrasladoSerializer, 400: dict, 404: dict}),
    put=extend_schema(request=dict, responses={200: TarifaTrasladoSerializer, 400: dict, 404: dict}),
)
class TransferTariffDetailView(IsAdminMixin, APIView):
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
        qs = Customer.objects.all().order_by('code')
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q))
        return Response(CustomerSerializer(qs[:20], many=True).data)


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
        qs = Sale.objects.select_related('plan', 'planFromId', 'createdBy').filter(
            deleted_at__isnull=True).order_by('-date', '-id')
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

        return Response({
            # El catalogo va en el context: sin esto, get_previousService y
            # get_isServiceChange lo pedirian una vez por cada venta de la pagina.
            'items': SaleSerializer(
                items, many=True,
                context={'catalog': request_type_catalog()}).data,
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
        if (hasattr(sale, 'traslado_externo')
                or sale.idempotency_keys.exists()):
            return Response(
                {'error': 'No se puede eliminar la solicitud porque tiene '
                          'dependencias o forma parte del historial.'},
                status=status.HTTP_409_CONFLICT)
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
            resolve_motivo)

        data = request.data
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
        else:
            service_type_from = None
            plan_from = None
            if mode != MODO_ADICION:
                data = {**data, 'additionType': ''}

        sale.date = data.get('date', sale.date)
        sale.clientCode = data.get('clientCode', sale.clientCode)
        sale.clientName = data.get('clientName', sale.clientName)
        sale.serviceType = service_type
        sale.requestType = request_type
        sale.additionType = data.get('additionType', sale.additionType)
        sale.changeReason = change_reason
        sale.motivo = motivo
        sale.notes = data.get('notes', sale.notes)
        sale.plan = plan
        if plan.id != old_plan_id or not sale.planName:
            sale.planName = plan.label
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
class UserListView(IsAdminMixin, APIView):
    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error
        return Response(UserSerializer(User.objects.all().order_by('id'), many=True).data)

    def post(self, request):
        error = self.check_admin(request)
        if error:
            return error
        serializer = UserWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': _first_error(serializer)}, status=status.HTTP_400_BAD_REQUEST)
        if not request.data.get('password'):
            return Response({'error': 'La contraseña es requerida'},
                            status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    put=extend_schema(request=UserWriteSerializer, responses={200: UserSerializer, 400: dict, 404: dict}),
    delete=extend_schema(responses={204: None, 400: dict, 404: dict, 409: dict}),
)
class UserDetailView(IsAdminMixin, APIView):
    def delete(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response({'error': 'Usuario no encontrado'}, status=status.HTTP_404_NOT_FOUND)
        if user == request.user:
            return Response({'error': 'No puedes eliminarte a ti mismo'},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            user.active = False
            user.save(update_fields=['active'])
        except ProtectedError:
            return Response(
                {'error': 'No se puede eliminar el usuario porque tiene '
                          'registros asociados.'},
                status=status.HTTP_409_CONFLICT)
        from .audit import record_audit
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
        serializer = UserWriteSerializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'error': _first_error(serializer)}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(UserSerializer(user).data)


@extend_schema(responses={200: dict, 400: dict, 500: dict})
class DashboardStatsView(APIView):
    MOVEMENT_TYPES = {
        'all', 'nuevo_contrato', 'recontrataciones', 'instalaciones',
        'retiros', 'cambios_plan',
        'adiciones', 'otros',
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
        for name, mode in (
            ('retiros', MODO_RETIRO),
            ('cambios_plan', MODO_CAMBIO_PLAN),
            ('adiciones', MODO_ADICION),
        ):
            categories[name] = [
                code for code, tipo in catalog.items()
                if code not in classified and tipo.modo == mode]
            classified.update(categories[name])
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

        service_rows = queryset.values('serviceType').annotate(
            count=Count('id'), total=Sum('total')).order_by('serviceType')
        service_labels = {
            'internet': 'Internet',
            'tv': 'TV analógica',
            'tv_digital': 'TV digital',
            'combo_analog': 'Internet + TV analógica',
            'combo_digital': 'Internet + TV digital',
        }
        services = [
            {
                'serviceType': row['serviceType'],
                'label': service_labels.get(row['serviceType'], row['serviceType']),
                'count': row['count'],
                'total': cls._amount(row['total']),
            }
            for row in service_rows
        ]

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
            'categorias': movement_breakdown,
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

            is_admin = getattr(request.user, 'role', '') == 'admin'
            if is_admin:
                try:
                    from_date, to_date = self._parse_range(
                        request.query_params, today)
                except ValueError as exc:
                    return Response({'error': str(exc)},
                                    status=status.HTTP_400_BAD_REQUEST)
            else:
                from_date = to_date = today

            all_sales = Sale.objects.filter(deleted_at__isnull=True)
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

            selected_sales = all_sales.filter(
                date__gte=from_date, date__lte=to_date)
            if movement_type != 'all':
                selected_sales = selected_sales.filter(
                    requestType__in=categories[movement_type])

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


def _first_error(serializer):
    errors = serializer.errors
    if isinstance(errors, dict):
        for key, value in errors.items():
            if isinstance(value, list) and value:
                return str(value[0])
            return str(value)
    return 'Error de validación'


@extend_schema(exclude=True)
class BackupListView(IsAdminMixin, APIView):
    """Historial de respaldos. Solo metadatos: el archivo nunca se conserva."""

    def get(self, request):
        error = self.check_admin(request)
        if error:
            return error
        backups = Backup.objects.all()[:50]
        serializer = BackupSerializer(backups, many=True)
        return Response(serializer.data)

    def post(self, request):
        global _backup_in_progress
        error = self.check_admin(request)
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
class BackupDeleteView(IsAdminMixin, APIView):
    def delete(self, request, pk):
        error = self.check_admin(request)
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
        backup.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
