from django.db import migrations


DEFAULT_CATALOGS = {
    'attention_type': (
        ('consulta', 'Consulta'),
        ('queja', 'Queja'),
        ('reclamo', 'Reclamo'),
        ('pago', 'Registro de pago'),
    ),
    'classification': (
        ('servicio', 'Servicio'),
        ('facturacion', 'Facturación'),
        ('soporte', 'Soporte técnico'),
        ('otro', 'Otro'),
    ),
    'channel': (
        ('mensaje', 'Mensaje'),
        ('oficina', 'Oficina'),
        ('llamada', 'Llamada'),
    ),
    'support_action': (
        ('informado', 'Se informó al cliente'),
        ('reboot', 'Reinicio remoto'),
        ('resync', 'Resincronización'),
        ('cambio-contrasena', 'Cambio de contraseña'),
        ('configuracion-onu', 'Configuración de ONU'),
        ('queja-generada', 'Queja generada'),
        ('otro', 'Otra acción'),
    ),
}


def seed_catalogs(apps, schema_editor):
    catalog_model = apps.get_model('core', 'AtencionCatalogo')
    for catalog_type, entries in DEFAULT_CATALOGS.items():
        for sort_order, (code, name) in enumerate(entries):
            catalog_model.objects.get_or_create(
                catalog_type=catalog_type,
                code=code,
                defaults={'name': name, 'sort_order': sort_order},
            )


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0055_atencioncatalogo_atencion_pagoatendido_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_catalogs, migrations.RunPython.noop),
    ]
