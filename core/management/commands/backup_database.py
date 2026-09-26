"""Generacion de copias de seguridad de la base de datos.

En produccion (PostgreSQL/Supabase) usa `pg_dump` en formato custom (.dump),
que es un respaldo LOGICO recuperable con `pg_restore`.

En desarrollo (SQLite) mantiene la copia por la API de backup de SQLite.

El archivo NUNCA se conserva: se genera en un temporal, el caller lo
transmite al navegador y luego lo borra. El modelo Backup solo guarda
metadatos.
"""
import hashlib
import os
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime

import dj_database_url

from django.conf import settings
from django.db import IntegrityError
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Backup, User

# Tamaño maximo permitido para un dump. Frena a un proceso descontrolado
# si alguien manipula parametros. 200 MB es holgado para esta base de datos.
MAX_DUMP_BYTES = 200 * 1024 * 1024
PG_DUMP_TIMEOUT = 300


def compute_checksum(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def find_pg_dump():
    """Localiza el binario pg_dump. Prefiere la version 17 explicita para
    no depender de cual alternativa este activa en el sistema."""
    candidates = [
        '/usr/lib/postgresql/17/bin/pg_dump',
        '/usr/lib/postgresql/16/bin/pg_dump',
        '/usr/lib/postgresql/15/bin/pg_dump',
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return shutil.which('pg_dump')


def _sanitize_error(text, limit=400):
    """Quita cualquier credencial que pudiera aparecer en un error de
    pg_dump antes de guardarlo o devolverlo al cliente."""
    if not text:
        return ''
    import re
    text = re.sub(r'://[^:@/\s]+:[^@/\s]+@', '://***:***@', text)
    text = re.sub(r'password=[^\s]+', 'password=***', text, flags=re.I)
    return ' '.join(text.split())[:limit]


class BackupError(Exception):
    """Error de negocio al generar el respaldo (mensaje ya saneado)."""


def _pg_dump_major(pg_dump):
    """Version mayor del cliente pg_dump instalado."""
    import re
    try:
        proc = subprocess.run([pg_dump, '--version'], capture_output=True,
                              text=True, timeout=10)
        m = re.search(r'(\d+)', proc.stdout or '')
        return int(m.group(1)) if m else None
    except Exception:
        return None


def _server_major():
    """Version mayor del servidor PostgreSQL al que se conectaria Django."""
    import re
    try:
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute('SHOW server_version')
            raw = str(cur.fetchone()[0])
        m = re.match(r'(\d+)', raw)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def check_pg_dump_compatible():
    """pg_dump no puede respaldar un servidor mas nuevo que el mismo.

    Render trae postgresql-client 15 por defecto y Supabase corre 17.6:
    sin este control el respaldo fallaria con un error incomprensible.
    Devuelve (ok, mensaje).
    """
    pg_dump = find_pg_dump()
    if not pg_dump:
        return False, 'pg_dump no esta instalado en el servidor.'
    client = _pg_dump_major(pg_dump)
    server = _server_major()
    if client and server and client < server:
        return False, (
            f'pg_dump instalado es la version {client}, pero el servidor es '
            f'la version {server}. Un respaldo requiere un cliente igual o '
            f'mas nuevo que el servidor.'
        )
    return True, ''


def _pg_dump_config():
    """Configuracion de conexion que debe usar pg_dump.

    La app puede apuntar al transaction pooler (puerto 6543), que es lo
    recomendado para un backend web, pero pg_dump necesita una sesion
    estable. Por eso se admite BACKUP_DATABASE_URL para darle una
    conexion propia al Session pooler (puerto 5432) sin cambiar la de
    la aplicacion.
    """
    backup_url = os.environ.get('BACKUP_DATABASE_URL', '').strip()
    if backup_url:
        cfg = dj_database_url.parse(backup_url, conn_max_age=600)
        # El Session Pooler de Supabase exige SSL.
        cfg['OPTIONS'] = {**(cfg.get('OPTIONS') or {}), 'ssl_require': True}
    else:
        cfg = settings.DATABASES['default']
    return cfg


def _run_pg_dump(target_path):
    """Ejecuta pg_dump contra la base configurada en Django.
    Devuelve (ok, mensaje_saneado)."""
    cfg = _pg_dump_config()
    pg_dump = find_pg_dump()
    if not pg_dump:
        return False, 'pg_dump no esta instalado en el servidor.'

    compatible, why = check_pg_dump_compatible()
    if not compatible:
        return False, why

    host = cfg.get('HOST')
    port = cfg.get('PORT')
    user = cfg.get('USER')
    password = cfg.get('PASSWORD')
    name = cfg.get('NAME')

    if not (host and user and name):
        return False, 'Configuracion de base de datos incompleta.'

    opts = cfg.get('OPTIONS') or {}
    # dj_database_url translatea esto a los parametros de libpq.
    sslmode = 'require' if opts.get('ssl_require') or 'sslmode' in str(opts) else None

    cmd = [
        pg_dump,
        '--host', str(host),
        '--port', str(port or 5432),
        '--username', str(user),
        '--dbname', str(name),
        '--format', 'custom',      # -Fc : comprimido y restaurable con pg_restore
        '--schema', 'public',      # solo nuestro esquema
        '--no-owner',              # los roles de Supabase no existen en el destino
        '--no-privileges',
        '--file', target_path,
    ]
    env = os.environ.copy()
    if sslmode:
        env['PGSSLMODE'] = sslmode

    # La contraseña viaja por entorno, nunca en la linea de comandos
    # (quedaria expuesta en `ps`).
    if password:
        env['PGPASSWORD'] = str(password)

    try:
        proc = subprocess.run(
            cmd, env=env, capture_output=True, text=True,
            timeout=PG_DUMP_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return False, 'pg_dump supero el tiempo limite permitido.'
    except OSError as e:
        return False, f'No se pudo ejecutar pg_dump: {_sanitize_error(str(e), 200)}'

    if proc.returncode != 0:
        return False, _sanitize_error(proc.stderr or 'pg_dump finalizo con error.')

    if not os.path.exists(target_path):
        return False, 'pg_dump no genero el archivo esperado.'
    if os.path.getsize(target_path) == 0:
        return False, 'El archivo generado esta vacio.'

    return True, ''


def _run_sqlite_backup(db_path, target_path):
    import sqlite3
    source = sqlite3.connect(db_path)
    try:
        dest = sqlite3.connect(target_path)
        try:
            source.backup(dest)
        finally:
            dest.close()
    finally:
        source.close()


def _is_in_memory_sqlite(db_path):
    return ':memory:' in str(db_path) or 'memorydb' in str(db_path)


def _run_inmemory_sqlite_dump(target_path):
    """Respaldo de una base SQLite en memoria (solo ocurre en las pruebas
    de Django). Se usa el serializer de Django para volcar los datos."""
    import json

    from django.apps import apps
    from django.core import serializers

    objects = []
    for model in apps.get_models():
        if model._meta.app_label != 'core':
            continue
        for obj in model.objects.all():
            objects.append(serializers.serialize('python', [obj])[0])
    with open(target_path, 'w', encoding='utf-8') as fh:
        json.dump(objects, fh, ensure_ascii=False, default=str)


def create_backup(backup_type='manual', user=None):
    """Genera un respaldo y devuelve (backup, file_path).

    El archivo es temporal: el caller es responsable de eliminarlo cuando
    haya terminado de transmitirlo.
    Lanza BackupError con mensaje ya saneado si falla.
    """
    engine = settings.DATABASES['default']['ENGINE']
    is_postgres = 'postgresql' in engine

    now = timezone.localtime()
    stamp = now.strftime('%Y-%m-%d_%H%M%S')
    # Sufijo unico: dos respaldos dentro del mismo segundo no deben
    # sobrescribirse. La fecha y hora siguen siendo legibles.
    unique = uuid.uuid4().hex[:6]

    in_memory_sqlite = (not is_postgres
                        and _is_in_memory_sqlite(
                            settings.DATABASES['default']['NAME']))
    if is_postgres:
        backup_format, ext = 'dump', 'dump'
    elif in_memory_sqlite:
        backup_format, ext = 'json', 'json'
    else:
        backup_format, ext = 'sqlite3', 'sqlite3'

    filename = f'govista_backup_{stamp}_{unique}.{ext}'

    # La restriccion unica de la base de datos es lo que garantiza que no
    # haya dos respaldos simultaneos: funciona igual con el pooler de
    # transacciones que con conexion directa.
    try:
        backup = Backup.objects.create(
            filename=filename,
            backup_type=backup_type,
            status='running',
            backup_format=backup_format,
            started_at=now,
            created_by=user,
        )
    except IntegrityError:
        raise BackupError('Ya hay un respaldo en proceso. '
                          'Intente en un momento.')

    tmp_dir = getattr(settings, 'BACKUP_TMP_DIR', None) or tempfile.gettempdir()
    os.makedirs(tmp_dir, exist_ok=True)
    target_path = os.path.join(tmp_dir, filename)

    try:
        if is_postgres:
            ok, message = _run_pg_dump(target_path)
            if not ok:
                raise BackupError(message)
        elif in_memory_sqlite:
            _run_inmemory_sqlite_dump(target_path)
        else:
            db_path = settings.DATABASES['default']['NAME']
            if not os.path.exists(db_path):
                raise BackupError('Base de datos local no encontrada.')
            _run_sqlite_backup(db_path, target_path)

        size = os.path.getsize(target_path)
        if size > MAX_DUMP_BYTES:
            raise BackupError('El respaldo excede el tamano maximo permitido.')

        checksum = compute_checksum(target_path)

        backup.status = 'success'
        backup.size = size
        backup.checksum = checksum
        backup.verified = True
        backup.finished_at = timezone.localtime()
        backup.save(update_fields=[
            'status', 'size', 'checksum', 'verified', 'finished_at'])
    except Exception as e:
        backup.status = 'failed'
        backup.error_message = _sanitize_error(
            str(e) if isinstance(e, BackupError)
            else 'Error interno al generar el respaldo.')
        backup.finished_at = timezone.localtime()
        backup.save(update_fields=['status', 'error_message', 'finished_at'])
        # No dejamos archivos huerfanos
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
            except OSError:
                pass
        raise

    backup.storage_path = target_path
    return backup, target_path


def cleanup_old_backups(keep=12):
    """Elimina registros antiguos. Los archivos ya se borran al descargarse,
    asi que aqui solo se limpia el historial (no borra backups manuales)."""
    stale = Backup.objects.filter(
        backup_type='automatic', status__in=['success', 'failed']
    ).order_by('-created_at')[keep:]
    count = 0
    for b in stale:
        if b.storage_path and os.path.exists(b.storage_path):
            try:
                os.remove(b.storage_path)
            except OSError:
                pass
        b.delete()
        count += 1
    return count


class Command(BaseCommand):
    help = 'Crea un respaldo consistente de la base de datos (pg_dump o SQLite).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type', dest='backup_type', default='manual',
            choices=['automatic', 'manual'],
            help='Tipo de backup (default: manual)')
        parser.add_argument(
            '--user', dest='user_id', type=int, default=None,
            help='ID del usuario que crea el backup')

    def handle(self, *args, **options):
        backup_type = options['backup_type']
        user = None
        if options['user_id']:
            try:
                user = User.objects.get(id=options['user_id'])
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'Usuario con id {options["user_id"]} no encontrado.'))

        try:
            backup, path = create_backup(backup_type=backup_type, user=user)
            self.stdout.write(self.style.SUCCESS(
                f'Backup creado: {backup.filename} '
                f'({backup.size} bytes, sha256 {backup.checksum[:16]}...)'))
            self.stdout.write(f'Archivo temporal: {path}')
            self.stdout.write(self.style.WARNING(
                'El archivo es temporal: transfiérelo y bórralo si no lo necesita.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al crear backup: {e}'))
            raise
