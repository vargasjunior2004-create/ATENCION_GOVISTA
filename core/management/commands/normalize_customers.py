"""Deduplica clientes repetidos (mismo nombre normalizado, distinto kardex)
re-apuntando sus ventas al registro canonico y eliminando los duplicados.

El kardex del cliente no es fiable en el Excel origen: una misma persona
aparece varias veces (p.ej. "13316", "20123-1", "14511" -> PAUL ROGER
NINA PENA). Este comando elige un registro canonico por grupo y fusiona.

Uso:
    python manage.py normalize_customers --dry-run   # muestra el plan
    python manage.py normalize_customers             # aplica
"""

from collections import defaultdict
from django.core.management.base import BaseCommand

from core.models import Customer, Sale

import re
import unicodedata


def normalize(s):
    s = unicodedata.normalize('NFKD', str(s))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', s.upper()).strip()


def sale_count(customer):
    return Sale.objects.filter(customer=customer).count()


def is_clean_code(code):
    return bool(code) and '/' not in code


class Command(BaseCommand):
    help = 'Deduplica clientes repetidos por nombre normalizado.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Solo muestra el plan, no aplica.')
        parser.add_argument('--min-name', type=int, default=3,
                            help='Ignorar nombres mas cortos que esto.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        min_name = options['min_name']

        groups = defaultdict(list)
        for c in Customer.objects.all():
            n = normalize(c.name)
            if len(n) >= min_name:
                groups[n].append(c)

        groups = {k: v for k, v in groups.items() if len(v) > 1}
        self.stdout.write(f'Grupos con clientes repetidos: {len(groups)}')

        merged = 0
        repointed = 0
        for name, members in sorted(groups.items()):
            canonical = max(
                members,
                key=lambda c: (is_clean_code(c.code), sale_count(c), -c.id))
            extras = [m for m in members if m.id != canonical.id]
            for extra in extras:
                n = sale_count(extra)
                if dry_run:
                    self.stdout.write(
                        f'  {extra.code} ({extra.name}) -> '
                        f'{canonical.code}  [{n} ventas]')
                    continue
                if n:
                    Sale.objects.filter(customer=extra).update(
                        customer=canonical, clientCode=canonical.code)
                    repointed += n
                extra.delete()
                merged += 1

        if dry_run:
            self.stdout.write(self.style.WARNING(
                'Dry-run: no se aplico nada.'))
            return

        self.stdout.write(self.style.SUCCESS(
            f'Fusionados {merged} clientes duplicados, '
            f'{repointed} ventas re-apuntadas. '
            f'Clientes totales: {Customer.objects.count()}'))
