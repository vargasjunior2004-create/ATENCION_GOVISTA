"""Backup SQLite database using SQLite's backup API for consistency.

Usage:
    python manage.py backup_database                    # automatic backup
    python manage.py backup_database --type manual      # manual backup
    python manage.py backup_database --user <user_id>   # with creator
"""
import hashlib
import os
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Backup, User


def get_backup_dir():
    base = os.path.dirname(settings.DATABASES['default']['NAME'])
    backup_dir = os.path.join(base, 'backups')
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def compute_checksum(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def create_backup(backup_type='automatic', user=None):
    """Create a consistent SQLite backup using the SQLite backup API."""
    import sqlite3

    db_path = settings.DATABASES['default']['NAME']

    if not os.path.exists(db_path):
        raise FileNotFoundError(f'Database not found: {db_path}')

    now = timezone.localtime()
    sub = 'automatic' if backup_type == 'automatic' else 'manual'
    backup_dir = os.path.join(get_backup_dir(), sub)
    os.makedirs(backup_dir, exist_ok=True)

    filename = f'sales_tracker_backup_{now.strftime("%Y-%m-%d_%H%M")}.sqlite3'
    filepath = os.path.join(backup_dir, filename)

    # Open source database
    source = sqlite3.connect(db_path)
    try:
        # Create backup using SQLite's backup API (consistent snapshot)
        dest = sqlite3.connect(filepath)
        try:
            source.backup(dest)
        finally:
            dest.close()
    finally:
        source.close()

    size = os.path.getsize(filepath)
    checksum = compute_checksum(filepath)

    backup = Backup.objects.create(
        filename=filename,
        backup_type=backup_type,
        status='success',
        size=size,
        storage_path=filepath,
        checksum=checksum,
        created_by=user,
    )

    return backup


def cleanup_old_backups(keep=7):
    """Remove old automatic backups beyond the retention limit."""
    automatics = Backup.objects.filter(
        backup_type='automatic', status='success'
    ).order_by('-created_at')

    if automatics.count() > keep:
        to_delete = automatics[keep:]
        for b in to_delete:
            if b.storage_path and os.path.exists(b.storage_path):
                try:
                    os.remove(b.storage_path)
                except OSError:
                    pass
            b.delete()
        return len(to_delete)
    return 0


class Command(BaseCommand):
    help = 'Crea un backup consistente de la base de datos SQLite.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type', dest='backup_type', default='automatic',
            choices=['automatic', 'manual'],
            help='Tipo de backup (default: automatic)')
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
                    f'Usuario con id {options["user_id"]} no encontrado. '
                    f'Backup sera sin usuario.'))

        try:
            backup = create_backup(backup_type=backup_type, user=user)
            self.stdout.write(self.style.SUCCESS(
                f'Backup creado: {backup.filename} '
                f'({backup.size} bytes, {backup.checksum[:16]}...)'))

            if backup_type == 'automatic':
                deleted = cleanup_old_backups(keep=7)
                if deleted:
                    self.stdout.write(
                        f'Eliminados {deleted} backups automaticos antiguos.')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error al crear backup: {e}'))
            raise
