"""
WSGI config for salestracker project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'salestracker.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Entrypoint que usa Wasmer Edge
app = application

# Bootstrap: fixture + seed al arrancar (idempotente)
# migrate ya lo ejecuta after_deploy de Wasmer
try:
    from django.core.management import call_command
    logger = logging.getLogger('wsgi')

    from core.models import Plan
    if not Plan.objects.exists():
        logger.info('Sin planes — cargando fixture...')
        call_command('loaddata', 'planes', verbosity=0)
        logger.info('Fixture planes cargado')

    call_command('seed', users_only=True)
    logger.info('Seed users completado')
except Exception:
    logging.getLogger('wsgi').exception('Bootstrap en arranque falló')
