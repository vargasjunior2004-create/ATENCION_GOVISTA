from django.test import Client, TestCase

from .models import Permission, Role, RolePermission, User, UserRole


class UserRoleManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = self.create_user('role-admin', 'admin')
        self.login()
        self.jefa = Role.objects.create(
            code='jefa-comercial', name='Jefa Comercial')
        self.caja = Role.objects.create(code='caja-test', name='Caja')

    def create_user(self, name, role):
        user = User.objects.create(name=name, password='', role=role)
        user.set_password('password')
        user.save()
        return user

    def login(self):
        response = self.client.post(
            '/api/auth/login',
            {'name': self.admin.name, 'password': 'password'},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.auth = {
            'HTTP_AUTHORIZATION': f"Bearer {response.json()['token']}",
        }

    def test_create_user_with_selected_rbac_roles(self):
        response = self.client.post(
            '/api/users',
            {
                'name': 'nuevo-usuario',
                'password': 'password',
                'role': 'ventas',
                'roleIds': [self.jefa.id],
            },
            content_type='application/json',
            **self.auth,
        )

        self.assertEqual(response.status_code, 201, response.content)
        user = User.objects.get(name='nuevo-usuario')
        self.assertEqual(user.role, 'ventas')
        self.assertEqual(
            list(user.role_assignments.filter(active=True).values_list(
                'role_id', flat=True)),
            [self.jefa.id],
        )
        self.assertEqual(response.json()['roles'], [{
            'id': self.jefa.id,
            'name': 'Jefa Comercial',
            'is_system_role': False,
        }])

    def test_update_user_replaces_roles_and_preserves_history(self):
        user = self.create_user('user-to-update', 'ventas')
        old_assignment = UserRole.objects.create(
            user=user, role=self.jefa, assigned_by=self.admin)

        response = self.client.put(
            f'/api/users/{user.id}',
            {'roleIds': [self.caja.id]},
            content_type='application/json',
            **self.auth,
        )

        self.assertEqual(response.status_code, 200, response.content)
        old_assignment.refresh_from_db()
        self.assertFalse(old_assignment.active)
        self.assertIsNotNone(old_assignment.revoked_at)
        self.assertEqual(
            list(user.role_assignments.filter(active=True).values_list(
                'role_id', flat=True)),
            [self.caja.id],
        )
        self.assertEqual(response.json()['roles'][0]['name'], 'Caja')

    def test_system_role_cannot_be_assigned_through_user_form(self):
        system_role = Role.objects.get(is_system_role=True)

        response = self.client.post(
            '/api/users',
            {
                'name': 'invalid-user',
                'password': 'password',
                'role': 'ventas',
                'roleIds': [system_role.id],
            },
            content_type='application/json',
            **self.auth,
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(name='invalid-user').exists())

    def test_user_form_requires_at_least_one_role(self):
        response = self.client.post(
            '/api/users',
            {
                'name': 'no-role-user',
                'password': 'password',
                'role': 'ventas',
                'roleIds': [],
            },
            content_type='application/json',
            **self.auth,
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(name='no-role-user').exists())

    def test_login_payload_exposes_assigned_role_permissions(self):
        permission = Permission.objects.get(
            module='commercial_config', action='manage')
        RolePermission.objects.create(role=self.jefa, permission=permission)
        user = self.create_user('jefa-user', 'ventas')
        UserRole.objects.create(user=user, role=self.jefa, assigned_by=self.admin)

        response = self.client.post(
            '/api/auth/login',
            {'name': user.name, 'password': 'password'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        user_data = response.json()['user']
        self.assertEqual(user_data['roles'][0]['name'], 'Jefa Comercial')
        self.assertIn('commercial_config.manage', user_data['permissions'])
        self.assertFalse(user_data['isSystemAdmin'])
