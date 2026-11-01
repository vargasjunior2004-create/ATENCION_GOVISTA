#!/bin/bash
set -ex

echo "=== Build SaleStracker ==="
echo "Working dir: $(pwd)"

export DJANGO_SETTINGS_MODULE=salestracker.settings

echo "Verificando cliente PostgreSQL..."
PG_DUMP_VERSION=$(pg_dump --version)
echo "$PG_DUMP_VERSION"
PG_DUMP_MAJOR=$(printf '%s\n' "$PG_DUMP_VERSION" | sed -n 's/^pg_dump (PostgreSQL) \([0-9][0-9]*\).*/\1/p')
if [ -z "$PG_DUMP_MAJOR" ] || [ "$PG_DUMP_MAJOR" -lt 17 ]; then
  echo "Se requiere pg_dump 17 o superior para respaldar PostgreSQL 17; encontrado: $PG_DUMP_VERSION" >&2
  exit 1
fi

echo "Build del backend completado."
