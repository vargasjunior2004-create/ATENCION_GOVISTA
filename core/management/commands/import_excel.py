"""Importa el historico de MOV. CLIENTES del Excel de atencion al cliente
a los modelos: Customer (kardex maestro), Plan (catalogo) y Sale.

Uso:
    python manage.py import_excel --file "ARCHIVO ATENCION AL CLIENTE 2026.xlsx"
    python manage.py import_excel --file <ruta> --dry-run   # solo informa
    python manage.py import_excel --file <ruta> --force     # reimporta kardex ya existentes

Reglas de negocio aplicadas:
  - serviceType se normaliza desde TIPO DE SERVICIO (INTERNET -> internet,
    TV -> tv, combos -> combo).
  - Customer se crea/deduplica por KARDEX (clave natural).
  - El Plan se deduce del PAQUETE del servicio (cambio -> paquete nuevo).
  - requestType, changeReason, planFrom, totalFrom y notes se importan.
  - Para CAMBIO DE PLAN: planFrom/totalFrom = paquete y monto anterior,
    total = MONTO FINAL. Para el resto: total = MONTO INICIAL.
  - CAJERA se mapea a un User existente por nombre normalizado; si no
    coincide, se usa el primer admin.
  - Filas corruptas (fecha invalida o monto negativo) se omiten y se reportan.
"""

from __future__ import annotations

import datetime as _dt
import re
import unicodedata

from django.core.management.base import BaseCommand

from core.models import Customer, Plan, Sale, User

SHEET = 'MOV. CLIENTES'
HEADER_ROW = 6


def normalize(s):
    """Normaliza texto: mayusculas, sin tildes, espacios extra."""
    if s is None:
        return ''
    s = unicodedata.normalize('NFKD', str(s))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', s.upper()).strip()


def parse_fecha(v):
    if isinstance(v, str):
        v = v.strip()
        d = parse_date_iso(v)
        if d:
            return d
        m = re.match(r'(\d{1,2})/(\d{1,2})/(\d{2,4})$', v)
        if m:
            day, mon, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if year < 100:
                year += 2000
            if not 2000 <= year <= 2100:
                return None
            try:
                return _dt.date(year, mon, day)
            except ValueError:
                return None
        return None
    if hasattr(v, 'date'):
        return v.date()
    return None


def parse_date_iso(v):
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', v)
    if m:
        try:
            return _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


SERVICE_TYPE_MAP = [
    ('INTERNET + TV', 'combo'),
    ('INTERNET + TV ANALOGA', 'combo'),
    ('INTERNET + TV DIGITAL', 'combo'),
    ('INTERNET', 'internet'),
    ('TV ANALOGA', 'tv'),
    ('TV DIGITAL', 'tv'),
    ('TV', 'tv'),
    ('COMBO', 'combo'),
]


def to_service_type(tipo):
    t = normalize(tipo)
    if not t:
        return 'internet'
    for k, v in SERVICE_TYPE_MAP:
        if k in t:
            return v
    return 'internet'


REQUEST_TYPE_MAP = [
    ('NUEVO COMTRATO', 'nuevo_contrato'),
    ('NUEVO CONTRATO', 'nuevo_contrato'),
    ('CAMBIO DE PLAN', 'cambio_plan'),
    ('RECONTRATACION', 'recontratacion'),
    ('RETIRO', 'retiro'),
    ('ADICION', 'adicion'),
    ('BAJA TEMPORAL', 'baja_temporal'),
]


def to_request_type(tipo):
    t = normalize(tipo)
    if not t:
        return 'nuevo_contrato'
    for k, v in REQUEST_TYPE_MAP:
        if k in t:
            return v
    return 'otro'


class Command(BaseCommand):
    help = 'Importa el historico de MOV. CLIENTES del Excel.'

    def add_arguments(self, parser):
        parser.add_argument('--file', required=True,
                            help='Ruta del archivo .xlsx')
        parser.add_argument('--dry-run', action='store_true',
                            help='Solo analiza y reporta, no escribe.')
        parser.add_argument('--force', action='store_true',
                            help='Reimporta aunque el kardex ya exista.')

    def handle(self, *args, **options):
        import openpyxl

        path = options['file']
        dry_run = options['dry_run']
        force = options['force']

        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        ws = wb[SHEET]
        rows = [r for r in ws.iter_rows(min_row=HEADER_ROW + 1,
                                        values_only=True)
                if any(v not in (None, '') for v in r)]
        wb.close()
        self.stdout.write(f'Filas con datos en {SHEET}: {len(rows)}')

        existing_codes = set(Sale.objects.values_list('clientCode', flat=True))
        first_run = not existing_codes
        customers = {c.code: c for c in Customer.objects.all()}
        plans = {p.code: p for p in Plan.objects.all()}
        users = list(User.objects.filter(role='admin'))
        fallback_user = users[0] if users else None

        stats = {'ok': 0, 'sin_fecha': 0, 'monto_invalido': 0,
                 'omitido_duplicado': 0, 'clientes': 0}
        errores = []

        for i, r in enumerate(rows, start=HEADER_ROW + 1):
            fecha = r[0]
            kardex = r[1]
            nombre = r[2]
            tipo = r[3]
            solicitud = r[4]
            p_tv = r[5]
            p_int = r[6]
            monto = r[7]
            motivo = r[8]
            p_cambio_tv = r[9]
            p_cambio_int = r[10]
            monto_final = r[11]
            cajera = r[13]
            comentarios = r[14]

            fecha = parse_fecha(fecha)
            if fecha is None or fecha.year < 2000:
                stats['sin_fecha'] += 1
                errores.append((i, 'fecha invalida'))
                continue

            monto = monto if isinstance(monto, (int, float)) else 0
            if monto < 0:
                stats['monto_invalido'] += 1
                errores.append((i, f'monto negativo {monto}'))
                continue

            code = normalize(kardex)
            if not code:
                stats['sin_fecha'] += 1
                continue

            if not force and not first_run and code in existing_codes:
                stats['omitido_duplicado'] += 1
                continue

            stype = to_service_type(tipo)
            rtype = to_request_type(solicitud)

            if rtype == 'cambio_plan':
                paquete = (p_cambio_int if stype == 'internet'
                           else p_cambio_tv if stype == 'tv'
                           else (p_cambio_tv or p_cambio_int))
                plan_from = (p_cambio_tv or p_cambio_int) or ''
                total_from = monto if monto > 0 else None
                total = monto_final if isinstance(monto_final, (int, float)) \
                    and monto_final > 0 else monto
            else:
                paquete = (p_int if stype == 'internet'
                           else p_tv if stype == 'tv'
                           else (p_tv or p_int))
                plan_from = ''
                total_from = None
                total = monto

            paquete = normalize(paquete) or (stype.upper() + '-GEN')

            plan = plans.get(paquete)
            if plan is None:
                plan = Plan(code=paquete, label=paquete,
                            type=stype, speed=None, monthly=total,
                            installation=0)
                if not dry_run:
                    plan.save()
                plans[paquete] = plan

            customer = customers.get(code)
            if customer is None:
                customer = Customer(code=code, name=normalize(nombre))
                if not dry_run:
                    customer.save()
                customers[code] = customer
                stats['clientes'] += 1

            user = None
            if cajera:
                user = next((u for u in User.objects.all()
                             if normalize(u.name) == normalize(cajera)), None)
            if user is None:
                user = fallback_user
            if user is None and not dry_run:
                continue

            if dry_run:
                stats['ok'] += 1
                continue

            Sale.objects.create(
                date=fecha, clientCode=code, clientName=normalize(nombre),
                customer=customer, serviceType=stype, requestType=rtype,
                changeReason=normalize(motivo), planFrom=plan_from,
                totalFrom=total_from, notes=(comentarios or ''),
                plan=plan, total=total, createdBy=user,
            )
            stats['ok'] += 1

        self.stdout.write(
            f"OK: {stats['ok']} | clientes: {stats['clientes']} | "
            f"sin_fecha: {stats['sin_fecha']} | "
            f"monto_invalido: {stats['monto_invalido']} | "
            f"omitido (ya existe): {stats['omitido_duplicado']}")
        if errores[:10]:
            self.stdout.write('Ejemplos de filas omitidas: '
                              + ', '.join(f'R{r}: {m}' for r, m in errores[:10]))
        if dry_run:
            self.stdout.write(self.style.WARNING(
                'Modo --dry-run: no se escribio nada en la base de datos.'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Importacion completada. Ventas: {Sale.objects.count()} | '
                f'Clientes: {Customer.objects.count()} | Planes: {Plan.objects.count()}'))
