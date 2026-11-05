from datetime import date
from io import BytesIO

from django.test import TestCase
from openpyxl import load_workbook

from .models import Plan, Sale, User
from .reports import build_sales_pdf, build_sales_xlsx


class ReportEquipmentColumnTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(name='report-columns', role='admin')
        self.plan = Plan.objects.create(
            type='internet', code='REPORT-COLUMNS', label='Plan reportes',
            monthly=100, installation=0, speed='20', active=True)

    def sale(self, request_type, code, serial=''):
        return Sale.objects.create(
            date=date.today(), clientCode=code, clientName=f'Cliente {code}',
            serviceType='internet', requestType=request_type,
            plan=self.plan, planName=self.plan.label, total=100,
            equipment_delivered=bool(serial), equipment_serial=serial,
            createdBy=self.user,
        )

    def xlsx_headers_and_rows(self, request_type=None):
        output = build_sales_xlsx(
            date.today().isoformat(), date.today().isoformat(), request_type)
        workbook = load_workbook(BytesIO(output.getvalue()), read_only=True)
        rows = list(workbook.active.iter_rows(values_only=True))
        return rows[0], rows[1:]

    def test_retirement_report_includes_serial_and_fallback(self):
        self.sale('retiro', 'RET-001', 'ONU-001')
        self.sale('retiro', 'RET-002')
        headers, rows = self.xlsx_headers_and_rows('retiro')
        self.assertIn('SERIE DEL EQUIPO', headers)
        serial_index = headers.index('SERIE DEL EQUIPO')
        self.assertEqual(rows[0][serial_index], 'ONU-001')
        self.assertEqual(rows[1][serial_index], 'No registrada')

    def test_non_retirement_report_does_not_include_serial(self):
        self.sale('nuevo_contrato', 'NEW-001')
        headers, _ = self.xlsx_headers_and_rows('nuevo_contrato')
        self.assertNotIn('SERIE DEL EQUIPO', headers)

    def test_mixed_report_includes_serial_and_leaves_other_rows_empty(self):
        self.sale('nuevo_contrato', 'NEW-001')
        self.sale('retiro', 'RET-001', 'ONU-MIXED')
        headers, rows = self.xlsx_headers_and_rows()
        self.assertIn('SERIE DEL EQUIPO', headers)
        serial_index = headers.index('SERIE DEL EQUIPO')
        values = {row[1]: row[serial_index] for row in rows}
        self.assertIn(values['NEW-001'], ('', None))
        self.assertEqual(values['RET-001'], 'ONU-MIXED')

    def test_pdf_retirement_report_is_generated_with_serial_column(self):
        self.sale('retiro', 'RET-PDF', 'ONU-PDF')
        output = build_sales_pdf(
            date.today().isoformat(), date.today().isoformat(), 'retiro')
        self.assertTrue(output.getvalue().startswith(b'%PDF'))
        self.assertGreater(len(output.getvalue()), 500)
