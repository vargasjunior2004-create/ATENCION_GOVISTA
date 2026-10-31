from datetime import date

from django.test import TestCase, Client

from .models import AuditLog, Plan, Sale, User


class AuditLogTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User(name='audit-admin', role='admin')
        self.admin.set_password('audit-pass')
        self.admin.save()
        self.plan = Plan.objects.create(
            code='AUDIT-PLAN', label='Plan auditoria', type='internet',
            monthly=100, installation=50)

    def token(self):
        response = self.client.post(
            '/api/auth/login',
            {'name': self.admin.name, 'password': 'audit-pass'},
            content_type='application/json')
        return response.json()['token']

    def test_sale_creation_creates_minimized_audit_event(self):
        response = self.client.post(
            '/api/sales', {
                'clientCode': 'AUDIT-1', 'clientName': 'CLIENTE AUDIT',
                'serviceType': 'internet', 'requestType': 'nuevo_contrato',
                'planId': self.plan.id,
            }, content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token()}')

        self.assertEqual(response.status_code, 201, response.content)
        event = AuditLog.objects.get(entity='sale', action='created')
        self.assertEqual(event.entity_id, str(response.json()['id']))
        self.assertEqual(event.actor_id, self.admin.id)
        self.assertEqual(event.after['requestType'], 'nuevo_contrato')
        self.assertNotIn('AUDIT-1', str(event.after))
        self.assertNotIn('CLIENTE AUDIT', str(event.after))

    def test_sale_update_creates_before_and_after_versions(self):
        sale = Sale.objects.create(
            date=date.today(), clientCode='AUDIT-2', clientName='CLIENTE',
            serviceType='internet', plan=self.plan, total=150,
            createdBy=self.admin)
        response = self.client.put(
            f'/api/sales/{sale.id}', {'version': 1, 'notes': 'EDITADO'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token()}')

        self.assertEqual(response.status_code, 200, response.content)
        event = AuditLog.objects.get(entity_id=str(sale.id), action='updated')
        self.assertEqual(event.before['version'], 1)
        self.assertEqual(event.after['version'], 2)

    def test_plan_admin_changes_are_audited_without_sensitive_data(self):
        response = self.client.post(
            '/api/plans', {
                'code': 'AUDIT-NEW', 'label': 'Plan nuevo',
                'type': 'internet', 'monthly': '120', 'installation': '0',
            }, content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token()}')
        self.assertEqual(response.status_code, 201, response.content)
        created = AuditLog.objects.get(entity='plan', action='created',
                                       entity_id=str(response.json()['id']))
        self.assertEqual(created.after['code'], 'AUDIT-NEW')

        response = self.client.put(
            f"/api/plans/{response.json()['id']}", {'active': False},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self.token()}')
        self.assertEqual(response.status_code, 200, response.content)
        updated = AuditLog.objects.get(entity='plan', action='updated',
                                       entity_id=created.entity_id)
        self.assertTrue(updated.before['active'])
        self.assertFalse(updated.after['active'])
        self.assertNotIn('password', str(updated.after).lower())
