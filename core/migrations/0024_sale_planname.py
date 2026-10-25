from django.db import migrations, models


# Los numeros 0022/0023 pertenecieron al modulo de quejas que se descarto.
# Se deja el hueco para no chocar con bases donde esas migraciones ya
# quedaron registradas antes del rollback.
def backfill_plan_name(apps, schema_editor):
    Sale = apps.get_model('core', 'Sale')
    for sale in Sale.objects.select_related('plan').iterator():
        if not sale.planName:
            sale.planName = sale.plan.label
            sale.save(update_fields=['planName'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_seed_motivos'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='planName',
            field=models.CharField(
                blank=True, default='', max_length=120,
                help_text='Snapshot del nombre del plan al momento del registro'),
        ),
        migrations.RunPython(backfill_plan_name, migrations.RunPython.noop),
    ]
