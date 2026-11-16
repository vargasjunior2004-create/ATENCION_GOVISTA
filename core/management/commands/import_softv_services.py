"""Carga servicios SOFTV como servicios externos, no como contratos.

Por defecto el comando solo analiza. ``--apply`` crea CustomerService faltantes
por cliente y nombre original del servicio. Nunca crea clientes, contratos ni
solicitudes.
"""

import json
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import Customer, CustomerService
from .import_softv_customers import read_records
from .inspect_softv_excel import clean


def service_candidates(records):
    grouped = defaultdict(list)
    for record in records:
        raw_services = record.get('services_raw') or record.get('services', '')
        # La celda completa representa un plan/paquete SOFTV. No se separa
        # por comas: "GO-120(...)-COMBO, Iptv Basico, TV-120" es un solo
        # servicio combinado y debe conservarse íntegramente.
        raw_name = raw_services.strip()
        if not raw_name:
            continue
        key = (record['code'], clean(raw_name).casefold())
        grouped[key].append({
            'code': record['code'],
            'raw_name': raw_name,
            'normalized': clean(raw_name).casefold(),
            'period': record.get('period', ''),
            'year': record.get('year') or None,
            'row': record['row_number'],
            'file': '',
        })
    return [
        {
            'code': key[0],
            'raw_name': items[0]['raw_name'],
            'normalized': items[0]['normalized'],
            'period': next((item['period'] for item in items if item['period']), ''),
            'year': next((item['year'] for item in items if item['year']), None),
            'rows': sorted({item['row'] for item in items}),
        }
        for key, items in sorted(grouped.items())
    ]


class Command(BaseCommand):
    help = 'Carga servicios SOFTV separados de los contratos de GO VISTA.'

    def add_arguments(self, parser):
        parser.add_argument('--file', required=True, help='Ruta del Excel SOFTV')
        parser.add_argument('--sheet', default='Hoja1')
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--report', help='Ruta opcional para informe JSON')

    def handle(self, *args, **options):
        path = Path(options['file'])
        if not path.is_file():
            raise CommandError(f'No existe el archivo: {path}')

        records, ignored = read_records(path, options['sheet'])
        candidates = service_candidates(records)
        customers = {
            customer.code: customer
            for customer in Customer.objects.all().only('id', 'code', 'name')
        }
        report = {
            'file': str(path),
            'sheet': options['sheet'],
            'mode': 'apply' if options['apply'] else 'dry-run',
            'ignored_rows': ignored,
            'services': [],
            'counts': {
                'candidate_services': len(candidates),
                'customers_missing': 0,
                'already_existing': 0,
                'to_create': 0,
                'created': 0,
                'name_differences': 0,
            },
        }

        for candidate in candidates:
            customer = customers.get(candidate['code'])
            item = {**candidate, 'customer_id': customer.id if customer else None}
            if customer is None:
                item['action'] = 'review_customer_missing'
                report['counts']['customers_missing'] += 1
            else:
                existing = CustomerService.objects.filter(
                    source=CustomerService.SOURCE_SOFTV,
                    customer=customer,
                    raw_name_normalized=candidate['normalized'],
                ).first()
                item['existing_service_id'] = existing.id if existing else None
                if existing:
                    item['action'] = 'existing'
                    report['counts']['already_existing'] += 1
                else:
                    item['action'] = 'create'
                    report['counts']['to_create'] += 1
            report['services'].append(item)

        if options['apply']:
            with transaction.atomic():
                for item in report['services']:
                    if item['action'] != 'create':
                        continue
                    customer = customers[item['code']]
                    service, created = CustomerService.objects.get_or_create(
                        source=CustomerService.SOURCE_SOFTV,
                        customer=customer,
                        raw_name_normalized=item['normalized'],
                        defaults={
                            'source_customer_code': item['code'],
                            'raw_name': item['raw_name'],
                            'source_period': item['period'],
                            'source_year': int(item['year']) if str(
                                item['year']).isdigit() else None,
                            'source_file': path.name,
                            'source_row': item['rows'][0],
                            'service_status': None,
                        },
                    )
                    if created:
                        report['counts']['created'] += 1
            report['counts']['to_create'] = report['counts']['created']

        if options.get('report'):
            report_path = Path(options['report'])
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )

        counts = report['counts']
        self.stdout.write(f'Archivo: {path}')
        self.stdout.write(f'Servicios candidatos: {counts["candidate_services"]}')
        self.stdout.write(f'Servicios existentes: {counts["already_existing"]}')
        self.stdout.write(f'Clientes no encontrados: {counts["customers_missing"]}')
        self.stdout.write(f'Para crear: {counts["to_create"]}')
        if options['apply']:
            self.stdout.write(f'Creados: {counts["created"]}')
        else:
            self.stdout.write(self.style.WARNING(
                'Dry-run: no se crearon servicios ni se modificaron contratos.'
            ))
        if options.get('report'):
            self.stdout.write(f'Informe JSON: {options["report"]}')
