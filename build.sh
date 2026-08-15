#!/bin/bash
set -e

echo "=== Build SaleStracker ==="

export DJANGO_SETTINGS_MODULE=salestracker.settings

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Cargar planes si la tabla está vacía
python -c "
import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'salestracker.settings'
django.setup()
from core.models import Plan
if not Plan.objects.exists():
    from django.core.management import call_command
    call_command('loaddata', 'planes', verbosity=0)
    print('Planes cargados')
else:
    print('Planes ya existen')
"

python manage.py seed --users-only

echo "=== Build completo ==="
