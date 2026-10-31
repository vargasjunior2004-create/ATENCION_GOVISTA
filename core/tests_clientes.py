from decimal import Decimal

from django.test import Client, TestCase

from .models import Customer, Plan, User


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

        contract_id = payload['contracts'][0]['id']
        review = self.client.patch(
            f'/api/contracts/{contract_id}/meter-review',
            {'meter_review_status': 'observado',
             'meter_review_notes': 'Coincide con contrato externo'},
            content_type='application/json', **self.headers)
        self.assertEqual(review.status_code, 200)
        self.assertEqual(_json(review)['meter_review_status'], 'observado')
