from rest_framework import serializers
from .models import User, Plan, Sale, CashCount, Outflow


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


class PlanSerializer(serializers.ModelSerializer):
    total = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Plan
        fields = ['id', 'code', 'label', 'type', 'speed',
                  'monthly', 'installation', 'total', 'active']


class PlanPublicSerializer(serializers.ModelSerializer):
    total = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Plan
        fields = ['id', 'code', 'label', 'type', 'speed',
                  'monthly', 'installation', 'total']


class SaleSerializer(serializers.ModelSerializer):
    """Respuesta de venta con las claves exactas que consume el frontend:
    sale.Plan.label y sale.creator.name."""
    planId = serializers.IntegerField(source='plan_id', read_only=True)
    Plan = serializers.SerializerMethodField()
    creator = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = ['id', 'date', 'clientCode', 'clientName', 'serviceType',
                  'planId', 'total', 'Plan', 'creator']

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
        choices=[('internet', 'internet'), ('tv', 'tv'), ('combo', 'combo')])
    planId = serializers.IntegerField()

    def validate(self, attrs):
        try:
            plan = Plan.objects.get(id=attrs['planId'], active=True)
        except Plan.DoesNotExist:
            raise serializers.ValidationError(
                {'planId': 'Plan no encontrado o inactivo'})
        if plan.type != attrs['serviceType']:
            raise serializers.ValidationError(
                {'serviceType': 'El plan no pertenece al tipo de servicio seleccionado'})
        attrs['plan'] = plan
        return attrs

    def create(self, validated_data):
        user = self.context['user']
        plan = validated_data.pop('plan')
        return Sale.objects.create(
            date=validated_data['date'],
            clientCode=validated_data['clientCode'],
            clientName=validated_data['clientName'],
            serviceType=validated_data['serviceType'],
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
        fields = ['id', 'date', 'personName', 'amount', 'concept']
