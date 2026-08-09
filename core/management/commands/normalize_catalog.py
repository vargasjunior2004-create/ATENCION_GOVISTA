"""Normaliza el catalogo de planes: conserva SOLO los planes vigentes
(deducidos de LISTAS + paquetes realmente vendidos en 2025-2026), re-apunta
las ventas historicas de planes viejos a su equivalente actual y elimina
los planes legacy (ej. "30 M", "SERVICIO BASICO 1", genericos GEN).

Uso:
    python manage.py normalize_catalog --dry-run   # muestra el plan
    python manage.py normalize_catalog             # aplica
"""

import re
from collections import Counter

from django.core.management.base import BaseCommand

from core.models import Plan, Sale

VERSION_SUFFIX = re.compile(r'\(FEB25\)$|\(JUL24\)$|\([0-9]{4}\)$')

# Lista de precios (Bs/mes) deducida de LISTAS + analisis de montos reales.
PRICES = {
    'GO-30(JUL24)': 90, 'GO-40(JUL24)': 130, 'GO-50(JUL24)': 145,
    'GO-60(FEB25)': 230, 'GO-90(JUL24)': 175, 'GO-120(JUL24)': 190,
    'GO-200(FEB25)': 290, 'GO-300(JUL24)': 260, 'GO-400(FEB25)': 360,
    'GoBasic': 230, 'GoStandard': 290, 'GoPremium': 360,
    'GOINT-30': 515, 'GOINT-50': 562, 'GOINT-80': 810, 'GOINT-140': 1487,
    'GOEMP-40': 2260,
    'TV-120': 170, 'TV DIGITAL FULL HD FTTH(GOHD)': 180, 'COMERCIAL': 900,
    'GOTV-120': 300, 'GOTV-120(FEB25)': 300,
    'GOTV-121': 300, 'GOTV-122': 300, 'GOTV-123': 300, 'GOTV-124': 300,
    'GOTV-125': 300, 'GOTV-60(JUL24)': 230, 'GOTV-300(FEB25)': 350,
    'GOTV-400(JUL24)': 260, 'GOTV-500(FEB25)': 470,
    'GoDuoBasic': 300, 'GoDuoGamer': 350,
}

# Planes vigentes: codigo -> (label, tipo). Se marca activo=True.
CURRENT = {
    # Internet residencial
    'GO-30(JUL24)': ('GO-30', 'internet'),
    'GO-40(JUL24)': ('GO-40', 'internet'),
    'GO-50(JUL24)': ('GO-50', 'internet'),
    'GO-60(FEB25)': ('GO-60', 'internet'),
    'GO-90(JUL24)': ('GO-90', 'internet'),
    'GO-120(JUL24)': ('GO-120', 'internet'),
    'GO-200(FEB25)': ('GO-200', 'internet'),
    'GO-300(JUL24)': ('GO-300', 'internet'),
    'GO-400(FEB25)': ('GO-400', 'internet'),
    'GoBasic': ('GoBasic', 'internet'),
    'GoStandard': ('GoStandard', 'internet'),
    'GoPremium': ('GoPremium', 'internet'),
    # Internet empresarial / GOINT
    'GOINT-30': ('GOINT-30', 'internet'),
    'GOINT-50': ('GOINT-50', 'internet'),
    'GOINT-80': ('GOINT-80', 'internet'),
    'GOINT-140': ('GOINT-140', 'internet'),
    'GOEMP-40': ('GOEMP-40', 'internet'),
    # TV
    'TV-120': ('TV-120', 'tv'),
    'TV DIGITAL FULL HD FTTH(GOHD)': ('GOHD TV Digital Full HD', 'tv'),
    'COMERCIAL': ('TV Comercial', 'tv'),
    # Combos
    'GOTV-120': ('GOTV-120', 'combo'),
    'GOTV-120(FEB25)': ('GOTV-120 (FEB25)', 'combo'),
    'GOTV-121': ('GOTV-121', 'combo'),
    'GOTV-122': ('GOTV-122', 'combo'),
    'GOTV-123': ('GOTV-123', 'combo'),
    'GOTV-124': ('GOTV-124', 'combo'),
    'GOTV-125': ('GOTV-125', 'combo'),
    'GOTV-60(JUL24)': ('GOTV-60 (JUL24)', 'combo'),
    'GOTV-300(FEB25)': ('GOTV-300 (FEB25)', 'combo'),
    'GOTV-400(JUL24)': ('GOTV-400 (JUL24)', 'combo'),
    'GOTV-500(FEB25)': ('GOTV-500 (FEB25)', 'combo'),
    'GoDuoBasic': ('GoDuoBasic', 'combo'),
    'GoDuoGamer': ('GoDuoGamer', 'combo'),
}

# Planes legacy -> plan vigente al que re-apuntar sus ventas.
LEGACY_MAP = {
    '25 M': 'GO-30(JUL24)',
    '25M': 'GO-30(JUL24)',
    '30 M': 'GO-120(JUL24)',
    '35 M': 'GO-40(JUL24)',
    '40 M': 'GO-40(JUL24)',
    '45 M': 'GO-50(JUL24)',
    '50 M': 'GO-60(FEB25)',
    '65 M': 'GO-90(JUL24)',
    '70 M': 'GO-300(JUL24)',
    '80 M': 'GO-400(FEB25)',
    '90 M': 'GO-400(FEB25)',
    '130 M': 'GO-300(JUL24)',
    '140 M': 'GO-300(JUL24)',
    'SERVICIO BASICO 1': 'TV-120',
    'SERVICIO BASICO 2': 'TV-120',
    'BASICO SD': 'TV-120',
    'GOHFC': 'TV-120',
    'FULLHD-HFC': 'TV-120',
    'NO APLICA': 'GOTV-120(FEB25)',
    'INTERNET-GEN': 'GO-60(FEB25)',
    'COMBO-GEN': 'GOTV-120(FEB25)',
    'TV-GEN': 'TV-120',
}


class Command(BaseCommand):
    help = 'Normaliza el catalogo de planes (solo vigentes).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Solo muestra el plan, no aplica.')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        plans = {p.code: p for p in Plan.objects.all()}
        by_upper = {c.upper(): p for c, p in plans.items()}

        def canonical_plan(code):
            plan = plans.get(code)
            if plan is not None:
                return plan
            upper = code.upper()
            existing = by_upper.get(upper)
            if existing is None:
                return None
            if existing.code != code and not dry_run:
                if code in plans:  # colision, borrar el vacio
                    plans[code].delete()
                old_code = existing.code
                existing.code = code
                existing.save()
                plans.pop(old_code, None)
                by_upper[upper] = existing
                plans[code] = existing
            return existing

        for code, (label, ptype) in CURRENT.items():
            plan = canonical_plan(code)
            if plan is None:
                plan = Plan(code=code, label=label, type=ptype,
                            monthly=0, installation=0)
                plans[code] = plan
            else:
                plan.label = label
                plan.type = ptype
                plan.active = True

        # Marcas como legacy los planes superados por una version mas nueva
        # (misma base de codigo, p.ej. "GOTV-120" vs "GOTV-120(FEB25)").
        # El plan de la version anterior queda disponible solo para retiros.
        for a in list(plans.values()):
            if a.pk is None:
                continue
            base_a = VERSION_SUFFIX.sub('', a.code)
            has_twin = any(
                p is not a and p.pk is not None
                and VERSION_SUFFIX.sub('', p.code) == base_a
                for p in plans.values())
            if not has_twin or VERSION_SUFFIX.search(a.code):
                continue
            if dry_run:
                self.stdout.write(
                    f'Legacy: "{a.code}" es la version anterior de '
                    f'"{base_a}"')
            else:
                a.legacy = True

        # Precio de referencia: moda de los montos reales vendidos por plan
        for code, plan in plans.items():
            if plan.pk is None:
                continue
            sales_totals = Sale.objects.filter(plan=plan).values_list(
                'total', flat=True)
            amounts = [float(t) for t in sales_totals if t > 0]
            if amounts:
                moda = Counter(amounts).most_common(1)[0][0]
                plan.monthly = moda

        # Precio por defecto para planes sin ventas
        for code, plan in list(plans.items()):
            if plan.pk is None:
                continue
            price = PRICES.get(code)
            if price is not None:
                plan.monthly = price

        # Re-apuntar ventas de planes legacy y marcarlos para borrar
        to_delete = []
        for legacy, current_code in LEGACY_MAP.items():
            legacy_plan = plans.get(legacy)
            if legacy_plan is None:
                continue
            target = plans.get(current_code)
            if target is None or legacy_plan.id == target.id:
                continue
            if target.pk is None and not dry_run:
                target.save()
                plans[current_code] = target
            count = Sale.objects.filter(plan=legacy_plan).count()
            if count:
                if not dry_run:
                    Sale.objects.filter(plan=legacy_plan).update(plan=target)
                self.stdout.write(
                    f'Re-apuntadas {count} ventas de "{legacy}" -> '
                    f'"{current_code}"')
            to_delete.append(legacy_plan)

        if dry_run:
            self.stdout.write(self.style.WARNING(
                'Dry-run: no se aplico nada. Planes a borrar: '
                f'{len(to_delete)}'))
            for p in to_delete:
                self.stdout.write(f'  - {p.code}')
            return

        for plan in to_delete:
            plan.delete()

        for code, plan in plans.items():
            if code in CURRENT:
                plan.save()

        self.stdout.write(self.style.SUCCESS(
            f'Catalogo normalizado. Planes activos: '
            f'{Plan.objects.filter(active=True).count()} | '
            f'total planes: {Plan.objects.count()}'))
