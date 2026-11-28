from django.db import migrations, models


COVERAGE_MAPS = {
    'villa busch': (
        'https://www.google.com/maps/d/u/0/viewer?mid=1wbTe0yQgCet3cFowbPbMejip3njFilKg'
        '&ll=-11.084442928048484%2C-68.77239128169253&z=15'
    ),
    'las isla': (
        'https://www.google.com/maps/d/u/0/viewer?mid=1wbTe0yQgCet3cFowbPbMejip3njFilKg'
        '&ll=-11.042655499999979%2C-68.80124675&z=18'
    ),
    'castanal': (
        'https://www.google.com/maps/d/u/0/viewer?mid=1wbTe0yQgCet3cFowbPbMejip3njFilKg'
        '&ll=-11.037896500000004%2C-68.80360825&z=17'
    ),
    'roberto rojas': (
        'https://www.google.com/maps/d/u/0/viewer?mid=1wbTe0yQgCet3cFowbPbMejip3njFilKg'
        '&ll=-11.031699499999991%2C-68.79058725&z=17'
    ),
    'mototaxi': (
        'https://www.google.com/maps/d/u/0/viewer?mid=1wbTe0yQgCet3cFowbPbMejip3njFilKg'
        '&ll=-11.031502509383234%2C-68.79053900000001&z=17'
    ),
    'paraíso': (
        'https://www.google.com/maps/d/u/0/viewer?mid=1wbTe0yQgCet3cFowbPbMejip3njFilKg'
        '&ll=-11.02388499999998%2C-68.77447225000002&z=16'
    ),
    'mejillones': (
        'https://www.google.com/maps/d/u/0/viewer?mid=1wbTe0yQgCet3cFowbPbMejip3njFilKg'
        '&ll=-11.070286333333337%2C-68.81737650000001&z=17'
    ),
    'gatty ribeiro': (
        'https://www.google.com/maps/d/u/0/viewer?mid=1wbTe0yQgCet3cFowbPbMejip3njFilKg'
        '&ll=-11.03703199999997%2C-68.77884240000002&z=16'
    ),
    'mercado evo morales': (
        'https://www.google.com/maps/d/u/0/viewer?mid=1wbTe0yQgCet3cFowbPbMejip3njFilKg'
        '&ll=-11.048410499999989%2C-68.77346450000002&z=18'
    ),
    'san juan ii': (
        'https://www.google.com/maps/d/u/0/viewer?mid=1wbTe0yQgCet3cFowbPbMejip3njFilKg'
        '&ll=-11.053223714285721%2C-68.776283&z=16'
    ),
    'avaroa': (
        'https://www.google.com/maps/d/u/0/viewer?mid=1wbTe0yQgCet3cFowbPbMejip3njFilKg'
        '&ll=-11.083027999999986%2C-68.79755575&z=16'
    ),
    'barrio monte líbano': (
        'https://www.google.com/maps/d/u/0/viewer?mid=1wbTe0yQgCet3cFowbPbMejip3njFilKg'
        '&ll=-11.090082833333332%2C-68.772644&z=17'
    ),
    'tahuamanu': (
        'https://www.google.com/maps/d/u/0/viewer?mid=1wbTe0yQgCet3cFowbPbMejip3njFilKg'
        '&ll=-11.033353733333334%2C-68.75225113333333&z=17'
    ),
    'terminal': (
        'https://www.google.com/maps/d/u/0/viewer?mid=1wbTe0yQgCet3cFowbPbMejip3njFilKg'
        '&ll=-11.062182500000002%2C-68.789622625&z=17'
    ),
    'el portugués': (
        'https://www.google.com/maps/d/u/0/viewer?mid=1wbTe0yQgCet3cFowbPbMejip3njFilKg'
        '&ll=-11.0179885%2C-68.78190966666666&z=17'
    ),
}


def set_existing_zone_map_urls(apps, schema_editor):
    CoverageZone = apps.get_model('core', 'CoverageZone')
    manager = CoverageZone.objects.using(schema_editor.connection.alias)
    missing = []

    for normalized_name, url in COVERAGE_MAPS.items():
        zone = manager.filter(normalized_name=normalized_name).first()
        if zone is None:
            missing.append(normalized_name)
            continue
        if not zone.google_maps_url:
            manager.filter(pk=zone.pk, google_maps_url='').update(
                google_maps_url=url)

    if missing:
        raise RuntimeError(
            'No se encontraron zonas existentes para asociar URLs de cobertura: '
            + ', '.join(missing))


def clear_migrated_zone_map_urls(apps, schema_editor):
    CoverageZone = apps.get_model('core', 'CoverageZone')
    manager = CoverageZone.objects.using(schema_editor.connection.alias)
    for normalized_name, url in COVERAGE_MAPS.items():
        manager.filter(
            normalized_name=normalized_name,
            google_maps_url=url,
        ).update(google_maps_url='')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0042_coveragezone_sale_coverage_zone'),
    ]

    operations = [
        migrations.AddField(
            model_name='coveragezone',
            name='google_maps_url',
            field=models.URLField(blank=True, default='', max_length=500),
        ),
        migrations.RunPython(
            set_existing_zone_map_urls,
            clear_migrated_zone_map_urls,
        ),
    ]
