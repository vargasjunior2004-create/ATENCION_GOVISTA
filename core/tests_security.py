import os
from unittest.mock import patch

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

    @override_settings(DEBUG=False)
    def test_seed_rejects_weak_production_credentials(self):
        env = {
            'DJANGO_SEED_ADMIN_PASSWORD': 'admin',
            'DJANGO_SEED_SALES_PASSWORD': 'ventas',
        }
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaises(CommandError):
                management.call_command('seed', users_only=True)
