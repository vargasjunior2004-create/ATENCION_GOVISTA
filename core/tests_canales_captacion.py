"""Catalogo de canales de captacion ("¿Como nos conocio?").

Cubre el CRUD administrativo, los permisos RBAC, la integracion con
contratos y recontrataciones, y la conservacion del historial cuando un
canal se desactiva.
"""

from decimal import Decimal

from django.db.models import ProtectedError
from django.test import Client, TestCase

from .models import (
    CanalCaptacion, CoverageZone, Plan, Role, Sale, User, UserRole,
)


def create_user(name, password, role='ventas'):
    user = User.objects.create(name=name, password='', role=role, active=True)
    user.set_password(password)
    user.save()
    return user


class CanalCaptacionBase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = create_user('canal_admin', 'pass1', 'admin')
        self.manager = create_user('canal_manager', 'pass1')
        self.commercial_lead = create_user('canal_lead', 'pass1')
        self.cashier = create_user('canal_cashier', 'pass1')
        self.call_center = create_user('canal_call_center', 'pass1')
        self.no_role = create_user('canal_no_role', 'pass1')
        self._attach_role(self.manager, 'gerente')
        self._attach_role(self.commercial_lead, 'jefe-comercial')
        self._attach_role(self.cashier, 'caja')
        self._attach_role(self.call_center, 'call-center')

        self.plan = Plan.objects.create(
            code='CANAL-100', label='Plan canales', type='internet',
            monthly=Decimal('200'), installation=Decimal('100'), active=True)
        self.zone = CoverageZone.objects.get(normalized_name='villa busch')
        self.canal = CanalCaptacion.objects.get(nombre_normalizado='facebook')

    @staticmethod
    def _attach_role(user, code):
        role = Role.objects.get(code=code)
        UserRole.objects.create(user=user, role=role)

    def auth(self, user):
        response = self.client.post(
            '/api/auth/login', {'name': user.name, 'password': 'pass1'},
            content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        return {'HTTP_AUTHORIZATION': f'Bearer {response.json()["token"]}'}

    def contract_payload(self, code, request_type='nuevo_contrato', **extra):
        payload = {
            'clientCode': code,
            'clientName': f'Cliente {code}',
            'serviceType': 'internet',
            'requestType': request_type,
            'planId': self.plan.id,
        }
        if request_type in ('nuevo_contrato', 'recontratacion'):
            payload['coverageZoneId'] = self.zone.id
        if request_type == 'recontratacion':
            payload.update({
                'equipmentRetained': True,
                'requiresTechnicalVisit': False,
                'debtApplies': False,
                'debtAmount': 0,
            })
        payload.update(extra)
        return payload

    def create_sale(self, user, code, request_type='nuevo_contrato', **extra):
        return self.client.post(
            '/api/sales',
            self.contract_payload(code, request_type, **extra),
            content_type='application/json',
            **self.auth(user))


class CanalCaptacionCrudTests(CanalCaptacionBase):
    def test_catalogo_inicial_sembrado(self):
        response = self.client.get(
            '/api/canales-captacion', **self.auth(self.admin))
        self.assertEqual(response.status_code, 200, response.content)
        nombres = [item['nombre'] for item in response.json()]
        self.assertIn('Facebook', nombres)
        self.assertIn('Recomendación', nombres)
        self.assertGreaterEqual(len(nombres), 7)

    def test_admin_crea_y_edita_canal(self):
        response = self.client.post(
            '/api/canales-captacion',
            {'nombre': 'Instagram', 'descripcion': 'Red social'},
            content_type='application/json', **self.auth(self.admin))
        self.assertEqual(response.status_code, 201, response.content)
        canal_id = response.json()['id']

        response = self.client.put(
            f'/api/canales-captacion/{canal_id}',
            {'nombre': 'Instagram Ads', 'descripcion': 'Publicidad pagada'},
            content_type='application/json', **self.auth(self.admin))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['nombre'], 'Instagram Ads')
        self.assertTrue(
            CanalCaptacion.objects.filter(
                id=canal_id, nombre_normalizado='instagram ads').exists())

    def test_nombres_duplicados_se_rechazan(self):
        response = self.client.post(
            '/api/canales-captacion',
            {'nombre': '  facebook  '},
            content_type='application/json', **self.auth(self.admin))
        self.assertEqual(response.status_code, 400, response.content)

        response = self.client.post(
            '/api/canales-captacion',
            {'nombre': 'FACEBOOK'},
            content_type='application/json', **self.auth(self.admin))
        self.assertEqual(response.status_code, 400, response.content)

        tiktok = CanalCaptacion.objects.get(nombre_normalizado='tiktok')
        response = self.client.put(
            f'/api/canales-captacion/{tiktok.id}',
            {'nombre': 'facebook'},
            content_type='application/json', **self.auth(self.admin))
        self.assertEqual(response.status_code, 400, response.content)

    def test_desactivar_no_borra_el_canal(self):
        response = self.client.delete(
            f'/api/canales-captacion/{self.canal.id}', **self.auth(self.admin))
        self.assertEqual(response.status_code, 204, response.content)
        self.canal.refresh_from_db()
        self.assertFalse(self.canal.activo)

        activos = self.client.get(
            '/api/canales-captacion/active', **self.auth(self.cashier))
        self.assertEqual(activos.status_code, 200)
        self.assertNotIn(
            self.canal.id, [item['id'] for item in activos.json()])

        admin_list = self.client.get(
            '/api/canales-captacion', **self.auth(self.admin))
        estados = {item['id']: item['activo'] for item in admin_list.json()}
        self.assertFalse(estados[self.canal.id])

    def test_no_se_puede_borrar_fisicamente_un_canal_con_ventas(self):
        response = self.create_sale(
            self.admin, 'CANAL-FK-1', canalCaptacionId=self.canal.id)
        self.assertEqual(response.status_code, 201, response.content)
        with self.assertRaises(ProtectedError):
            self.canal.delete()


class CanalCaptacionPermisosTests(CanalCaptacionBase):
    def test_gerente_y_jefe_comercial_administran(self):
        for user, nombre in (
                (self.manager, 'Gerente canal'),
                (self.commercial_lead, 'Jefe canal')):
            listado = self.client.get(
                '/api/canales-captacion', **self.auth(user))
            self.assertEqual(listado.status_code, 200, listado.content)

            response = self.client.post(
                '/api/canales-captacion', {'nombre': nombre},
                content_type='application/json', **self.auth(user))
            self.assertEqual(response.status_code, 201, response.content)
            canal_id = response.json()['id']
            response = self.client.patch(
                f'/api/canales-captacion/{canal_id}',
                {'activo': False},
                content_type='application/json', **self.auth(user))
            self.assertEqual(response.status_code, 200, response.content)

    def test_caja_y_call_center_no_administran(self):
        for user in (self.cashier, self.call_center, self.no_role):
            response = self.client.post(
                '/api/canales-captacion', {'nombre': f'No autorizado {user.id}'},
                content_type='application/json', **self.auth(user))
            self.assertEqual(response.status_code, 403, response.content)

            response = self.client.put(
                f'/api/canales-captacion/{self.canal.id}',
                {'nombre': 'Nombre cambiado'},
                content_type='application/json', **self.auth(user))
            self.assertEqual(response.status_code, 403, response.content)

            response = self.client.delete(
                f'/api/canales-captacion/{self.canal.id}', **self.auth(user))
            self.assertEqual(response.status_code, 403, response.content)

    def test_no_autorizados_no_ven_el_listado_administrativo(self):
        response = self.client.get(
            '/api/canales-captacion', **self.auth(self.cashier))
        self.assertEqual(response.status_code, 403, response.content)

    def test_roles_operativos_leen_canales_activos(self):
        for user in (self.cashier, self.call_center):
            response = self.client.get(
                '/api/canales-captacion/active', **self.auth(user))
            self.assertEqual(response.status_code, 200, response.content)
            self.assertTrue(response.json())
            self.assertTrue(all(item['nombre'] for item in response.json()))


class CanalCaptacionVentasTests(CanalCaptacionBase):
    def test_contrato_nuevo_guarda_canal(self):
        response = self.create_sale(
            self.cashier, 'CANAL-NUEVO-1', canalCaptacionId=self.canal.id)
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertEqual(data['canalCaptacionId'], self.canal.id)
        self.assertEqual(data['canalCaptacion']['nombre'], 'Facebook')

        sale = Sale.objects.get(id=data['id'])
        self.assertEqual(sale.canal_captacion_id, self.canal.id)

    def test_recontratacion_guarda_canal(self):
        response = self.create_sale(
            self.call_center, 'CANAL-REHIRE-1',
            request_type='recontratacion', canalCaptacionId=self.canal.id)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(
            response.json()['canalCaptacionId'], self.canal.id)

    def test_otros_tipos_no_aceptan_canal(self):
        response = self.create_sale(
            self.cashier, 'CANAL-OTRO-1', request_type='otro',
            canalCaptacionId=self.canal.id)
        self.assertEqual(response.status_code, 400, response.content)

    def test_otros_tipos_sin_canal_siguen_funcionando(self):
        response = self.create_sale(
            self.cashier, 'CANAL-OTRO-2', request_type='otro')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIsNone(response.json()['canalCaptacion'])

    def test_venta_sin_canal_sigue_funcionando(self):
        response = self.create_sale(self.cashier, 'CANAL-SIN-1')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIsNone(response.json()['canalCaptacion'])
        self.assertIsNone(response.json()['canalCaptacionId'])

    def test_historial_conserva_canal_desactivado(self):
        response = self.create_sale(
            self.cashier, 'CANAL-HIST-1', canalCaptacionId=self.canal.id)
        self.assertEqual(response.status_code, 201, response.content)

        self.client.delete(
            f'/api/canales-captacion/{self.canal.id}', **self.auth(self.admin))

        historial = self.client.get(
            '/api/sales?page=1&page_size=25', **self.auth(self.cashier))
        self.assertEqual(historial.status_code, 200, historial.content)
        fila = next(
            item for item in historial.json()['items']
            if item['clientCode'] == 'CANAL-HIST-1')
        self.assertEqual(fila['canalCaptacionId'], self.canal.id)
        self.assertEqual(fila['canalCaptacion']['nombre'], 'Facebook')
        self.assertFalse(fila['canalCaptacion']['activo'])

    def test_editar_solicitud_sin_enviar_canal_lo_conserva(self):
        response = self.create_sale(
            self.admin, 'CANAL-EDIT-1', canalCaptacionId=self.canal.id)
        self.assertEqual(response.status_code, 201, response.content)
        sale_id = response.json()['id']

        response = self.client.put(
            f'/api/sales/{sale_id}', {'notes': 'Nota editada'},
            content_type='application/json', **self.auth(self.admin))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['canalCaptacionId'], self.canal.id)

    def test_editar_solicitud_permite_cambiar_canal_activo(self):
        response = self.create_sale(self.admin, 'CANAL-EDIT-2')
        self.assertEqual(response.status_code, 201, response.content)
        sale_id = response.json()['id']

        response = self.client.put(
            f'/api/sales/{sale_id}',
            {'canalCaptacionId': self.canal.id},
            content_type='application/json', **self.auth(self.admin))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['canalCaptacionId'], self.canal.id)

    def test_no_se_puede_asignar_canal_inactivo(self):
        self.canal.activo = False
        self.canal.save(update_fields=['activo', 'updated_at'])
        response = self.create_sale(
            self.cashier, 'CANAL-INACTIVO-1', canalCaptacionId=self.canal.id)
        self.assertEqual(response.status_code, 400, response.content)
