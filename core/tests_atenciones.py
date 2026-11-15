from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

from .atencion_services import finish_attention, start_attention
from .models import Atencion, AtencionCatalogo, User


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
        self.catalogs = {
            catalog_type: AtencionCatalogo.objects.create(
                catalog_type=catalog_type,
                code=f'{catalog_type}-test',
                name=f'{catalog_type} test',
            )
            for catalog_type in ('attention_type', 'classification', 'channel')
        }
        self.action = AtencionCatalogo.objects.create(
            catalog_type='support_action',
            code='informado-test',
            name='Informado',
        )

    def create_attention(self):
        response = self.client.post(
            '/api/atenciones',
            {
                'customer_code': 'K-1',
                'customer_name': 'Cliente de prueba',
                'attention_type': self.catalogs['attention_type'].id,
                'classification': self.catalogs['classification'].id,
                'channel': self.catalogs['channel'].id,
            },
            content_type='application/json',
            **self.auth,
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_duration_is_calculated_in_backend(self):
        attention = Atencion.objects.get(pk=self.create_attention()['id'])
        start_attention(attention)
        attention.started_at = timezone.now() - timedelta(minutes=3)
        attention.save(update_fields=['started_at'])
        finish_attention(attention)
        attention.refresh_from_db()
        self.assertEqual(attention.status, 'finished')
        self.assertGreaterEqual(attention.duration_seconds, 179)

    def test_dashboard_aggregates_finished_attentions(self):
        attention = Atencion.objects.get(pk=self.create_attention()['id'])
        start_attention(attention)
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
