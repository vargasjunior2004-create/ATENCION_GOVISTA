from datetime import date

from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .reports import (
    build_sales_pdf, build_sales_xlsx, build_sales_png, build_cash_pdf,
    sign_report_token, unsign_report_token, REQUEST_TYPE_LABELS,
)


def _sales_range(params, default_day=True):
    today = date.today().isoformat()
    from_date = params.get('from') or (today if default_day else '')
    to_date = params.get('to') or (today if default_day else '')
    return from_date, to_date


def _pdf_response(buf, filename):
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


class SalesPdfView(APIView):
    def get(self, request):
        from_date, to_date = _sales_range(request.query_params)
        request_type = request.query_params.get('requestType') or None
        buf = build_sales_pdf(from_date, to_date, request_type)
        suffix = f'-{REQUEST_TYPE_LABELS.get(request_type, "TODOS")}' if request_type else ''
        return _pdf_response(buf, f'planilla{suffix}-{from_date}-{to_date}.pdf')


class SalesXlsxView(APIView):
    def get(self, request):
        from_date, to_date = _sales_range(request.query_params)
        buf = build_sales_xlsx(from_date, to_date)
        response = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="planilla-{from_date}-{to_date}.xlsx"'
        return response


class SalesPngView(APIView):
    def get(self, request):
        from_date, to_date = _sales_range(request.query_params)
        buf = build_sales_png(from_date, to_date)
        response = HttpResponse(buf.getvalue(), content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="foto-{from_date}-{to_date}.png"'
        return response


class SalesPdfLinkView(APIView):
    def get(self, request):
        from_date, to_date = _sales_range(request.query_params)
        token = sign_report_token(f'{from_date}:{to_date}')
        url = f'/api/reports/pdf-public/?token={token}'
        return Response({'url': url})


class SalesXlsxLinkView(APIView):
    def get(self, request):
        from_date, to_date = _sales_range(request.query_params)
        token = sign_report_token(f'xlsx:{from_date}:{to_date}')
        url = f'/api/reports/xlsx-public/?token={token}'
        return Response({'url': url})


class SalesPdfPublicView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get('token', '')
        payload = unsign_report_token(token)
        if not payload:
            return HttpResponse('Enlace inválido o expirado', status=400)
        parts = payload.split(':')
        if payload.startswith('xlsx:'):
            return HttpResponse('Tipo de archivo no válido', status=400)
        if len(parts) != 2:
            return HttpResponse('Enlace inválido', status=400)
        from_date, to_date = parts
        return _pdf_response(build_sales_pdf(from_date, to_date),
                             f'planilla-{from_date}-{to_date}.pdf')


class SalesXlsxPublicView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get('token', '')
        payload = unsign_report_token(token)
        if not payload or not payload.startswith('xlsx:'):
            return HttpResponse('Enlace inválido o expirado', status=400)
        from_date, to_date = payload[5:].split(':')
        buf = build_sales_xlsx(from_date, to_date)
        response = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="planilla-{from_date}-{to_date}.xlsx"'
        return response


class CashPdfView(APIView):
    def get(self, request):
        d = request.query_params.get('date') or date.today().isoformat()
        return _pdf_response(build_cash_pdf(d), f'arqueo-{d}.pdf')


class CashPdfLinkView(APIView):
    def get(self, request):
        d = request.query_params.get('date') or date.today().isoformat()
        token = sign_report_token(f'cash:{d}')
        return Response({'url': f'/api/reports/cash-public/?token={token}'})


class CashPdfPublicView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get('token', '')
        payload = unsign_report_token(token)
        if not payload or not payload.startswith('cash:'):
            return HttpResponse('Enlace inválido o expirado', status=400)
        d = payload[5:]
        return _pdf_response(build_cash_pdf(d), f'arqueo-{d}.pdf')
