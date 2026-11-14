from django.test import Client, TestCase

from .models import User


class LoginSecurityTests(TestCase):
    def test_login_repairs_missing_normalized_username(self):
        user = User.objects.create(name='Usuario Antiguo', role='ventas')
        user.set_password('valid-login-password')
        user.save()
        User.objects.filter(pk=user.pk).update(name_normalized=None)

        response = Client().post(
            '/api/auth/login',
            {'name': ' usuario antiguo ', 'password': 'valid-login-password'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        user.refresh_from_db()
        self.assertEqual(user.name_normalized, 'usuario antiguo')

    def test_failed_attempts_do_not_create_temporary_lockout(self):
        user = User.objects.create(name='login-security', role='ventas')
        user.set_password('valid-login-password')
        user.save()
        client = Client()

        for _ in range(6):
            response = client.post(
                '/api/auth/login',
                {'name': user.name, 'password': 'wrong-password'},
                content_type='application/json',
            )
            self.assertEqual(response.status_code, 401)

        response = client.post(
            '/api/auth/login',
            {'name': user.name, 'password': 'valid-login-password'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_password_login_remains_case_sensitive(self):
        user = User.objects.create(name='case-sensitive-login', role='ventas')
        user.set_password('MixedCase-password-123')
        user.save()
        client = Client()

        wrong_case = client.post(
            '/api/auth/login',
            {'name': user.name, 'password': 'MIXEDCASE-PASSWORD-123'},
            content_type='application/json',
        )
        valid = client.post(
            '/api/auth/login',
            {'name': user.name, 'password': 'MixedCase-password-123'},
            content_type='application/json',
        )

        self.assertEqual(wrong_case.status_code, 401)
        self.assertEqual(valid.status_code, 200, valid.content)
