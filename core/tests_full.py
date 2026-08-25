from django.test import TestCase, Client
from django.utils import timezone
from decimal import Decimal

from .models import User, Plan, Sale, CashCount, Outflow


def _json(response):
    try:
        return response.json()
    except Exception:
        return {'_raw': response.content.decode()[:500]}


def _create_user(name, password, role='ventas'):
    u = User.objects.create(name=name, password='', role=role, active=True)
    u.set_password(password)
    u.save()
    return u


class AuthTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.admin = _create_user('admin_test', 'admin123', 'admin')
        self.ventas = _create_user('ventas_test', 'ventas123', 'ventas')
        self.plan = Plan.objects.create(
            type='internet', code='TEST01', label='Plan Test 100',
            monthly=100, speed='10', active=True,
            installation=Decimal('0'))

    def test_login_ok(self):
        r = self.c.post('/api/auth/login', {'name': 'admin_test', 'password': 'admin123'},
                        content_type='application/json')
        self.assertEqual(r.status_code, 200)
        data = _json(r)
        self.assertIn('token', data)
        self.assertEqual(data['user']['role'], 'admin')

    def test_login_wrong_password(self):
        r = self.c.post('/api/auth/login', {'name': 'admin_test', 'password': 'wrong'},
                        content_type='application/json')
        self.assertEqual(r.status_code, 401)

    def test_login_nonexistent_user(self):
        r = self.c.post('/api/auth/login', {'name': 'noexiste', 'password': 'x'},
                        content_type='application/json')
        self.assertEqual(r.status_code, 401)

    def test_login_empty_name(self):
        r = self.c.post('/api/auth/login', {'name': '', 'password': 'x'},
                        content_type='application/json')
        self.assertEqual(r.status_code, 400)

    def test_login_empty_password(self):
        r = self.c.post('/api/auth/login', {'name': 'admin_test', 'password': ''},
                        content_type='application/json')
        self.assertEqual(r.status_code, 400)

    def test_login_case_insensitive(self):
        r = self.c.post('/api/auth/login', {'name': 'ADMIN_TEST', 'password': 'admin123'},
                        content_type='application/json')
        self.assertEqual(r.status_code, 200)

    def test_me_with_token(self):
        r = self.c.post('/api/auth/login', {'name': 'admin_test', 'password': 'admin123'},
                        content_type='application/json')
        token = _json(r)['token']
        r2 = self.c.get('/api/auth/me', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(_json(r2)['user']['name'], 'admin_test')

    def test_me_without_token(self):
        r = self.c.get('/api/auth/me')
        self.assertEqual(r.status_code, 401)


class SaleTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.admin = _create_user('admin1', 'pass1', 'admin')
        self.ventas_user = _create_user('ventas1', 'pass2', 'ventas')
        self.plan = Plan.objects.create(
            type='internet', code='P001', label='Plan 150',
            monthly=150, speed='20', active=True,
            installation=Decimal('0'))

    def _token(self, user, pw):
        r = self.c.post('/api/auth/login', {'name': user.name, 'password': pw},
                        content_type='application/json')
        return _json(r)['token']

    def test_create_sale_admin(self):
        token = self._token(self.admin, 'pass1')
        r = self.c.post('/api/sales', {
            'clientCode': 'K001', 'clientName': 'CLIENTE TEST',
            'serviceType': 'internet', 'requestType': 'nuevo_contrato',
            'planId': self.plan.id
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 201)
        data = _json(r)
        self.assertEqual(data['clientName'], 'CLIENTE TEST')
        self.assertEqual(float(data['total']), 150.0)

    def test_create_sale_ventas_user(self):
        token = self._token(self.ventas_user, 'pass2')
        r = self.c.post('/api/sales', {
            'clientCode': 'K002', 'clientName': 'CLIENTE 2',
            'serviceType': 'internet', 'requestType': 'nuevo_contrato',
            'planId': self.plan.id
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 201)

    def test_create_sale_without_token(self):
        r = self.c.post('/api/sales', {
            'clientCode': 'K003', 'clientName': 'X',
            'serviceType': 'internet', 'requestType': 'nuevo_contrato',
            'planId': self.plan.id
        }, content_type='application/json')
        self.assertEqual(r.status_code, 401)

    def test_create_sale_missing_fields(self):
        token = self._token(self.admin, 'pass1')
        r = self.c.post('/api/sales', {'clientCode': 'K004'},
                        content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertIn(r.status_code, [400, 500])

    def test_list_sales(self):
        token = self._token(self.admin, 'pass1')
        self.c.post('/api/sales', {
            'clientCode': 'K010', 'clientName': 'L1',
            'serviceType': 'internet', 'requestType': 'nuevo_contrato',
            'planId': self.plan.id
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        r = self.c.get('/api/sales', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 200)
        data = _json(r)
        self.assertIn('items', data)
        self.assertGreaterEqual(data['total'], 1)

    def test_list_sales_filter_by_date(self):
        token = self._token(self.admin, 'pass1')
        today = timezone.localdate().isoformat()
        r = self.c.post('/api/sales', {
            'clientCode': 'K020', 'clientName': 'F1',
            'serviceType': 'internet', 'requestType': 'cambio_plan',
            'planId': self.plan.id
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 201)
        r2 = self.c.get(f'/api/sales?from={today}&to={today}',
                       HTTP_AUTHORIZATION=f'Bearer {token}')
        data = _json(r2)
        self.assertGreaterEqual(data['total'], 1)

    def test_list_sales_filter_by_type(self):
        token = self._token(self.admin, 'pass1')
        self.c.post('/api/sales', {
            'clientCode': 'K030', 'clientName': 'RET',
            'serviceType': 'internet', 'requestType': 'retiro',
            'planId': self.plan.id
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        r = self.c.get('/api/sales?requestType=retiro',
                       HTTP_AUTHORIZATION=f'Bearer {token}')
        data = _json(r)
        self.assertGreaterEqual(data['total'], 1)
        for item in data['items']:
            self.assertEqual(item['requestType'], 'retiro')

    def test_edit_sale_admin(self):
        token = self._token(self.admin, 'pass1')
        r = self.c.post('/api/sales', {
            'clientCode': 'K040', 'clientName': 'EDIT ME',
            'serviceType': 'internet', 'requestType': 'nuevo_contrato',
            'planId': self.plan.id
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        sale_id = _json(r)['id']
        r2 = self.c.put(f'/api/sales/{sale_id}', {
            'clientName': 'EDITED',
            'serviceType': 'internet', 'requestType': 'cambio_plan',
            'planId': self.plan.id
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(_json(r2)['clientName'], 'EDITED')

    def test_edit_sale_ventas_user_forbidden(self):
        token_v = self._token(self.ventas_user, 'pass2')
        token_a = self._token(self.admin, 'pass1')
        r = self.c.post('/api/sales', {
            'clientCode': 'K050', 'clientName': 'NO EDIT',
            'serviceType': 'internet', 'requestType': 'nuevo_contrato',
            'planId': self.plan.id
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token_a}')
        sale_id = _json(r)['id']
        r2 = self.c.put(f'/api/sales/{sale_id}', {'clientName': 'HACKED'},
                        content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token_v}')
        self.assertEqual(r2.status_code, 403)

    def test_sale_date_is_localdate(self):
        token = self._token(self.admin, 'pass1')
        r = self.c.post('/api/sales', {
            'clientCode': 'K060', 'clientName': 'TZ TEST',
            'serviceType': 'internet', 'requestType': 'nuevo_contrato',
            'planId': self.plan.id
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 201)
        data = _json(r)
        self.assertEqual(data['date'], timezone.localdate().isoformat())


class DashboardTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.admin = _create_user('admin2', 'pass1', 'admin')
        self.plan = Plan.objects.create(
            type='internet', code='P002', label='Plan 200',
            monthly=200, speed='30', active=True,
            installation=Decimal('0'))

    def _token(self):
        r = self.c.post('/api/auth/login', {'name': 'admin2', 'password': 'pass1'},
                        content_type='application/json')
        return _json(r)['token']

    def test_dashboard_stats_empty(self):
        token = self._token()
        r = self.c.get('/api/dashboard/stats', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 200)
        data = _json(r)
        self.assertIn('movimientos', data)
        self.assertIn('instalaciones', data)
        self.assertIn('retiros', data)
        self.assertEqual(data['movimientos']['today']['count'], 0)

    def test_dashboard_stats_with_data(self):
        token = self._token()
        self.c.post('/api/sales', {
            'clientCode': 'D001', 'clientName': 'DASH1',
            'serviceType': 'internet', 'requestType': 'nuevo_contrato',
            'planId': self.plan.id
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.c.post('/api/sales', {
            'clientCode': 'D002', 'clientName': 'DASH2',
            'serviceType': 'internet', 'requestType': 'retiro',
            'planId': self.plan.id
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')

        r = self.c.get('/api/dashboard/stats', HTTP_AUTHORIZATION=f'Bearer {token}')
        data = _json(r)
        self.assertEqual(data['movimientos']['today']['count'], 2)
        self.assertEqual(data['instalaciones']['today']['count'], 1)
        self.assertEqual(data['retiros']['today']['count'], 1)

    def test_dashboard_no_auth(self):
        r = self.c.get('/api/dashboard/stats')
        self.assertEqual(r.status_code, 401)


class CashCountTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.admin = _create_user('admin3', 'pass1', 'admin')

    def _token(self):
        r = self.c.post('/api/auth/login', {'name': 'admin3', 'password': 'pass1'},
                        content_type='application/json')
        return _json(r)['token']

    def test_save_cash_count(self):
        token = self._token()
        r = self.c.post('/api/cash-count', {
            'date': timezone.localdate().isoformat(),
            'coin_1': 10, 'bill_10': 5, 'bill_20': 2
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 200)
        data = _json(r)
        self.assertEqual(data['coin_1'], 10)

    def test_load_cash_count(self):
        token = self._token()
        today = timezone.localdate().isoformat()
        self.c.post('/api/cash-count', {
            'date': today, 'bill_50': 3
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        r = self.c.get(f'/api/cash-count?date={today}',
                       HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 200)
        data = _json(r)
        self.assertIsNotNone(data['cashCount'])
        self.assertEqual(data['cashCount']['bill_50'], 3)

    def test_add_outflow(self):
        token = self._token()
        r = self.c.post('/api/cash-count/outflows', {
            'date': timezone.localdate().isoformat(),
            'personName': 'TEST PERSON', 'amount': 50, 'concept': 'PRUEBA'
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 201)
        data = _json(r)
        self.assertEqual(data['outflow']['personName'], 'TEST PERSON')
        self.assertEqual(data['outflow']['amount'], 50.0)

    def test_add_outflow_missing_person(self):
        token = self._token()
        r = self.c.post('/api/cash-count/outflows', {
            'date': timezone.localdate().isoformat(),
            'amount': 50
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 400)

    def test_add_outflow_missing_amount(self):
        token = self._token()
        r = self.c.post('/api/cash-count/outflows', {
            'date': timezone.localdate().isoformat(),
            'personName': 'X'
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 400)

    def test_delete_outflow(self):
        token = self._token()
        r = self.c.post('/api/cash-count/outflows', {
            'date': timezone.localdate().isoformat(),
            'personName': 'DEL ME', 'amount': 25
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        outflow_id = _json(r)['outflow']['id']
        r2 = self.c.delete(f'/api/cash-count/outflows/{outflow_id}',
                           HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r2.status_code, 200)

    def test_delete_nonexistent_outflow(self):
        token = self._token()
        r = self.c.delete('/api/cash-count/outflows/99999',
                          HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 404)

    def test_cash_count_no_auth(self):
        r = self.c.get('/api/cash-count')
        self.assertEqual(r.status_code, 401)

    def test_cash_count_total(self):
        token = self._token()
        self.c.post('/api/cash-count/outflows', {
            'date': timezone.localdate().isoformat(),
            'personName': 'A', 'amount': 100
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.c.post('/api/cash-count/outflows', {
            'date': timezone.localdate().isoformat(),
            'personName': 'B', 'amount': 200
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        r = self.c.get(f'/api/cash-count?date={timezone.localdate().isoformat()}',
                       HTTP_AUTHORIZATION=f'Bearer {token}')
        data = _json(r)
        self.assertEqual(data['totalOutflows'], 300.0)


class ReportTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.admin = _create_user('admin4', 'pass1', 'admin')
        self.plan = Plan.objects.create(
            type='internet', code='P003', label='Plan 100',
            monthly=100, speed='10', active=True,
            installation=Decimal('0'))

    def _token(self):
        r = self.c.post('/api/auth/login', {'name': 'admin4', 'password': 'pass1'},
                        content_type='application/json')
        return _json(r)['token']

    def test_pdf_empty(self):
        token = self._token()
        r = self.c.get('/api/reports/pdf?from=2026-01-01&to=2026-01-01',
                       HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')

    def test_pdf_with_type(self):
        token = self._token()
        self.c.post('/api/sales', {
            'clientCode': 'R001', 'clientName': 'RPDF',
            'serviceType': 'internet', 'requestType': 'retiro',
            'planId': self.plan.id
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        today = timezone.localdate().isoformat()
        r = self.c.get(f'/api/reports/pdf?from={today}&to={today}&requestType=retiro',
                       HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 200)
        self.assertIn('attachment', r.get('Content-Disposition', ''))

    def test_xlsx_empty(self):
        token = self._token()
        r = self.c.get('/api/reports/xlsx?from=2026-01-01&to=2026-01-01',
                       HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 200)

    def test_png_empty(self):
        token = self._token()
        r = self.c.get('/api/reports/png?from=2026-01-01&to=2026-01-01',
                       HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 200)

    def test_cash_pdf(self):
        token = self._token()
        r = self.c.get('/api/cash-count/pdf',
                       HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 200)

    def test_report_no_auth(self):
        r = self.c.get('/api/reports/pdf?from=2026-01-01&to=2026-01-01')
        self.assertEqual(r.status_code, 401)


class PlanTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.admin = _create_user('admin5', 'pass1', 'admin')
        self.ventas_user = _create_user('ventas5', 'pass2', 'ventas')

    def _token(self, user, pw):
        r = self.c.post('/api/auth/login', {'name': user.name, 'password': pw},
                        content_type='application/json')
        return _json(r)['token']

    def test_list_plans_admin(self):
        token = self._token(self.admin, 'pass1')
        r = self.c.get('/api/plans', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 200)

    def test_list_plans_ventas_forbidden(self):
        token = self._token(self.ventas_user, 'pass2')
        r = self.c.get('/api/plans', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 403)

    def test_active_plans_requires_auth(self):
        r = self.c.get('/api/plans/active')
        self.assertEqual(r.status_code, 401)


class UserManagementTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.admin = _create_user('admin6', 'pass1', 'admin')
        self.ventas_user = _create_user('ventas6', 'pass2', 'ventas')

    def _token(self, user, pw):
        r = self.c.post('/api/auth/login', {'name': user.name, 'password': pw},
                        content_type='application/json')
        return _json(r)['token']

    def test_list_users_admin(self):
        token = self._token(self.admin, 'pass1')
        r = self.c.get('/api/users', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 200)

    def test_list_users_ventas_forbidden(self):
        token = self._token(self.ventas_user, 'pass2')
        r = self.c.get('/api/users', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 403)

    def test_create_user_admin(self):
        token = self._token(self.admin, 'pass1')
        r = self.c.post('/api/users', {
            'name': 'newuser',
            'password': 'newpass', 'role': 'ventas'
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 201)

    def test_create_user_ventas_forbidden(self):
        token = self._token(self.ventas_user, 'pass2')
        r = self.c.post('/api/users', {
            'name': 'hack',
            'password': 'hack', 'role': 'admin'
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 403)

    def test_edit_user_admin(self):
        token = self._token(self.admin, 'pass1')
        r = self.c.put(f'/api/users/{self.ventas_user.id}', {
            'name': 'ventas_updated', 'role': 'ventas'
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(_json(r)['name'], 'ventas_updated')

    def test_edit_nonexistent_user(self):
        token = self._token(self.admin, 'pass1')
        r = self.c.put('/api/users/99999', {'name': 'X'},
                       content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 404)


class CustomerTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.admin = _create_user('admin7', 'pass1', 'admin')

    def _token(self):
        r = self.c.post('/api/auth/login', {'name': 'admin7', 'password': 'pass1'},
                        content_type='application/json')
        return _json(r)['token']

    def test_search_customers(self):
        token = self._token()
        r = self.c.get('/api/customers?q=', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 200)


class HealthTests(TestCase):
    def setUp(self):
        self.c = Client()

    def test_health(self):
        r = self.c.get('/api/health')
        self.assertEqual(r.status_code, 200)
        data = _json(r)
        self.assertEqual(data['status'], 'ok')
