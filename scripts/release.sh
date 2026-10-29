#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${PYTHON_BIN:-}" ]]; then
  :
elif [[ -x .venv/bin/python ]]; then
  PYTHON_BIN=".venv/bin/python"
else
  PYTHON_BIN="python3"
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL es obligatoria para el release." >&2
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import os

import django
from django.core.management import call_command
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'salestracker.settings')
django.setup()

with connection.cursor() as cursor:
    cursor.execute('SELECT pg_advisory_lock(824751902)')
try:
    call_command('migrate', interactive=False, verbosity=1)
finally:
    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_unlock(824751902)')
PY
