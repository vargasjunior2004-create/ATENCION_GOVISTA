"""Completa relaciones Customer de ventas históricas sin borrar información.

Uso seguro:
    python manage.py backfill_customers              # solo diagnóstico
    python manage.py backfill_customers --apply      # aplica vínculos/altas

El comando nunca fusiona clientes por nombre ni modifica el texto histórico
de una venta. Si encuentra un código con nombres incompatibles, lo reporta
para revisión manual.
"""

from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Customer, Sale


class Command(BaseCommand):
    help = 'Completa clientes faltantes a partir de solicitudes históricas.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help='Aplica altas y relaciones; sin esta opción solo informa.')

    def handle(self, *args, **options):
        apply = options['apply']
        sales = Sale.objects.filter(customer__isnull=True).exclude(clientCode='')
        existing = {
            customer.code: customer
            for customer in Customer.objects.all()
        }
        names_by_code = defaultdict(set)
        for sale in sales.iterator():
            names_by_code[sale.clientCode].add(sale.clientName.strip())

        missing = []
        conflicts = []
        linkable = []
        for code, names in sorted(names_by_code.items()):
            customer = existing.get(code)
            if customer is None:
                missing.append((code, sorted(names)[0] if names else code))
                continue
            if names and customer.name.strip() not in names:
                conflicts.append((code, customer.name, sorted(names)))
            else:
                linkable.append(customer)

        self.stdout.write(f'Ventas sin cliente asociado: {sales.count()}')
        self.stdout.write(f'Clientes nuevos posibles: {len(missing)}')
        self.stdout.write(f'Clientes vinculables: {len(linkable)}')
        self.stdout.write(f'Conflictos para revisión manual: {len(conflicts)}')
        for code, current, historical in conflicts[:20]:
            self.stdout.write(
                self.style.WARNING(
                    f'  {code}: cliente={current!r}; ventas={historical!r}'))

        if not apply:
            self.stdout.write(self.style.WARNING(
                'Dry-run: no se modificaron clientes ni ventas.'))
            return

        created = 0
        linked = 0
        with transaction.atomic():
            for code, name in missing:
                customer = Customer.objects.create(code=code, name=name)
                existing[code] = customer
                created += 1
            for sale in sales.select_related('customer').iterator():
                customer = existing.get(sale.clientCode)
                if customer is None:
                    continue
                if customer.name.strip() != sale.clientName.strip():
                    continue
                Sale.objects.filter(pk=sale.pk, customer__isnull=True).update(
                    customer=customer)
                linked += 1

        self.stdout.write(self.style.SUCCESS(
            f'Aplicado: {created} clientes creados, {linked} ventas vinculadas.'))
