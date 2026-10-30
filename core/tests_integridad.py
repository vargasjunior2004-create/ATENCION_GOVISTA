from datetime import date

from django.test import TestCase, Client

from .models import (Customer, Plan, Sale, TarifaTraslado, TrasladoExterno,
                     User)


class ProtectedDeleteTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User(name='integridad-admin', role='admin')
        self.admin.set_password('pass-admin')
        self.admin.save()
        self.plan = Plan.objects.create(
            code='INTEGRIDAD-PLAN', label='Plan integridad', type='internet',
            monthly=100, installation=50)

    def token(self):
        response = self.client.post(
            '/api/auth/login',
            {'name': self.admin.name, 'password': 'pass-admin'},
            content_type='application/json')
        return response.json()['token']

    def test_delete_sale_with_protected_dependencies_returns_409(self):
        sale = Sale.objects.create(
            date=date.today(), clientCode='PROTECT-1', clientName='PRUEBA',
            serviceType='internet', plan=self.plan, total=150,
            createdBy=self.admin)
        customer = Customer.objects.create(code='PROTECT-1', name='PRUEBA')
        tariff = TarifaTraslado.objects.get(service_type='internet')
        sale.customer = customer
        sale.save(update_fields=['customer'])
        TrasladoExterno.objects.create(
            sale=sale, customer=customer, tariff=tariff,
            tariff_amount=tariff.amount, new_address='DOMICILIO',
            has_physical_sketch=True, created_by=self.admin)
        response = self.client.delete(
            f'/api/sales/{sale.id}',
            HTTP_AUTHORIZATION=f'Bearer {self.token()}')
        self.assertEqual(response.status_code, 409)
        self.assertTrue(Sale.objects.filter(id=sale.id).exists())

    def test_sale_creation_is_idempotent(self):
        payload = {
            'clientCode': 'IDEMP-1', 'clientName': 'PRUEBA IDEMPOTENCIA',
            'serviceType': 'internet', 'requestType': 'nuevo_contrato',
            'planId': self.plan.id,
        }
        headers = {
            'HTTP_AUTHORIZATION': f'Bearer {self.token()}',
            'HTTP_IDEMPOTENCY_KEY': 'idempotency-test-001',
        }
        first = self.client.post('/api/sales', payload,
                                 content_type='application/json', **headers)
        second = self.client.post('/api/sales', payload,
                                  content_type='application/json', **headers)

        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(second.status_code, 201, second.content)
        self.assertEqual(second['Idempotent-Replayed'], 'true')
        self.assertEqual(first.json()['id'], second.json()['id'])
        self.assertEqual(Sale.objects.filter(clientCode='IDEMP-1').count(), 1)

    def test_delete_user_with_sales_returns_409(self):
        operator = User(name='integridad-operator', role='ventas')
        operator.set_password('pass-operator')
        operator.save()
        sale = Sale.objects.create(
            date=date.today(), clientCode='PROTECT-2', clientName='PRUEBA',
            serviceType='internet', plan=self.plan, total=150,
            createdBy=operator)
        response = self.client.delete(
            f'/api/users/{operator.id}',
            HTTP_AUTHORIZATION=f'Bearer {self.token()}')
        self.assertEqual(response.status_code, 409)
        self.assertTrue(User.objects.filter(id=operator.id).exists())
        self.assertTrue(Sale.objects.filter(id=sale.id).exists())

    def test_edit_with_stale_version_returns_409(self):
        sale = Sale.objects.create(
            date=date.today(), clientCode='VERSION-1', clientName='PRUEBA',
            serviceType='internet', plan=self.plan, total=150,
            createdBy=self.admin)
        response = self.client.put(
            f'/api/sales/{sale.id}',
            {'version': 0, 'notes': 'CAMBIO OBSOLETO'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token()}')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['currentVersion'], 1)
