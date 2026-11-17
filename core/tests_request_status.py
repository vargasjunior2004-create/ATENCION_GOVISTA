from django.test import Client, TestCase

from .models import CanalCaptacion, CoverageZone, Motivo, Plan, Sale, User


class RequestStatusTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(name='status-admin', password='', role='admin')
        self.user.set_password('status-password-123')
        self.user.save()
        self.plan = Plan.objects.create(
            type='internet', code='STATUS-NEW', label='Plan estado nuevo',
            monthly=100, installation=0, speed='10', active=True)
        self.previous_plan = Plan.objects.create(
            type='internet', code='STATUS-OLD', label='Plan estado anterior',
            monthly=80, installation=0, speed='5', active=True)
        self.zone = CoverageZone.objects.get(normalized_name='villa busch')
        self.channel = CanalCaptacion.objects.filter(activo=True).first()
        if self.channel is None:
            self.channel = CanalCaptacion.objects.create(nombre='Prueba')
        self.change_reason = Motivo.objects.create(
            categoria='cambio', nombre='Cambio de prueba')
        self.withdrawal_reason = Motivo.objects.create(
            categoria='retiro', nombre='Retiro de prueba')

    def auth(self):
        response = self.client.post(
            '/api/auth/login',
            {'name': self.user.name, 'password': 'status-password-123'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        return {'HTTP_AUTHORIZATION': f"Bearer {response.json()['token']}"}

    def create(self, payload):
        response = self.client.post(
            '/api/sales', payload, content_type='application/json', **self.auth())
        self.assertEqual(response.status_code, 201, response.content)
        return Sale.objects.get(pk=response.json()['id'])

    def test_new_contract_is_persisted_as_contratado(self):
        sale = self.create({
            'clientCode': 'STATUS-N', 'clientName': 'Nuevo estado',
            'serviceType': 'internet', 'requestType': 'nuevo_contrato',
            'planId': self.plan.id, 'coverageZoneId': self.zone.id,
            'canalCaptacionId': self.channel.id,
        })

        self.assertEqual(sale.status, 'contratado')

        customer = sale.customer
        response = self.client.get(
            f'/api/customers/{customer.id}', **self.auth())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['contracts'][0]['status'], 'Contratado')
        self.assertEqual(response.json()['timeline'][0]['status'], 'Contratado')

        productivity = self.client.get(
            '/api/dashboard/productivity', **self.auth())
        self.assertEqual(productivity.status_code, 200)
        self.assertEqual(productivity.json()['items'][0]['status'], 'Contratado')

    def test_plan_change_is_persisted_as_cambiado(self):
        sale = self.create({
            'clientCode': 'STATUS-C', 'clientName': 'Cambio estado',
            'serviceType': 'internet', 'requestType': 'cambio_plan',
            'planId': self.plan.id, 'planFromId': self.previous_plan.id,
            'motivoId': self.change_reason.id,
        })

        self.assertEqual(sale.status, 'cambiado')

    def test_rehire_is_persisted_as_recontratado(self):
        sale = self.create({
            'clientCode': 'STATUS-RC', 'clientName': 'Recontratado estado',
            'serviceType': 'internet', 'requestType': 'recontratacion',
            'planId': self.plan.id, 'coverageZoneId': self.zone.id,
            'equipmentRetained': True, 'requiresTechnicalVisit': False,
            'debtApplies': False, 'debtAmount': 0,
        })

        self.assertEqual(sale.status, 'recontratado')

        response = self.client.get(
            f'/api/customers/{sale.customer.id}', **self.auth())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['contracts'][0]['status'], 'Recontratado')

    def test_withdrawal_is_persisted_as_retirado(self):
        sale = self.create({
            'clientCode': 'STATUS-R', 'clientName': 'Retiro estado',
            'serviceType': 'internet', 'requestType': 'retiro',
            'planId': self.plan.id, 'motivoId': self.withdrawal_reason.id,
        })

        self.assertEqual(sale.status, 'retirado')

    def test_client_cannot_choose_an_arbitrary_status(self):
        response = self.client.post(
            '/api/sales',
            {
                'clientCode': 'STATUS-X', 'clientName': 'Estado arbitrario',
                'serviceType': 'internet', 'requestType': 'nuevo_contrato',
                'planId': self.plan.id, 'coverageZoneId': self.zone.id,
                'canalCaptacionId': self.channel.id, 'status': 'instalado',
            },
            content_type='application/json', **self.auth())

        self.assertEqual(response.status_code, 400)
        self.assertIn('estado', str(response.json()).lower())

    def test_serializer_exposes_derived_status_for_safe_historical_rows(self):
        sale = self.create({
            'clientCode': 'STATUS-H', 'clientName': 'Histórico estado',
            'serviceType': 'internet', 'requestType': 'retiro',
            'planId': self.plan.id, 'motivoId': self.withdrawal_reason.id,
        })
        Sale.objects.filter(pk=sale.pk).update(status=None)

        response = self.client.get(
            '/api/sales', **self.auth())

        self.assertEqual(response.status_code, 200)
        item = next(row for row in response.json()['items'] if row['id'] == sale.id)
        self.assertEqual(item['status'], 'Retirado')
