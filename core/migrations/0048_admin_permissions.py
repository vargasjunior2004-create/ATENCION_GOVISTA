from django.db import migrations


PERMISSIONS = [
    # module, resource, action, name, reserved
    ('sistema', 'acceso', 'view', 'Acceder a Administración del Sistema', False),
    ('usuarios', 'accounts', 'view', 'Consultar cuentas', False),
    ('usuarios', 'accounts', 'create', 'Crear cuentas', True),
    ('usuarios', 'accounts', 'change', 'Modificar cuentas', True),
    ('usuarios', 'accounts', 'delete', 'Desactivar cuentas', True),
    ('usuarios', 'accounts', 'reset_password', 'Restablecer contraseñas', True),
    ('usuarios', 'sessions', 'view', 'Consultar sesiones', False),
    ('usuarios', 'sessions', 'revoke', 'Revocar sesiones', True),
    ('usuarios', 'temporary', 'view', 'Consultar asignaciones temporales', False),
    ('usuarios', 'temporary', 'assign', 'Asignar funciones temporales', True),
    ('usuarios', 'temporary', 'change', 'Modificar funciones temporales', True),
    ('roles', 'roles', 'view', 'Consultar roles', False),
    ('roles', 'roles', 'create', 'Crear roles personalizados', True),
    ('roles', 'roles', 'change', 'Modificar roles personalizados', True),
    ('roles', 'roles', 'delete', 'Desactivar roles personalizados', True),
    ('roles', 'roles', 'manage', 'Administrar roles', True),
    ('roles', 'permisos', 'view', 'Consultar matriz de permisos', False),
    ('roles', 'permisos', 'manage', 'Administrar matriz de permisos', True),
    ('roles', 'system_roles', 'assign', 'Asignar roles protegidos', True),
    ('auditoria', 'eventos', 'view', 'Consultar auditoría', False),
    ('auditoria', 'eventos', 'export', 'Exportar auditoría', True),
    ('respaldos', 'backups', 'view', 'Consultar respaldos', False),
    ('respaldos', 'backups', 'create', 'Generar respaldos', True),
    ('respaldos', 'backups', 'download', 'Descargar respaldos', True),
    ('respaldos', 'backups', 'delete', 'Eliminar respaldos', True),
    ('respaldos', 'backups', 'verify', 'Verificar respaldos', True),
    ('respaldos', 'schedules', 'manage', 'Programar respaldos', True),
    ('respaldos', 'restores', 'view', 'Consultar restauraciones', False),
    ('respaldos', 'restores', 'request', 'Solicitar restauraciones', True),
    ('respaldos', 'restores', 'approve', 'Aprobar restauraciones', True),
    ('respaldos', 'restores', 'execute', 'Ejecutar restauraciones', True),
    ('seguridad', 'politicas', 'view', 'Consultar política de seguridad', False),
    ('seguridad', 'politicas', 'manage', 'Administrar política de seguridad', True),
    ('seguridad', 'sessions', 'view', 'Consultar sesiones de seguridad', False),
    ('seguridad', 'sessions', 'revoke', 'Revocar sesiones de seguridad', True),
    ('sistema', 'configuracion', 'view', 'Consultar configuración general', False),
    ('sistema', 'configuracion', 'manage', 'Administrar configuración general', True),
]


def seed_admin_permissions(apps, schema_editor):
    Permission = apps.get_model('core', 'Permission')
    Role = apps.get_model('core', 'Role')
    RolePermission = apps.get_model('core', 'RolePermission')

    created = {}
    for order, (module, resource, action, name, reserved) in enumerate(PERMISSIONS):
        permission, _ = Permission.objects.get_or_create(
            module=module, resource=resource, action=action,
            defaults={
                'name': name,
                'description': name,
                'active': True,
                'is_reserved': reserved,
                'sort_order': order,
            })
        updates = []
        if permission.name != name:
            permission.name = name
            updates.append('name')
        if permission.is_reserved != reserved:
            permission.is_reserved = reserved
            updates.append('is_reserved')
        if permission.sort_order != order:
            permission.sort_order = order
            updates.append('sort_order')
        if updates:
            permission.save(update_fields=updates)
        created[f'{module}.{resource}.{action}'] = permission

    # Quienes ya podían ver auditoría conservan ese acceso en el módulo
    # nuevo, y además pueden entrar a Administración del Sistema.
    audit_old = Permission.objects.filter(
        module='audit', action='view').first()
    if audit_old:
        role_ids = RolePermission.objects.filter(
            permission=audit_old).values_list('role_id', flat=True)
        for role in Role.objects.filter(id__in=role_ids, active=True):
            RolePermission.objects.get_or_create(
                role=role, permission=created['auditoria.eventos.view'])
            RolePermission.objects.get_or_create(
                role=role, permission=created['sistema.acceso.view'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0047_admin_security_foundation'),
    ]

    operations = [
        migrations.RunPython(seed_admin_permissions, noop),
    ]
