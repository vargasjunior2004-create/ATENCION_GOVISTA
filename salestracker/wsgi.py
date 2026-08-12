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

# Bootstrap: migrate + fixture + seed al arrancar (idempotente)
try:
    from django.core.management import call_command
    logger = logging.getLogger('wsgi')
    logger.info('migrate iniciando...')
    call_command('migrate', interactive=False, verbosity=0)
    logger.info('migrate completado')

    from core.models import Plan
    if not Plan.objects.exists():
        logger.info('Sin planes — cargando fixture...')
        call_command('loaddata', 'planes', verbosity=0)
        logger.info('Fixture planes cargado')

    call_command('seed', users_only=True)
    logger.info('Seed users completado')
except Exception:
    logging.getLogger('wsgi').exception('Bootstrap en arranque falló')
