from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase
from openpyxl import Workbook

from .models import Customer


def write_softv_workbook(path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Hoja1'
    sheet.append([])
    sheet.append(['COBIJA'])
    sheet.append([
        'K-001', 'CLIENTE UNO', 'Octubre', 2026,
        'PLAN INTERNET', '70000001', '70000002',
        'Treinta y Dos', 'Calle 1', 'EMPRESA',
    ])
    sheet.append([
        'K-001', 'CLIENTE UNO', 'PLAN TV',
        '70000003', '', 'Treinta y Dos', 'EMPRESA',
    ])
    sheet.append([
        'K-002', 'CLIENTE DOS', 'Octubre', 2026,
        'PLAN INTERNET', '0', '70000004',
        'Treinta y Dos', 'Calle 2', 'EMPRESA',
    ])
    workbook.save(path)


class SoftvCustomerImportTests(TestCase):
    def test_dry_run_does_not_create_customers(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'softv.xlsx'
            report = Path(directory) / 'report.json'
            write_softv_workbook(path)

            call_command(
                'import_softv_customers',
                file=str(path),
                report=str(report),
            )

            self.assertEqual(Customer.objects.count(), 0)
            self.assertTrue(report.exists())

    def test_apply_is_idempotent_and_groups_services_by_kardex(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'softv.xlsx'
            write_softv_workbook(path)

            call_command('import_softv_customers', file=str(path), apply=True)
            call_command('import_softv_customers', file=str(path), apply=True)

            self.assertEqual(Customer.objects.count(), 2)
            customer = Customer.objects.get(code='K-001')
            self.assertEqual(customer.name, 'CLIENTE UNO')
            self.assertEqual(customer.phone, '')

    def test_existing_name_difference_is_not_overwritten(self):
        Customer.objects.create(
            code='K-001',
            name='NOMBRE OPERATIVO',
            phone='79999999',
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'softv.xlsx'
            write_softv_workbook(path)

            call_command('import_softv_customers', file=str(path), apply=True)

        customer = Customer.objects.get(code='K-001')
        self.assertEqual(customer.name, 'NOMBRE OPERATIVO')
        self.assertEqual(customer.phone, '79999999')
        self.assertEqual(Customer.objects.count(), 2)
