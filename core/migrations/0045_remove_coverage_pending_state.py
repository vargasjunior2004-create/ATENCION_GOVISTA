from django.db import migrations


ROLE_PERMISSIONS = {
    'jefa-operativa': ('view', 'create', 'change', 'manage'),
    'encargado-red': ('view', 'create'),
    'tecnico-uno': ('view',),
    'tecnico-dos': ('view',),
}


def set_coverage_permissions(apps, schema_editor):
    database = schema_editor.connection.alias
    Permission = apps.get_model('core', 'Permission')
    Role = apps.get_model('core', 'Role')
    RolePermission = apps.get_model('core', 'RolePermission')

    permissions = {
        permission.action: permission
        for permission in Permission.objects.using(database).filter(
            module='coverage')
    }
    RolePermission.objects.using(database).filter(
        permission__module='coverage').delete()

    for role_code, actions in ROLE_PERMISSIONS.items():
        role = Role.objects.using(database).filter(code=role_code).first()
        if role is None:
            continue
        for action in actions:
            permission = permissions.get(action)
            if permission is not None:
                RolePermission.objects.using(database).get_or_create(
                    role=role,
                    permission=permission,
                )


def restore_coverage_permissions(apps, schema_editor):
    database = schema_editor.connection.alias
    Permission = apps.get_model('core', 'Permission')
    Role = apps.get_model('core', 'Role')
    RolePermission = apps.get_model('core', 'RolePermission')
    permissions = {
        permission.action: permission
        for permission in Permission.objects.using(database).filter(
            module='coverage')
    }
    view_permission = permissions.get('view')
    if view_permission is not None:
        for role in Role.objects.using(database).all():
            RolePermission.objects.using(database).get_or_create(
                role=role,
                permission=view_permission,
            )
    for role_code, actions in ROLE_PERMISSIONS.items():
        role = Role.objects.using(database).filter(code=role_code).first()
        if role is None:
            continue
        for action in actions:
            permission = permissions.get(action)
            if permission is not None:
                RolePermission.objects.using(database).get_or_create(
                    role=role,
                    permission=permission,
                )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0044_coverage_zone_registration_rbac'),
    ]

    operations = [
        migrations.RunPython(
            set_coverage_permissions,
            restore_coverage_permissions,
        ),
        migrations.RemoveField(
            model_name='coveragezone',
            name='is_pending',
        ),
    ]
