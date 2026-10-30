"""Extensiones de OpenAPI para componentes propios de la API."""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CoreJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """Describe el Bearer JWT usado por las vistas de core."""

    target_class = 'core.auth.CoreJWTAuthentication'
    name = 'CoreJWT'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
        }
