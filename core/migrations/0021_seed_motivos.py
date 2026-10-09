from django.db import migrations


# Opciones que antes vivian fijas en el formulario (CHANGE_REASONS /
# RETIRO_REASONS). Al pasar a catalogo quedaron sin sembrar, dejando los
# selects vacios. Se restauran aqui, respetando el orden original.
MOTIVOS_INICIALES = [
    ('cambio', 'ECONOMICOS', 10),
    ('cambio', 'AUMENTO DE DISPOSITIVOS', 20),
    ('cambio', 'VIAJE', 30),
    ('cambio', 'POCO USO', 40),
    ('cambio', 'NO UTILIZA EL SERVICIO', 50),
    ('cambio', 'MEJOR CALIDAD', 60),
    ('cambio', 'OTROS', 70),
    ('retiro', 'ECONOMICOS', 10),
    ('retiro', 'CAMBIO A OTRA EMPRESA', 20),
    ('retiro', 'MAL SERVICIO', 30),
    ('retiro', 'TRASLADO', 40),
    ('retiro', 'NO UTILIZA EL SERVICIO', 50),
    ('retiro', 'FUERA DE AREA', 60),
    ('retiro', 'VIAJE', 70),
    ('retiro', 'OTROS', 80),
]


def sembrar_motivos(apps, schema_editor):
    Motivo = apps.get_model('core', 'Motivo')
    for categoria, nombre, orden in MOTIVOS_INICIALES:
        Motivo.objects.update_or_create(
            categoria=categoria,
            nombre=nombre,
            defaults={'orden': orden, 'activo': True},
        )


def quitar_motivos(apps, schema_editor):
    Motivo = apps.get_model('core', 'Motivo')
    Sale = apps.get_model('core', 'Sale')
    for categoria, nombre, _ in MOTIVOS_INICIALES:
        for motivo in Motivo.objects.filter(categoria=categoria, nombre=nombre):
            if not Sale.objects.filter(motivo_id=motivo.id).exists():
                motivo.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_motivo_alter_sale_changereason_sale_motivo'),
    ]

    operations = [
        migrations.RunPython(sembrar_motivos, quitar_motivos),
    ]
