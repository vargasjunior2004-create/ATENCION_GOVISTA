from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('core', '0049_equipment_recovery_status')]

    operations = [
        migrations.CreateModel(
            name='CustomerLocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('photo_path', models.CharField(max_length=500)),
                ('latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('accuracy_meters', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('captured_at', models.DateTimeField(blank=True, null=True)),
                ('maps_url', models.URLField(blank=True, default='', max_length=1000)),
                ('source', models.CharField(choices=[('gps', 'GPS'), ('maps_url', 'URL de Google Maps')], max_length=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='customer_locations_created', to='core.user')),
                ('customer', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='location', to='core.customer')),
                ('updated_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='customer_locations_updated', to='core.user')),
            ],
            options={'indexes': [models.Index(fields=['customer', 'updated_at'], name='core_custom_custome_abcf71_idx'), models.Index(fields=['updated_by', 'updated_at'], name='core_custom_updated_599e24_idx')]},
        ),
        migrations.CreateModel(
            name='CustomerLocationHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('change_type', models.CharField(choices=[('created', 'Creación'), ('updated', 'Actualización')], max_length=12)),
                ('previous_photo_path', models.CharField(blank=True, default='', max_length=500)),
                ('new_photo_path', models.CharField(max_length=500)),
                ('previous_latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('previous_longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('previous_accuracy_meters', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('previous_maps_url', models.URLField(blank=True, default='', max_length=1000)),
                ('previous_source', models.CharField(blank=True, default='', max_length=12)),
                ('new_latitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('new_longitude', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('new_accuracy_meters', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('new_maps_url', models.URLField(blank=True, default='', max_length=1000)),
                ('new_source', models.CharField(max_length=12)),
                ('changed_at', models.DateTimeField(auto_now_add=True)),
                ('changed_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='customer_location_changes', to='core.user')),
                ('location', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='history', to='core.customerlocation')),
            ],
            options={'ordering': ['-changed_at', '-id'], 'indexes': [models.Index(fields=['location', 'changed_at'], name='core_custom_locatio_bc0ee0_idx'), models.Index(fields=['changed_by', 'changed_at'], name='core_custom_changed_be3a21_idx')]},
        ),
    ]
