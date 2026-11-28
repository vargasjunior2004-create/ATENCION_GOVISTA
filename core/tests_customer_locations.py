from datetime import date
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from .models import Customer, User, Role, Permission, RolePermission, UserRole


def jpeg_file(name='fachada.jpg'):
    output = BytesIO()
    Image.new('RGB', (40, 40), 'red').save(output, format='JPEG')
    return SimpleUploadedFile(name, output.getvalue(), content_type='image/jpeg')


class CustomerLocationApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(name='tecnico', password='x', role='ventas')
        self.customer = Customer.objects.create(code='KDX-001', name='Cliente Uno')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch('core.views.has_permission', return_value=True)
    @patch('core.views.upload_photo', return_value='customers/1/photo.jpg')
    @patch('core.views.optimize_photo', return_value=(b'jpeg', 'image/jpeg'))
    def test_create_requires_existing_customer_and_records_history(self, optimize, upload, allowed):
        response = self.client.post('/api/ubicaciones', {
            'customer': self.customer.id,
            'photo': jpeg_file(),
            'source': 'gps',
            'latitude': '-17.783300',
            'longitude': '-63.182100',
            'accuracy_meters': '18.4',
            'captured_at': '2026-11-05T12:00:00Z',
        }, format='multipart')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['customerCode'], 'KDX-001')
        self.assertEqual(response.data['source'], 'gps')
        self.assertEqual(response.data['updatedBy'], 'tecnico')
        self.assertEqual(response.data['photoUrl'], '')

        missing = self.client.post('/api/ubicaciones', {
            'customer': 99999, 'photo': jpeg_file(), 'source': 'gps',
            'latitude': 1, 'longitude': 1,
        }, format='multipart')
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(self.client.get('/api/ubicaciones/1/historial').status_code, 200)

    @patch('core.views.has_permission', return_value=True)
    @patch('core.views.upload_photo', return_value='customers/1/second.jpg')
    @patch('core.views.optimize_photo', return_value=(b'jpeg', 'image/jpeg'))
    def test_maps_url_and_update_preserve_history(self, optimize, upload, allowed):
        created = self.client.post('/api/ubicaciones', {
            'customer': self.customer.id, 'photo': jpeg_file(),
            'source': 'maps_url',
            'maps_url': 'https://www.google.com/maps/@-17.7833,-63.1821,18z',
        }, format='multipart')
        self.assertEqual(created.status_code, 201)
        location_id = created.data['id']
        updated = self.client.patch(f'/api/ubicaciones/{location_id}', {
            'photo': jpeg_file('new.jpg'), 'source': 'gps',
            'latitude': '-17.78', 'longitude': '-63.18', 'accuracy_meters': '75',
        }, format='multipart')
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data['source'], 'gps')
        history = self.client.get(f'/api/ubicaciones/{location_id}/historial')
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.data), 2)
        self.assertEqual(history.data[0]['changedBy'], 'tecnico')

    @patch('core.views.has_permission', return_value=True)
    def test_invalid_maps_url_is_rejected(self, allowed):
        response = self.client.post('/api/ubicaciones', {
            'customer': self.customer.id, 'photo': jpeg_file(),
            'source': 'maps_url', 'maps_url': 'https://example.com/location',
        }, format='multipart')
        self.assertEqual(response.status_code, 400)

    def test_location_endpoints_require_location_permissions(self):
        response = self.client.get('/api/ubicaciones/clientes?q=KDX')
        self.assertEqual(response.status_code, 403)
        response = self.client.post('/api/ubicaciones', {'customer': self.customer.id})
        self.assertEqual(response.status_code, 403)
