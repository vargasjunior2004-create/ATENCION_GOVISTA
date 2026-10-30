from django.test import TestCase, Client

from .models import User


class SaleListQueryValidationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User(name='api-query-user', role='ventas')
        self.user.set_password('api-pass')
        self.user.save()
        login = self.client.post(
            '/api/auth/login',
            {'name': self.user.name, 'password': 'api-pass'},
            content_type='application/json')
        self.auth = {'HTTP_AUTHORIZATION': f'Bearer {login.json()["token"]}'}

    def test_non_numeric_page_size_returns_400(self):
        response = self.client.get(
            '/api/sales?page_size=abc', **self.auth)
        self.assertEqual(response.status_code, 400)

    def test_page_size_over_limit_returns_400(self):
        response = self.client.get(
            '/api/sales?page_size=10000', **self.auth)
        self.assertEqual(response.status_code, 400)

    def test_invalid_date_range_returns_400(self):
        response = self.client.get(
            '/api/sales?from=2026-02-01&to=2026-01-01', **self.auth)
        self.assertEqual(response.status_code, 400)

    def test_unknown_service_filter_returns_400(self):
        response = self.client.get(
            '/api/sales?serviceType=desconocido', **self.auth)
        self.assertEqual(response.status_code, 400)
