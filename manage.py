#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'salestracker.settings')
    # Asegurar que el directorio de la BD exista (Wasmer volume /data)
    db_path = os.environ.get('SQLITE_PATH',
                             str(os.path.join(os.path.dirname(__file__), 'data', 'db.sqlite3')))
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        _test = os.path.join(os.path.dirname(db_path), '.write_test')
        open(_test, 'w').close()
        os.remove(_test)
    except OSError:
        pass  # settings.py will fall back to local path
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
