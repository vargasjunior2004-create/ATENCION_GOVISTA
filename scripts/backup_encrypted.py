#!/usr/bin/env python3
"""Genera un backup cifrado localmente a partir del comando de Django."""
import hashlib
import os
import subprocess
from pathlib import Path


def checksum(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    passphrase = os.environ.get('BACKUP_ENCRYPTION_PASSPHRASE', '')
    if len(passphrase) < 16:
        raise SystemExit(
            'BACKUP_ENCRYPTION_PASSPHRASE debe tener al menos 16 caracteres.')
    if not os.environ.get('BACKUP_DATABASE_URL'):
        raise SystemExit('BACKUP_DATABASE_URL es obligatoria.')

    output_dir = Path(os.environ.get('BACKUP_OUTPUT_DIR', 'backups-local'))
    output_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(output_dir, 0o700)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'salestracker.settings')
    import django
    django.setup()
    from core.management.commands.backup_database import create_backup

    raw_path = None
    encrypted_path = None
    try:
        backup, raw_path = create_backup(backup_type='manual')
        raw_path = Path(raw_path)
        encrypted_path = output_dir / f'{backup.filename}.enc'
        subprocess.run(
            [
                'openssl', 'enc', '-aes-256-cbc', '-pbkdf2', '-salt',
                '-in', str(raw_path), '-out', str(encrypted_path),
                '-pass', 'env:BACKUP_ENCRYPTION_PASSPHRASE',
            ],
            env=os.environ.copy(), check=True,
            capture_output=True, text=True,
        )
        os.chmod(encrypted_path, 0o600)
        digest = checksum(encrypted_path)
        checksum_path = encrypted_path.with_suffix(encrypted_path.suffix + '.sha256')
        checksum_path.write_text(f'{digest}  {encrypted_path.name}\n', encoding='utf-8')
        os.chmod(checksum_path, 0o600)
        backup.storage_path = ''
        backup.save(update_fields=['storage_path'])
        print(f'Backup cifrado: {encrypted_path}')
        print(f'Checksum SHA-256: {checksum_path}')
    except subprocess.CalledProcessError as error:
        raise SystemExit('No se pudo cifrar el backup con openssl.') from error
    finally:
        if raw_path and raw_path.exists():
            raw_path.unlink()


if __name__ == '__main__':
    main()
