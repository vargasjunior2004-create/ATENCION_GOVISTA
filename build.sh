#!/bin/bash
set -ex

echo "=== Build SaleStracker ==="
echo "Working dir: $(pwd)"

export DJANGO_SETTINGS_MODULE=salestracker.settings

echo "Verificando cliente PostgreSQL..."
PG_DUMP_VERSION=$(pg_dump --version)
echo "$PG_DUMP_VERSION"
case "$PG_DUMP_VERSION" in
  *" 17."*) ;;
  *)
    echo "Se requiere pg_dump 17 para respaldar PostgreSQL 17." >&2
    exit 1
    ;;
esac

echo "Build del backend completado."
