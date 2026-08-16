"""
ASGI config for salestracker project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'salestracker.settings')

from django.core.asgi import get_asgi_application
application = get_asgi_application()

app = application

try:
    from django.core.management import call_command
    logger = logging.getLogger('asgi')
    call_command('migrate', interactive=False, verbosity=0)

    from core.models import Plan
    if not Plan.objects.exists():
        call_command('loaddata', 'planes', verbosity=0)

    call_command('seed', users_only=True)
    logger.info('Bootstrap ASGI completado')
except Exception:
    logging.getLogger('asgi').exception('Bootstrap en arranque ASGI falló')
