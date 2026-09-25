from rest_framework import serializers
from .models import User, Customer, Plan, Promotion, Sale, Backup


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
                  'monthly', 'installation', 'total', 'legacy']


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

    class Meta:
        model = Sale
        fields = ['id', 'date', 'clientCode', 'clientName', 'serviceType',
                  'requestType', 'additionType', 'changeReason', 'planFrom',
                  'totalFrom', 'notes', 'planId', 'total', 'Plan', 'creator',
                  'promotion', 'promotion_name',
                  'applied_installation', 'applied_monthly']

    def get_Plan(self, obj):
        return {'id': obj.plan.id, 'label': obj.plan.label, 'code': obj.plan.code}

    def get_creator(self, obj):
        return {'id': obj.createdBy.id, 'name': obj.createdBy.name}


class SaleCreateSerializer(serializers.Serializer):
    """Crea una venta. El total se calcula en el servidor a partir del plan."""
    date = serializers.DateField()
    clientCode = serializers.CharField(max_length=40)
    clientName = serializers.CharField(max_length=160)
    serviceType = serializers.ChoiceField(
        choices=[c[0] for c in Sale.TYPE_CHOICES])
    requestType = serializers.ChoiceField(
        choices=[c[0] for c in Sale.REQUEST_CHOICES], required=False,
        default='nuevo_contrato')
    changeReason = serializers.CharField(required=False, allow_blank=True)
    planFrom = serializers.CharField(required=False, allow_blank=True)
    totalFrom = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    planId = serializers.IntegerField()
    promotionId = serializers.IntegerField(required=False, allow_null=True)
    additionType = serializers.ChoiceField(
        choices=[c[0] for c in Sale.ADDITION_TYPE_CHOICES],
        required=False, allow_blank=True, default='')

    def validate(self, attrs):
        try:
            plan = Plan.objects.get(id=attrs['planId'], active=True)
        except Plan.DoesNotExist:
            raise serializers.ValidationError(
                {'planId': 'Plan no encontrado o inactivo'})
        # Map service types to plan types for validation
        type_map = {
            'internet': 'internet',
            'tv': 'tv',
            'tv_digital': 'tv',
            'combo_analog': 'combo',
            'combo_digital': 'combo',
        }
        expected_type = type_map.get(attrs['serviceType'])
        if plan.type != expected_type:
            raise serializers.ValidationError(
                {'serviceType': 'El plan no pertenece al tipo de servicio seleccionado'})

        # additionType requerido cuando requestType = adicion
        if attrs.get('requestType') == 'adicion':
            if not attrs.get('additionType'):
                raise serializers.ValidationError(
                    {'additionType': 'Debe seleccionar el tipo de adicion (Internet o TV)'})
        else:
            attrs['additionType'] = ''

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
        code = validated_data.get('clientCode', '')
        customer = Customer.objects.filter(code=code).first()
        if customer is None and code:
            customer = Customer(code=code, name=validated_data['clientName'])
            customer.save()
        is_retiro = validated_data.get('requestType', 'nuevo_contrato') == 'retiro'

        # Calculate prices
        if promotion:
            installation = (promotion.installation_price
                            if promotion.apply_installation
                            else plan.installation)
            monthly = (promotion.monthly_price
                       if promotion.apply_monthly
                       else plan.monthly)
        else:
            installation = plan.installation
            monthly = plan.monthly

        sale_total = monthly if is_retiro else monthly + installation

        return Sale.objects.create(
            date=validated_data['date'],
            clientCode=validated_data['clientCode'],
            clientName=validated_data['clientName'],
            serviceType=validated_data['serviceType'],
            requestType=validated_data.get('requestType', 'nuevo_contrato'),
            additionType=validated_data.get('additionType', ''),
            changeReason=validated_data.get('changeReason', ''),
            planFrom=validated_data.get('planFrom', ''),
            totalFrom=validated_data.get('totalFrom'),
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
        fields = ['id', 'filename', 'backup_type', 'status', 'created_at',
                  'created_by', 'size', 'size_display', 'storage_path',
                  'checksum', 'creator']

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
