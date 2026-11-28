from decimal import Decimal

from django.test import Client, TestCase

from .models import Customer, Plan, User, CoverageZone, CanalCaptacion


def _json(response):
    return response.json()


class CustomerProfileTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(name='cliente_admin', password='', role='admin')
        self.user.set_password('password')
        self.user.save()
        self.plan = Plan.objects.create(
            code='CLI-001', label='Plan Cliente', type='internet',
            monthly=100, installation=0, active=True)
        self.coverage_zone_id = CoverageZone.objects.get(
            normalized_name='villa busch').id
        self.canal_captacion = CanalCaptacion.objects.filter(
            activo=True).first()
        token_response = self.client.post(
            '/api/auth/login',
            {'name': 'cliente_admin', 'password': 'password'},
            content_type='application/json')
        self.headers = {'HTTP_AUTHORIZATION': f"Bearer {token_response.json()['token']}"}

    def create_sale(self, code, ci, meter):
        return self.client.post(
            '/api/sales',
            {
                'clientCode': code,
                'clientName': f'CLIENTE {code}',
                'clientCi': ci,
                'serviceType': 'internet',
                'requestType': 'nuevo_contrato',
                'planId': self.plan.id,
                'coverageZoneId': self.coverage_zone_id,
                'canalCaptacionId': self.canal_captacion.id,
                'meterNumber': meter,
            },
            content_type='application/json', **self.headers)

    def test_detail_search_and_manual_meter_review(self):
        first = self.create_sale('CLI-01', 'CI-001', 'MED-77')
        second = self.create_sale('CLI-02', 'CI-002', 'MED-77')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)

        customer = Customer.objects.get(ci='CI-001')
        detail = self.client.get(
            f'/api/customers/{customer.id}', **self.headers)
        self.assertEqual(detail.status_code, 200)
        payload = _json(detail)
        self.assertEqual(payload['summary']['contracts'], 1)
        self.assertEqual(payload['summary']['movements'], 1)
        self.assertEqual(len(payload['contracts'][0]['meterMatches']), 1)

        search = self.client.get('/api/customers?q=MED-77', **self.headers)
        self.assertEqual(search.status_code, 200)
        self.assertEqual(len(_json(search)), 2)
        self.assertEqual(len(_json(search)[0]['services']), 1)

        contract_id = payload['contracts'][0]['id']
        review = self.client.patch(
            f'/api/contracts/{contract_id}/meter-review',
            {'meter_review_status': 'observado',
             'meter_review_notes': 'Coincide con contrato externo'},
            content_type='application/json', **self.headers)
        self.assertEqual(review.status_code, 200)
        self.assertEqual(_json(review)['meter_review_status'], 'observado')

    def test_customer_search_requires_criterion_and_prioritizes_kardex(self):
        Customer.objects.create(code='SEARCH-001', name='CLIENTE POR NOMBRE')
        Customer.objects.create(code='SEARCH-002', name='CLIENTE POR KARDEX')

        empty = self.client.get('/api/customers', **self.headers)
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(_json(empty), [])

        by_name = self.client.get(
            '/api/customers?name=CLIENTE%20POR%20NOMBRE', **self.headers)
        self.assertEqual(len(_json(by_name)), 1)
        self.assertEqual(_json(by_name)[0]['code'], 'SEARCH-001')

        by_both = self.client.get(
            '/api/customers?code=SEARCH-002&name=CLIENTE%20POR%20NOMBRE',
            **self.headers)
        self.assertEqual(len(_json(by_both)), 1)
        self.assertEqual(_json(by_both)[0]['code'], 'SEARCH-002')

    def test_selected_customer_is_reused_without_creating_duplicate(self):
        customer = Customer.objects.create(
            code='SOFTV-001',
            name='CLIENTE CENTRALIZADO',
            ci='CI-CENTRAL',
            phone='70000001',
        )
        payload = {
            'customerId': customer.id,
            'clientCode': customer.code,
            'clientName': customer.name,
            'clientCi': customer.ci,
            'clientPhone': customer.phone,
            'serviceType': 'internet',
            'requestType': 'nuevo_contrato',
            'planId': self.plan.id,
            'coverageZoneId': self.coverage_zone_id,
            'canalCaptacionId': self.canal_captacion.id,
            'meterNumber': 'CENTRAL-1',
        }
        first = self.client.post(
            '/api/sales', payload, content_type='application/json',
            **self.headers)
        second = self.client.post(
            '/api/sales', {**payload, 'meterNumber': 'CENTRAL-2'},
            content_type='application/json', **self.headers)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(Customer.objects.filter(code='SOFTV-001').count(), 1)
        self.assertEqual(
            Customer.objects.get(pk=customer.id).sales.count(), 2)

    def test_selected_customer_must_match_kardex(self):
        customer = Customer.objects.create(
            code='SOFTV-002', name='CLIENTE DOS')
        response = self.client.post(
            '/api/sales',
            {
                'customerId': customer.id,
                'clientCode': 'OTRO-KARDEX',
                'clientName': customer.name,
                'serviceType': 'internet',
                'requestType': 'nuevo_contrato',
                'planId': self.plan.id,
                'coverageZoneId': self.coverage_zone_id,
                'canalCaptacionId': self.canal_captacion.id,
            },
            content_type='application/json',
            **self.headers)
        self.assertEqual(response.status_code, 400)
