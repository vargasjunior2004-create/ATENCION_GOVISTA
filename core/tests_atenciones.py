from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

from .atencion_services import finish_attention
from .models import Atencion, AtencionCatalogo, Plan, User


class AtencionWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User(name='call-center-test', role='call-center')
        self.user.set_password('test-pass')
        self.user.save()
        response = self.client.post(
            '/api/auth/login',
            {'name': self.user.name, 'password': 'test-pass'},
            content_type='application/json',
        )
        self.auth = {'HTTP_AUTHORIZATION': f'Bearer {response.json()["token"]}'}
        self.catalogs = {}
        for catalog_type in ('attention_type', 'classification'):
            self.catalogs[catalog_type] = AtencionCatalogo.objects.create(
                catalog_type=catalog_type,
                code=f'{catalog_type}-test',
                name=f'{catalog_type} test',
            )
        self.catalogs['channel'], _ = AtencionCatalogo.objects.get_or_create(
            catalog_type='channel',
            code='mensaje',
            defaults={'name': 'Mensajes'},
        )
        self.action = AtencionCatalogo.objects.create(
            catalog_type='support_action',
            code='informado-test',
            name='Informado',
        )

    def create_attention(self):
        response = self.client.post(
            '/api/atenciones/iniciar',
            {
                'customer_code': 'K-1',
                'customer_name': 'Cliente de prueba',
                'attention_type': self.catalogs['attention_type'].id,
                'classification': self.catalogs['classification'].id,
                'channel': self.catalogs['channel'].id,
            },
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='create-attention-key',
            **self.auth,
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_duration_is_calculated_in_backend(self):
        attention = Atencion.objects.get(pk=self.create_attention()['id'])
        attention.started_at = timezone.now() - timedelta(minutes=3)
        attention.save(update_fields=['started_at'])
        finish_attention(attention)
        attention.refresh_from_db()
        self.assertEqual(attention.status, 'finished')
        self.assertGreaterEqual(attention.duration_seconds, 179)

    def test_dashboard_aggregates_finished_attentions(self):
        attention = Atencion.objects.get(pk=self.create_attention()['id'])
        attention.started_at = timezone.now() - timedelta(seconds=30)
        attention.save(update_fields=['started_at'])
        finish_attention(attention)
        response = self.client.get('/api/call-center/dashboard', **self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['total'], 1)
        self.assertEqual(response.json()['by_agent'][0]['attention_count'], 1)

    def test_invalid_catalog_cannot_create_attention(self):
        response = self.client.post(
            '/api/atenciones',
            {
                'attention_type': self.catalogs['channel'].id,
                'classification': self.catalogs['classification'].id,
                'channel': self.catalogs['channel'].id,
            },
            content_type='application/json',
            **self.auth,
        )
        self.assertEqual(response.status_code, 400)

    def test_start_is_idempotent_and_recovers_open_attention(self):
        payload = {
            'customer_code': 'K-2',
            'customer_name': 'Cliente idempotente',
            'attention_type': self.catalogs['attention_type'].id,
            'classification': self.catalogs['classification'].id,
            'channel': self.catalogs['channel'].id,
        }
        response = self.client.post(
            '/api/atenciones/iniciar',
            payload,
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='attention-test-key',
            **self.auth,
        )
        repeated = self.client.post(
            '/api/atenciones/iniciar',
            payload,
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='attention-test-key',
            **self.auth,
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(response.json()['id'], repeated.json()['id'])
        open_response = self.client.get('/api/atenciones/abierta', **self.auth)
        self.assertEqual(open_response.status_code, 200)
        self.assertEqual(open_response.json()['id'], response.json()['id'])
        self.assertEqual(Atencion.objects.filter(agent=self.user, status='open').count(), 1)

    def test_call_center_cannot_use_office_channel(self):
        office = AtencionCatalogo.objects.create(
            catalog_type='channel', code='oficina-test', name='Oficina')
        response = self.client.post(
            '/api/atenciones/iniciar',
            {
                'attention_type': self.catalogs['attention_type'].id,
                'classification': self.catalogs['classification'].id,
                'channel': office.id,
            },
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='office-test-key',
            **self.auth,
        )
        self.assertEqual(response.status_code, 400)

    def test_second_open_attention_is_rejected(self):
        payload = {
            'customer_code': 'K-3',
            'customer_name': 'Cliente uno',
            'attention_type': self.catalogs['attention_type'].id,
            'classification': self.catalogs['classification'].id,
            'channel': self.catalogs['channel'].id,
        }
        first = self.client.post(
            '/api/atenciones/iniciar',
            payload,
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='first-open-key',
            **self.auth,
        )
        second = self.client.post(
            '/api/atenciones/iniciar',
            {**payload, 'customer_code': 'K-4'},
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='second-open-key',
            **self.auth,
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(Atencion.objects.filter(
            agent=self.user, status='open').count(), 1)

    def test_finish_is_not_repeatable(self):
        attention = Atencion.objects.get(pk=self.create_attention()['id'])
        response = self.client.post(
            f'/api/atenciones/{attention.id}/finalizar', **self.auth)
        repeated = self.client.post(
            f'/api/atenciones/{attention.id}/finalizar', **self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(repeated.status_code, 400)

    def test_service_plan_and_dashboard_filters_are_consistent(self):
        plan = Plan.objects.create(
            code='TEST-PLAN',
            label='Plan de prueba',
            type='internet',
            monthly=100,
            installation=50,
        )
        complaint_type = AtencionCatalogo.objects.get(
            catalog_type='attention_type', code='queja')
        payload = {
            'customer_code': 'K-5',
            'customer_name': 'Cliente con plan',
            'attention_type': complaint_type.id,
            'classification': self.catalogs['classification'].id,
            'channel': self.catalogs['channel'].id,
            'service_type': 'internet',
            'plan': plan.id,
        }
        response = self.client.post(
            '/api/atenciones/iniciar',
            payload,
            content_type='application/json',
            HTTP_IDEMPOTENCY_KEY='plan-filter-key',
            **self.auth,
        )
        self.assertEqual(response.status_code, 201)
        attention = Atencion.objects.get(pk=response.json()['id'])
        finish_attention(attention)
        dashboard = self.client.get(
            f'/api/call-center/dashboard?service_type=internet&plan={plan.id}',
            **self.auth,
        )
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.json()['summary']['total_attentions'], 1)
        self.assertEqual(dashboard.json()['by_plan'][0]['plan_name'], 'Plan de prueba')
