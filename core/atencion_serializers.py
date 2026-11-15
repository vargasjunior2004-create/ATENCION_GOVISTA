from rest_framework import serializers

from .atencion_services import validate_call_center_channel, validate_catalog_entry
from .domain import SERVICE_TYPE_LABELS, SERVICE_TYPE_TO_PLAN_TYPE
from .models import AtencionCatalogo, Atencion, AtencionAccion, PagoAtendido


class AtencionCatalogoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AtencionCatalogo
        fields = (
            'id', 'catalog_type', 'code', 'name', 'description',
            'active', 'sort_order',
        )
        read_only_fields = ('id',)


class AtencionAccionSerializer(serializers.ModelSerializer):
    action_name = serializers.CharField(source='action.name', read_only=True)
    executed_by_name = serializers.CharField(
        source='executed_by.name', read_only=True)

    class Meta:
        model = AtencionAccion
        fields = (
            'id', 'action', 'action_name', 'executed_by',
            'executed_by_name', 'notes', 'executed_at',
        )
        read_only_fields = ('id', 'executed_by', 'executed_at')


class AtencionSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source='agent.name', read_only=True)
    plan_display_name = serializers.SerializerMethodField()
    customer_display_name = serializers.SerializerMethodField()
    actions = AtencionAccionSerializer(many=True, read_only=True)

    class Meta:
        model = Atencion
        fields = (
            'id', 'registered_by', 'agent', 'agent_name', 'customer',
            'customer_code', 'customer_name', 'customer_display_name',
            'contract', 'service_type', 'plan', 'plan_name', 'plan_display_name',
            'attention_type', 'classification', 'channel',
            'notes', 'started_at', 'ended_at', 'duration_seconds', 'status',
            'actions', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'registered_by', 'agent', 'started_at', 'ended_at',
            'duration_seconds', 'status', 'actions', 'created_at', 'updated_at',
        )

    def get_customer_display_name(self, obj):
        return obj.customer.name if obj.customer else obj.customer_name

    def get_plan_display_name(self, obj):
        return obj.plan_name or (obj.plan.label if obj.plan else '')

    def validate(self, attrs):
        catalog_fields = (
            ('attention_type', 'attention_type'),
            ('classification', 'classification'),
            ('channel', 'channel'),
        )
        for field, catalog_type in catalog_fields:
            if field in attrs:
                validate_catalog_entry(attrs[field], catalog_type)
        channel = attrs.get('channel')
        user = self.context.get('user')
        if channel and user:
            validate_call_center_channel(channel, user)

        contract = attrs.get('contract')
        plan = attrs.get('plan')
        service_type = attrs.get('service_type', '')
        if contract:
            if service_type and service_type != contract.service_type:
                raise serializers.ValidationError(
                    {'service_type': 'El servicio no coincide con el contrato.'})
            if plan and plan.id != contract.plan_id:
                raise serializers.ValidationError(
                    {'plan': 'El plan no coincide con el contrato.'})
            attrs['service_type'] = contract.service_type
            attrs['plan'] = contract.plan

        if service_type and service_type not in SERVICE_TYPE_LABELS:
            raise serializers.ValidationError(
                {'service_type': 'Tipo de servicio no válido.'})
        if plan and service_type:
            expected_plan_type = SERVICE_TYPE_TO_PLAN_TYPE[service_type]
            if plan.type != expected_plan_type:
                raise serializers.ValidationError(
                    {'plan': 'El plan no corresponde al tipo de servicio.'})
            attrs['plan_name'] = plan.label
        elif plan:
            attrs['plan_name'] = plan.label
        return attrs


class AtencionStartSerializer(AtencionSerializer):
    class Meta(AtencionSerializer.Meta):
        read_only_fields = AtencionSerializer.Meta.read_only_fields + (
            'status', 'started_at', 'ended_at', 'duration_seconds',
        )


class PagoAtendidoSerializer(serializers.ModelSerializer):
    registered_by_name = serializers.CharField(
        source='registered_by.name', read_only=True)

    class Meta:
        model = PagoAtendido
        fields = (
            'id', 'atencion', 'registered_by', 'registered_by_name',
            'customer', 'customer_code', 'customer_name', 'amount', 'paid_on',
            'payment_channel', 'reference', 'notes', 'created_at',
        )
        read_only_fields = ('id', 'registered_by', 'created_at')

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('El monto debe ser mayor a cero.')
        return value
