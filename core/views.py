import logging
import os
import threading
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta

from django.db.models import Count, Q, Sum
from django.http import FileResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .models import User, Customer, Plan, Promotion, Sale, Backup, TipoSolicitud, Motivo
from .serializers import (
    UserSerializer, UserWriteSerializer, PlanSerializer,
    PlanPublicSerializer, CustomerSerializer, SaleSerializer,
    SaleCreateSerializer, BackupSerializer,
    PromotionSerializer, PromotionWriteSerializer,
    TipoSolicitudPublicSerializer, MotivoSerializer, MotivoPublicSerializer,
)
from .domain import (
    request_type_mode, request_type_catalog,
    MODO_RETIRO, MODO_CAMBIO_PLAN, MODO_ADICION,
    MODO_SIMPLE,
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


class HealthView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        from django.db import connection
        try:
            with connection.cursor() as cursor:
                if connection.vendor == 'postgresql':
                    cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")
                else:
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [r[0] for r in cursor.fetchall()]
            user_count = User.objects.count()
            plan_count = Plan.objects.count()
            return Response({
                'status': 'ok',
                'tables': tables,
                'users': user_count,
                'plans': plan_count,
                'db': str(connection.settings_dict['NAME']),
                'version': 'v3-render',
            })
        except Exception as e:
            return Response({'status': 'error', 'detail': str(e)}, status=500)


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


class MeView(APIView):
    def get(self, request):
        return Response({'user': _user_payload(request.user)})


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
        if Sale.objects.filter(plan=plan).exists():
            return Response({'error': 'No se puede eliminar: tiene ventas asociadas'},
                            status=status.HTTP_400_BAD_REQUEST)
        # Tambien como plan anterior: borrarlo dejaria movimientos historicos
        # sin origen, que es justo lo que el cambio de plan debe conservar.
        if Sale.objects.filter(planFromId=plan).exists():
            return Response({'error': 'No se puede eliminar: es el plan anterior de un cambio de plan'},
                            status=status.HTTP_400_BAD_REQUEST)
        plan.delete()
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


class ActivePlansView(APIView):
    def get(self, request):
        plans = Plan.objects.filter(active=True).order_by('type', 'code')
        return Response(PlanPublicSerializer(plans, many=True).data)


class ActiveRequestTypesView(APIView):
    """Catalogo para el formulario de movimientos.

    Sin IsAdminMixin, igual que ActivePlansView: el operador registra
    movimientos y necesita los tipos, aunque no pueda administrarlos.
    """

    def get(self, request):
        return Response(TipoSolicitudPublicSerializer(
            TipoSolicitud.objects.filter(activo=True), many=True).data)


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
        # La FK es PROTECT: borrar un motivo usado dejaria el historial sin
        # trazabilidad. Se desactiva en su lugar.
        if Sale.objects.filter(motivo=motivo).exists():
            return Response(
                {'error': 'No se puede eliminar: tiene solicitudes asociadas. '
                          'Desactivelo en su lugar para que deje de ofrecerse.'},
                status=status.HTTP_400_BAD_REQUEST)
        motivo.delete()
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
        promo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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


class CustomerListView(APIView):
    """Busqueda de clientes por kardex o nombre (para autocompletar)."""
    def get(self, request):
        q = request.query_params.get('q', '').strip()
        qs = Customer.objects.all().order_by('code')
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q))
        return Response(CustomerSerializer(qs[:20], many=True).data)


class SaleListView(APIView):
    def get(self, request):
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        rtype = request.query_params.get('requestType')
        stype = request.query_params.get('serviceType')
        stype_from = request.query_params.get('serviceTypeFrom')
        qs = Sale.objects.select_related('plan', 'planFromId', 'createdBy').all().order_by('-date', '-id')
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
        page = max(1, int(request.query_params.get('page', 1)))
        page_size = max(1, int(request.query_params.get('page_size', 25)))
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
        logger.warning('SaleListView POST data: %s', data)
        try:
            serializer = SaleCreateSerializer(data=data, context={'user': request.user})
            if not serializer.is_valid():
                return Response({'error': _first_error(serializer)}, status=status.HTTP_400_BAD_REQUEST)
            sale = serializer.save()
            return Response(SaleSerializer(sale).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error('SaleListView POST error: %s\n%s', e, traceback.format_exc())
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SaleDetailView(IsAdminMixin, APIView):
    def delete(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        try:
            sale = Sale.objects.get(id=pk)
        except Sale.DoesNotExist:
            return Response({'error': 'Venta no encontrada'}, status=status.HTTP_404_NOT_FOUND)
        sale.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def put(self, request, pk):
        error = self.check_admin(request)
        if error:
            return error
        try:
            sale = Sale.objects.get(id=pk)
        except Sale.DoesNotExist:
            return Response({'error': 'Venta no encontrada'}, status=status.HTTP_404_NOT_FOUND)

        from .domain import (
            SERVICE_TYPE_LABELS, SERVICE_TYPE_TO_PLAN_TYPE,
            motivo_categoria_de_modo)
        from .serializers import (
            SaleSerializer, resolve_sale_prices, validate_cambio_plan,
            resolve_motivo)

        data = request.data
        old_plan_id = sale.plan_id
        old_plan_from_id = sale.planFromId_id

        plan = sale.plan
        if data.get('planId'):
            plan = Plan.objects.filter(id=data['planId'], active=True).first()
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

        # Un cambio de plan no puede apuntar a un plan legacy. Se permite
        # editar un movimiento historico que ya tenia ese plan como destino.
        if (mode == MODO_CAMBIO_PLAN and plan.legacy
                and (plan.id != old_plan_id or mode_changed)):
            return Response(
                {'error': 'No se puede cambiar a un plan anterior (legacy)'},
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

        # Mismos precios que en el alta: la edicion no puede inventarse
        # una regla de cobro distinta a la del registro original.
        installation, monthly, total = resolve_sale_prices(
            plan, sale.promotion, request_type)
        sale.applied_installation = installation
        sale.applied_monthly = monthly
        sale.total = total

        sale.lastEditedBy = request.user
        sale.lastEditedAt = timezone.now()
        sale.save()
        return Response(SaleSerializer(sale).data)


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
        user.delete()
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

            all_sales = Sale.objects.all()
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
