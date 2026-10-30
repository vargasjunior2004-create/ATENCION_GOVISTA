import logging
import traceback as tb
import uuid

logger = logging.getLogger('salestracker.errors')


class RequestIDMiddleware:
    """Propaga un identificador seguro para correlacionar una petición."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        candidate = request.headers.get('X-Request-ID', '')
        try:
            request_id = str(uuid.UUID(candidate))
        except (ValueError, AttributeError):
            request_id = str(uuid.uuid4())
        request.request_id = request_id
        response = self.get_response(request)
        response['X-Request-ID'] = request_id
        return response


class ErrorLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        logger.error(
            'UNHANDLED EXCEPTION request_id=%s %s %s: %s\n%s',
            getattr(request, 'request_id', '-'), request.method,
            request.path, exception, tb.format_exc()
        )
        return None
