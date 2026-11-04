from decimal import Decimal

from django.test import Client, TestCase

from .models import Motivo, Plan, Sale, User


class RetirementEquipmentDeliveryTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(name='retiros_qa', password='', role='admin')
        self.user.set_password('qa-password-123')
        self.user.save()
        self.plan = Plan.objects.create(
            type='internet', code='RET-EQ', label='Plan retiro QA',
            monthly=100, installation=Decimal('0'), speed='20', active=True)
        self.reason = Motivo.objects.create(categoria='retiro', nombre='QA RETIRO')
        response = self.client.post(
            '/api/auth/login',
            {'name': 'retiros_qa', 'password': 'qa-password-123'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.auth = {'HTTP_AUTHORIZATION': f"Bearer {response.json()['token']}"}

    def _create(self, **extra):
        payload = {
            'date': '2026-11-04',
            'clientCode': 'RET-EQ-001',
            'clientName': 'Cliente retiro QA',
            'serviceType': 'internet',
            'requestType': 'retiro',
            'planId': self.plan.id,
            'motivoId': self.reason.id,
            **extra,
        }
        return self.client.post(
            '/api/sales', payload, content_type='application/json', **self.auth)

    def test_no_equipment_creates_recovery_pending_state(self):
        response = self._create(equipmentDelivered=False)
        self.assertEqual(response.status_code, 201, response.content)
        sale = Sale.objects.get(pk=response.json()['id'])
        self.assertFalse(sale.equipment_delivered)
        self.assertTrue(sale.equipment_recovery_required)
        self.assertEqual(sale.equipment_recovery_status, 'pending')
        self.assertEqual(sale.equipment_serial, '')

    def test_unknown_declared_serial_does_not_block_delivery(self):
        response = self._create(
            clientCode='RET-EQ-002',
            equipmentDelivered=True,
            equipmentSerial='SERIE-NUEVA-QA',
        )
        self.assertEqual(response.status_code, 201, response.content)
        sale = Sale.objects.get(pk=response.json()['id'])
        self.assertTrue(sale.equipment_delivered)
        self.assertFalse(sale.equipment_recovery_required)
        self.assertEqual(sale.equipment_recovery_status, 'not_required')
        self.assertEqual(sale.equipment_serial, 'SERIE-NUEVA-QA')
