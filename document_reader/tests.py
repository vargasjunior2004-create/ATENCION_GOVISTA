import pymupdf
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase

from core.models import User


def make_order_pdf():
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text(
        (40, 60),
        'ORDEN\nCONTRATO: 16742-1\nNo. Orden: 172787\n'
        'Fecha: 10-nov-2026\nNOMBRE: SAUL TEODORO NINA FERNANDEZ\n'
        'PLACA: 2146031\nRetiro de aparato (XPONDD494C46)',
    )
    return document.tobytes()


class RetirementDocumentExtractTests(TestCase):
    def setUp(self):
        self.client = Client()
        user = User.objects.create(name='reader-test', password='', role='admin')
        user.set_password('reader-test-password')
        user.save()
        login = self.client.post(
            '/api/auth/login',
            {'name': 'reader-test', 'password': 'reader-test-password'},
            content_type='application/json')
        self.auth = {'HTTP_AUTHORIZATION': f"Bearer {login.json()['token']}"}

    def test_extracts_only_fields_for_existing_retirement_form(self):
        upload = SimpleUploadedFile(
            'orden-retiro.pdf', make_order_pdf(), content_type='application/pdf')
        response = self.client.post(
            '/api/document-reader/extract-retirement/', {'file': upload}, **self.auth)

        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()['fields']
        self.assertEqual(data['clientCode'], '16742-1')
        self.assertEqual(data['clientName'], 'SAUL TEODORO NINA FERNANDEZ')
        self.assertEqual(data['equipmentSerial'], 'XPONDD494C46')
        self.assertEqual(data['date'], '2026-11-10')
        self.assertNotIn('2146031', data.values())
