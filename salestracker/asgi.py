"""
ASGI config for salestracker project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'salestracker.settings')

from django.core.asgi import get_asgi_application
application = get_asgi_application()

app = application
