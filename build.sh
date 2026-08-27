#!/bin/bash
set -ex

echo "=== Build SaleStracker ==="
echo "Working dir: $(pwd)"

export DJANGO_SETTINGS_MODULE=salestracker.settings

echo "Running collectstatic..."
python manage.py collectstatic --noinput --verbosity 2

echo "Static files:"
ls -la staticfiles/ | head -10

echo "=== Build completo ==="
