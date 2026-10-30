import json

from django.test import TestCase, Client


class OpenApiTests(TestCase):
    def test_schema_is_available(self):
        response = Client().get('/api/schema/?format=json')
        self.assertEqual(response.status_code, 200)
        document = json.loads(response.content)
        self.assertIn('openapi', document)
        self.assertEqual(document['info']['title'], 'SaleStracker API')

    def test_swagger_ui_is_available(self):
        response = Client().get('/api/schema/swagger-ui/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'SwaggerUIBundle', response.content)
