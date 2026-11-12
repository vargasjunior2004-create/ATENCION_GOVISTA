from decimal import Decimal
from django.db import DatabaseError, connection

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import (
    User, Customer, Contract, CoverageZone, Role, Permission, RolePermission, UserRole,
    TemporaryFunction, TemporaryAssignment, Plan, Promotion, Sale, Backup, TipoSolicitud, Motivo,
    TarifaTraslado, TarifaTrasladoHistorial, TrasladoExterno,
    InventarioMovimiento, CanalCaptacion,
    CustomerLocation, CustomerLocationHistory,
)
from .models import normalize_canal_captacion_name
from .domain import (
    SERVICE_TYPE_LABELS, SERVICE_TYPE_FAMILY, SERVICE_TYPE_TO_PLAN_TYPE,
    service_family_label, previous_service_family, is_service_change,
    request_type_mode, request_type_catalog,
    movement_status_for_request_type,
    SOLICITUD_STATUS_CHOICES,
    MODO_ADICION, MODO_CAMBIO_PLAN, MODO_RETIRO, MODO_TRASLADO,
    MODOS_SOLO_MENSUAL,
    plan_is_selectable,
    motivo_categoria_de_modo, MOTIVO_CAMBIO,
)
from .rbac import can_register_external_sale


def sale_catalog(serializer_or_context=None):
    """Catalogo de tipos de solicitud para usar en un bucle.

    SaleSerializer se usa sobre listas de movimientos, y pedir el catalogo
    por fila seria una consulta por venta. Los llamadores lo ponen en el
    context; si no esta, se genera aqui.
    """
    context = getattr(serializer_or_context, 'context', serializer_or_context)
    if isinstance(context, dict) and context.get('catalog') is not None:
        return context['catalog']
    return request_type_catalog()


def resolve_sale_prices(plan, promotion, request_type, catalog=None):
    """Precios de un movimiento, siempre derivados del plan en el servidor.

    Se comparte entre el alta y la edicion para que ambas rutas apliquen
    exactamente la misma regla. Las reglas vienen del MODO del tipo de
    solicitud, no de su nombre.
    """
    if promotion:
        installation = (promotion.installation_price
                        if promotion.apply_installation else plan.installation)
        monthly = (promotion.monthly_price
                   if promotion.apply_monthly else plan.monthly)
    else:
        installation = plan.installation
        monthly = plan.monthly

    mode = request_type_mode(request_type, catalog)
    if mode in (MODO_ADICION, MODO_CAMBIO_PLAN):
        installation = Decimal('0')
    if mode in MODOS_SOLO_MENSUAL:
        total = monthly
    else:
        total = monthly + installation
    return installation, monthly, total


def validate_service_from(plan_from, service_type_from, errors):
    """Comprueba que el servicio anterior sea coherente con su plan."""
    if not service_type_from:
        return
    if service_type_from not in SERVICE_TYPE_LABELS:
        errors['serviceTypeFrom'] = 'Tipo de servicio anterior no valido'
        return
    expected = SERVICE_TYPE_FAMILY.get(service_type_from)
    if plan_from is not None and plan_from.type != expected:
        errors['serviceTypeFrom'] = (
            f'El servicio anterior no corresponde al plan anterior '
            f'({plan_from.code})')


def validate_service_movement(plan, plan_from, service_type, service_type_from,
                              *, movement='cambio_plan', change_reason='',
                              addition_type=None):
    """Valida el movimiento común de servicio/plan.

    Una adición y un cambio de plan son el mismo movimiento de dominio:
    parten de un servicio/plan y llegan a otro. ``movement`` solo determina
    la clasificación comercial: la adición exige coherencia con el servicio
    incorporado, mientras el cambio de plan exige plan anterior y motivo.
    """
    errors = {}
    is_addition = movement == MODO_ADICION
    if not is_addition and plan_from is None:
        errors['planFromId'] = 'Debe seleccionar el plan anterior'
    if movement == MODO_CAMBIO_PLAN and not (change_reason or '').strip():
        errors['changeReason'] = 'Debe indicar el motivo del cambio de plan'

    # Un movimiento que no cambia nada no es válido. Se admite el mismo plan
    # si cambia la variante del servicio (combo analógico -> digital).
    if plan_from is not None and plan_from.id == plan.id:
        same_service = (not service_type_from
                        or service_type_from == service_type)
        if same_service:
            errors['planFromId'] = (
                'El plan anterior y el nuevo son el mismo: '
                'registre la solicitud con otro tipo')

    validate_service_from(plan_from, service_type_from, errors)

    if is_addition:
        current_family = SERVICE_TYPE_FAMILY.get(service_type_from)
        new_family = SERVICE_TYPE_FAMILY.get(service_type)
        if not service_type_from:
            errors['serviceTypeFrom'] = 'Debe seleccionar el servicio actual'
        elif current_family not in ('internet', 'tv'):
            errors['serviceTypeFrom'] = (
                'El servicio actual de una adición debe ser Internet o TV')
        if new_family != 'combo':
            errors['serviceType'] = (
                'El servicio nuevo de una adición debe ser un Combo')
        expected_addition = {
            'internet': 'adicion_tv',
            'tv': 'adicion_internet',
        }.get(current_family)
        if expected_addition and addition_type != expected_addition:
            errors['additionType'] = (
                'El tipo de adición no corresponde al servicio que se incorpora')
        if current_family and new_family == current_family:
            errors['serviceTypeFrom'] = (
                'La adición debe incorporar el servicio que falta')
    return errors


def validate_cambio_plan(plan, plan_from, service_type, service_type_from,
                         change_reason):
    """Compatibilidad: delega en la validación común de movimientos."""
    return validate_service_movement(
        plan, plan_from, service_type, service_type_from,
        movement=MODO_CAMBIO_PLAN, change_reason=change_reason)


def validate_adicion(plan, plan_from, service_type, service_type_from,
                     addition_type):
    """Compatibilidad: delega en la validación común de movimientos."""
    return validate_service_movement(
        plan, plan_from, service_type, service_type_from,
        movement=MODO_ADICION, addition_type=addition_type)


def resolve_motivo(motivo_id, mode, errors):
    """Resuelve el motivo de un movimiento y valida su categoria/estado.

    Un motivo inexistente, inactivo o de la categoria equivocada se
    apunta en `errors`. La obligatoriedad se decide en el llamador para
    no tapar otras validaciones (plan anterior, compatibilidad, etc.).
    Devuelve (motivo | None, categoria_esperada | None).
    """
    categoria = motivo_categoria_de_modo(mode)
    if categoria is None:
        return None, None
    if not motivo_id:
        return None, categoria
    try:
        motivo = Motivo.objects.get(id=motivo_id)
    except Motivo.DoesNotExist:
        errors['motivoId'] = 'Motivo no encontrado'
        return None, categoria
    if not motivo.activo:
        errors['motivoId'] = 'El motivo esta inactivo'
    elif motivo.categoria != categoria:
        errors['motivoId'] = 'El motivo no corresponde a este tipo de solicitud'
    return motivo, categoria


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'name', 'role', 'active', 'roles',
            'last_login_at', 'last_login_ip', 'must_change_password',
            'created_at',
        ]

    def get_roles(self, obj):
        return [
            {
                'id': assignment.role_id,
                'code': assignment.role.code,
                'name': assignment.role.name,
                'is_system_role': assignment.role.is_system_role,
                'grants_full_access': assignment.role.grants_full_access,
            }
            for assignment in obj.role_assignments.all()
            if assignment.active and assignment.role.active
        ]


class UserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    password_confirm = serializers.CharField(write_only=True, required=False)
    roleIds = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        write_only=True,
    )

    class Meta:
        model = User
        fields = [
            'id', 'name', 'password', 'password_confirm', 'active', 'roleIds',
        ]

    def validate(self, attrs):
        from .models import normalize_user_name
        from .passwords import PasswordPolicyError, validate_password

        if 'role' in self.initial_data:
            raise serializers.ValidationError({
                'role': 'El rol heredado ya no se registra; asigne roleIds.'
            })

        name = attrs.get('name')
        if name is not None:
            normalized = normalize_user_name(name)
            if not normalized:
                raise serializers.ValidationError(
                    {'name': 'El nombre no puede estar vacío.'})
            duplicates = User.objects.filter(name_normalized=normalized)
            if self.instance is not None:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    {'name': 'Ya existe un usuario con ese nombre.'})

        password = attrs.get('password')
        if password:
            confirmation = attrs.get('password_confirm')
            if confirmation is None:
                raise serializers.ValidationError({
                    'password_confirm': 'Confirme la contraseña.'})
            if password != confirmation:
                raise serializers.ValidationError({
                    'password_confirm': 'Las contraseñas no coinciden.'})
            try:
                validate_password(password, self.instance or User(
                    name=attrs.get('name') or ''))
            except PasswordPolicyError as exc:
                raise serializers.ValidationError({'password': str(exc)})

        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        validated_data.pop('password_confirm', None)
        validated_data.pop('roleIds', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_password('')
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        validated_data.pop('password_confirm', None)
        validated_data.pop('roleIds', None)
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)


class PermissionSerializer(serializers.ModelSerializer):
    code = serializers.ReadOnlyField()

    class Meta:
        model = Permission
        fields = [
            'id', 'code', 'module', 'resource', 'action', 'name',
            'description', 'active', 'is_reserved', 'sort_order',
        ]


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            'id', 'code', 'name', 'description', 'active',
            'is_system_role', 'grants_full_access', 'permissions',
            'user_count', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'is_system_role', 'grants_full_access', 'permissions',
            'user_count', 'created_at', 'updated_at',
        ]

    def validate_code(self, value):
        if self.instance is not None and value != self.instance.code:
            raise serializers.ValidationError(
                'El código del rol no se puede modificar.')
        return value

    def get_permissions(self, obj):
        permissions = Permission.objects.filter(
            role_permissions__role=obj, active=True).order_by(
                'module', 'resource', 'action')
        return PermissionSerializer(permissions, many=True).data

    def get_user_count(self, obj):
        return obj.user_assignments.filter(active=True).count()


class UserRoleSerializer(serializers.ModelSerializer):
    roleName = serializers.CharField(source='role.name', read_only=True)
    userName = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = UserRole
        fields = [
            'id', 'user', 'userName', 'role', 'roleName', 'assigned_by',
            'assigned_at', 'revoked_at', 'active',
        ]
        read_only_fields = ['assigned_by', 'assigned_at', 'revoked_at']


class TemporaryFunctionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemporaryFunction
        fields = ['id', 'code', 'name', 'description', 'active']


class TemporaryAssignmentSerializer(serializers.ModelSerializer):
    userName = serializers.CharField(source='user.name', read_only=True)
    functionName = serializers.CharField(source='function.name', read_only=True)
    assignedByName = serializers.CharField(source='assigned_by.name', read_only=True)

    class Meta:
        model = TemporaryAssignment
        fields = [
            'id', 'user', 'userName', 'function', 'functionName',
            'assigned_by', 'assignedByName', 'starts_at', 'ends_at',
            'finished_at', 'status', 'notes', 'created_at',
        ]
        read_only_fields = ['assigned_by', 'finished_at', 'created_at']


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'code', 'name', 'ci', 'phone', 'status', 'active']


class CustomerLocationSerializer(serializers.ModelSerializer):
    customerCode = serializers.CharField(source='customer.code', read_only=True)
    customerName = serializers.CharField(source='customer.name', read_only=True)
    photoUrl = serializers.SerializerMethodField()
    updatedBy = serializers.CharField(source='updated_by.name', read_only=True)
    createdBy = serializers.CharField(source='created_by.name', read_only=True)

    class Meta:
        model = CustomerLocation
        fields = [
            'id', 'customer', 'customerCode', 'customerName', 'photoUrl',
            'latitude', 'longitude', 'accuracy_meters', 'captured_at',
            'maps_url', 'source', 'createdBy', 'updatedBy', 'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'customerCode', 'customerName', 'photoUrl', 'createdBy',
            'updatedBy', 'created_at', 'updated_at',
        ]

    def get_photoUrl(self, obj):
        from .location_storage import signed_url
        try:
            return signed_url(obj.photo_path)
        except Exception:
            return ''


class CustomerLocationHistorySerializer(serializers.ModelSerializer):
    changedBy = serializers.CharField(source='changed_by.name', read_only=True)
    previousPhotoUrl = serializers.SerializerMethodField()
    newPhotoUrl = serializers.SerializerMethodField()

    class Meta:
        model = CustomerLocationHistory
        fields = [
            'id', 'change_type', 'changedBy', 'changed_at',
            'previousPhotoUrl', 'newPhotoUrl',
            'previous_latitude', 'previous_longitude',
            'previous_accuracy_meters', 'previous_maps_url', 'previous_source',
            'new_latitude', 'new_longitude', 'new_accuracy_meters',
            'new_maps_url', 'new_source',
        ]

    def get_previousPhotoUrl(self, obj):
        from .location_storage import signed_url
        try:
            return signed_url(obj.previous_photo_path)
        except Exception:
            return ''

    def get_newPhotoUrl(self, obj):
        from .location_storage import signed_url
        try:
            return signed_url(obj.new_photo_path)
        except Exception:
            return ''


class ContractSerializer(serializers.ModelSerializer):
    customerId = serializers.IntegerField(source='customer_id', read_only=True)
    saleId = serializers.IntegerField(source='sale_id', read_only=True)
    sellerUserId = serializers.IntegerField(
        source='seller_user_id', read_only=True)
    sellerName = serializers.CharField(source='seller_name', read_only=True)
    planLabel = serializers.SerializerMethodField()
    createdBy = serializers.SerializerMethodField()
    reviewedBy = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Contract
        fields = [
            'id', 'number', 'customerId', 'saleId', 'service_type',
            'plan', 'planLabel', 'contracted_on', 'status', 'origin',
            'external_seller', 'meter_number', 'meter_review_status',
            'sellerUserId', 'sellerName', 'meter_review_notes', 'reviewedBy',
            'meter_reviewed_at',
            'createdBy', 'created_at',
        ]
        read_only_fields = [
            'id', 'customerId', 'saleId', 'sellerUserId', 'sellerName',
            'planLabel', 'reviewedBy', 'meter_reviewed_at', 'createdBy',
            'created_at',
        ]

    def get_planLabel(self, obj):
        return obj.plan_name or obj.plan.label

    @extend_schema_field(str)
    def get_status(self, obj):
        """Prioriza el estado comercial persistido en la solicitud vinculada.

        Contract.status pertenece al ciclo operativo histórico del contrato
        (activo, retirado, etc.). Para contratos originados en Gestión
        Comercial, la fuente del estado mostrado es Sale.status.
        """
        sale = getattr(obj, 'sale', None)
        if sale is not None and sale.status:
            return dict(SOLICITUD_STATUS_CHOICES).get(sale.status, sale.status)
        return obj.get_status_display() if obj.status else None

    def get_createdBy(self, obj):
        return {'id': obj.created_by_id, 'name': obj.created_by.name}

    def get_reviewedBy(self, obj):
        if not obj.meter_reviewed_by:
            return None
        return {'id': obj.meter_reviewed_by_id, 'name': obj.meter_reviewed_by.name}


class PlanSerializer(serializers.ModelSerializer):
    total = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Plan
        fields = ['id', 'code', 'label', 'type', 'speed',
                  'monthly', 'installation', 'total', 'active', 'legacy']


class PlanPublicSerializer(serializers.ModelSerializer):
    total = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Plan
        fields = ['id', 'code', 'label', 'type', 'speed',
                  'monthly', 'installation', 'total', 'legacy', 'active']


class CoverageZoneSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source='created_by.name', read_only=True, default='')

    class Meta:
        model = CoverageZone
        fields = [
            'id', 'name', 'description', 'google_maps_url', 'is_active',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_by', 'created_by_name', 'created_at', 'updated_at',
        ]

    def validate_name(self, value):
        from .models import normalize_coverage_zone_name

        value = normalize_coverage_zone_name(value)
        if not value:
            raise serializers.ValidationError('El nombre de la zona es obligatorio')
        if len(value) > 120:
            raise serializers.ValidationError(
                'El nombre no puede superar 120 caracteres')
        normalized_name = value.casefold()
        zones = CoverageZone.objects.filter(normalized_name=normalized_name)
        if self.instance:
            zones = zones.exclude(pk=self.instance.pk)
        if zones.exists():
            raise serializers.ValidationError(
                'Ya existe una zona con ese nombre')
        return value


class MotivoSerializer(serializers.ModelSerializer):
    """CRUD administrativo de motivos."""

    class Meta:
        model = Motivo
        fields = ['id', 'categoria', 'nombre', 'descripcion',
                  'activo', 'orden', 'created_at']
        read_only_fields = ['created_at']


class MotivoPublicSerializer(serializers.ModelSerializer):
    """Lo que recibe el formulario de movimientos: solo motivos activos."""

    class Meta:
        model = Motivo
        fields = ['id', 'categoria', 'nombre', 'orden']


class TipoSolicitudPublicSerializer(serializers.ModelSerializer):
    """Lo que recibe el formulario de movimientos.

    `modo` viaja al frontend para que el formulario muestre plan anterior,
    motivo de retiro o tipo de adicion sin volver a codificar los nombres.
    """

    class Meta:
        model = TipoSolicitud
        fields = ['id', 'code', 'nombre', 'descripcion', 'modo', 'orden']


class CanalCaptacionSerializer(serializers.ModelSerializer):
    """CRUD administrativo de canales de captacion."""

    class Meta:
        model = CanalCaptacion
        fields = ['id', 'nombre', 'descripcion', 'activo',
                  'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_nombre(self, value):
        nombre = normalize_canal_captacion_name(value)
        if not nombre:
            raise serializers.ValidationError('El nombre es obligatorio')
        duplicados = CanalCaptacion.objects.filter(
            nombre_normalizado=nombre.casefold())
        if self.instance is not None:
            duplicados = duplicados.exclude(pk=self.instance.pk)
        if duplicados.exists():
            raise serializers.ValidationError(
                'Ya existe un canal con ese nombre')
        return nombre


class CanalCaptacionPublicSerializer(serializers.ModelSerializer):
    """Lo que recibe el selector "¿Como nos conocio?"."""

    class Meta:
        model = CanalCaptacion
        fields = ['id', 'nombre']


class PromotionSerializer(serializers.ModelSerializer):
    planLabel = serializers.SerializerMethodField()
    is_current = serializers.BooleanField(read_only=True)

    class Meta:
        model = Promotion
        fields = ['id', 'name', 'plan', 'planLabel',
                  'apply_installation', 'apply_monthly',
                  'installation_price', 'monthly_price',
                  'start_date', 'end_date', 'active',
                  'created_at', 'is_current']

    @extend_schema_field(str)
    def get_planLabel(self, obj):
        return f'{obj.plan.code} - {obj.plan.label}'


class PromotionWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    plan = serializers.IntegerField()
    apply_installation = serializers.BooleanField(default=False)
    apply_monthly = serializers.BooleanField(default=False)
    installation_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True)
    monthly_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    active = serializers.BooleanField(default=True)

    def validate(self, attrs):
        plan_id = attrs.get('plan')
        try:
            plan = Plan.objects.get(id=plan_id)
        except Plan.DoesNotExist:
            raise serializers.ValidationError(
                {'plan': 'Plan no encontrado, inactivo o anterior'})
        if not plan_is_selectable(plan):
            raise serializers.ValidationError(
                {'plan': 'Plan no encontrado, inactivo o anterior'})
        attrs['plan'] = plan

        if not attrs.get('apply_installation') and not attrs.get('apply_monthly'):
            raise serializers.ValidationError(
                'Debe seleccionar al menos un concepto (instalacion o mensualidad)')

        if attrs.get('apply_installation'):
            price = attrs.get('installation_price')
            if price is None:
                raise serializers.ValidationError(
                    {'installation_price': 'Precio de instalacion requerido'})
            if price < 0:
                raise serializers.ValidationError(
                    {'installation_price': 'El precio no puede ser negativo'})

        if attrs.get('apply_monthly'):
            price = attrs.get('monthly_price')
            if price is None:
                raise serializers.ValidationError(
                    {'monthly_price': 'Precio de mensualidad requerido'})
            if price < 0:
                raise serializers.ValidationError(
                    {'monthly_price': 'El precio no puede ser negativo'})

        if attrs['start_date'] > attrs['end_date']:
            raise serializers.ValidationError(
                'La fecha de fin debe ser mayor o igual a la fecha de inicio')

        return attrs


class TarifaTrasladoSerializer(serializers.ModelSerializer):
    serviceType = serializers.CharField(source='service_type', read_only=True)
    createdBy = serializers.SerializerMethodField()
    updatedBy = serializers.SerializerMethodField()

    class Meta:
        model = TarifaTraslado
        fields = ['id', 'service_type', 'serviceType', 'name', 'amount',
                  'active', 'created_at', 'updated_at', 'created_by',
                  'updated_by', 'createdBy', 'updatedBy']
        read_only_fields = ['created_at', 'updated_at', 'created_by',
                            'updated_by', 'createdBy', 'updatedBy']

    @extend_schema_field(dict)
    def get_createdBy(self, obj):
        return {'id': obj.created_by_id, 'name': obj.created_by.name} if obj.created_by else None

    @extend_schema_field(dict)
    def get_updatedBy(self, obj):
        return {'id': obj.updated_by_id, 'name': obj.updated_by.name} if obj.updated_by else None


class TarifaTrasladoHistorialSerializer(serializers.ModelSerializer):
    changedBy = serializers.SerializerMethodField()

    class Meta:
        model = TarifaTrasladoHistorial
        fields = ['id', 'previous_amount', 'new_amount', 'previous_active',
                  'new_active', 'action', 'changed_by', 'changedBy',
                  'created_at']

    @extend_schema_field(dict)
    def get_changedBy(self, obj):
        return {'id': obj.changed_by_id, 'name': obj.changed_by.name} if obj.changed_by else None


class SaleSerializer(serializers.ModelSerializer):
    """Respuesta de venta con las claves exactas que consume el frontend:
    sale.Plan.label y sale.creator.name."""
    planId = serializers.IntegerField(source='plan_id', read_only=True)
    sellerUserId = serializers.IntegerField(
        source='seller_user_id', read_only=True)
    sellerName = serializers.CharField(source='seller_name', read_only=True)
    Plan = serializers.SerializerMethodField()
    creator = serializers.SerializerMethodField()
    previousPlan = serializers.SerializerMethodField()
    previousService = serializers.SerializerMethodField()
    isServiceChange = serializers.SerializerMethodField()
    motivoNombre = serializers.SerializerMethodField()
    equipmentRetained = serializers.BooleanField(
        source='equipment_retained', read_only=True)
    requiresTechnicalVisit = serializers.BooleanField(
        source='requires_technical_visit', read_only=True)
    debtApplies = serializers.BooleanField(source='debt_applies', read_only=True)
    equipmentDelivered = serializers.BooleanField(
        source='equipment_delivered', read_only=True)
    equipmentSerial = serializers.CharField(
        source='equipment_serial', read_only=True)
    equipmentRecoveryRequired = serializers.BooleanField(
        source='equipment_recovery_required', read_only=True)
    equipmentRecoveryStatus = serializers.CharField(
        source='equipment_recovery_status', read_only=True)
    debtAmount = serializers.DecimalField(
        source='debt_amount', max_digits=12, decimal_places=2, read_only=True)
    totalToCollect = serializers.SerializerMethodField()
    traslado = serializers.SerializerMethodField()
    coverageZoneId = serializers.IntegerField(
        source='coverage_zone_id', read_only=True)
    coverageZone = serializers.SerializerMethodField()
    canalCaptacionId = serializers.IntegerField(
        source='canal_captacion_id', read_only=True)
    canalCaptacion = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = ['id', 'date', 'clientCode', 'clientName', 'serviceType',
                   'requestType', 'additionType', 'changeReason', 'motivo',
                   'status',
                  'motivoNombre', 'planFrom',
                  'serviceTypeFrom', 'previousService', 'isServiceChange',
                   'totalFrom', 'notes', 'planId', 'total', 'Plan', 'creator',
                   'sellerUserId', 'sellerName', 'promotion', 'promotion_name',
                   'applied_installation', 'applied_monthly', 'previousPlan']
        fields = fields + [
            'equipmentRetained', 'requiresTechnicalVisit', 'debtApplies',
             'equipmentDelivered', 'equipmentSerial', 'equipmentRecoveryRequired',
             'equipmentRecoveryStatus', 'debtAmount',
            'totalToCollect', 'version']
        fields = fields + ['traslado', 'coverageZoneId', 'coverageZone',
                           'canalCaptacionId', 'canalCaptacion']

    @extend_schema_field(str)
    def get_motivoNombre(self, obj):
        """Nombre del motivo: el snapshot si existe, o el texto historico."""
        return obj.changeReason or ''

    @extend_schema_field(str)
    def get_status(self, obj):
        """Expone una etiqueta estable y repara visualmente históricos seguros.

        Los registros antiguos pueden no tener status persistido. Para los
        tres tipos definidos se deriva únicamente para lectura; no se altera
        ningún histórico automáticamente.
        """
        code = obj.status or movement_status_for_request_type(
            obj.requestType, sale_catalog(self))
        return dict(SOLICITUD_STATUS_CHOICES).get(code) if code else None

    @extend_schema_field(dict)
    def get_Plan(self, obj):
        return {'id': obj.plan.id,
                'label': obj.planName or obj.plan.label,
                'code': obj.plan.code}

    @extend_schema_field(dict)
    def get_previousPlan(self, obj):
        pf = getattr(obj, 'planFromId', None) or getattr(obj, 'planfromid', None)
        if pf:
            return {'id': pf.id,
                    'label': obj.planFrom or pf.label,
                    'code': pf.code, 'type': pf.type}
        return None

    @extend_schema_field(dict)
    def get_previousService(self, obj):
        """Servicio anterior del movimiento, deducido si no se registro."""
        if request_type_mode(obj.requestType, sale_catalog(self)) not in (
                MODO_CAMBIO_PLAN, MODO_ADICION):
            return None
        family = previous_service_family(obj)
        if not family:
            return None
        return {
            'family': family,
            'label': service_family_label(family),
            'serviceType': obj.serviceTypeFrom or None,
        }

    @extend_schema_field(bool)
    def get_isServiceChange(self, obj):
        return is_service_change(obj, sale_catalog(self))

    @extend_schema_field(dict)
    def get_creator(self, obj):
        return {'id': obj.createdBy.id, 'name': obj.createdBy.name}

    @extend_schema_field(str)
    def get_totalToCollect(self, obj):
        return obj.total or Decimal('0')

    @extend_schema_field(dict)
    def get_traslado(self, obj):
        traslado = getattr(obj, 'traslado_externo', None)
        if not traslado:
            return None
        return {
            'id': traslado.id,
            'tariffAmount': traslado.tariff_amount,
            'currentAddress': traslado.current_address,
            'newAddress': traslado.new_address,
            'zone': traslado.zone,
            'references': traslado.references,
            'hasPhysicalSketch': traslado.has_physical_sketch,
            'status': traslado.status,
        }

    @extend_schema_field(dict)
    def get_coverageZone(self, obj):
        zone = obj.coverage_zone
        if not zone:
            return None
        return {
            'id': zone.id,
            'name': zone.name,
            'is_active': zone.is_active,
        }

    @extend_schema_field(dict)
    def get_canalCaptacion(self, obj):
        canal = obj.canal_captacion
        if not canal:
            return None
        return {
            'id': canal.id,
            'nombre': canal.nombre,
            'activo': canal.activo,
        }


class SaleCreateSerializer(serializers.Serializer):
    """Crea una venta. El total se calcula en el servidor a partir del plan."""
    date = serializers.DateField()
    clientCode = serializers.CharField(max_length=40)
    clientName = serializers.CharField(max_length=160)
    clientCi = serializers.CharField(required=False, allow_blank=True, max_length=30)
    clientPhone = serializers.CharField(required=False, allow_blank=True, max_length=40)
    serviceType = serializers.ChoiceField(
        choices=[c[0] for c in Sale.TYPE_CHOICES])
    requestType = serializers.CharField(
        max_length=20, required=False, default='nuevo_contrato')
    changeReason = serializers.CharField(required=False, allow_blank=True)
    planFrom = serializers.CharField(required=False, allow_blank=True)
    serviceTypeFrom = serializers.CharField(
        required=False, allow_null=True, allow_blank=True)
    totalFrom = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    planId = serializers.IntegerField()
    coverageZoneId = serializers.IntegerField(required=False, allow_null=True)
    canalCaptacionId = serializers.IntegerField(required=False, allow_null=True)
    meterNumber = serializers.CharField(
        required=False, allow_blank=True, max_length=80)
    sellerUserId = serializers.IntegerField(required=False, allow_null=True)
    promotionId = serializers.IntegerField(required=False, allow_null=True)
    additionType = serializers.ChoiceField(
        choices=[c[0] for c in Sale.ADDITION_TYPE_CHOICES],
        required=False, allow_blank=True, default='')
    planFromId = serializers.IntegerField(required=False, allow_null=True)
    motivoId = serializers.IntegerField(required=False, allow_null=True)
    equipmentRetained = serializers.BooleanField(
        source='equipment_retained', required=False, allow_null=True)
    requiresTechnicalVisit = serializers.BooleanField(
        source='requires_technical_visit', required=False, allow_null=True)
    debtApplies = serializers.BooleanField(
        source='debt_applies', required=False, default=False)
    debtAmount = serializers.DecimalField(
        source='debt_amount', max_digits=12, decimal_places=2,
        required=False, allow_null=True, default=Decimal('0'))
    transferTariffId = serializers.IntegerField(required=False, allow_null=True)
    transferNewAddress = serializers.CharField(required=False, allow_blank=True, max_length=255)
    transferCurrentAddress = serializers.CharField(required=False, allow_blank=True, max_length=255)
    transferZone = serializers.CharField(required=False, allow_blank=True, max_length=120)
    transferReferences = serializers.CharField(required=False, allow_blank=True, max_length=500)
    transferHasSketch = serializers.BooleanField(required=False, allow_null=True)
    equipmentDelivered = serializers.BooleanField(
        source='equipment_delivered', required=False, allow_null=True)
    equipmentSerial = serializers.CharField(
        source='equipment_serial', required=False, allow_blank=True, max_length=255)
    equipmentRecoveryRequired = serializers.BooleanField(
        source='equipment_recovery_required', required=False)

    def validate(self, attrs):
        if 'status' in self.initial_data:
            raise serializers.ValidationError(
                {'status': 'El estado se determina automáticamente según el tipo de solicitud.'})
        editable_origin_fields = {'contractOrigin', 'externalSeller'}
        if editable_origin_fields.intersection(self.initial_data):
            raise serializers.ValidationError(
                'El origen del contrato se determina automáticamente.')

        catalog = request_type_catalog()
        request_type = attrs.get('requestType', 'nuevo_contrato')
        tipo = catalog.get(request_type)
        if tipo is None:
            raise serializers.ValidationError(
                {'requestType': 'Tipo de solicitud desconocido'})
        if not tipo.activo:
            raise serializers.ValidationError(
                {'requestType': 'El tipo de solicitud esta inactivo'})
        mode = tipo.modo

        is_rehire = request_type == 'recontratacion'
        is_transfer = request_type_mode(request_type, catalog) == MODO_TRASLADO
        equipment_retained = attrs.get('equipment_retained')
        requires_technical_visit = attrs.get('requires_technical_visit')
        debt_applies = attrs.get('debt_applies', False)
        debt_amount = attrs.get('debt_amount')
        equipment_delivered = attrs.get('equipment_delivered')
        equipment_serial = (attrs.get('equipment_serial') or '').strip().upper()
        contract_mode = mode == 'nuevo' or is_rehire
        coverage_zone_id = attrs.get('coverageZoneId')
        if contract_mode or is_transfer:
            if coverage_zone_id is None:
                raise serializers.ValidationError(
                    {'coverageZoneId': 'Seleccione una zona de cobertura'})
            coverage_zone = CoverageZone.objects.filter(
                id=coverage_zone_id, is_active=True).first()
            if coverage_zone is None:
                raise serializers.ValidationError(
                    {'coverageZoneId':
                     'La zona de cobertura no existe o está inactiva'})
        else:
            if coverage_zone_id is not None:
                raise serializers.ValidationError(
                    {'coverageZoneId':
                     'La zona solo aplica a contratos, recontrataciones y traslados'})
            coverage_zone = None
        attrs['coverageZone'] = coverage_zone

        canal_captacion_id = attrs.get('canalCaptacionId')
        is_new_contract = request_type == 'nuevo_contrato'
        if is_new_contract and canal_captacion_id is None:
            raise serializers.ValidationError(
                {'canalCaptacionId':
                 'Seleccione cómo nos conoció para registrar el nuevo contrato'})
        if not is_new_contract and canal_captacion_id is not None:
            raise serializers.ValidationError(
                {'canalCaptacionId':
                 'El canal de captación solo aplica a nuevos contratos'})
        if canal_captacion_id is not None:
            canal_captacion = CanalCaptacion.objects.filter(
                id=canal_captacion_id, activo=True).first()
            if canal_captacion is None:
                raise serializers.ValidationError(
                    {'canalCaptacionId':
                     'El canal de captacion no existe o esta inactivo'})
        else:
            canal_captacion = None
        attrs['canalCaptacion'] = canal_captacion
        meter_number = (attrs.get('meterNumber') or '').strip()
        seller_user_id = attrs.get('sellerUserId')

        if contract_mode:
            if seller_user_id is not None:
                seller = User.objects.filter(
                    id=seller_user_id, active=True).first()
                if seller is None or not can_register_external_sale(seller):
                    raise serializers.ValidationError(
                        {'sellerUserId':
                         'Seleccione un usuario con asignación externa activa'})
                attrs['sellerUser'] = seller
                attrs['sellerName'] = seller.name
                attrs['externalSeller'] = seller.name
                attrs['contractOrigin'] = 'externo'
            else:
                attrs['sellerUser'] = None
                attrs['sellerName'] = ''
                attrs['externalSeller'] = ''
                registrar = self.context.get('user')
                is_call_center = bool(
                    registrar
                    and registrar.role_assignments.filter(
                        active=True, role__active=True,
                        role__code='call-center').exists())
                attrs['contractOrigin'] = 'virtual' if is_call_center else 'oficina'
        else:
            attrs['clientCi'] = ''
            attrs['clientPhone'] = ''
            attrs['meterNumber'] = ''
            attrs['contractOrigin'] = 'oficina'
            attrs['externalSeller'] = ''
            attrs['sellerUser'] = None
            attrs['sellerName'] = ''

        if mode == MODO_RETIRO:
            if equipment_delivered is None:
                # Compatibilidad con solicitudes antiguas que no enviaban este
                # campo; el formulario actual siempre lo solicita explícitamente.
                equipment_delivered = False
                attrs['equipment_delivered'] = False
            if equipment_delivered:
                if not equipment_serial:
                    raise serializers.ValidationError(
                        {'equipmentSerial': 'Ingrese la serie del equipo entregado'})
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT o.serie
                            FROM public.onu AS o
                            WHERE LOWER(TRIM(o.serie)) = LOWER(TRIM(%s))
                            LIMIT 1
                            """,
                            [equipment_serial],
                        )
                        registered = cursor.fetchone()
                except DatabaseError:
                    # Inventario puede no estar disponible; el retiro
                    # comercial conserva la serie como pendiente de
                    # identificación en vez de bloquear el registro.
                    registered = None
                normalized_serial = registered[0] if registered else equipment_serial
                if registered and InventarioMovimiento.objects.filter(
                        serie__iexact=normalized_serial,
                        estado=InventarioMovimiento.ESTADO_PENDIENTE).exists():
                    raise serializers.ValidationError(
                        {'equipmentSerial': 'La serie ya tiene una recepción pendiente'})
                # La serie puede ser nueva para Inventario. Se conserva como
                # declaración pendiente de identificación, sin bloquear el
                # retiro comercial.
                attrs['equipment_serial'] = normalized_serial
                attrs['equipment_recovery_required'] = False
                attrs['equipment_recovery_status'] = 'not_required'
            else:
                attrs['equipment_serial'] = ''
                attrs['equipment_recovery_required'] = True
                attrs['equipment_recovery_status'] = 'pending'
        else:
            attrs['equipment_delivered'] = None
            attrs['equipment_serial'] = ''
            attrs['equipment_recovery_required'] = False
            attrs['equipment_recovery_status'] = 'not_required'

        if is_rehire:
            if equipment_retained is None:
                raise serializers.ValidationError(
                    {'equipmentRetained': 'Indique si conserva el router/ONU'})
            if requires_technical_visit is None:
                raise serializers.ValidationError(
                    {'requiresTechnicalVisit': 'Indique si requiere visita tecnica'})
            if debt_applies:
                if debt_amount is None or debt_amount <= 0:
                    raise serializers.ValidationError(
                        {'debtAmount': 'Ingrese un adeudo mayor que cero'})
            elif debt_amount not in (None, Decimal('0')):
                raise serializers.ValidationError(
                    {'debtAmount': 'El adeudo debe ser cero si no aplica'})
            attrs['debt_amount'] = debt_amount or Decimal('0')
        else:
            if debt_applies or (debt_amount not in (None, Decimal('0'))):
                raise serializers.ValidationError(
                    {'debtAmount': 'El adeudo solo aplica a recontrataciones'})
            attrs['equipment_retained'] = None
            attrs['requires_technical_visit'] = None
            attrs['debt_applies'] = False
            attrs['debt_amount'] = Decimal('0')

        if is_transfer:
            tariff_id = attrs.get('transferTariffId')
            tariff = TarifaTraslado.objects.filter(
                id=tariff_id, active=True).first()
            if tariff is None:
                raise serializers.ValidationError(
                    {'transferTariffId': 'Tarifa de traslado no encontrada o inactiva'})
            service_family = SERVICE_TYPE_FAMILY.get(attrs['serviceType'])
            if tariff.service_type != service_family:
                raise serializers.ValidationError(
                    {'transferTariffId': 'La tarifa no corresponde al servicio seleccionado'})
            if not (attrs.get('transferNewAddress') or '').strip():
                raise serializers.ValidationError(
                    {'transferNewAddress': 'El nuevo domicilio es obligatorio'})
            if attrs.get('transferHasSketch') is None:
                raise serializers.ValidationError(
                    {'transferHasSketch': 'Indique si el cliente trajo croquis físico'})
            attrs['transferTariff'] = tariff
        else:
            for key in ('transferTariffId', 'transferNewAddress',
                        'transferZone', 'transferReferences',
                        'transferCurrentAddress',
                        'transferHasSketch'):
                if attrs.get(key) not in (None, '', False):
                    raise serializers.ValidationError(
                        {'transferTariffId': 'Los datos de traslado solo aplican a traslados externos'})

        try:
            plan = Plan.objects.get(id=attrs['planId'])
        except Plan.DoesNotExist:
            raise serializers.ValidationError(
                {'planId': 'Plan no encontrado o inactivo'})

        if not plan_is_selectable(plan, mode, request_type):
            raise serializers.ValidationError(
                {'planId': ('El plan legacy no esta disponible para este tipo '
                            'de solicitud') if plan.legacy else
                           'El plan no esta disponible para este tipo de solicitud'})

        # El plan nuevo debe pertenecer al tipo de servicio nuevo.
        expected_type = SERVICE_TYPE_TO_PLAN_TYPE.get(attrs['serviceType'])
        if plan.type != expected_type:
            raise serializers.ValidationError(
                {'serviceType': 'El plan no pertenece al tipo de servicio seleccionado'})

        # Una adición incorpora el servicio faltante y siempre termina en
        # Combo. No exige motivo; additionType identifica lo incorporado.
        service_type_from = attrs.get('serviceTypeFrom') or None

        if mode == MODO_ADICION:
            if not attrs.get('additionType'):
                raise serializers.ValidationError(
                    {'additionType': 'Debe seleccionar el tipo de adicion (Internet o TV)'})
            addition_errors = validate_adicion(
                plan=plan,
                plan_from=None,
                service_type=attrs['serviceType'],
                service_type_from=service_type_from,
                addition_type=attrs.get('additionType'))
            if addition_errors:
                raise serializers.ValidationError(addition_errors)
        else:
            attrs['additionType'] = ''

        plan_from = None
        # Motivo del cambio / del retiro. Se resuelve primero para usar su
        # nombre como motivo, pero sus errores se reportan al final para no
        # tapar los mensajes de plan anterior o compatibilidad de servicio.
        reason_errors = {}
        motivo, categoria_motivo = resolve_motivo(
            attrs.get('motivoId'), mode, reason_errors)
        attrs['changeReason'] = (
            motivo.nombre if motivo else (attrs.get('changeReason') or ''))

        if mode == MODO_CAMBIO_PLAN:
            pf_id = attrs.get('planFromId')
            try:
                plan_from = Plan.objects.get(id=pf_id) if pf_id else None
            except Plan.DoesNotExist:
                raise serializers.ValidationError(
                    {'planFromId': 'Plan anterior no encontrado'})

            errors = validate_cambio_plan(
                plan=plan, plan_from=plan_from,
                service_type=attrs['serviceType'],
                service_type_from=service_type_from,
                change_reason=attrs['changeReason'])
            if errors:
                raise serializers.ValidationError(errors)
        elif mode != MODO_ADICION:
            service_type_from = None

        if reason_errors:
            raise serializers.ValidationError(reason_errors)
        # Un cambio o un retiro nuevo no puede quedar sin motivo.
        if categoria_motivo and motivo is None:
            etiqueta = ('del cambio' if categoria_motivo == MOTIVO_CAMBIO
                        else 'del retiro')
            raise serializers.ValidationError(
                {'motivoId': f'Debe seleccionar el motivo {etiqueta}'})

        attrs['planFromPlan'] = plan_from
        attrs['serviceTypeFromValue'] = service_type_from
        attrs['motivoValue'] = motivo

        # Validate promotion if provided
        promotion = None
        promotion_id = attrs.get('promotionId')
        if promotion_id:
            from django.utils import timezone as tz
            today = tz.localdate()
            try:
                promotion = Promotion.objects.get(
                    id=promotion_id, plan=plan, active=True,
                    start_date__lte=today, end_date__gte=today)
            except Promotion.DoesNotExist:
                raise serializers.ValidationError(
                    {'promotionId': 'Promocion no valida, vencida o no pertenece al plan'})
        attrs['plan'] = plan
        attrs['promotion'] = promotion
        attrs['meterNumber'] = meter_number
        return attrs

    def create(self, validated_data):
        user = self.context['user']
        plan = validated_data.pop('plan')
        coverage_zone = validated_data.pop('coverageZone', None)
        canal_captacion = validated_data.pop('canalCaptacion', None)
        promotion = validated_data.pop('promotion', None)
        transfer_tariff = validated_data.pop('transferTariff', None)
        plan_from = validated_data.pop('planFromPlan', None)
        service_type_from = validated_data.pop('serviceTypeFromValue', None)
        motivo = validated_data.pop('motivoValue', None)
        request_type = validated_data.get('requestType', 'nuevo_contrato')
        movement_status = movement_status_for_request_type(
            request_type, request_type_catalog())

        code = validated_data.get('clientCode', '').strip()
        ci = validated_data.get('clientCi', '').strip()
        customer = Customer.objects.filter(ci=ci).first() if ci else None
        by_code = Customer.objects.filter(code=code).first()
        if customer and by_code and customer.id != by_code.id:
            raise serializers.ValidationError(
                {'clientCi': 'El CI y el código corresponden a clientes distintos'})
        customer = customer or by_code
        if customer is None and code:
            customer = Customer(
                code=code, name=validated_data['clientName'], ci=ci,
                phone=validated_data.get('clientPhone', '').strip())
            customer.save()
        elif customer:
            updates = []
            if ci and not customer.ci:
                customer.ci = ci
                updates.append('ci')
            phone = validated_data.get('clientPhone', '').strip()
            if phone and not customer.phone:
                customer.phone = phone
                updates.append('phone')
            if updates:
                customer.save(update_fields=updates)

        installation, monthly, sale_total = resolve_sale_prices(
            plan, promotion, request_type)
        if request_type == 'recontratacion':
            sale_total += validated_data.get('debt_amount', Decimal('0'))
        if request_type == 'traslado_externo':
            installation = Decimal('0')
            monthly = Decimal('0')
            sale_total = transfer_tariff.amount

        sale = Sale.objects.create(
            date=validated_data['date'],
            clientCode=validated_data['clientCode'],
            clientName=validated_data['clientName'],
            serviceType=validated_data['serviceType'],
            requestType=request_type,
            status=movement_status,
            coverage_zone=coverage_zone,
            canal_captacion=canal_captacion,
            additionType=validated_data.get('additionType', ''),
            changeReason=validated_data.get('changeReason', ''),
            motivo=motivo,
            planFrom=plan_from.label if plan_from else validated_data.get('planFrom', ''),
            planFromId=plan_from,
            serviceTypeFrom=service_type_from,
            totalFrom=(plan_from.total if plan_from
                       else validated_data.get('totalFrom')),
            notes=validated_data.get('notes', ''),
            customer=customer,
            plan=plan,
            planName=plan.label,
            total=sale_total,
            promotion=promotion,
            promotion_name=promotion.name if promotion else '',
            applied_installation=installation,
            applied_monthly=monthly,
            equipment_retained=validated_data.get('equipment_retained'),
            requires_technical_visit=validated_data.get('requires_technical_visit'),
            debt_applies=validated_data.get('debt_applies', False),
            debt_amount=validated_data.get('debt_amount', Decimal('0')),
            equipment_delivered=validated_data.get('equipment_delivered'),
            equipment_serial=validated_data.get('equipment_serial', ''),
            equipment_recovery_required=validated_data.get(
                'equipment_recovery_required', False),
            equipment_recovery_status=validated_data.get(
                'equipment_recovery_status', 'not_required'),
            seller_user=validated_data.get('sellerUser'),
            seller_name=validated_data.get('sellerName', ''),
            createdBy=user,
        )
        if transfer_tariff is not None:
            TrasladoExterno.objects.create(
                sale=sale,
                customer=customer,
                tariff=transfer_tariff,
                tariff_amount=transfer_tariff.amount,
                current_address=validated_data.get('transferCurrentAddress', '').strip(),
                new_address=validated_data.get('transferNewAddress', '').strip(),
                zone=coverage_zone.name,
                references=validated_data.get('transferReferences', '').strip(),
                has_physical_sketch=validated_data.get('transferHasSketch'),
                status=('recibido' if validated_data.get('transferHasSketch')
                        else 'pendiente_ubicacion'),
                created_by=user,
            )
        if request_type == 'recontratacion' or request_type_mode(
                request_type, request_type_catalog()) == 'nuevo':
            Contract.objects.create(
                number=f'GV-{sale.date:%Y%m%d}-{sale.id}',
                customer=customer,
                sale=sale,
                service_type=sale.serviceType,
                plan=plan,
                plan_name=plan.label,
                contracted_on=sale.date,
                origin=validated_data.get('contractOrigin', 'oficina'),
                external_seller=validated_data.get('externalSeller', ''),
                seller_user=validated_data.get('sellerUser'),
                seller_name=validated_data.get('sellerName', ''),
                meter_number=validated_data.get('meterNumber') or None,
                created_by=user,
            )
        if validated_data.get('equipment_delivered'):
            InventarioMovimiento.objects.create(
                sale=sale,
                serie=validated_data['equipment_serial'],
                tipo=InventarioMovimiento.TIPO_DEVOLUCION_DECLARADA,
                estado=InventarioMovimiento.ESTADO_PENDIENTE,
                created_by=user,
            )
        return sale


class BackupSerializer(serializers.ModelSerializer):
    creator = serializers.SerializerMethodField()
    size_display = serializers.SerializerMethodField()

    class Meta:
        model = Backup
        # 'storage_path' queda fuera a proposito: expone rutas del
        # sistema de archivos del servidor.
        fields = ['id', 'filename', 'backup_type', 'status', 'backup_format',
                  'created_at', 'started_at', 'finished_at', 'created_by',
                  'size', 'size_display', 'checksum', 'verified',
                  'error_message', 'creator']

    def get_creator(self, obj):
        if obj.created_by:
            return {'id': obj.created_by.id, 'name': obj.created_by.name}
        return None

    def get_size_display(self, obj):
        size = obj.size
        if size < 1024:
            return f'{size} B'
        elif size < 1024 * 1024:
            return f'{size / 1024:.1f} KB'
        else:
            return f'{size / (1024 * 1024):.1f} MB'
