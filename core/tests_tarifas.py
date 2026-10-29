from decimal import Decimal

from django.test import TestCase, Client

from .models import TarifaTraslado, User


class TransferTariffTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = self._user('tariff-admin', 'admin')
        self.operator = self._user('tariff-operator', 'ventas')

    def _user(self, name, role):
        user = User(name=name, role=role)
        user.set_password('pass1')
        user.save()
        return user

    def _token(self, user):
        response = self.client.post(
            '/api/auth/login', {'name': user.name, 'password': 'pass1'},
            content_type='application/json')
        return response.json()['token']

    def test_active_tariffs_are_available_to_authenticated_operator(self):
        response = self.client.get(
            '/api/transfer-tariffs/active',
            HTTP_AUTHORIZATION=f'Bearer {self._token(self.operator)}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 3)

    def test_only_admin_can_update_and_history_is_kept(self):
        tariff = TarifaTraslado.objects.get(service_type='internet')
        operator_response = self.client.put(
            f'/api/transfer-tariffs/{tariff.id}',
            {'amount': '125.00'}, content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self._token(self.operator)}')
        self.assertEqual(operator_response.status_code, 403)

        admin_response = self.client.put(
            f'/api/transfer-tariffs/{tariff.id}',
            {'amount': '125.00'}, content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self._token(self.admin)}')
        self.assertEqual(admin_response.status_code, 200)
        tariff.refresh_from_db()
        self.assertEqual(tariff.amount, Decimal('125.00'))
        self.assertTrue(tariff.history.exists())

    def test_operator_cannot_create_tariff(self):
        response = self.client.post(
            '/api/transfer-tariffs',
            {'service_type': 'internet', 'name': 'Duplicada', 'amount': 99},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self._token(self.operator)}')
        self.assertEqual(response.status_code, 403)
