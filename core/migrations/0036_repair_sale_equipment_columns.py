from django.db import migrations, models


def repair_columns(apps, schema_editor):
    connection = schema_editor.connection
    table = 'core_sale'
    existing = {
        column.name
        for column in connection.introspection.get_table_description(
            connection.cursor(), table)
    }

    if 'equipment_delivered' not in existing:
        schema_editor.add_field(
            apps.get_model('core', 'Sale'),
            models.BooleanField(
                name='equipment_delivered', null=True, blank=True),
        )
    if 'equipment_serial' not in existing:
        schema_editor.add_field(
            apps.get_model('core', 'Sale'),
            models.CharField(
                name='equipment_serial', max_length=255, default='', blank=True),
        )


def reverse_columns(apps, schema_editor):
    Sale = apps.get_model('core', 'Sale')
    connection = schema_editor.connection
    existing = {
        column.name
        for column in connection.introspection.get_table_description(
            connection.cursor(), 'core_sale')
    }
    for field_name in ('equipment_serial', 'equipment_delivered'):
        if field_name in existing:
            schema_editor.remove_field(Sale, Sale._meta.get_field(field_name))


class Migration(migrations.Migration):
    """Repara instalaciones donde 0033 quedó registrada sin alterar core_sale."""

    dependencies = [
        ('core', '0035_inventariomovimiento_confirmed_at_and_more'),
    ]

    operations = [
        migrations.RunPython(repair_columns, reverse_columns),
    ]
