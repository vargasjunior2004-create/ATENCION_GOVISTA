import logging
import traceback as tb

logger = logging.getLogger('salestracker.errors')


class ErrorLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        logger.error(
            'UNHANDLED EXCEPTION %s %s: %s\n%s',
            request.method, request.path, exception, tb.format_exc()
        )
        return None
