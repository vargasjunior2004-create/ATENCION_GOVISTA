from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from .models import User, UserSession


class JwtSessionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(name='session-user', role='ventas')
        self.user.set_password('session-password-123')
        self.user.save()

    def login(self):
        response = self.client.post(
            '/api/auth/login',
            {'name': self.user.name, 'password': 'session-password-123'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()['token']

    @staticmethod
    def auth(token):
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_login_creates_a_valid_individual_session(self):
        token = self.login()

        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 1)
        response = self.client.get('/api/auth/me', **self.auth(token))

        self.assertEqual(response.status_code, 200)

    def test_invalid_login_is_rejected(self):
        response = self.client.post(
            '/api/auth/login',
            {'name': self.user.name, 'password': 'wrong-password'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 401)

    def test_logout_revokes_only_the_current_session(self):
        first_token = self.login()
        second_token = self.login()

        logout = self.client.post('/api/auth/logout', **self.auth(first_token))

        self.assertEqual(logout.status_code, 200)
        self.assertTrue(logout.json()['revoked'])
        self.assertEqual(
            self.client.get('/api/auth/me', **self.auth(first_token)).status_code,
            401,
        )
        self.assertEqual(
            self.client.get('/api/auth/me', **self.auth(second_token)).status_code,
            200,
        )

    def test_password_change_invalidates_all_previous_sessions(self):
        first_token = self.login()
        second_token = self.login()

        changed = self.client.post(
            '/api/auth/change-password',
            {
                'current_password': 'session-password-123',
                'new_password': 'session-password-456',
                'new_password_confirm': 'session-password-456',
            },
            content_type='application/json',
            **self.auth(first_token),
        )

        self.assertEqual(changed.status_code, 200, changed.content)
        self.assertEqual(
            self.client.get('/api/auth/me', **self.auth(first_token)).status_code,
            401,
        )
        self.assertEqual(
            self.client.get('/api/auth/me', **self.auth(second_token)).status_code,
            401,
        )
        self.assertEqual(
            self.client.get(
                '/api/auth/me', **self.auth(changed.json()['token'])
            ).status_code,
            200,
        )

    def test_inactive_user_cannot_use_an_existing_token(self):
        token = self.login()
        self.user.active = False
        self.user.save(update_fields=['active'])

        response = self.client.get('/api/auth/me', **self.auth(token))

        self.assertEqual(response.status_code, 401)

    def test_expired_access_token_is_rejected(self):
        token = AccessToken.for_user(self.user)
        token['ver'] = self.user.token_version
        token['sid'] = str(UserSession.objects.create(
            user=self.user,
            expires_at=timezone.now() + timedelta(minutes=30),
        ).session_id)
        token.set_exp(lifetime=timedelta(seconds=-1))

        response = self.client.get('/api/auth/me', **self.auth(str(token)))

        self.assertEqual(response.status_code, 401)
