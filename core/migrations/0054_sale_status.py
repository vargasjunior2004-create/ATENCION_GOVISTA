from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0053_usersession'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='status',
            field=models.CharField(
                blank=True,
                choices=[
                    ('contratado', 'Contratado'),
                    ('recontratado', 'Recontratado'),
                    ('cambiado', 'Cambiado'),
                    ('retirado', 'Retirado'),
                ],
                default=None,
                help_text='Estado comercial derivado del tipo de solicitud; no lo aporta el cliente',
                max_length=12,
                null=True,
            ),
        ),
    ]
