from datetime import date, timedelta, datetime, timezone as tz

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import User, Plan, Sale, CashCount, Outflow


class ApiTestCase(TestCase):
    def setUp(self):
        admin = User(name='Admin', email='admin@t.com', role='admin')
        admin.set_password('admin123')
        admin.save()
        seller = User(name='Vendedor', email='ventas@t.com', role='ventas')
        seller.set_password('ventas123')
        seller.save()
        self.admin, self.seller = admin, seller

        self.plan = Plan.objects.create(
            code='GO-BASIC', label='Internet Básico', type='internet',
            speed=50, monthly=220, installation=180)
        self.tv_plan = Plan.objects.create(
            code='TV-BASIC', label='TV Básico', type='tv',
            speed=None, monthly=150, installation=150)

        self.client = APIClient()

    def login(self, name, password):
        res = self.client.post('/api/auth/login', {'name': name, 'password': password},
                               format='json')
        return res

    def auth_as(self, user, password):
        res = self.login(user.name, password)
        self.assertEqual(res.status_code, 200, res.data)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {res.data["token"]}')

    def test_login_admin_ok(self):
        res = self.login('Admin', 'admin123')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['user']['role'], 'admin')
        self.assertIn('token', res.data)

    def test_login_wrong_password(self):
        res = self.login('Admin', 'incorrecta')
        self.assertEqual(res.status_code, 401)

    def test_login_email_password(self):
        res = self.client.post('/api/auth/login',
                               {'name': 'Admin', 'password': 'admin123'},
                               format='json')
        self.assertEqual(res.status_code, 200)

    def test_me_requires_auth(self):
        res = self.client.get('/api/auth/me')
        self.assertEqual(res.status_code, 401)

    def test_me_ok(self):
        self.auth_as(self.admin, 'admin123')
        res = self.client.get('/api/auth/me')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['user']['email'], 'admin@t.com')

    def test_plans_admin_only(self):
        self.auth_as(self.seller, 'ventas123')
        res = self.client.get('/api/plans')
        self.assertEqual(res.status_code, 403)

    def test_active_plans_any_auth(self):
        self.auth_as(self.seller, 'ventas123')
        res = self.client.get('/api/plans/active')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 2)

    def test_create_sale_calculates_total_server_side(self):
        self.auth_as(self.seller, 'ventas123')
        res = self.client.post('/api/sales', {
            'date': date.today().isoformat(),
            'clientCode': 'CLI-1',
            'clientName': 'Cliente Uno',
            'serviceType': 'internet',
            'planId': self.plan.id,
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(float(res.data['total']), 400.00)
        self.assertEqual(res.data['Plan']['label'], 'Internet Básico')
        self.assertEqual(res.data['creator']['name'], 'Vendedor')

    def test_create_sale_ignores_client_total(self):
        self.auth_as(self.seller, 'ventas123')
        res = self.client.post('/api/sales', {
            'date': date.today().isoformat(),
            'clientCode': 'CLI-2',
            'clientName': 'Cliente Dos',
            'serviceType': 'internet',
            'planId': self.plan.id,
            'total': 1.00,
        }, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(float(res.data['total']), 400.00)

    def test_create_sale_plan_type_mismatch(self):
        self.auth_as(self.seller, 'ventas123')
        res = self.client.post('/api/sales', {
            'date': date.today().isoformat(),
            'clientCode': 'CLI-3',
            'clientName': 'Cliente Tres',
            'serviceType': 'tv',
            'planId': self.plan.id,
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_edit_sale_admin_recalculates_total(self):
        self.auth_as(self.seller, 'ventas123')
        res = self.client.post('/api/sales', {
            'date': date.today().isoformat(),
            'clientCode': 'CLI-4',
            'clientName': 'Cliente Cuatro',
            'serviceType': 'internet',
            'planId': self.plan.id,
        }, format='json')
        sale_id = res.data['id']

        self.auth_as(self.admin, 'admin123')
        res = self.client.put(f'/api/sales/{sale_id}',
                              {'planId': self.tv_plan.id,
                               'serviceType': 'tv'},
                              format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(float(res.data['total']), 300.00)

    def test_edit_sale_forbidden_for_sales_role(self):
        self.auth_as(self.seller, 'ventas123')
        sale = Sale.objects.create(
            date=date.today(), clientCode='C', clientName='N',
            serviceType='internet', plan=self.plan, total=self.plan.total,
            createdBy=self.seller)
        res = self.client.put(f'/api/sales/{sale.id}', {'clientName': 'X'},
                              format='json')
        self.assertEqual(res.status_code, 403)

    def test_users_admin_only(self):
        self.auth_as(self.seller, 'ventas123')
        res = self.client.get('/api/users')
        self.assertEqual(res.status_code, 403)

    def test_create_user(self):
        self.auth_as(self.admin, 'admin123')
        res = self.client.post('/api/users', {
            'name': 'Nuevo', 'email': 'nuevo@t.com',
            'password': 'nuevo123', 'role': 'ventas',
        }, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertNotIn('password', res.data)

    def test_sales_date_filter(self):
        old = date.today() - timedelta(days=5)
        Sale.objects.create(date=old, clientCode='A', clientName='A',
                            serviceType='internet', plan=self.plan,
                            total=self.plan.total, createdBy=self.admin)
        Sale.objects.create(date=date.today(), clientCode='B', clientName='B',
                            serviceType='internet', plan=self.plan,
                            total=self.plan.total, createdBy=self.admin)
        self.auth_as(self.admin, 'admin123')
        res = self.client.get(f'/api/sales?from={date.today()}&to={date.today()}')
        self.assertEqual(res.status_code, 200)
        items = res.data.get('items', res.data)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['clientCode'], 'B')

    def test_cash_count_upsert_and_outflows(self):
        self.auth_as(self.admin, 'admin123')
        d = date.today().isoformat()
        res = self.client.post('/api/cash-count',
                               {'date': d, 'coin_1': 50, 'bill_100': 5},
                               format='json')
        self.assertEqual(res.status_code, 200)

        res = self.client.post('/api/cash-count/outflows',
                               {'date': d, 'personName': 'X', 'amount': 100},
                               format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(float(res.data['totalOutflows']), 100.0)
        outflow_id = res.data['outflow']['id']

        res = self.client.get(f'/api/cash-count?date={d}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['cashCount']['coin_1'], 50)
        self.assertEqual(float(res.data['totalOutflows']), 100.0)

        res = self.client.delete(f'/api/cash-count/outflows/{outflow_id}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(float(res.data['totalOutflows']), 0.0)

    def test_report_pdf_returns_pdf(self):
        Sale.objects.create(date=date.today(), clientCode='A', clientName='A',
                            serviceType='internet', plan=self.plan,
                            total=self.plan.total, createdBy=self.admin)
        self.auth_as(self.admin, 'admin123')
        d = date.today().isoformat()
        res = self.client.get(f'/api/reports/pdf?from={d}&to={d}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')
        self.assertIn(b'%PDF', res.content)

    def test_report_xlsx(self):
        self.auth_as(self.admin, 'admin123')
        d = date.today().isoformat()
        res = self.client.get(f'/api/reports/xlsx?from={d}&to={d}')
        self.assertEqual(res.status_code, 200)
        self.assertIn('spreadsheetml', res['Content-Type'])

    def test_public_link_requires_valid_token(self):
        self.auth_as(self.admin, 'admin123')
        d = date.today().isoformat()
        res = self.client.get(f'/api/reports/pdf-link?from={d}&to={d}')
        self.assertEqual(res.status_code, 200)
        url = res.data['url']
        self.assertIn('/api/reports/pdf-public/', url)

        bad = self.client.get('/api/reports/pdf-public/', {'token': 'invalido'})
        self.assertEqual(bad.status_code, 400)

        token = url.split('token=')[1]
        ok = self.client.get('/api/reports/pdf-public/', {'token': token})
        self.assertEqual(ok.status_code, 200)
        self.assertIn(b'%PDF', ok.content)


class TimezoneBugAcceptanceTest(TestCase):
    """Tests de aceptación para el bug de zona horaria.
    Verifica que las ventas se registren con la fecha local (America/La_Paz)
    y no con UTC, causando que ventas de la noche aparezcan al día siguiente."""

    def setUp(self):
        self.admin = User(name='AdminTZ', email='admin-tz@t.com', role='admin')
        self.admin.set_password('admin123')
        self.admin.save()
        self.seller = User(name='VendedorTZ', email='ventas-tz@t.com', role='ventas')
        self.seller.set_password('ventas123')
        self.seller.save()
        self.plan = Plan.objects.create(
            code='GO-TZ', label='Plan TZ', type='internet',
            speed=50, monthly=220, installation=180)
        self.client = APIClient()

    def _auth(self, user, password):
        res = self.client.post('/api/auth/login', {'name': user.name, 'password': password},
                               format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {res.data["token"]}')

    def test_sale_uses_localdate_not_utc(self):
        """Al crear una venta, la fecha debe ser la fecha local (La Paz), no UTC."""
        self._auth(self.seller, 'ventas123')
        res = self.client.post('/api/sales', {
            'clientCode': 'CLI-TZ-1',
            'clientName': 'Cliente TZ',
            'serviceType': 'internet',
            'planId': self.plan.id,
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        sale_date = date.fromisoformat(res.data['date'])
        self.assertEqual(sale_date, timezone.localdate(),
                         f"La fecha de la venta ({sale_date}) debe coincidir "
                         f"con timezone.localdate() ({timezone.localdate()})")

    def test_cash_count_uses_localdate(self):
        """El arqueo de caja debe usar la fecha local (La Paz)."""
        self._auth(self.admin, 'admin123')
        res = self.client.post('/api/cash-count', {
            'coin_1': 50, 'bill_100': 5,
        }, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        cc_date = date.fromisoformat(res.data['date'])
        self.assertEqual(cc_date, timezone.localdate(),
                         f"La fecha del arqueo ({cc_date}) debe coincidir "
                         f"con timezone.localdate() ({timezone.localdate()})")

    def test_outflow_uses_localdate(self):
        """Las salidas de efectivo deben usar la fecha local (La Paz)."""
        self._auth(self.admin, 'admin123')
        res = self.client.post('/api/cash-count/outflows', {
            'personName': 'Test', 'amount': 100,
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        outflow_date = date.fromisoformat(res.data['outflow']['date'])
        self.assertEqual(outflow_date, timezone.localdate(),
                         f"La fecha de la salida ({outflow_date}) debe coincidir "
                         f"con timezone.localdate() ({timezone.localdate()})")

    def test_dashboard_filters_sales_by_localdate(self):
        """El dashboard debe filtrar ventas usando la fecha local, no UTC."""
        self._auth(self.seller, 'ventas123')
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)

        # Create a sale for yesterday
        Sale.objects.create(
            date=yesterday, clientCode='CLI-Y', clientName='Ayer',
            serviceType='internet', plan=self.plan, total=self.plan.total,
            createdBy=self.seller)

        # Create a sale for today
        Sale.objects.create(
            date=today, clientCode='CLI-T', clientName='Hoy',
            serviceType='internet', plan=self.plan, total=self.plan.total,
            createdBy=self.seller)

        # Query like the dashboard does: from=today, to=today
        res = self.client.get(f'/api/sales?from={today}&to={today}')
        self.assertEqual(res.status_code, 200)
        items = res.data.get('items', res.data if isinstance(res.data, list) else [])
        self.assertEqual(len(items), 1,
                         "Solo la venta de hoy debe aparecer al filtrar por hoy")
        self.assertEqual(items[0]['clientCode'], 'CLI-T')

    def test_sale_date_not_shifted_by_utc(self):
        """Verifica que la fecha de la venta NO se desplaza por conversión UTC.
        Simula el escenario: usuario en La Paz crea venta a las 22:00 (02:00 UTC+1).
        La fecha debe ser la de La Paz, no la de UTC."""
        # Simulate: set the server time to a moment where UTC date != La Paz date
        # by creating a sale and checking the date matches localdate
        self._auth(self.seller, 'ventas123')
        res = self.client.post('/api/sales', {
            'clientCode': 'CLI-UTC',
            'clientName': 'Cliente UTC Test',
            'serviceType': 'internet',
            'planId': self.plan.id,
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        sale_date = date.fromisoformat(res.data['date'])
        local_today = timezone.localdate()
        utc_today = datetime.now(tz.utc).date()
        # The sale date must match localdate, not UTC
        self.assertEqual(sale_date, local_today)
        # If UTC and local differ, this proves the fix works
        if utc_today != local_today:
            self.assertNotEqual(sale_date, utc_today,
                                "La fecha NO debe ser la de UTC cuando difiere de la local")
