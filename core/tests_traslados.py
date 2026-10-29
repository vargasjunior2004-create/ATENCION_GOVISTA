from decimal import Decimal

from django.test import TestCase, Client

from .models import Plan, Sale, TrasladoExterno, User, TarifaTraslado


class TrasladoExternoTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User(name='traslado-operador', role='ventas')
        self.user.set_password('pass1')
        self.user.save()
        self.plan = Plan.objects.create(
            code='TRAS-PLAN', label='Plan Internet', type='internet',
            monthly=200, installation=100, active=True)

    def token(self):
        response = self.client.post(
            '/api/auth/login', {'name': self.user.name, 'password': 'pass1'},
            content_type='application/json')
        return response.json()['token']

    def test_registers_transfer_with_tariff_snapshot(self):
        tariff = TarifaTraslado.objects.get(service_type='internet')
        response = self.client.post(
            '/api/sales', {
                'clientCode': '1-1', 'clientName': 'JUAN PEREZ',
                'serviceType': 'internet', 'requestType': 'traslado_externo',
                'planId': self.plan.id, 'transferTariffId': tariff.id,
                'transferCurrentAddress': 'BARRIO VICTORIA',
                'transferNewAddress': 'LAS PALMAS #20',
                'transferZone': 'LAS PALMAS',
                'transferReferences': 'CERCA DE LA PLAZA',
                'transferHasSketch': True,
            }, content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token()}')

        self.assertEqual(response.status_code, 201, response.content)
        sale = Sale.objects.get(requestType='traslado_externo')
        transfer = TrasladoExterno.objects.get(sale=sale)
        self.assertEqual(sale.total, Decimal('100.00'))
        self.assertEqual(transfer.tariff_amount, Decimal('100.00'))
        self.assertEqual(transfer.status, 'recibido')

    def test_transfer_without_sketch_waits_for_location(self):
        tariff = TarifaTraslado.objects.get(service_type='internet')
        response = self.client.post(
            '/api/sales', {
                'clientCode': '2-1', 'clientName': 'JUAN PEREZ',
                'serviceType': 'internet', 'requestType': 'traslado_externo',
                'planId': self.plan.id, 'transferTariffId': tariff.id,
                'transferNewAddress': 'NUEVO DOMICILIO',
                'transferHasSketch': False,
            }, content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token()}')

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(
            TrasladoExterno.objects.get().status, 'pendiente_ubicacion')
