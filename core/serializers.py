from rest_framework import serializers
from .models import User, Customer, Plan, Sale, CashCount, Outflow


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'role', 'active']


class UserWriteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'password', 'role', 'active']

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


class SaleSerializer(serializers.ModelSerializer):
    """Respuesta de venta con las claves exactas que consume el frontend:
    sale.Plan.label y sale.creator.name."""
    planId = serializers.IntegerField(source='plan_id', read_only=True)
    Plan = serializers.SerializerMethodField()
    creator = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = ['id', 'date', 'clientCode', 'clientName', 'serviceType',
                  'requestType', 'changeReason', 'planFrom', 'totalFrom',
                  'notes', 'planId', 'total', 'Plan', 'creator']

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
        attrs['plan'] = plan
        return attrs

    def create(self, validated_data):
        user = self.context['user']
        plan = validated_data.pop('plan')
        code = validated_data.get('clientCode', '')
        customer = Customer.objects.filter(code=code).first()
        if customer is None and code:
            customer = Customer(code=code, name=validated_data['clientName'])
            customer.save()
        return Sale.objects.create(
            date=validated_data['date'],
            clientCode=validated_data['clientCode'],
            clientName=validated_data['clientName'],
            serviceType=validated_data['serviceType'],
            requestType=validated_data.get('requestType', 'nuevo_contrato'),
            changeReason=validated_data.get('changeReason', ''),
            planFrom=validated_data.get('planFrom', ''),
            totalFrom=validated_data.get('totalFrom'),
            notes=validated_data.get('notes', ''),
            customer=customer,
            plan=plan,
            total=plan.total,
            createdBy=user,
        )


class CashCountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashCount
        fields = ['id', 'date', 'coin_050', 'coin_1', 'coin_2', 'coin_5',
                  'bill_10', 'bill_20', 'bill_50', 'bill_100', 'bill_200']


class OutflowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Outflow
        fields = ['id', 'date', 'personName', 'amount', 'concept', 'created_at']
