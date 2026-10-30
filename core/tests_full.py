from django.test import TestCase, Client
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from .models import User, Plan, Sale, Motivo


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
        # Un cambio de plan exige indicar el plan anterior (validado en
        # SaleSerializer), asi que hace falta un segundo plan.
        self.previous_plan = Plan.objects.create(
            type='internet', code='P000', label='Plan 100',
            monthly=100, speed='10', active=True,
            installation=Decimal('0'))
        # Los movimientos de cambio/retiro exigen un motivo del catalogo.
        self.motivo_cambio = Motivo.objects.create(
            categoria='cambio', nombre='AUMENTO DE DISPOSITIVOS')
        self.motivo_retiro = Motivo.objects.create(
            categoria='retiro', nombre='MUDANZA')

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
            'planId': self.plan.id, 'planFromId': self.previous_plan.id,
            'motivoId': self.motivo_cambio.id
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
            'planId': self.plan.id, 'motivoId': self.motivo_retiro.id
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
            'planId': self.plan.id, 'planFromId': self.previous_plan.id,
            'motivoId': self.motivo_cambio.id
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
        self.motivo_retiro = Motivo.objects.create(
            categoria='retiro', nombre='MUDANZA')

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
            'clientCode': 'D003', 'clientName': 'DASH3',
            'serviceType': 'internet', 'requestType': 'recontratacion',
            'planId': self.plan.id, 'equipmentRetained': True,
            'requiresTechnicalVisit': False, 'debtApplies': False,
            'debtAmount': 0
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.c.post('/api/sales', {
            'clientCode': 'D002', 'clientName': 'DASH2',
            'serviceType': 'internet', 'requestType': 'retiro',
            'planId': self.plan.id, 'motivoId': self.motivo_retiro.id
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')

        r = self.c.get('/api/dashboard/stats', HTTP_AUTHORIZATION=f'Bearer {token}')
        data = _json(r)
        self.assertEqual(data['movimientos']['today']['count'], 3)
        self.assertEqual(data['nuevo_contrato']['today']['count'], 1)
        self.assertEqual(data['recontrataciones']['today']['count'], 1)
        self.assertEqual(data['retiros']['today']['count'], 1)

    def test_dashboard_no_agrupa_cambio_plan_ni_adicion(self):
        """La agrupacion de instalaciones es solo nuevo contrato + recontratacion."""
        token = self._token()
        for code, tipo in (('E001', 'cambio_plan'), ('E002', 'adicion'), ('E003', 'otro')):
            Sale.objects.create(
                date=timezone.localdate(), clientCode=code,
                clientName=f'DASH_{tipo}', serviceType='internet',
                requestType=tipo, plan=self.plan, total=Decimal('100'),
                createdBy=self.admin)

        r = self.c.get('/api/dashboard/stats', HTTP_AUTHORIZATION=f'Bearer {token}')
        data = _json(r)
        self.assertEqual(data['movimientos']['today']['count'], 3)
        self.assertEqual(data['instalaciones']['today']['count'], 0)

    def test_dashboard_no_auth(self):
        r = self.c.get('/api/dashboard/stats')
        self.assertEqual(r.status_code, 401)

    def _sale(self, code, request_type, movement_date, service='internet', total=100):
        return Sale.objects.create(
            date=movement_date,
            clientCode=code,
            clientName=f'DASH_{code}',
            serviceType=service,
            requestType=request_type,
            plan=self.plan,
            planName=self.plan.label,
            total=Decimal(str(total)),
            createdBy=self.admin,
        )

    def test_dashboard_analytics_custom_range_and_series(self):
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        self._sale('A001', 'nuevo_contrato', yesterday, total=120)
        self._sale('A002', 'retiro', today, total=80)
        self._sale('A003', 'cambio_plan', today, service='tv_digital')
        self._sale('A004', 'adicion', today, service='combo_digital')

        token = self._token()
        r = self.c.get(
            f'/api/dashboard/stats?from={yesterday.isoformat()}&to={today.isoformat()}',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 200)
        data = _json(r)
        analytics = data['analytics']

        self.assertEqual(analytics['period']['from'], yesterday.isoformat())
        self.assertEqual(analytics['period']['to'], today.isoformat())
        self.assertEqual(analytics['nuevo_contrato']['count'], 1)
        self.assertEqual(analytics['recontrataciones']['count'], 0)
        self.assertEqual(analytics['retiros']['count'], 1)
        self.assertEqual(analytics['cambios_plan']['count'], 1)
        self.assertEqual(analytics['balance_neto'], 0)
        self.assertEqual(len(analytics['series']), 2)
        self.assertEqual(analytics['series'][0]['nuevo_contrato'], 1)
        self.assertEqual(analytics['series'][0]['recontrataciones'], 0)
        self.assertEqual(analytics['series'][1]['retiros'], 1)
        self.assertEqual(
            {item['serviceType'] for item in analytics['servicios']},
            {'internet', 'tv_digital', 'combo_digital'},
        )
        self.assertEqual(
            sum(item['count'] for item in analytics['categorias']),
            4,
        )

    def test_dashboard_analytics_movement_filter_excludes_other_categories(self):
        today = timezone.localdate()
        self._sale('B001', 'nuevo_contrato', today)
        self._sale('B002', 'retiro', today)
        self._sale('B003', 'cambio_plan', today)
        self._sale('B004', 'adicion', today)

        token = self._token()
        r = self.c.get(
            f'/api/dashboard/stats?from={today.isoformat()}&to={today.isoformat()}'
            '&movement_type=cambios_plan',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        data = _json(r)
        analytics = data['analytics']

        self.assertEqual(analytics['period']['movement_type'], 'cambios_plan')
        self.assertEqual(analytics['series'][0]['movimientos'], 1)
        self.assertEqual(analytics['cambios_plan']['count'], 1)
        self.assertEqual(analytics['nuevo_contrato']['count'], 0)
        self.assertEqual(analytics['recontrataciones']['count'], 0)
        self.assertEqual(analytics['retiros']['count'], 0)

    def test_dashboard_analytics_rejects_invalid_ranges_and_filters(self):
        token = self._token()
        today = timezone.localdate()
        tomorrow = today + timedelta(days=1)
        headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}

        reversed_range = self.c.get(
            f'/api/dashboard/stats?from={tomorrow.isoformat()}&to={today.isoformat()}',
            **headers)
        self.assertEqual(reversed_range.status_code, 400)

        incomplete_range = self.c.get(
            f'/api/dashboard/stats?from={today.isoformat()}', **headers)
        self.assertEqual(incomplete_range.status_code, 400)

        unknown_filter = self.c.get(
            '/api/dashboard/stats?movement_type=ventas', **headers)
        self.assertEqual(unknown_filter.status_code, 400)

    def test_dashboard_operator_is_limited_to_today(self):
        _create_user('operator-dashboard', 'pass1', 'ventas')
        yesterday = timezone.localdate() - timedelta(days=1)
        self._sale('OP001', 'nuevo_contrato', yesterday)
        self._sale('OP002', 'retiro', timezone.localdate())

        login = self.c.post(
            '/api/auth/login',
            {'name': 'operator-dashboard', 'password': 'pass1'},
            content_type='application/json')
        token = _json(login)['token']
        response = self.c.get(
            f'/api/dashboard/stats?from={yesterday.isoformat()}&to={timezone.localdate().isoformat()}',
            HTTP_AUTHORIZATION=f'Bearer {token}')

        self.assertEqual(response.status_code, 200)
        analytics = _json(response)['analytics']
        self.assertEqual(analytics['period']['from'], timezone.localdate().isoformat())
        self.assertEqual(analytics['period']['to'], timezone.localdate().isoformat())
        self.assertEqual(analytics['series'][0]['movimientos'], 1)


class ReportTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.admin = _create_user('admin4', 'pass1', 'admin')
        self.plan = Plan.objects.create(
            type='internet', code='P003', label='Plan 100',
            monthly=100, speed='10', active=True,
            installation=Decimal('0'))
        self.motivo_retiro = Motivo.objects.create(
            categoria='retiro', nombre='MUDANZA')

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
            'planId': self.plan.id, 'motivoId': self.motivo_retiro.id
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
        self.assertEqual(r['Content-Type'], 'image/png')

    def test_report_no_auth(self):
        r = self.c.get('/api/reports/pdf?from=2026-01-01&to=2026-01-01')
        self.assertEqual(r.status_code, 401)

    def test_dashboard_report_no_auth(self):
        r = self.c.get('/api/reports/dashboard/pdf')
        self.assertEqual(r.status_code, 401)

    def test_operador_reporta_dashboard_pero_no_historial(self):
        _create_user('op4', 'pass2', 'ventas')
        r = self.c.post('/api/auth/login',
                        {'name': 'op4', 'password': 'pass2'},
                        content_type='application/json')
        token = _json(r)['token']

        dashboard_urls = (
            '/api/reports/dashboard/pdf',
            '/api/reports/dashboard/xlsx',
            '/api/reports/dashboard/png',
        )
        for url in dashboard_urls:
            with self.subTest(url=url):
                resp = self.c.get(
                    url, HTTP_AUTHORIZATION=f'Bearer {token}')
                self.assertEqual(resp.status_code, 200)
                if url.endswith('/png'):
                    self.assertEqual(resp['Content-Type'], 'image/png')

        history_urls = (
            '/api/reports/pdf?from=2026-01-01&to=2026-01-01',
            '/api/reports/xlsx?from=2026-01-01&to=2026-01-01',
            '/api/reports/png?from=2026-01-01&to=2026-01-01',
            '/api/reports/pdf-link?from=2026-01-01&to=2026-01-01',
            '/api/reports/xlsx-link?from=2026-01-01&to=2026-01-01',
        )
        for url in history_urls:
            with self.subTest(url=url):
                resp = self.c.get(
                    url, HTTP_AUTHORIZATION=f'Bearer {token}')
                self.assertEqual(resp.status_code, 403)

    def test_labels_respetan_tipo_de_movimiento(self):
        """Cada tipo de movimiento conserva su propia etiqueta en el reporte.

        Un 'nuevo contrato' no debe aparecer como INSTALACIONES: la agrupacion
        de instalaciones es exclusiva del dashboard. La etiqueta sale del
        catalogo TipoSolicitud, no de una constante en el codigo.
        """
        from .models import Sale as SaleModel, TipoSolicitud
        from .reports import get_request_label
        from .domain import request_type_catalog

        catalog = request_type_catalog()
        self.assertTrue(catalog, 'la migracion 0019 debe sembrar el catalogo')

        for tipo in catalog.values():
            with self.subTest(tipo=tipo.code):
                sale = SaleModel(requestType=tipo.code, serviceType='internet')
                self.assertEqual(get_request_label(sale, catalog),
                                 tipo.nombre.upper())

        etiquetas = {t.nombre.upper() for t in catalog.values()}
        # La agrupacion de instalaciones no debe aparecer en ningun reporte.
        self.assertNotIn('INSTALACIONES', etiquetas)
        self.assertIn('NUEVO CONTRATO', etiquetas)
        self.assertIn('RECONTRATACION', etiquetas)

    def test_adicion_mantiene_subtipo(self):
        from .models import Sale as SaleModel
        from .reports import get_request_label
        from .domain import request_type_catalog

        catalog = request_type_catalog()
        internet = SaleModel(requestType='adicion', additionType='adicion_internet')
        tv = SaleModel(requestType='adicion', additionType='adicion_tv')
        self.assertEqual(get_request_label(internet, catalog), 'ADICION INTERNET')
        self.assertEqual(get_request_label(tv), 'ADICION TV')

    def test_nombre_de_archivo_usa_el_tipo_de_movimiento(self):
        """El PDF/XLSX descargado no debe llamarse INSTALACIONES."""
        token = self._token()
        today = timezone.localdate().isoformat()

        for tipo, esperado in (('nuevo_contrato', 'NUEVO CONTRATO'),
                               ('recontratacion', 'RECONTRATACION'),
                               ('retiro', 'RETIRO')):
            with self.subTest(tipo=tipo):
                for url in (f'/api/reports/pdf?from={today}&to={today}&requestType={tipo}',
                            f'/api/reports/xlsx?from={today}&to={today}&requestType={tipo}'):
                    r = self.c.get(url, HTTP_AUTHORIZATION=f'Bearer {token}')
                    self.assertEqual(r.status_code, 200)
                    nombre = r.get('Content-Disposition', '')
                    self.assertIn(esperado, nombre)
                    self.assertNotIn('INSTALACIONES', nombre)


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
