#!/bin/bash
set -e

echo "=== Build SaleStracker ==="

python manage.py collectstatic --noinput

echo "=== Build completo ==="
