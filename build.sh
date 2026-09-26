#!/bin/bash
set -ex

echo "=== Build SaleStracker ==="
echo "Working dir: $(pwd)"

export DJANGO_SETTINGS_MODULE=salestracker.settings

# --- pg_dump 17 (cliente PostgreSQL) -------------------------------------
# Render native runtime = Debian 12 bookworm con postgresql-client 15.
# La base de datos de Supabase corre PostgreSQL 17.6, y pg_dump NO puede
# respaldar un servidor mas nuevo que el mismo (aborta por version mismatch).
# Instalamos el cliente 17 desde el repositorio oficial de PGDG.
echo "Instalando postgresql-client-17..."
export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
apt-get install -y -qq --no-install-recommends ca-certificates curl gnupg

install -d /usr/share/postgresql-common/pgdg
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
  -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc

echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
  > /etc/apt/sources.list.d/pgdg.list

apt-get update -qq
apt-get install -y -qq --no-install-recommends postgresql-client-17

# Aseguramos que /usr/bin/pg_dump apunte a la version 17
if [ -x /usr/lib/postgresql/17/bin/pg_dump ]; then
  update-alternatives --install /usr/bin/pg_dump pg_dump \
    /usr/lib/postgresql/17/bin/pg_dump 100 2>/dev/null || true
  update-alternatives --set pg_dump /usr/lib/postgresql/17/bin/pg_dump 2>/dev/null || true
fi

echo "--- Version de pg_dump instalada ---"
/usr/lib/postgresql/17/bin/pg_dump --version || pg_dump --version
# -------------------------------------------------------------------------

echo "Running collectstatic..."
python manage.py collectstatic --noinput --verbosity 2

echo "Static files:"
ls -la staticfiles/ | head -10

echo "=== Build completo ==="
