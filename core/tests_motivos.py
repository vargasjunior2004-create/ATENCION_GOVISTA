"""Catalogo de motivos y filtro 'Mostrar motivos' en los reportes.

Cubre el CRUD administrativo, la validacion por categoria en el alta y
edicion de movimientos, y la aparicion condicional de la columna Motivo.
"""
from decimal import Decimal

from django.test import TestCase, Client
from django.utils import timezone

from .models import User, Plan, Sale, Motivo


def _create_user(name, password, role='admin'):
    u = User.objects.create(name=name, password='', role=role, active=True)
    u.set_password(password)
    u.save()
    return u


class MotivoApiTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.admin = _create_user('admin_mot', 'pass1', 'admin')
        self.ventas = _create_user('ventas_mot', 'pass2', 'ventas')
        self.plan = Plan.objects.create(
            type='internet', code='M001', label='Plan M', monthly=100,
            speed='10', active=True, installation=Decimal('0'))
        self.plan_from = Plan.objects.create(
            type='internet', code='M000', label='Plan M0', monthly=80,
            speed='5', active=True, installation=Decimal('0'))
        self.cambio = Motivo.objects.create(
            categoria='cambio', nombre='MEJOR CALIDAD')
        self.retiro = Motivo.objects.create(
            categoria='retiro', nombre='MUDANZA')
        self.retiro_inactivo = Motivo.objects.create(
            categoria='retiro', nombre='FALLECIMIENTO', activo=False)

    def _token(self, user, pw):
        r = self.c.post('/api/auth/login', {'name': user.name, 'password': pw},
                        content_type='application/json')
        return r.json()['token']

    def _auth(self, user, pw):
        return {'HTTP_AUTHORIZATION': f'Bearer {self._token(user, pw)}'}

    def _crear_cambio(self, **over):
        payload = {
            'clientCode': 'MC001', 'clientName': 'CAMBIO',
            'serviceType': 'internet', 'requestType': 'cambio_plan',
            'planId': self.plan.id, 'planFromId': self.plan_from.id,
            'motivoId': self.cambio.id,
        }
        payload.update(over)
        return self.c.post('/api/sales', payload,
                           content_type='application/json',
                           **self._auth(self.admin, 'pass1'))

    # ------------------------------------------------------------- CRUD
    def test_admin_puede_listar_y_crear_motivos(self):
        r = self.c.get('/api/motivos', **self._auth(self.admin, 'pass1'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 3)

        r2 = self.c.post('/api/motivos', {
            'categoria': 'cambio', 'nombre': 'PRECIO', 'orden': 5},
            content_type='application/json', **self._auth(self.admin, 'pass1'))
        self.assertEqual(r2.status_code, 201)
        self.assertTrue(Motivo.objects.filter(nombre='PRECIO').exists())

    def test_ventas_no_puede_administrar_motivos(self):
        r = self.c.get('/api/motivos', **self._auth(self.ventas, 'pass2'))
        self.assertEqual(r.status_code, 403)
        r2 = self.c.post('/api/motivos', {
            'categoria': 'cambio', 'nombre': 'X'},
            content_type='application/json', **self._auth(self.ventas, 'pass2'))
        self.assertEqual(r2.status_code, 403)

    def test_activos_filtra_categoria_y_excluye_inactivos(self):
        r = self.c.get('/api/motivos/active?categoria=retiro',
                       **self._auth(self.ventas, 'pass2'))
        self.assertEqual(r.status_code, 200)
        nombres = [m['nombre'] for m in r.json()]
        self.assertIn('MUDANZA', nombres)
        self.assertNotIn('FALLECIMIENTO', nombres)
        self.assertNotIn('MEJOR CALIDAD', nombres)

    def test_no_se_puede_borrar_motivo_con_movimientos(self):
        self._crear_cambio()
        r = self.c.delete(f'/api/motivos/{self.cambio.id}',
                          **self._auth(self.admin, 'pass1'))
        self.assertEqual(r.status_code, 400)
        self.assertTrue(Motivo.objects.filter(id=self.cambio.id).exists())

    def test_se_puede_borrar_motivo_sin_movimientos(self):
        r = self.c.delete(f'/api/motivos/{self.retiro.id}',
                          **self._auth(self.admin, 'pass1'))
        self.assertEqual(r.status_code, 204)
        self.assertFalse(Motivo.objects.filter(id=self.retiro.id).exists())

    # ------------------------------------------------------------- Alta
    def test_cambio_guarda_motivo_y_snapshot(self):
        r = self._crear_cambio()
        self.assertEqual(r.status_code, 201, r.content[:300])
        sale = Sale.objects.get(clientCode='MC001')
        self.assertEqual(sale.motivo, self.cambio)
        self.assertEqual(sale.changeReason, 'MEJOR CALIDAD')

    def test_cambio_sin_motivo_se_rechaza(self):
        r = self._crear_cambio(motivoId=None)
        self.assertEqual(r.status_code, 400)
        self.assertIn('motivo', r.json()['error'].lower())

    def test_cambio_con_motivo_de_otra_categoria_se_rechaza(self):
        r = self._crear_cambio(motivoId=self.retiro.id)
        self.assertEqual(r.status_code, 400)
        self.assertIn('corresponde', r.json()['error'])

    def test_cambio_con_motivo_inactivo_se_rechaza(self):
        r = self._crear_cambio(motivoId=self.retiro_inactivo.id)
        self.assertEqual(r.status_code, 400)

    def test_retiro_con_motivo_de_otra_categoria_se_rechaza(self):
        r = self.c.post('/api/sales', {
            'clientCode': 'MR001', 'clientName': 'RETIRO',
            'serviceType': 'internet', 'requestType': 'retiro',
            'planId': self.plan.id, 'motivoId': self.cambio.id},
            content_type='application/json', **self._auth(self.admin, 'pass1'))
        self.assertEqual(r.status_code, 400)

    def test_nuevo_contrato_no_exige_motivo(self):
        r = self.c.post('/api/sales', {
            'clientCode': 'MN001', 'clientName': 'ALTA',
            'serviceType': 'internet', 'requestType': 'nuevo_contrato',
            'planId': self.plan.id},
            content_type='application/json', **self._auth(self.admin, 'pass1'))
        self.assertEqual(r.status_code, 201)
        self.assertIsNone(Sale.objects.get(clientCode='MN001').motivo)

    # ---------------------------------------------------------- Edicion
    def test_edicion_sin_motivo_conserva_el_snapshot(self):
        self._crear_cambio()
        sale = Sale.objects.get(clientCode='MC001')
        r = self.c.put(f'/api/sales/{sale.id}', {
            'serviceType': 'internet', 'requestType': 'cambio_plan',
            'planId': self.plan.id, 'planFromId': self.plan_from.id,
            'notes': 'solo nota'},
            content_type='application/json', **self._auth(self.admin, 'pass1'))
        self.assertEqual(r.status_code, 200, r.content[:300])
        sale.refresh_from_db()
        self.assertEqual(sale.motivo, self.cambio)
        self.assertEqual(sale.changeReason, 'MEJOR CALIDAD')


class MotivoReportTests(TestCase):
    def setUp(self):
        self.c = Client()
        self.admin = _create_user('admin_rep', 'pass1', 'admin')
        self.plan = Plan.objects.create(
            type='internet', code='R100', label='Plan R', monthly=100,
            speed='10', active=True, installation=Decimal('0'))
        self.retiro = Motivo.objects.create(
            categoria='retiro', nombre='MUDANZA')
        token = self._token()
        self.c.post('/api/sales', {
            'clientCode': 'RR001', 'clientName': 'REPORT',
            'serviceType': 'internet', 'requestType': 'retiro',
            'planId': self.plan.id, 'motivoId': self.retiro.id},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}')

    def _token(self):
        r = self.c.post('/api/auth/login',
                        {'name': 'admin_rep', 'password': 'pass1'},
                        content_type='application/json')
        return r.json()['token']

    def _xlsx_headers(self, **params):
        import io
        import openpyxl
        token = self._token()
        extra = '&'.join(f'{k}={v}' for k, v in params.items())
        today = timezone.localdate().isoformat()
        r = self.c.get(f'/api/reports/xlsx?from={today}&to={today}&{extra}',
                       HTTP_AUTHORIZATION=f'Bearer {token}')
        ws = openpyxl.load_workbook(io.BytesIO(r.content)).active
        return [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]

    def test_columna_motivo_aparece_cuando_se_pide(self):
        self.assertIn('MOTIVO', self._xlsx_headers(showMotivos='si'))

    def test_columna_motivo_se_oculta_por_defecto(self):
        self.assertNotIn('MOTIVO', self._xlsx_headers())

    def test_pdf_y_png_soportan_show_motivos(self):
        from .reports import build_sales_pdf, build_sales_png
        today = timezone.localdate().isoformat()
        self.assertTrue(
            build_sales_pdf(today, today, show_motivos=True).getvalue())
        self.assertTrue(
            build_sales_png(today, today, show_motivos=True).getvalue())
