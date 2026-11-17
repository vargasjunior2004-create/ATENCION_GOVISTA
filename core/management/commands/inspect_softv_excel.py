"""Inspecciona una exportación de SOFTV sin modificar la base de datos.

El archivo recibido puede contener varios bloques con columnas distintas. Este
comando normaliza esos bloques únicamente en memoria, agrupa por Kardex y
compara los clientes encontrados con Customer.

Uso:
    python manage.py inspect_softv_excel --file /ruta/datasoftv.xlsx
    python manage.py inspect_softv_excel --file /ruta/datasoftv.xlsx \
        --report /tmp/softv-inspection.json
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core.models import Customer


def clean(value):
    if value is None:
        return ''
    return ' '.join(str(value).strip().split())


def cell(row, index):
    return row[index] if index < len(row) else None


def last_nonempty_column(row):
    positions = [
        index for index, value in enumerate(row, start=1)
        if value not in (None, '')
    ]
    return max(positions, default=0)


def normalize_row(row, row_number):
    """Devuelve un registro común para los bloques detectados en SOFTV."""
    last_column = last_nonempty_column(row)
    if last_column <= 1:
        return None

    # Bloque completo: kardex, nombre, periodo, año, servicios, teléfonos,
    # ciclo/empresa, domicilio y empresa.
    if last_column == 10:
        values = {
            'code': clean(cell(row, 0)),
            'name': clean(cell(row, 1)),
            'period': clean(cell(row, 2)),
            'year': clean(cell(row, 3)),
            'services': clean(cell(row, 4)),
            'services_raw': str(cell(row, 4)).strip() if cell(row, 4) is not None else '',
            'phones': [clean(cell(row, 5)), clean(cell(row, 6))],
            'collection_period': clean(cell(row, 7)),
            'address': clean(cell(row, 8)),
            'company': clean(cell(row, 9)),
        }
        block = 'full'
    # Bloque con periodo/año y sin domicilio.
    elif last_column == 9:
        values = {
            'code': clean(cell(row, 0)),
            'name': clean(cell(row, 1)),
            'period': clean(cell(row, 2)),
            'year': clean(cell(row, 3)),
            'services': clean(cell(row, 4)),
            'services_raw': str(cell(row, 4)).strip() if cell(row, 4) is not None else '',
            'phones': [clean(cell(row, 5)), clean(cell(row, 6))],
            'collection_period': clean(cell(row, 7)),
            'address': '',
            'company': clean(cell(row, 8)),
        }
        block = 'period_without_address'
    # Bloque compacto: kardex, nombre, servicios, teléfonos, ciclo y empresa.
    elif last_column == 7:
        values = {
            'code': clean(cell(row, 0)),
            'name': clean(cell(row, 1)),
            'period': '',
            'year': '',
            'services': clean(cell(row, 2)),
            'services_raw': str(cell(row, 2)).strip() if cell(row, 2) is not None else '',
            'phones': [clean(cell(row, 3)), clean(cell(row, 4))],
            'collection_period': clean(cell(row, 5)),
            'address': '',
            'company': clean(cell(row, 6)),
        }
        block = 'compact'
    else:
        return {
            'row_number': row_number,
            'block': f'unsupported_{last_column}_columns',
            'code': clean(cell(row, 0)),
            'name': clean(cell(row, 1)),
            'services': clean(cell(row, 2)),
            'phones': [],
            'address': '',
            'company': '',
            'error': 'Estructura de columnas no reconocida',
        }

    values['row_number'] = row_number
    values['block'] = block
    values['phones'] = sorted({
        phone for phone in values['phones'] if phone and phone not in {'0', '0.0'}
    })
    return values


class Command(BaseCommand):
    help = 'Inspecciona un Excel de SOFTV y compara Kardex con Customer.'

    def add_arguments(self, parser):
        parser.add_argument('--file', required=True, help='Ruta del archivo .xlsx')
        parser.add_argument(
            '--sheet', default='Hoja1',
            help='Nombre de la hoja que contiene los datos (por defecto: Hoja1).',
        )
        parser.add_argument(
            '--report',
            help='Ruta opcional para guardar el informe JSON.',
        )

    def handle(self, *args, **options):
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise CommandError('openpyxl no está instalado') from exc

        path = Path(options['file'])
        if not path.is_file():
            raise CommandError(f'No existe el archivo: {path}')

        try:
            workbook = load_workbook(path, read_only=True, data_only=True)
        except Exception as exc:
            raise CommandError(f'No fue posible abrir el Excel: {exc}') from exc

        sheet_name = options['sheet']
        if sheet_name not in workbook.sheetnames:
            workbook.close()
            raise CommandError(
                f'La hoja {sheet_name!r} no existe. '
                f'Hojas disponibles: {", ".join(workbook.sheetnames)}'
            )

        worksheet = workbook[sheet_name]
        workbook_sheets = list(workbook.sheetnames)
        rows = list(worksheet.iter_rows(values_only=True))
        workbook.close()

        records = []
        ignored_rows = []
        for row_number, row in enumerate(rows, start=1):
            if not any(value not in (None, '') for value in row):
                continue
            if row_number == 2 and clean(cell(row, 0)).upper() == 'COBIJA':
                ignored_rows.append({
                    'row_number': row_number,
                    'reason': 'Encabezado de ubicación',
                })
                continue
            record = normalize_row(row, row_number)
            if record is None:
                ignored_rows.append({
                    'row_number': row_number,
                    'reason': 'Fila sin datos utilizables',
                })
                continue
            records.append(record)

        grouped = defaultdict(list)
        for record in records:
            if record['code']:
                grouped[record['code']].append(record)
            else:
                record['error'] = 'Kardex vacío'
                ignored_rows.append(record)

        existing = {
            customer.code: customer
            for customer in Customer.objects.all().only('id', 'code', 'name', 'phone')
        }

        customers = []
        for code, items in sorted(grouped.items()):
            names = sorted({item['name'] for item in items if item['name']})
            services = sorted({item['services'] for item in items if item['services']})
            phones = sorted({
                phone for item in items for phone in item['phones']
                if phone
            })
            addresses = sorted({
                item['address'] for item in items if item['address']
            })
            customer = existing.get(code)
            customers.append({
                'code': code,
                'rows': [item['row_number'] for item in items],
                'occurrences': len(items),
                'names': names,
                'services': services,
                'phones': phones,
                'addresses': addresses,
                'blocks': sorted({item['block'] for item in items}),
                'existing_customer_id': customer.id if customer else None,
                'existing_customer_name': customer.name if customer else '',
                'existing_customer_phone': customer.phone if customer else '',
                'name_conflict': len(names) > 1,
                'service_count': len(services),
                # Un cliente puede tener dos teléfonos en una misma fila.
                # Solo se reportan variantes telefónicas para Kardex
                # repetidos; no se bloquea ni se descarta ningún teléfono.
                'phone_conflict': len(items) > 1 and len(phones) > 1,
                'phone_count': len(phones),
            })

        report = {
            'file': str(path),
            'sheet': sheet_name,
            'workbook_sheets': workbook_sheets,
            'total_rows_read': len(rows),
            'data_rows': len(records),
            'ignored_rows': ignored_rows,
            'block_counts': dict(Counter(record['block'] for record in records)),
            'unique_kardex': len(customers),
            'repeated_kardex': sum(
                1 for customer in customers if customer['occurrences'] > 1
            ),
            'rows_for_repeated_kardex': sum(
                customer['occurrences']
                for customer in customers if customer['occurrences'] > 1
            ),
            'existing_kardex': sum(
                1 for customer in customers
                if customer['existing_customer_id'] is not None
            ),
            'new_kardex': sum(
                1 for customer in customers
                if customer['existing_customer_id'] is None
            ),
            'name_conflicts': sum(
                1 for customer in customers if customer['name_conflict']
            ),
            'phone_conflicts': sum(
                1 for customer in customers if customer['phone_conflict']
            ),
            'customers': customers,
        }

        report_path = options.get('report')
        if report_path:
            destination = Path(report_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )

        self.stdout.write(f'Archivo: {path}')
        self.stdout.write(f'Hoja: {sheet_name}')
        self.stdout.write(f'Filas leídas: {len(rows)}')
        self.stdout.write(f'Filas de datos: {len(records)}')
        self.stdout.write(f'Kardex únicos: {len(customers)}')
        self.stdout.write(
            f'Kardex repetidos: {report["repeated_kardex"]} '
            f'({report["rows_for_repeated_kardex"]} filas)'
        )
        self.stdout.write(f'Kardex ya existentes: {report["existing_kardex"]}')
        self.stdout.write(f'Kardex nuevos posibles: {report["new_kardex"]}')
        self.stdout.write(f'Conflictos de nombre: {report["name_conflicts"]}')
        self.stdout.write(f'Conflictos de teléfono: {report["phone_conflicts"]}')
        self.stdout.write(f'Bloques: {report["block_counts"]}')
        self.stdout.write(
            self.style.WARNING(
                'Modo inspección: no se crearon ni modificaron registros.'
            )
        )
        if report_path:
            self.stdout.write(f'Informe JSON: {report_path}')
