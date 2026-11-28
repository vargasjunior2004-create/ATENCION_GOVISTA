from django.db import migrations


PERMISSIONS = [
    ('ubicaciones', 'clientes', 'view', 'Consultar ubicaciones de clientes'),
    ('ubicaciones', 'clientes', 'create', 'Registrar ubicaciones de clientes'),
    ('ubicaciones', 'clientes', 'change', 'Modificar ubicaciones de clientes'),
    ('ubicaciones', 'historial', 'view', 'Consultar historial de ubicaciones'),
]


def seed(apps, schema_editor):
    Permission = apps.get_model('core', 'Permission')
    Role = apps.get_model('core', 'Role')
    RolePermission = apps.get_model('core', 'RolePermission')
    permissions = {}
    for module, resource, action, name in PERMISSIONS:
        permission, _ = Permission.objects.get_or_create(
            module=module, resource=resource, action=action,
            defaults={'name': name, 'description': name, 'active': True})
        permissions[f'{module}.{resource}.{action}'] = permission
    role, _ = Role.objects.get_or_create(
        code='tecnico-campo',
        defaults={
            'name': 'Técnico de Campo',
            'description': 'Consulta y registra fotografías y ubicaciones de clientes.',
            'active': True,
            'is_system_role': False,
            'grants_full_access': False,
        })
    for permission in permissions.values():
        RolePermission.objects.get_or_create(role=role, permission=permission)


class Migration(migrations.Migration):
    dependencies = [('core', '0050_customerlocation')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
