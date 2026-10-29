import os
import subprocess
import sys
from unittest.mock import patch
from pathlib import Path

from django.core import management
from django.core.management.base import CommandError
from django.test import TestCase, override_settings


class SeedSecurityTests(TestCase):
    @override_settings(DEBUG=False)
    def test_seed_requires_credentials_from_environment(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('DJANGO_SEED_ADMIN_PASSWORD', None)
            os.environ.pop('DJANGO_SEED_SALES_PASSWORD', None)
            with self.assertRaises(CommandError):
                management.call_command('seed', users_only=True)

    def test_production_without_secret_fails_fast(self):
        root = Path(__file__).resolve().parent.parent
        env = os.environ.copy()
        env.pop('DJANGO_SECRET_KEY', None)
        env['DJANGO_DEBUG'] = 'false'
        result = subprocess.run(
            [sys.executable, 'manage.py', 'check'],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DJANGO_SECRET_KEY es obligatoria', result.stderr)

    @override_settings(DEBUG=False)
    def test_seed_rejects_weak_production_credentials(self):
        env = {
            'DJANGO_SEED_ADMIN_PASSWORD': 'admin',
            'DJANGO_SEED_SALES_PASSWORD': 'ventas',
        }
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaises(CommandError):
                management.call_command('seed', users_only=True)
