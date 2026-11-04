from django.test import TestCase, Client
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from .models import User, Plan, Sale, Motivo, Role, CoverageZone


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
        self.coverage_zone_id = CoverageZone.objects.get(
            normalized_name='villa busch').id

    def _token(self, user, pw):
        r = self.c.post('/api/auth/login', {'name': user.name, 'password': pw},
                        content_type='application/json')
        return _json(r)['token']

    def test_create_sale_admin(self):
        token = self._token(self.admin, 'pass1')
        r = self.c.post('/api/sales', {
            'clientCode': 'K001', 'clientName': 'CLIENTE TEST',
            'serviceType': 'internet', 'requestType': 'nuevo_contrato',
            'planId': self.plan.id, 'coverageZoneId': self.coverage_zone_id
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
            'planId': self.plan.id, 'coverageZoneId': self.coverage_zone_id
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 201)

    def test_create_sale_without_token(self):
        r = self.c.post('/api/sales', {
            'clientCode': 'K003', 'clientName': 'X',
            'serviceType': 'internet', 'requestType': 'nuevo_contrato',
            'planId': self.plan.id, 'coverageZoneId': self.coverage_zone_id
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
            'planId': self.plan.id, 'coverageZoneId': self.coverage_zone_id
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
            'planId': self.plan.id, 'coverageZoneId': self.coverage_zone_id
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
            'planId': self.plan.id, 'coverageZoneId': self.coverage_zone_id
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
            'planId': self.plan.id, 'coverageZoneId': self.coverage_zone_id
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
        self.coverage_zone_id = CoverageZone.objects.get(
            normalized_name='villa busch').id

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
            'planId': self.plan.id, 'coverageZoneId': self.coverage_zone_id
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.c.post('/api/sales', {
            'clientCode': 'D003', 'clientName': 'DASH3',
            'serviceType': 'internet', 'requestType': 'recontratacion',
            'planId': self.plan.id, 'equipmentRetained': True,
            'requiresTechnicalVisit': False, 'debtApplies': False,
            'debtAmount': 0, 'coverageZoneId': self.coverage_zone_id
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

    def _sale(self, code, request_type, movement_date, service='internet',
              total=100, coverage_zone=None):
        return Sale.objects.create(
            date=movement_date,
            clientCode=code,
            clientName=f'DASH_{code}',
            serviceType=service,
            requestType=request_type,
            plan=self.plan,
            planName=self.plan.label,
            total=Decimal(str(total)),
            coverage_zone=coverage_zone,
            createdBy=self.admin,
        )

    def test_dashboard_analytics_custom_range_and_series(self):
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        self._sale('A001', 'nuevo_contrato', yesterday, total=120)
        self._sale('A002', 'retiro', today, total=80)
        self._sale('A003', 'cambio_plan', today, service='tv_digital')
        self._sale('A004', 'adicion', today, service='combo_digital')
        self._sale('A005', 'recontratacion', today)

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
        self.assertEqual(analytics['recontrataciones']['count'], 1)
        self.assertEqual(analytics['retiros']['count'], 1)
        self.assertEqual(analytics['cambios_plan']['count'], 1)
        self.assertEqual(analytics['balance_neto'], 1)
        self.assertEqual(len(analytics['series']), 2)
        self.assertEqual(analytics['series'][0]['nuevo_contrato'], 1)
        self.assertEqual(analytics['series'][0]['recontrataciones'], 0)
        self.assertEqual(analytics['series'][1]['recontrataciones'], 1)
        self.assertEqual(analytics['series'][1]['retiros'], 1)
        self.assertEqual(
            {item['serviceType'] for item in analytics['servicios']},
            {'internet', 'tv_digital', 'combo_digital'},
        )
        self.assertEqual(
            sum(item['count'] for item in analytics['categorias']),
            5,
        )

    def test_dashboard_drilldown_matches_indicator_and_paginates_search(self):
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        self._sale('DD001', 'nuevo_contrato', today)
        self._sale('DD002', 'nuevo_contrato', today)
        self._sale('DD004', 'nuevo_contrato', yesterday)
        archived = self._sale('DD003', 'nuevo_contrato', today)
        archived.deleted_at = timezone.now()
        archived.save(update_fields=['deleted_at'])
        token = self._token()

        stats = self.c.get(
            f'/api/dashboard/stats?from={today.isoformat()}&to={today.isoformat()}',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        params = (
            f'from={today.isoformat()}&to={today.isoformat()}'
            '&indicator=nuevo_contrato&category=nuevo_contrato'
            '&search=DASH&page_size=1&page=1'
        )
        response = self.c.get(
            f'/api/dashboard/drilldown?{params}',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(response.status_code, 200, _json(response))
        data = _json(response)
        self.assertEqual(data['indicator_count'], 2)
        self.assertEqual(
            data['indicator_count'],
            _json(stats)['analytics']['nuevo_contrato']['count'])
        self.assertEqual(data['total'], 2)
        self.assertEqual(data['total_pages'], 2)
        self.assertEqual(len(data['items']), 1)

        next_page = self.c.get(
            f'/api/dashboard/drilldown?{params.replace("page=1", "page=2")}',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(next_page.status_code, 200)
        self.assertNotEqual(
            _json(response)['items'][0]['id'],
            _json(next_page)['items'][0]['id'])

        by_code = self.c.get(
            f'/api/dashboard/drilldown?from={today.isoformat()}&to={today.isoformat()}'
            '&indicator=nuevo_contrato&category=nuevo_contrato&search=DD002',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(_json(by_code)['total'], 1)
        self.assertEqual(_json(by_code)['items'][0]['clientCode'], 'DD002')

    def test_dashboard_drilldown_group_breakdown_matches_balance(self):
        today = timezone.localdate()
        self._sale('DG001', 'nuevo_contrato', today)
        self._sale('DG002', 'recontratacion', today)
        self._sale('DG003', 'retiro', today)
        token = self._token()
        params = f'from={today.isoformat()}&to={today.isoformat()}'

        stats = self.c.get(
            f'/api/dashboard/stats?{params}',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        balance = self.c.get(
            f'/api/dashboard/drilldown?{params}&indicator=balance_neto',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        altas = self.c.get(
            f'/api/dashboard/drilldown?{params}&indicator=altas_comerciales',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        filtered_altas = self.c.get(
            f'/api/dashboard/drilldown?{params}&indicator=altas_comerciales'
            '&movement_type=recontrataciones',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(balance.status_code, 200)
        self.assertEqual(altas.status_code, 200)
        self.assertEqual(filtered_altas.status_code, 200)
        self.assertEqual(
            _json(balance)['indicator_count'],
            _json(stats)['analytics']['balance_neto'])
        self.assertEqual(_json(altas)['indicator_count'], 2)
        self.assertEqual(_json(filtered_altas)['indicator_count'], 1)
        self.assertEqual(
            {item['category']: item['count'] for item in _json(balance)['breakdown']},
            {'nuevo_contrato': 1, 'recontrataciones': 1, 'retiros': 1})

    def test_dashboard_drilldown_requires_auth_and_limits_operator_to_today(self):
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        self._sale('DO001', 'nuevo_contrato', yesterday)
        self._sale('DO002', 'nuevo_contrato', today)
        self.assertEqual(
            self.c.get('/api/dashboard/drilldown?indicator=nuevo_contrato').status_code,
            401)

        operator = _create_user('drilldown-operator', 'pass1', 'ventas')
        login = self.c.post(
            '/api/auth/login',
            {'name': operator.name, 'password': 'pass1'},
            content_type='application/json')
        token = _json(login)['token']
        response = self.c.get(
            '/api/dashboard/drilldown'
            f'?from={yesterday.isoformat()}&to={today.isoformat()}'
            '&indicator=nuevo_contrato&category=nuevo_contrato',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(_json(response)['period']['from'], today.isoformat())
        self.assertEqual(_json(response)['total'], 1)

    def test_dashboard_drilldown_rejects_invalid_filters(self):
        token = self._token()
        response = self.c.get(
            '/api/dashboard/drilldown?indicator=incorrecto',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(response.status_code, 400)
        response = self.c.get(
            '/api/dashboard/drilldown?indicator=balance_neto&category=cambios_plan',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(response.status_code, 400)

    def test_dashboard_zones_rank_contracts_rehires_and_transfers(self):
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        token = self._token()
        villa_busch = CoverageZone.objects.get(normalized_name='villa busch')
        terminal = CoverageZone.objects.get(normalized_name='terminal')
        self._sale(
            'ZONE001', 'nuevo_contrato', today,
            coverage_zone=villa_busch)
        self._sale(
            'ZONE002', 'recontratacion', today,
            coverage_zone=villa_busch)
        self._sale(
            'ZONE003', 'traslado_externo', today,
            coverage_zone=terminal)
        self._sale(
            'ZONE004', 'retiro', today,
            coverage_zone=terminal)
        self._sale(
            'ZONE005', 'nuevo_contrato', yesterday,
            coverage_zone=terminal)

        headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        response = self.c.get(
            f'/api/dashboard/stats?from={today.isoformat()}&to={today.isoformat()}',
            **headers)

        self.assertEqual(response.status_code, 200)
        zones = _json(response)['analytics']['zonas']
        self.assertEqual(
            zones,
            [
                {'name': villa_busch.name, 'count': 2, 'percentage': 66.7},
                {'name': terminal.name, 'count': 1, 'percentage': 33.3},
            ],
        )

        filtered = self.c.get(
            f'/api/dashboard/stats?from={today.isoformat()}&to={today.isoformat()}'
            '&movement_type=nuevo_contrato',
            **headers)
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(
            _json(filtered)['analytics']['zonas'],
            [{'name': villa_busch.name, 'count': 1, 'percentage': 100.0}],
        )

    def test_dashboard_zone_ranking_groups_remaining_zones_as_others(self):
        today = timezone.localdate()
        token = self._token()
        zones = list(CoverageZone.objects.order_by('name')[:7])
        for index, zone in enumerate(zones):
            self._sale(
                f'ZONE-TOP-{index}',
                'nuevo_contrato',
                today,
                coverage_zone=zone,
            )
        self._sale(
            'ZONE-TOP-EXTRA',
            'recontratacion',
            today,
            coverage_zone=zones[0],
        )

        response = self.c.get(
            '/api/dashboard/stats',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(response.status_code, 200)
        ranking = _json(response)['analytics']['zonas']
        self.assertEqual(len(ranking), 6)
        self.assertEqual(ranking[0]['name'], zones[0].name)
        self.assertEqual(ranking[0]['count'], 2)
        self.assertEqual(ranking[-1]['name'], 'Otros barrios')
        self.assertEqual(ranking[-1]['count'], 2)

    def test_dashboard_zone_drilldown_matches_ranking_and_filters(self):
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        zones = list(CoverageZone.objects.order_by('name')[:7])
        selected_zone = zones[0]
        self._sale(
            'ZONE-DETAIL-001', 'nuevo_contrato', today,
            coverage_zone=selected_zone)
        self._sale(
            'ZONE-DETAIL-002', 'recontratacion', today,
            coverage_zone=selected_zone)
        self._sale(
            'ZONE-DETAIL-OLD', 'nuevo_contrato', yesterday,
            coverage_zone=selected_zone)
        self._sale(
            'ZONE-DETAIL-RETIRO', 'retiro', today,
            coverage_zone=selected_zone)
        for index, zone in enumerate(zones[1:]):
            self._sale(
                f'ZONE-DETAIL-OTHER-{index}', 'nuevo_contrato', today,
                coverage_zone=zone)

        token = self._token()
        headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        period_params = {
            'from': today.isoformat(),
            'to': today.isoformat(),
        }
        stats = self.c.get(
            '/api/dashboard/stats', period_params, **headers)
        self.assertEqual(stats.status_code, 200)
        ranking = _json(stats)['analytics']['zonas']
        self.assertEqual(ranking[0]['name'], selected_zone.name)
        self.assertEqual(ranking[0]['count'], 2)
        self.assertEqual(ranking[-1]['name'], 'Otros barrios')
        self.assertEqual(ranking[-1]['count'], 2)

        params = {
            **period_params,
            'indicator': 'zone',
            'zone_name': selected_zone.name,
            'page_size': 1,
        }
        first_page = self.c.get(
            '/api/dashboard/drilldown', params, **headers)
        self.assertEqual(first_page.status_code, 200, _json(first_page))
        first_data = _json(first_page)
        self.assertEqual(first_data['zone_count'], ranking[0]['count'])
        self.assertEqual(first_data['total'], ranking[0]['count'])
        self.assertEqual(first_data['indicator_count'], ranking[0]['count'])
        self.assertEqual(first_data['total_pages'], 2)
        first_sale = first_data['items'][0]
        for field in (
                'clientName', 'clientCode', 'date', 'requestType',
                'requestTypeLabel', 'serviceType', 'Plan', 'creator'):
            self.assertIn(field, first_sale)

        second_page = self.c.get(
            '/api/dashboard/drilldown',
            {**params, 'page': 2},
            **headers)
        self.assertEqual(second_page.status_code, 200)
        self.assertNotEqual(
            first_data['items'][0]['id'],
            _json(second_page)['items'][0]['id'])

        searched = self.c.get(
            '/api/dashboard/drilldown',
            {**params, 'page_size': 25, 'search': 'ZONE-DETAIL-002'},
            **headers)
        self.assertEqual(searched.status_code, 200)
        self.assertEqual(_json(searched)['zone_count'], 2)
        self.assertEqual(_json(searched)['total'], 1)

        other_zone_params = {
            **period_params,
            'indicator': 'zone',
            'zone_name': 'Otros barrios',
        }
        other_zones = self.c.get(
            '/api/dashboard/drilldown', other_zone_params, **headers)
        self.assertEqual(other_zones.status_code, 200)
        self.assertEqual(_json(other_zones)['zone_count'], ranking[-1]['count'])
        self.assertEqual(_json(other_zones)['total'], ranking[-1]['count'])

        filtered_stats = self.c.get(
            '/api/dashboard/stats',
            {**period_params, 'movement_type': 'nuevo_contrato'},
            **headers)
        filtered_ranking = _json(filtered_stats)['analytics']['zonas']
        filtered_detail = self.c.get(
            '/api/dashboard/drilldown',
            {
                **params,
                'movement_type': 'nuevo_contrato',
                'page_size': 25,
            },
            **headers)
        self.assertEqual(filtered_detail.status_code, 200)
        self.assertEqual(
            _json(filtered_detail)['zone_count'],
            filtered_ranking[0]['count'])
        self.assertEqual(_json(filtered_detail)['total'], 1)

    def test_dashboard_plan_demand_is_ordered_within_selected_range(self):
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)
        self._sale('PLAN001', 'nuevo_contrato', yesterday)
        self._sale('PLAN002', 'recontratacion', today)
        self._sale('PLAN003', 'retiro', today)

        less_demanded_plan = Plan.objects.create(
            type='tv', code='TEST02', label='Plan TV 50',
            monthly=80, speed=None, active=True,
            installation=Decimal('0'))
        Sale.objects.create(
            date=today, clientCode='PLAN004', clientName='DASH_PLAN004',
            serviceType='tv', requestType='nuevo_contrato',
            plan=less_demanded_plan, planName=less_demanded_plan.label,
            total=Decimal('80'), createdBy=self.admin)
        Sale.objects.create(
            date=two_days_ago, clientCode='PLAN005', clientName='DASH_PLAN005',
            serviceType='tv', requestType='nuevo_contrato',
            plan=less_demanded_plan, planName=less_demanded_plan.label,
            total=Decimal('80'), createdBy=self.admin)

        token = self._token()
        response = self.c.get(
            f'/api/dashboard/stats?from={yesterday.isoformat()}&to={today.isoformat()}',
            HTTP_AUTHORIZATION=f'Bearer {token}')

        self.assertEqual(response.status_code, 200)
        plans = _json(response)['analytics']['planes']
        self.assertEqual(
            [(item['label'], item['type_label'], item['count']) for item in plans],
            [('Plan 200', 'Internet', 2), ('Plan TV 50', 'TV', 1)],
        )

    def test_dashboard_plan_drilldown_matches_plan_demand_and_paginates(self):
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)
        first = self._sale(
            'PLAN-DETAIL-001', 'nuevo_contrato', today,
            coverage_zone=CoverageZone.objects.get(
                id=self.coverage_zone_id))
        second = self._sale(
            'PLAN-DETAIL-002', 'recontratacion', today,
            coverage_zone=CoverageZone.objects.get(
                id=self.coverage_zone_id))
        self._sale('PLAN-DETAIL-RETIRO', 'retiro', today)
        self._sale('PLAN-DETAIL-OLD', 'nuevo_contrato', yesterday)

        other_plan = Plan.objects.create(
            type='internet', code='TEST-PLAN-DETAIL', label='Plan Alternativo',
            monthly=100, speed='10', active=True,
            installation=Decimal('0'))
        Sale.objects.create(
            date=today, clientCode='PLAN-DETAIL-OTHER',
            clientName='DASH_PLAN-DETAIL-OTHER',
            serviceType='internet', requestType='nuevo_contrato',
            plan=other_plan, planName=other_plan.label,
            total=Decimal('100'), createdBy=self.admin)

        token = self._token()
        headers = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        params = {
            'from': today.isoformat(),
            'to': today.isoformat(),
        }
        stats = self.c.get('/api/dashboard/stats', params, **headers)
        self.assertEqual(stats.status_code, 200)
        plan = next(
            item for item in _json(stats)['analytics']['planes']
            if item['label'] == self.plan.label)
        self.assertEqual(plan['count'], 2)

        detail_params = {
            **params,
            'indicator': 'plan',
            'plan_name': plan['plan_name'],
            'catalog_label': plan['catalog_label'],
            'plan_type': plan['type'],
            'page_size': 1,
        }
        first_page = self.c.get(
            '/api/dashboard/drilldown', detail_params, **headers)
        self.assertEqual(first_page.status_code, 200, _json(first_page))
        first_data = _json(first_page)
        self.assertEqual(first_data['plan_count'], plan['count'])
        self.assertEqual(first_data['indicator_count'], plan['count'])
        self.assertEqual(first_data['total'], plan['count'])
        self.assertEqual(first_data['total_pages'], 2)
        self.assertIn(
            first_data['items'][0]['id'], {first.id, second.id})
        self.assertEqual(
            first_data['items'][0]['coverageZone']['name'],
            CoverageZone.objects.get(id=self.coverage_zone_id).name)
        self.assertIn('requestTypeLabel', first_data['items'][0])

        next_page = self.c.get(
            '/api/dashboard/drilldown',
            {**detail_params, 'page': 2},
            **headers)
        self.assertEqual(next_page.status_code, 200)
        self.assertNotEqual(
            first_data['items'][0]['id'],
            _json(next_page)['items'][0]['id'])

        searched = self.c.get(
            '/api/dashboard/drilldown',
            {
                **detail_params,
                'page_size': 25,
                'search': 'PLAN-DETAIL-002',
            },
            **headers)
        self.assertEqual(searched.status_code, 200)
        self.assertEqual(_json(searched)['plan_count'], plan['count'])
        self.assertEqual(_json(searched)['total'], 1)

        filtered_stats = self.c.get(
            '/api/dashboard/stats',
            {**params, 'movement_type': 'nuevo_contrato'},
            **headers)
        filtered_plan = next(
            item for item in _json(filtered_stats)['analytics']['planes']
            if item['label'] == self.plan.label)
        filtered_detail = self.c.get(
            '/api/dashboard/drilldown',
            {
                **detail_params,
                'movement_type': 'nuevo_contrato',
                'page_size': 25,
            },
            **headers)
        self.assertEqual(filtered_detail.status_code, 200)
        self.assertEqual(
            _json(filtered_detail)['plan_count'], filtered_plan['count'])
        self.assertEqual(_json(filtered_detail)['total'], filtered_plan['count'])

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
            'password': 'newpass',
            'roleIds': [Role.objects.get(code='caja').id]
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 201)

    def test_create_user_ventas_forbidden(self):
        token = self._token(self.ventas_user, 'pass2')
        r = self.c.post('/api/users', {
            'name': 'hack',
            'password': 'hack',
            'roleIds': [Role.objects.get(code='caja').id]
        }, content_type='application/json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 403)

    def test_edit_user_admin(self):
        token = self._token(self.admin, 'pass1')
        r = self.c.put(f'/api/users/{self.ventas_user.id}', {
            'name': 'ventas_updated'
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
