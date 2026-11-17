from django.db import migrations, models
import django.db.models.deletion


ROLE_PERMISSIONS = {
    'jefa-operativa': (
        'coverage.view', 'coverage.create', 'coverage.change',
        'coverage.manage',
    ),
    'encargado-red': ('coverage.view', 'coverage.create'),
    'tecnico-uno': ('coverage.view',),
    'tecnico-dos': ('coverage.view',),
}

ROLE_DETAILS = {
    'jefa-operativa': (
        'Jefa Operativa',
        'Administra y habilita barrios del catálogo de cobertura',
    ),
    'encargado-red': (
        'Encargado de Red',
        'Registra barrios nuevos y consulta el estado de sus registros',
    ),
    'tecnico-uno': ('Técnico Uno', 'Consulta las zonas de cobertura'),
    'tecnico-dos': ('Técnico Dos', 'Consulta las zonas de cobertura'),
}


def seed_coverage_rbac(apps, schema_editor):
    database = schema_editor.connection.alias
    Permission = apps.get_model('core', 'Permission')
    Role = apps.get_model('core', 'Role')
    RolePermission = apps.get_model('core', 'RolePermission')

    permission_names = {
        'view': 'Consultar zonas de cobertura',
        'create': 'Registrar zonas de cobertura',
        'change': 'Editar zonas de cobertura',
        'manage': 'Habilitar y desactivar zonas de cobertura',
    }
    permissions = {}
    for action, name in permission_names.items():
        permission, _ = Permission.objects.using(database).get_or_create(
            module='coverage',
            action=action,
            defaults={'name': name},
        )
        permissions[action] = permission

    for code, permission_codes in ROLE_PERMISSIONS.items():
        name, description = ROLE_DETAILS[code]
        role, _ = Role.objects.using(database).get_or_create(
            code=code,
            defaults={
                'name': name,
                'description': description,
                'active': True,
                'is_system_role': False,
            },
        )
        for permission_code in permission_codes:
            action = permission_code.split('.', 1)[1]
            RolePermission.objects.using(database).get_or_create(
                role=role,
                permission=permissions[action],
            )

    view_permission = permissions['view']
    for role in Role.objects.using(database).all():
        RolePermission.objects.using(database).get_or_create(
            role=role,
            permission=view_permission,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0043_coveragezone_google_maps_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='coveragezone',
            name='is_pending',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='coveragezone',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='coverage_zones_created',
                to='core.user',
            ),
        ),
        migrations.RunPython(seed_coverage_rbac, migrations.RunPython.noop),
    ]
