from decimal import Decimal
from datetime import date

from django.test import TestCase, Client

from .models import Plan, Sale, User
from .reports import _sales_queryset


class RecontratacionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = self._user('admin-rehire', 'admin')
        self.operator = self._user('operator-rehire', 'ventas')
        self.plan = Plan.objects.create(
            code='REHIRE-100', label='Plan Rehire', type='internet',
            monthly=200, installation=100, active=True)

    def _user(self, name, role):
        user = User(name=name, role=role)
        user.set_password('pass1')
        user.save()
        return user

    def _token(self, user):
        response = self.client.post(
            '/api/auth/login', {'name': user.name, 'password': 'pass1'},
            content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()['token']

    def _create(self, user, **extra):
        payload = {
            'clientCode': f'REH-{Sale.objects.count() + 1}',
            'clientName': 'CLIENTE RECONTRATACION',
            'serviceType': 'internet',
            'requestType': 'recontratacion',
            'planId': self.plan.id,
            'equipmentRetained': True,
            'requiresTechnicalVisit': False,
            'debtApplies': False,
            'debtAmount': 0,
        }
        payload.update(extra)
        return self.client.post(
            '/api/sales', payload, content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self._token(user)}')

    def test_new_contract_keeps_existing_calculation(self):
        response = self.client.post(
            '/api/sales', {
                'clientCode': 'NEW-1', 'clientName': 'CLIENTE NUEVO',
                'serviceType': 'internet', 'requestType': 'nuevo_contrato',
                'planId': self.plan.id,
            }, content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self._token(self.operator)}')

        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(Decimal(data['total']), Decimal('300.00'))
        self.assertEqual(Decimal(data['debtAmount']), Decimal('0.00'))
        self.assertEqual(Decimal(data['totalToCollect']), Decimal('300.00'))

    def test_rehire_with_equipment_and_without_debt(self):
        response = self._create(self.operator)

        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertTrue(data['equipmentRetained'])
        self.assertFalse(data['requiresTechnicalVisit'])
        self.assertFalse(data['debtApplies'])
        self.assertEqual(Decimal(data['total']), Decimal('300.00'))
        self.assertEqual(Decimal(data['totalToCollect']), Decimal('300.00'))

    def test_rehire_with_debt_is_separate_from_service_total(self):
        response = self._create(
            self.admin, debtApplies=True, debtAmount='80.50')

        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(Decimal(data['total']), Decimal('300.00'))
        self.assertEqual(Decimal(data['debtAmount']), Decimal('80.50'))
        self.assertEqual(Decimal(data['totalToCollect']), Decimal('380.50'))

    def test_both_roles_can_register_manual_debt(self):
        for user in (self.admin, self.operator):
            response = self._create(
                user, debtApplies=True, debtAmount='25.00')
            self.assertEqual(response.status_code, 201, response.content)

    def test_debt_disabled_with_residual_amount_is_rejected(self):
        response = self._create(
            self.operator, debtApplies=False, debtAmount='10.00')

        self.assertEqual(response.status_code, 400)

    def test_negative_debt_is_rejected_by_backend(self):
        response = self._create(
            self.operator, debtApplies=True, debtAmount='-1.00')

        self.assertEqual(response.status_code, 400)

    def test_rehire_requires_equipment_and_visit_decisions(self):
        response = self._create(
            self.operator, equipmentRetained=None,
            requiresTechnicalVisit=None)

        self.assertEqual(response.status_code, 400)

    def test_daily_report_excludes_rehire_that_keeps_equipment(self):
        self._create(self.operator, equipmentRetained=True,
                     requiresTechnicalVisit=False)
        self._create(self.operator, equipmentRetained=False,
                     requiresTechnicalVisit=True)

        all_sales = _sales_queryset(
            date.today().isoformat(), date.today().isoformat())
        technical_sales = _sales_queryset(
            date.today().isoformat(), date.today().isoformat(),
            technical_only=True)

        self.assertEqual(all_sales.count(), 2)
        self.assertEqual(technical_sales.count(), 1)

    def test_only_admin_can_update_record_amounts(self):
        created = self._create(self.operator)
        self.assertEqual(created.status_code, 201, created.content)
        sale_id = created.json()['id']

        forbidden = self.client.put(
            f'/api/sales/{sale_id}',
            {'appliedInstallation': 10, 'appliedMonthly': 20},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self._token(self.operator)}')
        self.assertEqual(forbidden.status_code, 403)

        updated = self.client.put(
            f'/api/sales/{sale_id}',
            {'appliedInstallation': '50.00', 'appliedMonthly': '300.00'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self._token(self.admin)}')
        self.assertEqual(updated.status_code, 200, updated.content)
        data = updated.json()
        self.assertEqual(Decimal(data['applied_installation']), Decimal('50.00'))
        self.assertEqual(Decimal(data['applied_monthly']), Decimal('300.00'))
        self.assertEqual(Decimal(data['total']), Decimal('350.00'))
