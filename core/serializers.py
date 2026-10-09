from decimal import Decimal

from rest_framework import serializers
from .models import (
    User, Customer, Plan, Promotion, Sale, Backup, TipoSolicitud, Motivo,
)
from .domain import (
    SERVICE_TYPE_LABELS, SERVICE_TYPE_FAMILY, SERVICE_TYPE_TO_PLAN_TYPE,
    service_family_label, previous_service_family, is_service_change,
    request_type_mode, request_type_catalog,
    MODO_ADICION, MODO_CAMBIO_PLAN, MODOS_SOLO_MENSUAL,
    motivo_categoria_de_modo, MOTIVO_CAMBIO,
)


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


def validate_cambio_plan(plan, plan_from, service_type, service_type_from,
                         change_reason):
    """Reglas de un cambio de plan. Devuelve {} o un dict de errores.

    La comparten el alta y la edicion: si cada ruta validara por su cuenta,
    volverian a divergir, que es como el PUT termino sin comprobar nada.
    """
    errors = {}
    if plan_from is None:
        errors['planFromId'] = 'Debe seleccionar el plan anterior'
        return errors

    if not (change_reason or '').strip():
        errors['changeReason'] = 'Debe indicar el motivo del cambio de plan'

    # Un cambio de plan que no cambia nada no es un cambio de plan.
    # Se admite el mismo plan si lo que cambia es la variante del servicio
    # (por ejemplo combo analogico -> combo digital).
    if plan_from.id == plan.id:
        same_service = (not service_type_from
                        or service_type_from == service_type)
        if same_service:
            errors['planFromId'] = (
                'El plan anterior y el nuevo son el mismo: '
                'registre el movimiento con otro tipo de solicitud')

    validate_service_from(plan_from, service_type_from, errors)
    return errors


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
        errors['motivoId'] = 'El motivo no corresponde a este tipo de movimiento'
    return motivo, categoria


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'role', 'active']


class UserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'name', 'password', 'role', 'active']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'code', 'name', 'active']


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
            plan = Plan.objects.get(id=plan_id, active=True, legacy=False)
        except Plan.DoesNotExist:
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


class SaleSerializer(serializers.ModelSerializer):
    """Respuesta de venta con las claves exactas que consume el frontend:
    sale.Plan.label y sale.creator.name."""
    planId = serializers.IntegerField(source='plan_id', read_only=True)
    Plan = serializers.SerializerMethodField()
    creator = serializers.SerializerMethodField()
    previousPlan = serializers.SerializerMethodField()
    previousService = serializers.SerializerMethodField()
    isServiceChange = serializers.SerializerMethodField()
    motivoNombre = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = ['id', 'date', 'clientCode', 'clientName', 'serviceType',
                  'requestType', 'additionType', 'changeReason', 'motivo',
                  'motivoNombre', 'planFrom',
                  'serviceTypeFrom', 'previousService', 'isServiceChange',
                  'totalFrom', 'notes', 'planId', 'total', 'Plan', 'creator',
                  'promotion', 'promotion_name',
                  'applied_installation', 'applied_monthly', 'previousPlan']

    def get_motivoNombre(self, obj):
        """Nombre del motivo: el snapshot si existe, o el texto historico."""
        return obj.changeReason or ''

    def get_Plan(self, obj):
        return {'id': obj.plan.id, 'label': obj.plan.label, 'code': obj.plan.code}

    def get_previousPlan(self, obj):
        pf = getattr(obj, 'planFromId', None) or getattr(obj, 'planfromid', None)
        if pf:
            return {'id': pf.id, 'label': pf.label, 'code': pf.code,
                    'type': pf.type}
        return None

    def get_previousService(self, obj):
        """Servicio anterior del movimiento, deducido si no se registro."""
        if request_type_mode(obj.requestType, sale_catalog(self)) != MODO_CAMBIO_PLAN:
            return None
        family = previous_service_family(obj)
        if not family:
            return None
        return {
            'family': family,
            'label': service_family_label(family),
            'serviceType': obj.serviceTypeFrom or None,
        }

    def get_isServiceChange(self, obj):
        return is_service_change(obj, sale_catalog(self))

    def get_creator(self, obj):
        return {'id': obj.createdBy.id, 'name': obj.createdBy.name}


class SaleCreateSerializer(serializers.Serializer):
    """Crea una venta. El total se calcula en el servidor a partir del plan."""
    date = serializers.DateField()
    clientCode = serializers.CharField(max_length=40)
    clientName = serializers.CharField(max_length=160)
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
    promotionId = serializers.IntegerField(required=False, allow_null=True)
    additionType = serializers.ChoiceField(
        choices=[c[0] for c in Sale.ADDITION_TYPE_CHOICES],
        required=False, allow_blank=True, default='')
    planFromId = serializers.IntegerField(required=False, allow_null=True)
    motivoId = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
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

        try:
            plan = Plan.objects.get(id=attrs['planId'], active=True)
        except Plan.DoesNotExist:
            raise serializers.ValidationError(
                {'planId': 'Plan no encontrado o inactivo'})

        # El plan nuevo debe pertenecer al tipo de servicio nuevo.
        expected_type = SERVICE_TYPE_TO_PLAN_TYPE.get(attrs['serviceType'])
        if plan.type != expected_type:
            raise serializers.ValidationError(
                {'serviceType': 'El plan no pertenece al tipo de servicio seleccionado'})

        # additionType requerido cuando el tipo es ADICION
        if mode == MODO_ADICION:
            if not attrs.get('additionType'):
                raise serializers.ValidationError(
                    {'additionType': 'Debe seleccionar el tipo de adicion (Internet o TV)'})
        else:
            attrs['additionType'] = ''

        plan_from = None
        service_type_from = attrs.get('serviceTypeFrom') or None

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
        else:
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
        return attrs

    def create(self, validated_data):
        user = self.context['user']
        plan = validated_data.pop('plan')
        promotion = validated_data.pop('promotion', None)
        plan_from = validated_data.pop('planFromPlan', None)
        service_type_from = validated_data.pop('serviceTypeFromValue', None)
        motivo = validated_data.pop('motivoValue', None)
        request_type = validated_data.get('requestType', 'nuevo_contrato')

        code = validated_data.get('clientCode', '')
        customer = Customer.objects.filter(code=code).first()
        if customer is None and code:
            customer = Customer(code=code, name=validated_data['clientName'])
            customer.save()

        installation, monthly, sale_total = resolve_sale_prices(
            plan, promotion, request_type)

        return Sale.objects.create(
            date=validated_data['date'],
            clientCode=validated_data['clientCode'],
            clientName=validated_data['clientName'],
            serviceType=validated_data['serviceType'],
            requestType=request_type,
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
            total=sale_total,
            promotion=promotion,
            promotion_name=promotion.name if promotion else '',
            applied_installation=installation,
            applied_monthly=monthly,
            createdBy=user,
        )


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
