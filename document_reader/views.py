from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from core.rbac import has_permission

from .services import DocumentReaderError, extract_retirement


class RetirementDocumentExtractView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        if not has_permission(request.user, 'comercial.view'):
            return Response({'error': 'No tienes permiso para usar el lector.'}, status=403)
        uploaded = request.FILES.get('file')
        if uploaded is None:
            return Response({'error': 'Adjunta una orden SOTV.'}, status=400)
        try:
            return Response(extract_retirement(uploaded), status=status.HTTP_200_OK)
        except DocumentReaderError as exc:
            return Response({'error': {'code': exc.code, 'message': str(exc)}}, status=exc.status)
