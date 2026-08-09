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
    try:
        call_command('collectstatic', interactive=False, verbosity=0)
        call_command('migrate', interactive=False, verbosity=0)
        # Arranque en limpio: si la BD está vacía se carga el catálogo de
        # planes (fixture); los usuarios se garantizan con seed (idempotente).
        # NUNCA se crean ventas/arqueos mock en producción.
        if not Plan.objects.exists():
            call_command('loaddata', 'planes', verbosity=0)
        call_command('seed', users_only=True)
    except Exception:
        import logging
        logging.getLogger(__name__).exception('migrate/seed en arranque falló')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

# Entrypoint que usa Wasmer Edge
app = application
