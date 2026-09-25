from django.db import migrations


def fix_addition_totals(apps, schema_editor):
    Sale = apps.get_model('core', 'Sale')
    for sale in Sale.objects.filter(requestType='adicion'):
        correct_total = sale.applied_monthly or 0
        if sale.total != correct_total or (sale.applied_installation or 0) != 0:
            sale.total = correct_total
            sale.applied_installation = 0
            sale.save(update_fields=['total', 'applied_installation'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_add_addition_type'),
    ]

    operations = [
        migrations.RunPython(fix_addition_totals, migrations.RunPython.noop),
    ]
