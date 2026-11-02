from decimal import Decimal

from django.test import Client, TestCase
from django.utils import timezone

from .models import (
    CoverageZone, Motivo, Plan, Role, Sale, TarifaTraslado, User, UserRole,
)


def create_user(name, password, role='ventas'):
    user = User.objects.create(name=name, password='', role=role, active=True)
    user.set_password(password)
    user.save()
    return user


class CoverageZoneApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = create_user('coverage_admin', 'pass1', 'admin')
        self.operator = create_user('coverage_operator', 'pass1')
        self.manager = create_user('coverage_manager', 'pass1')
        self.commercial_lead = create_user('coverage_commercial_lead', 'pass1')
        self.cashier = create_user('coverage_cashier', 'pass1')
        self.call_center = create_user('coverage_call_center', 'pass1')
        self.technical_lead = create_user('coverage_technical', 'pass1')
        self.registerer = create_user('coverage_registerer', 'pass1')
        self.operations_lead = create_user('coverage_operations', 'pass1')
        self.attach_role(self.operator, 'tecnico-uno')
        self.attach_role(self.manager, 'gerente')
        self.attach_role(self.commercial_lead, 'jefe-comercial')
        self.attach_role(self.cashier, 'caja')
        self.attach_role(self.call_center, 'call-center')
        self.attach_role(self.technical_lead, 'jefe-tecnico')
        self.attach_role(self.registerer, 'encargado-red')
        self.attach_role(self.operations_lead, 'jefa-operativa')
        self._auth_headers = {}
        self.zone = CoverageZone.objects.get(normalized_name='villa busch')
        self.plan = Plan.objects.create(
            type='internet', code='COV-001', label='Internet base',
            monthly=Decimal('100'), speed=10, active=True,
            installation=Decimal('0'))

    @staticmethod
    def attach_role(user, code):
        role = Role.objects.get(code=code)
        UserRole.objects.create(user=user, role=role)

    def auth(self, user):
        if user.id not in self._auth_headers:
            response = self.client.post(
                '/api/auth/login',
                {'name': user.name, 'password': 'pass1'},
                content_type='application/json',
            )
            self._auth_headers[user.id] = {
                'HTTP_AUTHORIZATION': f'Bearer {response.json()["token"]}'
            }
        return self._auth_headers[user.id]

    def post_sale(self, payload):
        return self.client.post(
            '/api/sales',
            payload,
            content_type='application/json',
            **self.auth(self.admin),
        )

    def base_sale(self, code, request_type='nuevo_contrato', **extra):
        return {
            'clientCode': code,
            'clientName': f'Cliente {code}',
            'serviceType': 'internet',
            'requestType': request_type,
            'planId': self.plan.id,
            **extra,
        }

    def test_seeded_zone_catalog_is_idempotent_shape(self):
        expected = {
            'villa busch', 'las isla', 'castanal', 'roberto rojas',
            'mototaxi', 'paraíso', 'mejillones', 'gatty ribeiro',
            'mercado evo morales', 'san juan ii', 'avaroa',
            'barrio monte líbano', 'tahuamanu', 'terminal', 'el portugués',
        }
        self.assertEqual(
            set(CoverageZone.objects.values_list('normalized_name', flat=True)),
            expected,
        )
        self.assertEqual(CoverageZone.objects.count(), 15)

    def test_map_urls_match_each_existing_zone(self):
        expected_locations = {
            'villa busch': ('-11.084442928048484%2C-68.77239128169253', '15'),
            'las isla': ('-11.042655499999979%2C-68.80124675', '18'),
            'castanal': ('-11.037896500000004%2C-68.80360825', '17'),
            'roberto rojas': ('-11.031699499999991%2C-68.79058725', '17'),
            'mototaxi': ('-11.031502509383234%2C-68.79053900000001', '17'),
            'paraíso': ('-11.02388499999998%2C-68.77447225000002', '16'),
            'mejillones': ('-11.070286333333337%2C-68.81737650000001', '17'),
            'gatty ribeiro': ('-11.03703199999997%2C-68.77884240000002', '16'),
            'mercado evo morales': ('-11.048410499999989%2C-68.77346450000002', '18'),
            'san juan ii': ('-11.053223714285721%2C-68.776283', '16'),
            'avaroa': ('-11.083027999999986%2C-68.79755575', '16'),
            'barrio monte líbano': ('-11.090082833333332%2C-68.772644', '17'),
            'tahuamanu': ('-11.033353733333334%2C-68.75225113333333', '17'),
            'terminal': ('-11.062182500000002%2C-68.789622625', '17'),
            'el portugués': ('-11.0179885%2C-68.78190966666666', '17'),
        }
        zones = {
            zone.normalized_name: zone
            for zone in CoverageZone.objects.all()
        }
        self.assertEqual(set(zones), set(expected_locations))
        for normalized_name, (coordinates, zoom) in expected_locations.items():
            with self.subTest(zone=normalized_name):
                url = zones[normalized_name].google_maps_url
                self.assertTrue(url.startswith(
                    'https://www.google.com/maps/d/u/0/viewer?mid='))
                self.assertIn(
                    '1wbTe0yQgCet3cFowbPbMejip3njFilKg', url)
                self.assertIn(f'll={coordinates}&z={zoom}', url)
        self.assertEqual(
            len({zone.google_maps_url for zone in zones.values()}), 15)

    def test_users_with_coverage_view_permission_can_list_all_zones(self):
        inactive = CoverageZone.objects.create(
            name='Zona sin servicio', is_active=False)
        for user in (self.operator, self.registerer, self.operations_lead):
            with self.subTest(user=user.name):
                response = self.client.get(
                    '/api/coverage/zones/', **self.auth(user))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.json()), 16)
                self.assertIn(
                    inactive.name, {zone['name'] for zone in response.json()})

    def test_users_without_coverage_view_permission_cannot_list_zones(self):
        for user in (self.cashier, self.call_center, self.manager):
            with self.subTest(user=user.name):
                response = self.client.get(
                    '/api/coverage/zones/', **self.auth(user))
                self.assertEqual(response.status_code, 403)

    def test_coverage_permissions_match_configured_roles(self):
        expected = {
            'jefa-operativa': {
                'coverage.view', 'coverage.create',
                'coverage.change', 'coverage.manage',
            },
            'encargado-red': {'coverage.view', 'coverage.create'},
            'tecnico-uno': {'coverage.view'},
            'tecnico-dos': {'coverage.view'},
        }
        for role_code, permission_codes in expected.items():
            role = Role.objects.get(code=role_code)
            actual = {
                f'{item.permission.module}.{item.permission.action}'
                for item in role.role_permissions.select_related('permission')
                if item.permission.module == 'coverage'
            }
            with self.subTest(role=role_code):
                self.assertEqual(actual, permission_codes)

    def test_active_zone_query_is_shared_with_commercial_forms(self):
        CoverageZone.objects.create(name='Zona inactiva', is_active=False)
        response = self.client.get(
            '/api/coverage/zones/?active=true', **self.auth(self.operator))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 15)
        self.assertTrue(all(zone['is_active'] for zone in response.json()))

    def test_anonymous_user_cannot_list_zones(self):
        response = self.client.get('/api/coverage/zones/')
        self.assertEqual(response.status_code, 401)

    def test_operations_lead_can_manage_and_register_zones(self):
        response = self.client.get(
            '/api/coverage/zones/manage/', **self.auth(self.operations_lead))
        self.assertEqual(response.status_code, 200)
        created = self.client.post(
            '/api/coverage/zones/manage/',
            {
                'name': 'Zona Operativa',
                'google_maps_url': 'https://maps.google.com/?q=zone',
            },
            content_type='application/json',
            **self.auth(self.operations_lead),
        )
        self.assertEqual(created.status_code, 201, created.content)
        self.assertTrue(created.json()['is_active'])

    def test_registerer_can_create_but_cannot_manage_or_edit(self):
        created = self.client.post(
            '/api/coverage/zones/manage/',
            {
                'name': 'Zona Encargado',
                'google_maps_url': 'https://maps.google.com/?q=zone',
            },
            content_type='application/json',
            **self.auth(self.registerer),
        )
        self.assertEqual(created.status_code, 201, created.content)
        self.assertTrue(created.json()['is_active'])
        response = self.client.get(
            '/api/coverage/zones/manage/', **self.auth(self.registerer))
        self.assertEqual(response.status_code, 403)
        response = self.client.post(
            '/api/coverage/zones/manage/',
            {
                'name': 'No autorizada',
                'google_maps_url': 'https://maps.google.com/',
            },
            content_type='application/json',
            **self.auth(self.cashier),
        )
        self.assertEqual(response.status_code, 403)

        edited = self.client.patch(
            f"/api/coverage/zones/{created.json()['id']}/",
            {'name': 'No autorizado'},
            content_type='application/json',
            **self.auth(self.registerer),
        )
        self.assertEqual(edited.status_code, 403)

    def test_registerer_creates_active_zone_available_to_commercial(self):
        created = self.client.post(
            '/api/coverage/zones/manage/',
            {
                'name': 'Barrio nuevo',
                'google_maps_url': 'https://maps.google.com/?q=-11.1,-68.8',
            },
            content_type='application/json',
            **self.auth(self.registerer),
        )
        self.assertEqual(created.status_code, 201, created.content)
        zone = CoverageZone.objects.get(name='Barrio nuevo')
        self.assertEqual(zone.created_by, self.registerer)
        self.assertTrue(zone.is_active)
        self.assertEqual(created.json()['created_by_name'], self.registerer.name)

        commercial = self.client.get(
            '/api/coverage/zones/?active=true', **self.auth(self.operator))
        self.assertIn(zone.name, {item['name'] for item in commercial.json()})

    def test_only_users_with_create_permission_can_register(self):
        response = self.client.post(
            '/api/coverage/zones/manage/',
            {
                'name': 'No autorizada',
                'google_maps_url': 'https://maps.google.com/',
            },
            content_type='application/json',
            **self.auth(self.cashier),
        )
        self.assertEqual(response.status_code, 403)

    def test_registration_requires_google_maps_url(self):
        response = self.client.post(
            '/api/coverage/zones/manage/',
            {'name': 'Barrio sin mapa'},
            content_type='application/json',
            **self.auth(self.registerer),
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            CoverageZone.objects.filter(name='Barrio sin mapa').count(), 0)

    def test_operations_lead_can_edit_urls_and_toggle_zone(self):
        inactive = CoverageZone.objects.create(
            name='Zona inactiva',
            google_maps_url='https://maps.google.com/?q=old',
            is_active=False,
            created_by=self.registerer,
        )
        updated = self.client.patch(
            f'/api/coverage/zones/{inactive.id}/',
            {
                'name': 'Zona habilitada',
                'google_maps_url': 'https://maps.google.com/?q=new',
            },
            content_type='application/json',
            **self.auth(self.operations_lead),
        )
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(updated.json()['google_maps_url'],
                         'https://maps.google.com/?q=new')
        self.assertFalse(updated.json()['is_active'])

        enabled = self.client.patch(
            f'/api/coverage/zones/{inactive.id}/',
            {'is_active': True},
            content_type='application/json',
            **self.auth(self.operations_lead),
        )
        self.assertEqual(enabled.status_code, 200, enabled.content)
        self.assertTrue(enabled.json()['is_active'])
        self.assertIn(
            'Zona habilitada',
            {
                item['name'] for item in self.client.get(
                    '/api/coverage/zones/?active=true',
                    **self.auth(self.operator),
                ).json()
            },
        )
        disabled = self.client.patch(
            f'/api/coverage/zones/{inactive.id}/',
            {'is_active': False},
            content_type='application/json',
            **self.auth(self.operations_lead),
        )
        self.assertEqual(disabled.status_code, 200, disabled.content)
        self.assertFalse(disabled.json()['is_active'])
        self.assertTrue(CoverageZone.objects.filter(pk=inactive.pk).exists())
        self.assertNotIn(
            'Zona habilitada',
            {
                item['name'] for item in self.client.get(
                    '/api/coverage/zones/?active=true',
                    **self.auth(self.operator),
                ).json()
            },
        )

    def test_view_permission_cannot_edit_or_activate_zones(self):
        response = self.client.patch(
            f'/api/coverage/zones/{self.zone.id}/',
            {'google_maps_url': 'https://maps.google.com/'},
            content_type='application/json',
            **self.auth(self.operator),
        )
        self.assertEqual(response.status_code, 403)
        response = self.client.patch(
            f'/api/coverage/zones/{self.zone.id}/',
            {'is_active': False},
            content_type='application/json',
            **self.auth(self.operator),
        )
        self.assertEqual(response.status_code, 403)

    def test_create_normalizes_name_and_rejects_case_space_duplicate(self):
        created = self.client.post(
            '/api/coverage/zones/manage/',
            {
                'name': '  Nueva   Zona  ',
                'google_maps_url': 'https://maps.google.com/?q=nueva',
            },
            content_type='application/json',
            **self.auth(self.admin),
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()['name'], 'Nueva Zona')
        duplicate = self.client.post(
            '/api/coverage/zones/manage/',
            {
                'name': ' nueva zona ',
                'google_maps_url': 'https://maps.google.com/?q=duplicate',
            },
            content_type='application/json',
            **self.auth(self.admin),
        )
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(
            CoverageZone.objects.filter(normalized_name='nueva zona').count(), 1)

    def test_rename_rejects_duplicate_and_accepts_new_name(self):
        another = CoverageZone.objects.create(name='Villa Rojas')
        duplicate = self.client.patch(
            f'/api/coverage/zones/{another.id}/',
            {'name': ' VILLA   BUSCH '},
            content_type='application/json',
            **self.auth(self.admin),
        )
        self.assertEqual(duplicate.status_code, 400)
        updated = self.client.patch(
            f'/api/coverage/zones/{another.id}/',
            {'name': ' Villa   Rojas Norte '},
            content_type='application/json',
            **self.auth(self.admin),
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['name'], 'Villa Rojas Norte')

    def test_deactivate_and_reactivate_keeps_zone_and_filters_active_list(self):
        deactivated = self.client.patch(
            f'/api/coverage/zones/{self.zone.id}/',
            {'is_active': False},
            content_type='application/json',
            **self.auth(self.admin),
        )
        self.assertEqual(deactivated.status_code, 200)
        self.assertFalse(deactivated.json()['is_active'])
        active_names = {
            item['name'] for item in self.client.get(
                '/api/coverage/zones/?active=true',
                **self.auth(self.operator)).json()
        }
        self.assertNotIn(self.zone.name, active_names)
        all_names = {
            item['name'] for item in self.client.get(
                '/api/coverage/zones/', **self.auth(self.operator)).json()
        }
        self.assertIn(self.zone.name, all_names)

        reactivated = self.client.patch(
            f'/api/coverage/zones/{self.zone.id}/',
            {'is_active': True},
            content_type='application/json',
            **self.auth(self.admin),
        )
        self.assertEqual(reactivated.status_code, 200)
        self.assertTrue(CoverageZone.objects.filter(pk=self.zone.pk).exists())

    def test_new_contract_requires_an_active_zone_and_serializes_relation(self):
        missing = self.post_sale(self.base_sale('COV-SALE-1'))
        self.assertEqual(missing.status_code, 400)
        self.assertIn('zona de cobertura', missing.json()['error'].lower())

        inactive = CoverageZone.objects.create(name='Zona inactiva', is_active=False)
        rejected = self.post_sale(self.base_sale(
            'COV-SALE-2', coverageZoneId=inactive.id))
        self.assertEqual(rejected.status_code, 400)

        created = self.post_sale(self.base_sale(
            'COV-SALE-3', coverageZoneId=self.zone.id))
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()['coverageZoneId'], self.zone.id)
        self.assertEqual(created.json()['coverageZone']['name'], self.zone.name)

    def test_rehire_requires_zone(self):
        fields = {
            'equipmentRetained': True,
            'requiresTechnicalVisit': False,
        }
        missing = self.post_sale(self.base_sale(
            'COV-REHIRE-1', 'recontratacion', **fields))
        self.assertEqual(missing.status_code, 400)

        created = self.post_sale(self.base_sale(
            'COV-REHIRE-2', 'recontratacion',
            coverageZoneId=self.zone.id, **fields))
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()['coverageZoneId'], self.zone.id)

    def test_transfer_requires_zone_and_saves_destination_snapshot(self):
        tariff, _ = TarifaTraslado.objects.get_or_create(
            service_type='internet',
            defaults={'name': 'Traslado internet', 'amount': Decimal('50')},
        )
        details = {
            'transferTariffId': tariff.id,
            'transferNewAddress': 'Calle Nueva 10',
            'transferHasSketch': False,
        }
        missing = self.post_sale(self.base_sale(
            'COV-TRANSFER-1', 'traslado_externo', **details))
        self.assertEqual(missing.status_code, 400)

        created = self.post_sale(self.base_sale(
            'COV-TRANSFER-2', 'traslado_externo',
            coverageZoneId=self.zone.id, **details))
        self.assertEqual(created.status_code, 201)
        sale = Sale.objects.get(pk=created.json()['id'])
        self.assertEqual(sale.coverage_zone_id, self.zone.id)
        self.assertEqual(sale.traslado_externo.zone, self.zone.name)

    def test_change_addition_and_retirement_do_not_need_zone(self):
        previous_plan = Plan.objects.create(
            type='internet', code='COV-000', label='Internet anterior',
            monthly=Decimal('80'), speed=8, active=True,
            installation=Decimal('0'))
        change_reason = Motivo.objects.create(
            categoria='cambio', nombre='Cambio requerido')
        retirement_reason = Motivo.objects.create(
            categoria='retiro', nombre='Retiro requerido')

        cases = (
            self.base_sale(
                'COV-CHANGE', 'cambio_plan',
                planFromId=previous_plan.id, motivoId=change_reason.id),
            self.base_sale(
                'COV-ADDITION', 'adicion', additionType='adicion_internet'),
            self.base_sale(
                'COV-RETIRE', 'retiro', motivoId=retirement_reason.id),
        )
        for payload in cases:
            response = self.post_sale(payload)
            self.assertEqual(response.status_code, 201, response.content)
            sale = Sale.objects.get(pk=response.json()['id'])
            self.assertIsNone(sale.coverage_zone_id)

    def test_historical_sale_retains_inactive_zone_reference(self):
        inactive = CoverageZone.objects.create(
            name='Zona histórica', is_active=False)
        sale = Sale.objects.create(
            date=timezone.localdate(),
            clientCode='COV-HISTORY',
            clientName='Histórico',
            serviceType='internet',
            requestType='nuevo_contrato',
            plan=self.plan,
            planName=self.plan.label,
            total=Decimal('100'),
            coverage_zone=inactive,
            createdBy=self.admin,
        )

        response = self.client.get(
            f'/api/sales?page_size=100', **self.auth(self.admin))
        self.assertEqual(response.status_code, 200)
        item = next(row for row in response.json()['items'] if row['id'] == sale.id)
        self.assertEqual(item['coverageZone']['id'], inactive.id)
        self.assertFalse(item['coverageZone']['is_active'])
