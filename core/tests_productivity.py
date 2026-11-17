from decimal import Decimal

from django.test import Client, TestCase
from datetime import timedelta

from django.utils import timezone

from .models import Plan, Role, Sale, User, UserRole


class CommercialProductivityTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.plan = Plan.objects.create(
            type='internet', code='PROD-QA', label='Plan productividad',
            monthly=100, installation=Decimal('0'), speed='20', active=True)
        self.supervisor = self._user('gerente_prod', 'gerente')
        self.agent = self._user('agente_prod', 'caja')
        self.other = self._user('otro_prod', 'caja')
        self._assign(self.supervisor, 'gerente')
        self._assign(self.agent, 'caja')
        self._assign(self.other, 'caja')
        self._sale(self.agent, 'PROD-A')
        self._sale(self.agent, 'PROD-B')
        self._sale(self.other, 'PROD-C')

    def _user(self, name, role='ventas'):
        user = User.objects.create(name=name, password='', role=role)
        user.set_password('productivity-pass')
        user.save()
        return user

    def _assign(self, user, code):
        role = Role.objects.get(code=code)
        UserRole.objects.create(user=user, role=role, assigned_by=self.supervisor)

    def _sale(self, user, code, sale_date=None):
        return Sale.objects.create(
            date=sale_date or timezone.localdate(), clientCode=code, clientName=f'Cliente {code}',
            serviceType='internet', requestType='nuevo_contrato', plan=self.plan,
            planName=self.plan.label, total=Decimal('100'), createdBy=user,
        )

    def _token(self, user):
        response = self.client.post(
            '/api/auth/login', {'name': user.name, 'password': 'productivity-pass'},
            content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()['token']

    def test_supervisor_sees_all_users(self):
        response = self.client.get(
            '/api/dashboard/productivity',
            HTTP_AUTHORIZATION=f'Bearer {self._token(self.supervisor)}')
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data['scope'], 'general')
        self.assertEqual(data['summary']['registered'], 3)
        self.assertEqual({row['userName'] for row in data['users']},
                         {'agente_prod', 'otro_prod'})

    def test_jefe_comercial_also_sees_general_scope(self):
        jefe = self._user('jefe_prod', 'ventas')
        self._assign(jefe, 'jefe-comercial')
        response = self.client.get(
            '/api/dashboard/productivity',
            HTTP_AUTHORIZATION=f'Bearer {self._token(jefe)}')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['scope'], 'general')

    def test_agent_is_limited_to_own_productivity(self):
        token = self._token(self.agent)
        response = self.client.get(
            '/api/dashboard/productivity',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data['scope'], 'personal')
        self.assertEqual(data['summary']['registered'], 2)
        self.assertEqual({item['registeredBy']['name'] for item in data['items']},
                         {'agente_prod'})

        forbidden = self.client.get(
            f'/api/dashboard/productivity?user_id={self.other.id}',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(forbidden.status_code, 403)

    def test_normal_user_cannot_expand_productivity_period(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        old_sale = self._sale(self.agent, 'PROD-OLD', yesterday)
        Sale.objects.filter(pk=old_sale.pk).update(
            created_at=timezone.now() - timedelta(days=1))
        token = self._token(self.agent)
        response = self.client.get(
            f'/api/dashboard/productivity?from={yesterday.isoformat()}&to={timezone.localdate().isoformat()}',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data['period']['from'], timezone.localdate().isoformat())
        self.assertEqual(data['period']['to'], timezone.localdate().isoformat())
        self.assertEqual(data['summary']['registered'], 2)
        self.assertEqual(len(data['series']), 1)

    def test_normal_user_dashboard_stats_forces_today(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        self._sale(self.agent, 'PROD-STATS-OLD', yesterday)
        token = self._token(self.agent)
        response = self.client.get(
            f'/api/dashboard/stats?from={yesterday.isoformat()}&to={timezone.localdate().isoformat()}',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data['analytics']['period']['from'], timezone.localdate().isoformat())
        self.assertEqual(data['analytics']['period']['to'], timezone.localdate().isoformat())
        self.assertEqual(data['analytics']['series'][0]['movimientos'], 3)

    def test_normal_user_drilldown_forces_today(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        self._sale(self.agent, 'PROD-DETAIL-OLD', yesterday)
        token = self._token(self.agent)
        response = self.client.get(
            f'/api/dashboard/drilldown?indicator=nuevo_contrato&from={yesterday.isoformat()}&to={timezone.localdate().isoformat()}',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()
        self.assertEqual(data['period']['from'], timezone.localdate().isoformat())
        self.assertEqual(data['period']['to'], timezone.localdate().isoformat())
        self.assertEqual(data['total'], 3)
