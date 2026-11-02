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
        self.manager = create_user('coverage_manager', 'pass1')
        self.commercial_lead = create_user('coverage_commercial_lead', 'pass1')
        self.cashier = create_user('coverage_cashier', 'pass1')
        self.call_center = create_user('coverage_call_center', 'pass1')
        self.technical_lead = create_user('coverage_technical', 'pass1')
        self.attach_role(self.manager, 'gerente')
        self.attach_role(self.commercial_lead, 'jefe-comercial')
        self.attach_role(self.cashier, 'caja')
        self.attach_role(self.call_center, 'call-center')
        self.attach_role(self.technical_lead, 'jefe-tecnico')
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

    def test_authenticated_operator_can_list_active_zones(self):
        response = self.client.get(
            '/api/coverage/zones/', **self.auth(self.cashier))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 15)
        call_center_response = self.client.get(
            '/api/coverage/zones/', **self.auth(self.call_center))
        self.assertEqual(call_center_response.status_code, 200)

    def test_anonymous_user_cannot_list_zones(self):
        response = self.client.get('/api/coverage/zones/')
        self.assertEqual(response.status_code, 401)

    def test_manager_and_technical_lead_can_manage_zones(self):
        for user in (
                self.manager, self.commercial_lead, self.technical_lead):
            response = self.client.get(
                '/api/coverage/zones/manage/', **self.auth(user))
            self.assertEqual(response.status_code, 200)
            created = self.client.post(
                '/api/coverage/zones/manage/',
                {'name': f'Zona {user.name}'},
                content_type='application/json',
                **self.auth(user),
            )
            self.assertEqual(created.status_code, 201)

    def test_cashier_can_consult_but_cannot_manage(self):
        response = self.client.get(
            '/api/coverage/zones/manage/', **self.auth(self.cashier))
        self.assertEqual(response.status_code, 403)
        response = self.client.post(
            '/api/coverage/zones/manage/',
            {'name': 'No autorizada'},
            content_type='application/json',
            **self.auth(self.cashier),
        )
        self.assertEqual(response.status_code, 403)

    def test_create_normalizes_name_and_rejects_case_space_duplicate(self):
        created = self.client.post(
            '/api/coverage/zones/manage/',
            {'name': '  Nueva   Zona  '},
            content_type='application/json',
            **self.auth(self.admin),
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()['name'], 'Nueva Zona')
        duplicate = self.client.post(
            '/api/coverage/zones/manage/',
            {'name': ' nueva zona '},
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
                '/api/coverage/zones/', **self.auth(self.cashier)).json()
        }
        self.assertNotIn(self.zone.name, active_names)

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
