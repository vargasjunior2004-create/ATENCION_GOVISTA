from django.db import migrations


PERMISSIONS = {
    'dashboard': ['view'],
    'comercial': ['view', 'create', 'change', 'delete', 'manage', 'export'],
    'customers': ['view', 'change', 'export'],
    'users': ['view', 'create', 'change', 'delete', 'manage'],
    'roles': ['view', 'create', 'change', 'delete', 'manage'],
    'commercial_config': ['view', 'change', 'manage'],
    'reports': ['view', 'export'],
    'operativa': ['view', 'create', 'change', 'manage'],
    'inventory': ['view', 'create', 'change', 'manage'],
    'complaints': ['view', 'create', 'change', 'manage'],
    'audit': ['view'],
    'temporary_assignments': ['view', 'assign', 'change'],
}

ROLE_PERMISSIONS = {
    'gerente': [
        'dashboard.view', 'comercial.view', 'customers.view',
        'reports.view', 'reports.export', 'operativa.view',
        'inventory.view', 'complaints.view', 'audit.view',
    ],
    'jefe-comercial': [
        'dashboard.view', 'comercial.view', 'comercial.create',
        'comercial.change', 'comercial.export', 'comercial.manage',
        'customers.view', 'customers.change', 'customers.export',
        'commercial_config.view', 'commercial_config.change',
        'commercial_config.manage', 'reports.view', 'reports.export',
        'temporary_assignments.view', 'temporary_assignments.assign',
        'temporary_assignments.change', 'audit.view',
    ],
    'caja': [
        'dashboard.view', 'comercial.view', 'comercial.create',
        'customers.view', 'reports.view', 'reports.export',
    ],
    'call-center': [
        'dashboard.view', 'comercial.view', 'comercial.create',
        'customers.view', 'reports.view', 'reports.export',
    ],
}

ROLE_NAMES = {
    'sistema-admin': ('Administrador de sistemas', True),
    'gerente': ('Gerente', False),
    'jefe-comercial': ('Jefe Comercial', False),
    'caja': ('Atención en caja', False),
    'call-center': ('Call Center', False),
}


def seed(apps, schema_editor):
    Role = apps.get_model('core', 'Role')
    Permission = apps.get_model('core', 'Permission')
    RolePermission = apps.get_model('core', 'RolePermission')
    User = apps.get_model('core', 'User')
    UserRole = apps.get_model('core', 'UserRole')
    TemporaryFunction = apps.get_model('core', 'TemporaryFunction')

    permission_map = {}
    for module, actions in PERMISSIONS.items():
        for action in actions:
            permission, _ = Permission.objects.get_or_create(
                module=module, action=action,
                defaults={'name': f'{module}.{action}'})
            permission_map[f'{module}.{action}'] = permission

    roles = {}
    for code, (name, is_system_role) in ROLE_NAMES.items():
        role, _ = Role.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'is_system_role': is_system_role,
                'active': True,
            })
        roles[code] = role

    for role_code, permission_codes in ROLE_PERMISSIONS.items():
        for permission_code in permission_codes:
            RolePermission.objects.get_or_create(
                role=roles[role_code], permission=permission_map[permission_code])

    TemporaryFunction.objects.get_or_create(
        code='external_seller',
        defaults={
            'name': 'Vendedor externo',
            'description': 'Función temporal para ventas fuera de oficina',
            'active': True,
        })

    for user in User.objects.filter(active=True):
        role_code = 'sistema-admin' if user.role == 'admin' else 'caja'
        UserRole.objects.get_or_create(
            user=user, role=roles[role_code], active=True,
            defaults={'assigned_by': None})


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0039_role_temporaryfunction_permission_rolepermission_and_more'),
    ]

    operations = [migrations.RunPython(seed, noop)]
