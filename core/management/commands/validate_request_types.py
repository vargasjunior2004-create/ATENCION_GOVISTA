"""Valida la integridad del catalogo de tipos de solicitud."""

from django.core.management.base import BaseCommand, CommandError

from core.models import Sale, TipoSolicitud


EXPECTED = {
    'nuevo_contrato': 'nuevo',
    'cambio_plan': 'cambio_plan',
    'recontratacion': 'nuevo',
    'retiro': 'retiro',
    'adicion': 'adicion',
    'otro': 'simple',
    'traslado_externo': 'traslado',
}


class Command(BaseCommand):
    help = 'Valida el catalogo requestType y detecta ventas con codigos huerfanos.'

    def handle(self, *args, **options):
        catalog = {
            item.code: item for item in TipoSolicitud.objects.all()
        }
        errors = []

        for code, expected_mode in EXPECTED.items():
            item = catalog.get(code)
            if item is None:
                errors.append(f'Falta el tipo requerido: {code}')
            elif item.modo != expected_mode:
                errors.append(
                    f'{code}: modo esperado {expected_mode}, actual {item.modo}')

        orphan_codes = set(
            Sale.objects.exclude(requestType__in=catalog)
            .values_list('requestType', flat=True)
            .distinct()
        )
        for code in sorted(orphan_codes):
            errors.append(f'Venta con requestType sin catalogar: {code!r}')

        inactive_codes = sorted(set(
            Sale.objects.filter(requestType__in=catalog)
            .values_list('requestType', flat=True)
            .distinct()
        ) & {code for code, item in catalog.items() if not item.activo})
        if inactive_codes:
            self.stdout.write(self.style.WARNING(
                'Tipos inactivos con historial: ' + ', '.join(inactive_codes)))

        if errors:
            for error in errors:
                self.stderr.write(self.style.ERROR(error))
            raise CommandError(
                f'Catalogo invalido: {len(errors)} problema(s) encontrado(s)')

        self.stdout.write(self.style.SUCCESS(
            f'Catalogo valido: {len(catalog)} tipos, sin requestType huerfanos.'))
