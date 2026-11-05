from django.test import Client, TestCase

from .models import User


class LoginSecurityTests(TestCase):
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
