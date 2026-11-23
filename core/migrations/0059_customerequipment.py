import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0058_customerservice'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerEquipment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mac_address', models.CharField(db_index=True, max_length=80)),
                ('brand', models.CharField(blank=True, default='', max_length=120)),
                ('model', models.CharField(blank=True, default='', max_length=120)),
                ('equipment_type', models.CharField(blank=True, default='', max_length=120)),
                ('status', models.CharField(blank=True, default='', max_length=40)),
                ('assignment_status', models.CharField(choices=[('pending', 'Pendiente de revisión'), ('verified', 'Verificado'), ('conflict', 'Requiere revisión')], default='pending', max_length=20)),
                ('source', models.CharField(default='softv', max_length=20)),
                ('source_row', models.PositiveIntegerField(blank=True, null=True)),
                ('notes', models.CharField(blank=True, default='', max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('contract', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='equipment_assignments', to='core.contract')),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='equipment_assignments', to='core.customer')),
            ],
            options={
                'ordering': ['-updated_at', '-id'],
                'indexes': [
                    models.Index(fields=['contract', 'assignment_status'], name='core_custom_contrac_1c4ec7_idx'),
                    models.Index(fields=['mac_address', 'assignment_status'], name='core_custom_mac_add_14f7c5_idx'),
                ],
                'constraints': [
                    models.UniqueConstraint(fields=('customer', 'mac_address'), name='unique_customer_equipment_mac'),
                ],
            },
        ),
    ]
