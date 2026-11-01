from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

from .models import (
    Permission, Role, TemporaryAssignment, TemporaryFunction, User, UserRole,
)


class RbacEndpointTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create(name='rbac-admin', password='', role='admin')
        self.admin.set_password('password')
        self.admin.save()
        self.operator = User.objects.create(name='rbac-operator', password='', role='ventas')
        self.operator.set_password('password')
        self.operator.save()
        caja = Role.objects.get(code='caja')
        UserRole.objects.create(user=self.operator, role=caja)
        login = self.client.post(
            '/api/auth/login', {'name': 'rbac-admin', 'password': 'password'},
            content_type='application/json')
        self.admin_headers = {'HTTP_AUTHORIZATION': f"Bearer {login.json()['token']}"}
        login = self.client.post(
            '/api/auth/login', {'name': 'rbac-operator', 'password': 'password'},
            content_type='application/json')
        self.operator_headers = {'HTTP_AUTHORIZATION': f"Bearer {login.json()['token']}"}

    def test_operator_cannot_read_roles(self):
        response = self.client.get('/api/roles', **self.operator_headers)
        self.assertEqual(response.status_code, 403)

    def test_admin_can_assign_and_finish_external_function(self):
        function = TemporaryFunction.objects.get(code='external_seller')
        starts = timezone.now() + timedelta(hours=1)
        ends = starts + timedelta(hours=4)
        response = self.client.post(
            '/api/temporary-assignments',
            {'user': self.operator.id, 'function': function.id,
             'starts_at': starts.isoformat(), 'ends_at': ends.isoformat()},
            content_type='application/json', **self.admin_headers)
        self.assertEqual(response.status_code, 201)
        assignment_id = response.json()['id']
        response = self.client.patch(
            f'/api/temporary-assignments/{assignment_id}',
            {'status': 'finished'},
            content_type='application/json', **self.admin_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'finished')

    def test_overlapping_external_assignments_are_rejected(self):
        function = TemporaryFunction.objects.get(code='external_seller')
        starts = timezone.now()
        payload = {
            'user': self.operator.id, 'function': function.id,
            'starts_at': starts.isoformat(),
            'ends_at': (starts + timedelta(hours=4)).isoformat(),
        }
        first = self.client.post(
            '/api/temporary-assignments', payload,
            content_type='application/json', **self.admin_headers)
        self.assertEqual(first.status_code, 201)
        second = self.client.post(
            '/api/temporary-assignments', payload,
            content_type='application/json', **self.admin_headers)
        self.assertEqual(second.status_code, 409)
