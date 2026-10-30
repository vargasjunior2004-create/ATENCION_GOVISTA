from decimal import Decimal
from datetime import date

from django.test import TestCase, Client

from .models import Customer, Plan, Sale, TrasladoExterno, User, TarifaTraslado


class TrasladoExternoTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User(name='traslado-operador', role='ventas')
        self.user.set_password('pass1')
        self.user.save()
        self.admin = User(name='traslado-admin', role='admin')
        self.admin.set_password('admin-pass1')
        self.admin.save()
        self.plan = Plan.objects.create(
            code='TRAS-PLAN', label='Plan Internet', type='internet',
            monthly=200, installation=100, active=True)

    def token(self, user=None, password=None):
        user = user or self.user
        password = password or ('admin-pass1' if user == self.admin else 'pass1')
        response = self.client.post(
            '/api/auth/login', {'name': user.name, 'password': password},
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

    def test_transfer_can_use_active_legacy_plan(self):
        legacy = Plan.objects.create(
            code='TRAS-LEGACY', label='Plan anterior', type='internet',
            monthly=200, installation=100, active=True, legacy=True)
        tariff = TarifaTraslado.objects.get(service_type='internet')
        response = self.client.post(
            '/api/sales', {
                'clientCode': '1-LEGACY', 'clientName': 'JUAN PEREZ',
                'serviceType': 'internet', 'requestType': 'traslado_externo',
                'planId': legacy.id, 'transferTariffId': tariff.id,
                'transferNewAddress': 'NUEVO DOMICILIO',
                'transferHasSketch': True,
            }, content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token()}')
        self.assertEqual(response.status_code, 201, response.content)

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

    def test_edit_transfer_keeps_tariff_total(self):
        tariff = TarifaTraslado.objects.get(service_type='internet')
        sale = Sale.objects.create(
            date=date.today(),
            clientCode='EDIT-1', clientName='EDITAR TRASLADO',
            serviceType='internet', requestType='traslado_externo',
            plan=self.plan, planName=self.plan.label, total=tariff.amount,
            createdBy=self.admin,
            customer=Customer.objects.create(code='EDIT-1', name='EDITAR TRASLADO'))
        TrasladoExterno.objects.create(
            sale=sale, customer=sale.customer, tariff=tariff,
            tariff_amount=tariff.amount,
            new_address='DOMICILIO ORIGINAL', has_physical_sketch=True,
            created_by=self.admin)

        response = self.client.put(
            f'/api/sales/{sale.id}',
            {'notes': 'REFERENCIA ACTUALIZADA'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token(self.admin)}')

        self.assertEqual(response.status_code, 200, response.content)
        sale.refresh_from_db()
        self.assertEqual(sale.total, Decimal('100.00'))
