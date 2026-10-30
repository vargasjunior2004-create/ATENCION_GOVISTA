import uuid

from django.test import TestCase, Client


class RequestIDTests(TestCase):
    def test_health_returns_request_id(self):
        response = Client().get('/api/health')
        self.assertEqual(response.status_code, 200)
        uuid.UUID(response['X-Request-ID'])

    def test_valid_request_id_is_propagated(self):
        request_id = '12345678-1234-5678-1234-567812345678'
        response = Client().get('/api/health', HTTP_X_REQUEST_ID=request_id)
        self.assertEqual(response['X-Request-ID'], request_id)

    def test_invalid_request_id_is_replaced(self):
        response = Client().get('/api/health', HTTP_X_REQUEST_ID='pii-or-log-injection')
        self.assertNotEqual(response['X-Request-ID'], 'pii-or-log-injection')
        uuid.UUID(response['X-Request-ID'])
