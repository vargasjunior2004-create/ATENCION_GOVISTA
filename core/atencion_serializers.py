from rest_framework import serializers

from .atencion_services import validate_catalog_entry
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
    customer_display_name = serializers.SerializerMethodField()
    actions = AtencionAccionSerializer(many=True, read_only=True)

    class Meta:
        model = Atencion
        fields = (
            'id', 'registered_by', 'agent', 'agent_name', 'customer',
            'customer_code', 'customer_name', 'customer_display_name',
            'contract', 'attention_type', 'classification', 'channel',
            'notes', 'started_at', 'ended_at', 'duration_seconds', 'status',
            'actions', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'registered_by', 'agent', 'started_at', 'ended_at',
            'duration_seconds', 'status', 'actions', 'created_at', 'updated_at',
        )

    def get_customer_display_name(self, obj):
        return obj.customer.name if obj.customer else obj.customer_name

    def validate(self, attrs):
        catalog_fields = (
            ('attention_type', 'attention_type'),
            ('classification', 'classification'),
            ('channel', 'channel'),
        )
        for field, catalog_type in catalog_fields:
            if field in attrs:
                validate_catalog_entry(attrs[field], catalog_type)
        return attrs


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
