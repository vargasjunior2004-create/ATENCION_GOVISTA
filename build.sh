#!/bin/bash
set -e

echo "=== Build SaleStracker ==="

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Cargar planes si la tabla está vacía
python -c "
from core.models import Plan
from django.core.management import call_command
if not Plan.objects.exists():
    call_command('loaddata', 'planes', verbosity=0)
    print('Planes cargados')
else:
    print('Planes ya existen')
"

python manage.py seed --users-only

echo "=== Build completo ==="
