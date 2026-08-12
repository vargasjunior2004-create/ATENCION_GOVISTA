"""
WSGI config for salestracker project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'salestracker.settings')

if os.environ.get('WASMER') == 'true':
    import django
    django.setup()
    from django.core.management import call_command
    from core.models import Plan
    import logging
    logger = logging.getLogger(__name__)
    try:
        call_command('collectstatic', interactive=False, verbosity=0)
        logger.info('migrate iniciando...')
        call_command('migrate', interactive=False, verbosity=0)
        logger.info('migrate completado')
        if not Plan.objects.exists():
            logger.info('Sin planes — cargando fixture...')
            call_command('loaddata', 'planes', verbosity=0)
            logger.info('Fixture planes cargado')
        call_command('seed', users_only=True)
        logger.info('Seed users completado')
    except Exception:
        logger.exception('migrate/seed en arranque falló')
        raise

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

# Entrypoint que usa Wasmer Edge
app = application
