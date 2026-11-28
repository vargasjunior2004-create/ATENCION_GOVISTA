from django.db.models import Avg, Count, FloatField, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDay
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .atencion_serializers import (
    AtencionAccionSerializer, AtencionCatalogoSerializer,
    AtencionSerializer, AtencionStartSerializer, PagoAtendidoSerializer,
)
from .atencion_services import (
    add_attention_action, create_started_attention, finish_attention,
    get_open_attention, start_attention,
    validate_catalog_type,
)
from .models import Atencion, AtencionAccion, AtencionCatalogo, PagoAtendido, User
from .rbac import has_permission, is_system_admin


def has_attention_access(user, permission):
    return (
        is_system_admin(user)
        or getattr(user, 'role', None) == 'call-center'
        or has_permission(user, permission)
    )


def permission_error():
    return Response(
        {'error': 'No tienes permiso para realizar esta operación.'},
        status=status.HTTP_403_FORBIDDEN)


def filter_attentions(queryset, params):
    start_value = params.get('from', '')
    end_value = params.get('to', '')
    start = parse_date(start_value)
    end = parse_date(end_value)
    if start_value and not start:
        raise ValidationError({'from': 'La fecha inicial no es válida.'})
    if end_value and not end:
        raise ValidationError({'to': 'La fecha final no es válida.'})
    if start and end and start > end:
        raise ValidationError({'to': 'La fecha final debe ser posterior a la inicial.'})
    if start:
        queryset = queryset.filter(created_at__date__gte=start)
    if end:
        queryset = queryset.filter(created_at__date__lte=end)
    for parameter, field in (
        ('agent', 'agent_id'), ('channel', 'channel_id'),
        ('attention_type', 'attention_type_id'),
        ('classification', 'classification_id'), ('status', 'status'),
        ('service_type', 'service_type'), ('plan', 'plan_id'),
    ):
        value = params.get(parameter)
        if value:
            queryset = queryset.filter(**{field: value})
    if params.get('action'):
        queryset = queryset.filter(
            acciones__action_id=params['action']).distinct()
    if params.get('complaints') == 'true':
        queryset = queryset.filter(
            attention_type__code__in=('queja', 'reclamo'))
    return queryset


def create_started_attention_response(request):
    if not has_attention_access(request.user, 'atenciones.create'):
        return permission_error()
    idempotency_key = (request.headers.get('Idempotency-Key') or '').strip()
    if not idempotency_key or len(idempotency_key) > 128:
        raise ValidationError({
            'Idempotency-Key': 'Debes enviar una clave de idempotencia válida.'
        })
    serializer = AtencionStartSerializer(
        data=request.data, context={'user': request.user})
    serializer.is_valid(raise_exception=True)
    attention, created = create_started_attention(
        serializer, request.user, idempotency_key)
    response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return Response(
        AtencionSerializer(
            attention, context={'user': request.user}).data,
        status=response_status,
    )


class AtencionListView(APIView):
    def get(self, request):
        if not has_attention_access(request.user, 'atenciones.view'):
            return permission_error()
        queryset = filter_attentions(
            Atencion.objects.select_related(
                'agent', 'customer', 'contract', 'plan',
                'attention_type', 'classification', 'channel'
            ).prefetch_related('acciones__action', 'acciones__executed_by'),
            request.query_params,
        )
        if (getattr(request.user, 'role', None) == 'call-center'
                and not has_attention_access(request.user, 'atenciones.view_all')):
            queryset = queryset.filter(agent=request.user)
        return Response(AtencionSerializer(
            queryset, many=True, context={'user': request.user}).data)

    def post(self, request):
        return create_started_attention_response(request)


class AtencionStartCreateView(APIView):
    def post(self, request):
        return create_started_attention_response(request)


class AtencionOpenView(APIView):
    def get(self, request):
        if not has_attention_access(request.user, 'atenciones.view'):
            return permission_error()
        attention = get_open_attention(request.user)
        if not attention:
            return Response(None)
        attention = Atencion.objects.select_related(
            'agent', 'customer', 'contract', 'plan',
            'attention_type', 'classification', 'channel',
        ).prefetch_related('acciones__action', 'acciones__executed_by').get(
            pk=attention.pk)
        return Response(AtencionSerializer(
            attention, context={'user': request.user}).data)


class AtencionDetailView(APIView):
    def get_object(self, pk):
        return get_object_or_404(Atencion.objects.select_related(
            'agent', 'customer', 'contract', 'plan',
            'attention_type', 'classification', 'channel'
        ).prefetch_related('acciones__action', 'acciones__executed_by'), pk=pk)

    def get(self, request, pk):
        if not has_attention_access(request.user, 'atenciones.view'):
            return permission_error()
        return Response(AtencionSerializer(
            self.get_object(pk), context={'user': request.user}).data)

    def patch(self, request, pk):
        if not has_attention_access(request.user, 'atenciones.change'):
            return permission_error()
        attention = self.get_object(pk)
        serializer = AtencionSerializer(
            attention, data=request.data, partial=True,
            context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AtencionActionView(APIView):
    def post(self, request, pk):
        if not has_attention_access(request.user, 'atenciones.change'):
            return permission_error()
        attention = get_object_or_404(Atencion, pk=pk)
        action = get_object_or_404(
            AtencionCatalogo,
            pk=request.data.get('action'),
            catalog_type='support_action',
            active=True,
        )
        relation = add_attention_action(
            attention, action, request.user, request.data.get('notes', ''))
        return Response(
            AtencionAccionSerializer(relation).data,
            status=status.HTTP_201_CREATED)


class AtencionStartView(APIView):
    def post(self, request, pk):
        if not has_attention_access(request.user, 'atenciones.change'):
            return permission_error()
        attention = start_attention(get_object_or_404(Atencion, pk=pk))
        return Response(AtencionSerializer(attention).data)


class AtencionFinishView(APIView):
    def post(self, request, pk):
        if not has_attention_access(request.user, 'atenciones.change'):
            return permission_error()
        attention = finish_attention(get_object_or_404(Atencion, pk=pk))
        return Response(AtencionSerializer(attention).data)


class AtencionDashboardView(APIView):
    def get(self, request):
        if not has_attention_access(request.user, 'atenciones.dashboard'):
            return permission_error()
        queryset = filter_attentions(
            Atencion.objects.select_related(
                'agent', 'channel', 'classification', 'attention_type'
            ).filter(status='finished'),
            request.query_params,
        )
        total = queryset.count()
        by_agent = queryset.values('agent_id', 'agent__name').annotate(
            attention_count=Count('id'),
            duration_seconds=Coalesce(Sum('duration_seconds'), Value(0)),
        )
        complaints = queryset.filter(
            attention_type__code__in=('queja', 'reclamo')).count()
        complaint_queryset = queryset.filter(
            attention_type__code__in=('queja', 'reclamo'))
        series = queryset.annotate(day=TruncDay('started_at')).values(
            'day').annotate(
                total=Count('id'),
                complaints=Count(
                    'id',
                    filter=Q(attention_type__code__in=('queja', 'reclamo'))),
                duration_seconds=Coalesce(Sum('duration_seconds'), Value(0)),
            ).order_by('day')

        def breakdown(query):
            return [
                {**row, 'percentage': round(
                    row['total'] * 100 / total, 2) if total else 0}
                for row in query
            ]

        return Response({
            'summary': {
                'total_attentions': total,
                'total_complaints': complaints,
                'total_duration_seconds': queryset.aggregate(
                    value=Coalesce(Sum('duration_seconds'), Value(0)))['value'],
                'average_duration_seconds': queryset.aggregate(
                value=Coalesce(
                    Avg('duration_seconds'),
                    Value(0.0, output_field=FloatField()),
                ))['value'],
            },
            'total': total,
            'by_agent': list(by_agent),
            'by_channel': breakdown(queryset.values(
                'channel_id', 'channel__name').annotate(total=Count('id'))),
            'by_classification': breakdown(queryset.values(
                'classification_id', 'classification__name').annotate(total=Count('id'))),
            'by_attention_type': breakdown(queryset.values(
                'attention_type_id', 'attention_type__name').annotate(total=Count('id'))),
            'by_service': breakdown(complaint_queryset.values(
                'service_type').annotate(total=Count('id'))),
            'by_plan': breakdown(complaint_queryset.values(
                'plan_id', 'plan_name').annotate(total=Count('id'))),
            'by_action': list(AtencionAccion.objects.filter(
                atencion__in=queryset
            ).values('action_id', 'action__name').annotate(total=Count('id'))),
            'series': list(series),
            'agent_options': list(User.objects.filter(
                role='call-center',
                active=True,
            ).values('id', 'name')),
        })


class AtencionCatalogoListView(APIView):
    def get(self, request):
        if not has_attention_access(request.user, 'atenciones.view'):
            return permission_error()
        catalog_type = request.query_params.get('catalog_type')
        queryset = AtencionCatalogo.objects.filter(active=True)
        if catalog_type:
            validate_catalog_type(catalog_type)
            queryset = queryset.filter(catalog_type=catalog_type)
        return Response(AtencionCatalogoSerializer(queryset, many=True).data)

    def post(self, request):
        if not has_attention_access(request.user, 'atenciones.catalogs_manage'):
            return permission_error()
        serializer = AtencionCatalogoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validate_catalog_type(serializer.validated_data['catalog_type'])
        return Response(
            AtencionCatalogoSerializer(serializer.save()).data,
            status=status.HTTP_201_CREATED)


class AtencionCatalogoDetailView(APIView):
    def patch(self, request, pk):
        if not (is_system_admin(request.user)
                or has_permission(request.user, 'atenciones.catalogs_manage')):
            return permission_error()
        catalog = get_object_or_404(AtencionCatalogo, pk=pk)
        serializer = AtencionCatalogoSerializer(
            catalog, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if 'catalog_type' in serializer.validated_data:
            validate_catalog_type(serializer.validated_data['catalog_type'])
        return Response(AtencionCatalogoSerializer(serializer.save()).data)


class PagoAtendidoListView(APIView):
    def get(self, request):
        if not has_attention_access(request.user, 'pagos_atendidos.view'):
            return permission_error()
        queryset = PagoAtendido.objects.select_related('registered_by', 'customer')
        return Response(PagoAtendidoSerializer(queryset, many=True).data)

    def post(self, request):
        if not has_attention_access(request.user, 'pagos_atendidos.create'):
            return permission_error()
        serializer = PagoAtendidoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            PagoAtendidoSerializer(serializer.save(registered_by=request.user)).data,
            status=status.HTTP_201_CREATED)


class PagoAtendidoDetailView(APIView):
    def get(self, request, pk):
        if not has_attention_access(request.user, 'pagos_atendidos.view'):
            return permission_error()
        payment = get_object_or_404(
            PagoAtendido.objects.select_related('registered_by', 'customer'),
            pk=pk,
        )
        return Response(PagoAtendidoSerializer(payment).data)
