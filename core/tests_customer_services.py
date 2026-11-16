import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase
from openpyxl import Workbook

from .models import Contract, Customer, CustomerService


def write_services_workbook(path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Hoja1'
    sheet.append([])
    sheet.append(['COBIJA'])
    sheet.append([
        'K-001', 'CLIENTE UNO', 'Octubre', 2026,
        'PLAN INTERNET, Iptv Basico', '70000001', '70000002',
        'Treinta y Dos', 'Calle 1', 'EMPRESA',
    ])
    sheet.append([
        'K-001', 'CLIENTE UNO', 'PLAN INTERNET',
        '70000003', '', 'Treinta y Dos', 'EMPRESA',
    ])
    sheet.append([
        'K-002', 'CLIENTE DOS', 'PLAN TV',
        '70000004', '', 'Treinta y Dos', 'EMPRESA',
    ])
    workbook.save(path)


class CustomerServiceImportTests(TestCase):
    def setUp(self):
        self.customer_one = Customer.objects.create(
            code='K-001', name='CLIENTE UNO')
        Customer.objects.create(code='K-002', name='CLIENTE DOS')

    def test_apply_keeps_raw_names_and_is_idempotent(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'softv.xlsx'
            report = Path(directory) / 'services.json'
            write_services_workbook(path)

            call_command(
                'import_softv_services',
                file=str(path),
                apply=True,
                report=str(report),
            )
            call_command(
                'import_softv_services',
                file=str(path),
                apply=True,
            )
            payload = json.loads(report.read_text(encoding='utf-8'))

        self.assertEqual(CustomerService.objects.count(), 3)
        self.assertEqual(
            CustomerService.objects.filter(
                customer=self.customer_one).count(), 2)
        self.assertEqual(
            CustomerService.objects.filter(raw_name='Iptv Basico').count(), 1)
        self.assertTrue(
            CustomerService.objects.filter(
                raw_name='Iptv Basico',
                plan__isnull=True,
                homologation_status='pending',
                service_status__isnull=True,
            ).exists())
        self.assertEqual(Contract.objects.count(), 0)
        self.assertEqual(payload['counts']['created'], 3)

    def test_missing_customer_is_reported_without_creating_service(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'softv.xlsx'
            write_services_workbook(path)
            Customer.objects.filter(code='K-002').delete()
            call_command(
                'import_softv_services',
                file=str(path),
                apply=True,
            )

        self.assertEqual(CustomerService.objects.count(), 2)
