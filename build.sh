#!/bin/bash
set -ex

echo "=== Build SaleStracker ==="
echo "Working dir: $(pwd)"

export DJANGO_SETTINGS_MODULE=salestracker.settings

echo "Compilando frontend..."
node --version
npm --version
PG_DUMP_VERSION=$(pg_dump --version)
echo "$PG_DUMP_VERSION"
PG_DUMP_MAJOR=$(printf '%s\n' "$PG_DUMP_VERSION" | sed -n 's/^pg_dump (PostgreSQL) \([0-9][0-9]*\).*/\1/p')
if [ -z "$PG_DUMP_MAJOR" ] || [ "$PG_DUMP_MAJOR" -lt 17 ]; then
  echo "Se requiere pg_dump 17 o superior para respaldar PostgreSQL 17; encontrado: $PG_DUMP_VERSION" >&2
  exit 1
fi

cd frontend
npm ci
BUILD_PATH=../frontend_build npm run build
cd ..

echo "Running collectstatic..."
python manage.py collectstatic --clear --noinput --verbosity 2

echo "Aplicando migraciones de base de datos..."
python manage.py migrate --noinput

if [ "${BACKFILL_CUSTOMERS:-false}" = "true" ]; then
  echo "Ejecutando backfill autorizado de clientes y contratos históricos..."
  python manage.py backfill_customers --apply
else
  echo "Backfill histórico omitido (BACKFILL_CUSTOMERS no está habilitado)."
fi

echo "Verificando assets del frontend..."
FRONTEND_JS=$(sed -n 's|.*"main.js": "/static/js/\([^"]*\)".*|\1|p' frontend_build/asset-manifest.json)
FRONTEND_CSS=$(sed -n 's|.*"main.css": "/static/css/\([^"]*\)".*|\1|p' frontend_build/asset-manifest.json)

if [ -z "$FRONTEND_JS" ] || [ -z "$FRONTEND_CSS" ]; then
  echo "No se pudieron obtener los assets principales desde asset-manifest.json"
  exit 1
fi

for asset in "staticfiles/js/$FRONTEND_JS" "staticfiles/css/$FRONTEND_CSS"; do
  if [ ! -f "$asset" ]; then
    echo "Asset del frontend ausente despues de collectstatic: $asset"
    exit 1
  fi
done

echo "Static files:"
ls -la staticfiles/ | head -10

echo "=== Build completo ==="
