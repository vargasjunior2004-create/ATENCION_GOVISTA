from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

from .models import (
    Plan, Role, Sale, TemporaryAssignment, TemporaryFunction, User, UserRole,
    Contract,
)


class ExternalSellerTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.registrar = self.create_user('registrar')
        self.seller = self.create_user('seller')
        caja_role = Role.objects.get(code='caja')
        UserRole.objects.create(
            user=self.registrar, role=caja_role, assigned_by=self.registrar)
        self.plan = Plan.objects.create(
            type='internet', code='EXT01', label='Plan externo',
            monthly=100, installation=0, active=True)
        self.function = TemporaryFunction.objects.get(code='external_seller')
        self.login(self.registrar)

    def create_user(self, name):
        user = User.objects.create(name=name, password='', role='ventas')
        user.set_password('password')
        user.save()
        return user

    def login(self, user):
        response = self.client.post(
            '/api/auth/login',
            {'name': user.name, 'password': 'password'},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.auth = {
            'HTTP_AUTHORIZATION': f"Bearer {response.json()['token']}",
        }

    def assign(self, user, *, starts_at=None, ends_at=None, status='active'):
        now = timezone.now()
        return TemporaryAssignment.objects.create(
            user=user,
            function=self.function,
            assigned_by=self.registrar,
            starts_at=starts_at or now - timedelta(hours=1),
            ends_at=ends_at or now + timedelta(hours=1),
            status=status,
        )

    def post_external_sale(self, **extra):
        payload = {
            'clientCode': 'EXT-001',
            'clientName': 'CLIENTE EXTERNO',
            'serviceType': 'internet',
            'requestType': 'nuevo_contrato',
            'planId': self.plan.id,
        }
        payload.update(extra)
        return self.client.post(
            '/api/sales', payload, content_type='application/json', **self.auth)

    def test_external_sale_requires_an_active_assigned_seller(self):
        response = self.post_external_sale(sellerUserId=self.seller.id)
        self.assertEqual(response.status_code, 400)
        self.assertIn('asignación externa activa', response.json()['error'])

        self.assign(
            self.seller, starts_at=timezone.now() + timedelta(hours=1))
        response = self.post_external_sale(sellerUserId=self.seller.id)
        self.assertEqual(response.status_code, 400)

        expired_seller = self.create_user('expired-seller')
        self.assign(
            expired_seller, ends_at=timezone.now() - timedelta(hours=1))
        response = self.post_external_sale(sellerUserId=expired_seller.id)
        self.assertEqual(response.status_code, 400)

        finished_seller = self.create_user('finished-seller')
        self.assign(finished_seller, status='finished')
        response = self.post_external_sale(sellerUserId=finished_seller.id)
        self.assertEqual(response.status_code, 400)

        inactive_seller = self.create_user('inactive-seller')
        self.assign(inactive_seller)
        inactive_seller.active = False
        inactive_seller.save(update_fields=['active'])
        response = self.post_external_sale(sellerUserId=inactive_seller.id)
        self.assertEqual(response.status_code, 400)

    def test_external_sale_keeps_registrar_and_seller_separate(self):
        self.assign(self.seller)
        response = self.post_external_sale(sellerUserId=self.seller.id)

        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        sale = Sale.objects.get(pk=data['id'])
        contract = Contract.objects.get(sale=sale)

        self.assertEqual(sale.createdBy, self.registrar)
        self.assertEqual(sale.seller_user, self.seller)
        self.assertEqual(sale.seller_name, self.seller.name)
        self.assertEqual(contract.created_by, self.registrar)
        self.assertEqual(contract.seller_user, self.seller)
        self.assertEqual(contract.seller_name, self.seller.name)
        self.assertEqual(contract.origin, 'externo')
        self.assertEqual(data['creator']['id'], self.registrar.id)
        self.assertEqual(data['sellerUserId'], self.seller.id)
        self.assertEqual(data['sellerName'], self.seller.name)

        self.seller.name = 'VENDEDOR RENOMBRADO'
        self.seller.save(update_fields=['name'])
        sale.refresh_from_db()
        contract.refresh_from_db()
        self.assertEqual(sale.seller_name, 'seller')
        self.assertEqual(contract.seller_name, 'seller')
        contract_response = self.client.get(
            f'/api/contracts/{contract.id}', **self.auth)
        self.assertEqual(contract_response.status_code, 200)
        contract_data = contract_response.json()
        self.assertEqual(contract_data['sellerUserId'], self.seller.id)
        self.assertEqual(contract_data['sellerName'], 'seller')
        self.assertEqual(contract_data['createdBy']['id'], self.registrar.id)

    def test_contract_origin_uses_registrar_role_without_external_seller(self):
        office_response = self.post_external_sale()
        self.assertEqual(office_response.status_code, 201, office_response.content)
        office_contract = Contract.objects.get(
            sale_id=office_response.json()['id'])
        self.assertEqual(office_contract.origin, 'oficina')

        call_center = self.create_user('call-center-registrar')
        call_center_role = Role.objects.get(code='call-center')
        UserRole.objects.create(
            user=call_center, role=call_center_role, assigned_by=self.registrar)
        self.login(call_center)

        response = self.post_external_sale()

        self.assertEqual(response.status_code, 201, response.content)
        contract = Contract.objects.get(sale_id=response.json()['id'])
        self.assertEqual(contract.origin, 'virtual')
        self.assertIsNone(contract.seller_user)

    def test_client_cannot_override_contract_origin(self):
        response = self.post_external_sale(contractOrigin='externo')
        self.assertEqual(response.status_code, 400)
        self.assertIn('automáticamente', str(response.json()['error']))

    def test_active_seller_list_only_returns_current_eligible_users(self):
        self.assign(self.seller)
        future_seller = self.create_user('future-seller')
        self.assign(
            future_seller,
            starts_at=timezone.now() + timedelta(hours=1))
        inactive_seller = self.create_user('inactive-seller')
        self.assign(inactive_seller)
        inactive_seller.active = False
        inactive_seller.save(update_fields=['active'])

        response = self.client.get('/api/external-sellers/active', **self.auth)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [
            {'id': self.seller.id, 'name': self.seller.name},
        ])

    def test_sale_snapshot_survives_seller_deactivation(self):
        self.assign(self.seller)
        response = self.post_external_sale(sellerUserId=self.seller.id)
        self.assertEqual(response.status_code, 201, response.content)
        sale = Sale.objects.get(pk=response.json()['id'])

        self.seller.active = False
        self.seller.save(update_fields=['active'])
        sale.refresh_from_db()
        self.assertEqual(sale.seller_user, self.seller)
        self.assertEqual(sale.seller_name, 'seller')


class ExternalSellerListAuthenticationTests(TestCase):
    def test_external_seller_list_requires_authentication(self):
        response = Client().get('/api/external-sellers/active')
        self.assertEqual(response.status_code, 401)
