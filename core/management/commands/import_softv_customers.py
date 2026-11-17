"""Carga inicial, idempotente y no destructiva de clientes desde SOFTV.

Por defecto el comando solo analiza. La opción ``--apply`` crea clientes
faltantes por Kardex; nunca actualiza ni elimina clientes existentes.

Uso:
    python manage.py import_softv_customers --file /ruta/datasoftv.xlsx
    python manage.py import_softv_customers --file /ruta/datasoftv.xlsx \
        --report /tmp/softv-import.json
    python manage.py import_softv_customers --file /ruta/datasoftv.xlsx \
        --apply --report /tmp/softv-import.json
"""

import json
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db import close_old_connections

from core.models import Customer
from .inspect_softv_excel import cell, clean, normalize_row


def read_records(path, sheet_name):
    try:
        from openpyxl import load_workbook
    except ImportError as exc:
        raise CommandError('openpyxl no está instalado') from exc

    try:
        workbook = load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:
        raise CommandError(f'No fue posible abrir el Excel: {exc}') from exc

    if sheet_name not in workbook.sheetnames:
        sheets = ', '.join(workbook.sheetnames)
        workbook.close()
        raise CommandError(
            f'La hoja {sheet_name!r} no existe. Hojas disponibles: {sheets}'
        )

    rows = list(workbook[sheet_name].iter_rows(values_only=True))
    workbook.close()
    records = []
    ignored = []
    for row_number, row in enumerate(rows, start=1):
        if not any(value not in (None, '') for value in row):
            continue
        if row_number == 2 and clean(cell(row, 0)).upper() == 'COBIJA':
            ignored.append({'row_number': row_number, 'reason': 'Encabezado'})
            continue
        record = normalize_row(row, row_number)
        if record is None:
            ignored.append({
                'row_number': row_number,
                'reason': 'Fila sin datos utilizables',
            })
            continue
        records.append(record)
    return records, ignored


def build_candidates(records):
    grouped = defaultdict(list)
    ignored = []
    for record in records:
        if record['code']:
            grouped[record['code']].append(record)
        else:
            record['error'] = 'Kardex vacío'
            ignored.append(record)

    candidates = []
    for code, items in sorted(grouped.items()):
        names = sorted({item['name'] for item in items if item['name']})
        phones = sorted({
            phone for item in items for phone in item['phones'] if phone
        })
        services = sorted({
            item['services'] for item in items if item['services']
        })
        candidate = {
            'code': code,
            'rows': [item['row_number'] for item in items],
            'occurrences': len(items),
            'names': names,
            'phones': phones,
            'services': services,
            'name_conflict': len(names) > 1,
            'phone_conflict': len(items) > 1 and len(phones) > 1,
            'error': '',
        }
        if not names:
            candidate['error'] = 'Nombre vacío'
        elif candidate['name_conflict']:
            candidate['error'] = 'Un Kardex tiene varios nombres'
        candidates.append(candidate)
    return candidates, ignored


class Command(BaseCommand):
    help = 'Carga clientes de SOFTV por Kardex sin sobrescribir datos existentes.'

    def add_arguments(self, parser):
        parser.add_argument('--file', required=True, help='Ruta del archivo .xlsx')
        parser.add_argument(
            '--sheet', default='Hoja1',
            help='Hoja de datos (por defecto: Hoja1).',
        )
        parser.add_argument(
            '--apply', action='store_true',
            help='Crea clientes faltantes. Sin esta opción solo analiza.',
        )
        parser.add_argument(
            '--batch-size', type=int, default=250,
            help='Cantidad de clientes por lote al aplicar (por defecto: 250).',
        )
        parser.add_argument('--report', help='Ruta opcional para informe JSON.')

    def handle(self, *args, **options):
        path = Path(options['file'])
        if not path.is_file():
            raise CommandError(f'No existe el archivo: {path}')

        records, ignored = read_records(path, options['sheet'])
        candidates, candidate_ignored = build_candidates(records)
        ignored.extend(candidate_ignored)

        existing = {
            customer.code: customer
            for customer in Customer.objects.all().only(
                'id', 'code', 'name', 'phone'
            )
        }
        report = {
            'file': str(path),
            'sheet': options['sheet'],
            'mode': 'apply' if options['apply'] else 'dry-run',
            'data_rows': len(records),
            'ignored_rows': ignored,
            'candidates': [],
            'counts': {
                'unique_kardex': len(candidates),
                'already_existing': 0,
                'to_create': 0,
                'name_conflicts': 0,
                'phone_conflicts': 0,
                'existing_name_differences': 0,
                'invalid': 0,
                'created': 0,
                'related': 0,
            },
        }

        for candidate in candidates:
            current = existing.get(candidate['code'])
            candidate['existing_customer_id'] = current.id if current else None
            candidate['existing_customer_name'] = current.name if current else ''
            candidate['existing_customer_phone'] = current.phone if current else ''

            if candidate['phone_conflict']:
                report['counts']['phone_conflicts'] += 1
            if candidate['name_conflict']:
                report['counts']['name_conflicts'] += 1
            if candidate['error']:
                report['counts']['invalid'] += 1
                candidate['action'] = 'review'
            elif current:
                report['counts']['already_existing'] += 1
                if clean(current.name).upper() != candidate['names'][0].upper():
                    candidate['action'] = 'review_name_difference'
                    report['counts']['existing_name_differences'] += 1
                else:
                    candidate['action'] = 'related'
                    report['counts']['related'] += 1
            else:
                candidate['action'] = 'create'
                report['counts']['to_create'] += 1
            report['candidates'].append(candidate)

        if options['apply']:
            pending = [
                candidate for candidate in report['candidates']
                if candidate['action'] == 'create'
            ]
            batch_size = max(1, options['batch_size'])
            existing_codes = set(existing)
            for start in range(0, len(pending), batch_size):
                batch = pending[start:start + batch_size]
                close_old_connections()
                objects = []
                for candidate in batch:
                    phone = candidate['phones'][0] if len(
                        candidate['phones']
                    ) == 1 else ''
                    objects.append(Customer(
                        code=candidate['code'],
                        name=candidate['names'][0],
                        phone=phone,
                        status='activo',
                        active=True,
                    ))
                with transaction.atomic():
                    Customer.objects.bulk_create(
                        objects,
                        batch_size=batch_size,
                        ignore_conflicts=True,
                    )
                batch_codes = {candidate['code'] for candidate in batch}
                inserted_codes = set(
                    Customer.objects.filter(code__in=batch_codes)
                    .values_list('code', flat=True)
                )
                report['counts']['created'] += len(
                    inserted_codes - existing_codes)
                existing_codes.update(inserted_codes)
                self.stdout.write(
                    f'Lote aplicado: {min(start + batch_size, len(pending))}/'
                    f'{len(pending)}'
                )
            report['counts']['to_create'] = report['counts']['created']

        report_path = options.get('report')
        if report_path:
            destination = Path(report_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )

        counts = report['counts']
        self.stdout.write(f'Archivo: {path}')
        self.stdout.write(f'Filas analizadas: {report["data_rows"]}')
        self.stdout.write(f'Kardex únicos: {counts["unique_kardex"]}')
        self.stdout.write(f'Ya existentes: {counts["already_existing"]}')
        self.stdout.write(f'Para crear: {counts["to_create"]}')
        self.stdout.write(f'Conflictos de nombre: {counts["name_conflicts"]}')
        self.stdout.write(f'Conflictos de teléfono: {counts["phone_conflicts"]}')
        self.stdout.write(
            f'Diferencias de nombre existentes: '
            f'{counts["existing_name_differences"]}'
        )
        self.stdout.write(f'Casos para revisión: {counts["invalid"]}')
        if options['apply']:
            self.stdout.write(f'Creados: {counts["created"]}')
        else:
            self.stdout.write(
                self.style.WARNING(
                    'Dry-run: no se crearon ni modificaron clientes.'
                )
            )
        if report_path:
            self.stdout.write(f'Informe JSON: {report_path}')
