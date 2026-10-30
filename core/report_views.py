from datetime import date, timedelta
import uuid

from django.http import HttpResponse
from django.utils import timezone
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from drf_spectacular.utils import (
    extend_schema, extend_schema_view, OpenApiResponse, OpenApiTypes,
)

from .reports import (
    build_sales_pdf, build_sales_xlsx, build_sales_png,
    sign_report_token, unsign_report_token,
)
from .domain import request_type_label


class IsAdminRole(BasePermission):
    """Solo el rol admin puede generar los reportes del historial.

    Los reportes del dashboard tienen sus propios endpoints y estan
    disponibles para cualquier usuario autenticado.
    """

    message = 'Se requieren permisos de administrador'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        return bool(
            user
            and getattr(user, 'active', True)
            and getattr(user, 'role', None) == 'admin'
        )


def _sales_range(params, default_day=True):
    today = timezone.localdate().isoformat()
    from_date = params.get('from') or (today if default_day else '')
    to_date = params.get('to') or (today if default_day else '')
    return from_date, to_date


def _show_motivos(params):
    """El filtro es obligatorio en la UI; la API lo interpreta como bool.

    Solo controla si la columna Motivo aparece en el reporte. Nunca
    altera ni filtra los movimientos incluidos.
    """
    value = str(params.get('showMotivos', '')).strip().lower()
    return value in ('1', 'true', 'si', 'sí', 'yes')


def _download_headers(response):
    response['Cache-Control'] = 'no-store'
    response['X-Robots-Tag'] = 'noindex, nofollow'
    response['Referrer-Policy'] = 'no-referrer'
    return response


def _pdf_response(buf, filename):
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return _download_headers(response)


def _report_token(request, file_format):
    now = timezone.now()
    params = request.query_params
    from_date, to_date = _sales_range(params)
    return {
        'from': from_date,
        'to': to_date,
        'requestType': params.get('requestType') or '',
        'serviceType': params.get('serviceType') or '',
        'serviceTypeFrom': params.get('serviceTypeFrom') or '',
        'showMotivos': _show_motivos(params),
        'format': file_format,
        'issued_at': int(now.timestamp()),
        'exp': int((now + timedelta(hours=1)).timestamp()),
        'jti': uuid.uuid4().hex,
        'user_id': request.user.id,
    }


def _filters_from_payload(payload):
    return (
        payload['from'], payload['to'],
        payload['requestType'] or None,
        payload['serviceType'] or None,
        payload['serviceTypeFrom'] or None,
        payload['showMotivos'],
    )


@extend_schema(responses={200: OpenApiResponse(OpenApiTypes.BINARY)})
class SalesPdfView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        from_date, to_date = _sales_range(request.query_params)
        request_type = request.query_params.get('requestType') or None
        service_type = request.query_params.get('serviceType') or None
        service_type_from = request.query_params.get('serviceTypeFrom') or None
        show_motivos = _show_motivos(request.query_params)
        buf = build_sales_pdf(from_date, to_date, request_type, service_type,
                              service_type_from, show_motivos)
        suffix = f'-{request_type_label(request_type)}' if request_type else ''
        return _pdf_response(buf, f'planilla{suffix}-{from_date}-{to_date}.pdf')


@extend_schema(responses={200: OpenApiResponse(OpenApiTypes.BINARY)})
class SalesXlsxView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        from_date, to_date = _sales_range(request.query_params)
        request_type = request.query_params.get('requestType') or None
        service_type = request.query_params.get('serviceType') or None
        service_type_from = request.query_params.get('serviceTypeFrom') or None
        show_motivos = _show_motivos(request.query_params)
        buf = build_sales_xlsx(from_date, to_date, request_type, service_type,
                               service_type_from, show_motivos)
        suffix = f'-{request_type_label(request_type)}' if request_type else ''
        response = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="planilla{suffix}-{from_date}-{to_date}.xlsx"'
        return _download_headers(response)


@extend_schema(responses={200: OpenApiResponse(OpenApiTypes.BINARY)})
class SalesPngView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        from_date, to_date = _sales_range(request.query_params)
        request_type = request.query_params.get('requestType') or None
        service_type = request.query_params.get('serviceType') or None
        service_type_from = request.query_params.get('serviceTypeFrom') or None
        show_motivos = _show_motivos(request.query_params)
        buf = build_sales_png(from_date, to_date, request_type, service_type,
                              service_type_from, show_motivos)
        response = HttpResponse(buf.getvalue())
        response['Content-Disposition'] = f'attachment; filename="foto-{from_date}-{to_date}.png"'
        return _download_headers(response)


@extend_schema(responses={200: OpenApiResponse(OpenApiTypes.BINARY)})
class DashboardPdfView(APIView):
    """Planilla del dia del dashboard: disponible para admin y operador."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate().isoformat()
        buf = build_sales_pdf(today, today)
        return _pdf_response(buf, f'planilla-{today}-{today}.pdf')


@extend_schema(responses={200: OpenApiResponse(OpenApiTypes.BINARY)})
class DashboardXlsxView(APIView):
    """Excel del dia del dashboard: disponible para admin y operador."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate().isoformat()
        buf = build_sales_xlsx(today, today)
        response = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="planilla-{today}-{today}.xlsx"'
        return _download_headers(response)


@extend_schema(responses={200: OpenApiResponse(OpenApiTypes.BINARY)})
class DashboardPngView(APIView):
    """Foto del dia del dashboard: disponible para admin y operador."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate().isoformat()
        buf = build_sales_png(today, today)
        response = HttpResponse(buf.getvalue())
        response['Content-Disposition'] = f'attachment; filename="foto-{today}-{today}.png"'
        return _download_headers(response)


@extend_schema(responses={200: dict, 400: dict, 429: dict})
class SalesPdfLinkView(APIView):
    permission_classes = [IsAdminRole]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'report_link'

    def get(self, request):
        token = sign_report_token(_report_token(request, 'pdf'))
        url = f'/api/reports/pdf-public/?token={token}'
        return Response({'url': url})


@extend_schema(responses={200: dict, 400: dict, 429: dict})
class SalesXlsxLinkView(APIView):
    permission_classes = [IsAdminRole]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'report_link'

    def get(self, request):
        token = sign_report_token(_report_token(request, 'xlsx'))
        url = f'/api/reports/xlsx-public/?token={token}'
        return Response({'url': url})


@extend_schema(responses={200: OpenApiResponse(OpenApiTypes.BINARY), 400: dict, 403: dict})
class SalesPdfPublicView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'report_public'

    def get(self, request):
        token = request.query_params.get('token', '')
        payload = unsign_report_token(token)
        if not payload or payload.get('format') != 'pdf':
            return HttpResponse('Enlace inválido o expirado', status=403)
        filters = _filters_from_payload(payload)
        from_date, to_date = filters[:2]
        return _pdf_response(build_sales_pdf(*filters, public=True),
                             f'planilla-{from_date}-{to_date}.pdf')


@extend_schema(responses={200: OpenApiResponse(OpenApiTypes.BINARY), 400: dict, 403: dict})
class SalesXlsxPublicView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'report_public'

    def get(self, request):
        token = request.query_params.get('token', '')
        payload = unsign_report_token(token)
        if not payload or payload.get('format') != 'xlsx':
            return HttpResponse('Enlace inválido o expirado', status=403)
        filters = _filters_from_payload(payload)
        from_date, to_date = filters[:2]
        buf = build_sales_xlsx(*filters, public=True)
        response = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="planilla-{from_date}-{to_date}.xlsx"'
        return _download_headers(response)


@extend_schema_view(get=extend_schema(exclude=True))
class SalesPdfPublicSlashView(SalesPdfPublicView):
    """Alias con slash final, excluido para evitar duplicar OpenAPI."""


@extend_schema_view(get=extend_schema(exclude=True))
class SalesXlsxPublicSlashView(SalesXlsxPublicView):
    """Alias con slash final, excluido para evitar duplicar OpenAPI."""
