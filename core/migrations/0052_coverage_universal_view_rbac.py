from django.db import migrations


AUTHORIZED_ROLES = {
    'gerente',
    'jefe-comercial',
    'jefa-operativa',
    'jefe-tecnico',
}


def configure_coverage_rbac(apps, schema_editor):
    Permission = apps.get_model('core', 'Permission')
    Role = apps.get_model('core', 'Role')
    RolePermission = apps.get_model('core', 'RolePermission')

    permissions = {
        item.action: item
        for item in Permission.objects.using(schema_editor.connection.alias).filter(
            module='coverage', active=True)
    }

    # La consulta se autoriza por autenticación en la API, no por una copia
    # de coverage.view asignada a cada rol. La administración sí conserva
    # el RBAC granular existente.
    RolePermission.objects.using(schema_editor.connection.alias).filter(
        permission__module='coverage').delete()

    for role in Role.objects.using(schema_editor.connection.alias).filter(
            code__in=AUTHORIZED_ROLES, active=True):
        for action in ('view', 'create', 'change', 'manage'):
            permission = permissions.get(action)
            if permission is not None:
                RolePermission.objects.using(schema_editor.connection.alias).get_or_create(
                    role=role, permission=permission)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0051_seed_customer_location_rbac'),
    ]

    operations = [
        migrations.RunPython(configure_coverage_rbac, migrations.RunPython.noop),
    ]
