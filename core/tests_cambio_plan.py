"""Cambio de plan entre distintos tipos de servicio.

Cubre la matriz completa de conversiones (Internet, TV, Combo), las reglas
de validacion del backend, la conservacion del historial y los permisos.
"""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from .models import User, Plan, Sale, Motivo
from .domain import SERVICE_TYPE_TO_PLAN_TYPE, sale_service_label


def _create_user(name, password, role):
    u = User.objects.create(name=name, role=role, active=True)
    u.set_password(password)
    u.save()
    return u


class CambioPlanEntreServiciosTest(TestCase):
    """Internet/TV/Combo en cualquier combinacion, incluido el mismo servicio."""

    def setUp(self):
        self.admin = _create_user('admin_cp', 'pass1', 'admin')
        self.ventas = _create_user('ventas_cp', 'pass2', 'ventas')
        self.plans = {}
        for ptype in ('internet', 'tv', 'combo'):
            for idx in (1, 2):
                self.plans[(ptype, idx)] = Plan.objects.create(
                    code=f'{ptype.upper()}{idx}', label=f'{ptype.upper()} {idx}',
                    type=ptype, monthly=Decimal('100') * idx,
                    installation=Decimal('50'), active=True)
        self.client_ = None
        from django.test import Client
        self.client_ = Client()
        self.motivo_cambio = Motivo.objects.create(
            categoria='cambio', nombre='MEJOR CALIDAD')

    def _token(self, user, password):
        r = self.client_.post('/api/auth/login',
                              {'name': user.name, 'password': password},
                              content_type='application/json')
        return r.json()['token']

    def _first_service_of(self, family):
        return next(svc for svc, fam in SERVICE_TYPE_TO_PLAN_TYPE.items()
                    if fam == family)

    def _post_cambio(self, old_family, new_family, service_type_from=None,
                     client_code='CP001', omit_reason=False, same_plan=False):
        plan_to = self.plans[(new_family, 1)]
        plan_from = plan_to if same_plan else self.plans[(old_family, 2)]
        payload = {
            'clientCode': client_code, 'clientName': 'Cambio Test',
            'serviceType': self._first_service_of(new_family),
            'requestType': 'cambio_plan',
            'planId': plan_to.id, 'planFromId': plan_from.id,
        }
        if not omit_reason:
            payload['motivoId'] = self.motivo_cambio.id
        if service_type_from:
            payload['serviceTypeFrom'] = service_type_from
        return self.client_.post(
            '/api/sales', payload, content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {self._token(self.admin, "pass1")}')

    def test_matriz_completa_de_conversiones(self):
        """Los 9 escenarios del modulo: 3 dentro del servicio y 6 entre servicios."""
        combinaciones = [
            ('internet', 'internet'), ('tv', 'tv'), ('combo', 'combo'),
            ('combo', 'internet'), ('combo', 'tv'),
            ('internet', 'combo'), ('tv', 'combo'),
            ('internet', 'tv'), ('tv', 'internet'),
        ]
        for i, (old, new) in enumerate(combinaciones):
            with self.subTest(desde=old, hacia=new):
                r = self._post_cambio(old, new, client_code=f'MAT{i:02d}')
                self.assertEqual(r.status_code, 201,
                                 f'{old} -> {new} fue rechazado: {r.content[:200]}')
                data = r.json()
                self.assertEqual(data['requestType'], 'cambio_plan')
                # El plan guardado debe ser el nuevo, no el anterior.
                self.assertEqual(data['planId'], self.plans[(new, 1)].id)
                self.assertIsNotNone(data['previousPlan'])

    def test_conversion_se_reporta_como_cambio_de_plan(self):
        """Una conversion entre servicios no se registra como alta ni como retiro."""
        self._post_cambio('combo', 'internet')
        sale = Sale.objects.get(clientCode='CP001')
        self.assertEqual(sale.requestType, 'cambio_plan')
        self.assertEqual(sale.plan.type, 'internet')
        self.assertEqual(sale.planFromId.type, 'combo')
        # Solo mensualidad: cambiar de servicio no cobra instalacion.
        self.assertEqual(sale.total, self.plans[('internet', 1)].monthly)
        self.assertEqual(sale.applied_installation, Decimal('0'))

    def test_etiqueta_de_conversion_en_el_reporte(self):
        self._post_cambio('combo', 'internet')
        self._post_cambio('internet', 'combo', client_code='CP002')
        sale = Sale.objects.get(clientCode='CP001')
        self.assertEqual(sale_service_label(sale), 'COMBO → INTERNET')
        otro = Sale.objects.get(clientCode='CP002')
        self.assertEqual(sale_service_label(otro), 'INTERNET → COMBO')

    def test_sin_conversion_mantiene_la_etiqueta_original(self):
        """Un cambio dentro del mismo servicio no inventa una flecha."""
        self._post_cambio('internet', 'internet', client_code='CP003')
        sale = Sale.objects.get(clientCode='CP003')
        self.assertEqual(sale_service_label(sale), 'INTERNET → INTERNET')

    def test_servicio_anterior_se_registra(self):
        self._post_cambio('combo', 'internet',
                          service_type_from='combo_analog')
        sale = Sale.objects.get(clientCode='CP001')
        self.assertEqual(sale.serviceTypeFrom, 'combo_analog')
        # Sigue siendo recuperable por el plan aunque no se registre.
        self.assertEqual(Sale.objects.get(pk=sale.pk).serviceTypeFrom,
                         'combo_analog')

    def test_plan_anterior_basta_para_deducir_el_servicio(self):
        """Si no se informa el servicio anterior, se deduce del plan anterior."""
        r = self._post_cambio('combo', 'internet')
        self.assertEqual(r.status_code, 201)
        sale = Sale.objects.get(clientCode='CP001')
        self.assertIsNone(sale.serviceTypeFrom)
        data = r.json()
        self.assertEqual(data['previousService']['family'], 'combo')
        self.assertEqual(data['previousService']['label'], 'COMBO')
        self.assertTrue(data['isServiceChange'])

    def test_servicio_anterior_incoherente_se_rechaza(self):
        """No se puede decir 'combo' con un plan anterior de Internet."""
        r = self._post_cambio('internet', 'combo',
                              service_type_from='combo_analog')
        self.assertEqual(r.status_code, 400)
        self.assertIn('no corresponde al plan anterior', r.json()['error'])

    def test_plan_nuevo_incompatible_se_rechaza(self):
        """El backend no confía en el filtro del formulario."""
        token = self._token(self.admin, 'pass1')
        r = self.client_.post('/api/sales', {
            'clientCode': 'CPX', 'clientName': 'Malo',
            'serviceType': 'internet', 'requestType': 'cambio_plan',
            'planId': self.plans[('combo', 1)].id,
            'planFromId': self.plans[('internet', 2)].id,
            'changeReason': 'X',
        }, content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 400)
        self.assertIn('no pertenece al tipo de servicio', r.json()['error'])

    def test_cambio_de_plan_exige_plan_anterior(self):
        token = self._token(self.admin, 'pass1')
        r = self.client_.post('/api/sales', {
            'clientCode': 'CPY', 'clientName': 'Sin anterior',
            'serviceType': 'internet', 'requestType': 'cambio_plan',
            'planId': self.plans[('internet', 1)].id,
            'changeReason': 'X',
        }, content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 400)
        self.assertIn('plan anterior', r.json()['error'])

    def test_cambio_de_plan_exige_motivo(self):
        r = self._post_cambio('combo', 'internet', omit_reason=True)
        self.assertEqual(r.status_code, 400)
        self.assertIn('motivo del cambio', r.json()['error'])

    def test_mismo_plan_sin_cambio_de_servicio_se_rechaza(self):
        """Un 'cambio' que no cambia nada no es un cambio de plan."""
        r = self._post_cambio('internet', 'internet', same_plan=True)
        self.assertEqual(r.status_code, 400)
        self.assertIn('son el mismo', r.json()['error'])

    def test_mismo_plan_si_cambia_la_variante_del_servicio(self):
        """Combo analogico -> combo digital si cambia el servicio: es real."""
        token = self._token(self.admin, 'pass1')
        combo = self.plans[('combo', 1)]
        r = self.client_.post('/api/sales', {
            'clientCode': 'CPV', 'clientName': 'Cambio de variante',
            'serviceType': 'combo_digital', 'requestType': 'cambio_plan',
            'planId': combo.id, 'planFromId': combo.id,
            'serviceTypeFrom': 'combo_analog',
            'motivoId': self.motivo_cambio.id,
        }, content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 201)

    def test_un_guardado_no_crea_duplicados(self):
        """Una sola operacion de guardado deja un unico movimiento."""
        self._post_cambio('combo', 'internet')
        self.assertEqual(
            Sale.objects.filter(clientCode='CP001', requestType='cambio_plan').count(), 1)

    def test_registros_previos_siguen_consultables(self):
        """Cambiar de nuevo mas adelante no borra el movimiento anterior."""
        self._post_cambio('combo', 'internet')
        primero = Sale.objects.get(clientCode='CP001')
        self._post_cambio('internet', 'combo', client_code='CP001')
        segundo = Sale.objects.get(clientCode='CP001', id__gt=primero.id)
        self.assertIsNotNone(primero.planFromId_id)
        self.assertEqual(primero.planFromId.type, 'combo')
        self.assertEqual(segundo.planFromId.type, 'internet')
        self.assertEqual(Sale.objects.filter(clientCode='CP001').count(), 2)

    def test_usuario_ventas_puede_registrar_la_conversion(self):
        token = self._token(self.ventas, 'pass2')
        r = self.client_.post('/api/sales', {
            'clientCode': 'CPV2', 'clientName': 'Registrado por ventas',
            'serviceType': 'internet', 'requestType': 'cambio_plan',
            'planId': self.plans[('internet', 1)].id,
            'planFromId': self.plans[('combo', 2)].id,
            'motivoId': self.motivo_cambio.id,
        }, content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Sale.objects.get(clientCode='CPV2').createdBy, self.ventas)

    def test_usuario_ventas_no_puede_editar_la_conversion(self):
        self._post_cambio('combo', 'internet')
        sale = Sale.objects.get(clientCode='CP001')
        token = self._token(self.ventas, 'pass2')
        r = self.client_.put(
            f'/api/sales/{sale.id}',
            {'clientName': 'MANIPULADO', 'serviceType': 'internet',
             'requestType': 'cambio_plan', 'planId': sale.plan_id,
             'planFromId': sale.planFromId_id, 'changeReason': 'X'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 403)
        sale.refresh_from_db()
        self.assertNotEqual(sale.clientName, 'MANIPULADO')

    def test_anonymous_no_puede_registrar(self):
        r = self.client_.post('/api/sales', {
            'clientCode': 'CPZ', 'clientName': 'Anonimo',
            'serviceType': 'internet', 'requestType': 'cambio_plan',
            'planId': self.plans[('internet', 1)].id,
            'planFromId': self.plans[('combo', 2)].id,
            'changeReason': 'X',
        }, content_type='application/json')
        self.assertEqual(r.status_code, 401)

    def test_edicion_conserva_el_mismo_criterio_de_cobro(self):
        """Editar un cambio de plan no debe sumar la instalacion."""
        self._post_cambio('combo', 'internet')
        sale = Sale.objects.get(clientCode='CP001')
        self.assertEqual(sale.total, self.plans[('internet', 1)].monthly)
        token = self._token(self.admin, 'pass1')
        r = self.client_.put(
            f'/api/sales/{sale.id}',
            {'serviceType': 'internet', 'requestType': 'cambio_plan',
             'planId': self.plans[('internet', 2)].id,
             'planFromId': self.plans[('combo', 2)].id,
             'changeReason': 'POCO USO'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 200)
        sale.refresh_from_db()
        self.assertEqual(sale.total, self.plans[('internet', 2)].monthly)
        self.assertEqual(sale.applied_installation, Decimal('0'))

    def test_edicion_rechaza_plan_incompatible(self):
        self._post_cambio('combo', 'internet')
        sale = Sale.objects.get(clientCode='CP001')
        token = self._token(self.admin, 'pass1')
        r = self.client_.put(
            f'/api/sales/{sale.id}',
            {'serviceType': 'internet', 'requestType': 'cambio_plan',
             'planId': self.plans[('combo', 1)].id,
             'planFromId': self.plans[('combo', 2)].id,
             'changeReason': 'X'},
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 400)
        sale.refresh_from_db()
        self.assertEqual(sale.plan_id, self.plans[('internet', 1)].id)

    def test_plan_anterior_no_se_puede_borrar(self):
        """Borrar el plan anterior dejaria el historico sin origen."""
        self._post_cambio('combo', 'internet')
        anterior = self.plans[('combo', 2)]
        token = self._token(self.admin, 'pass1')
        r = self.client_.delete(f'/api/plans/{anterior.id}',
                                HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 400)
        self.assertTrue(Plan.objects.filter(id=anterior.id).exists())
        sale = Sale.objects.get(clientCode='CP001')
        self.assertIsNotNone(sale.planFromId_id)

    def test_plan_anterior_inactivo_sigue_siendo_valido(self):
        """El cliente puede estar en un plan que ya no se vende."""
        retirado = self.plans[('combo', 2)]
        retirado.active = False
        retirado.save()
        r = self._post_cambio('combo', 'internet')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Sale.objects.get(clientCode='CP001').planFromId_id,
                         retirado.id)

    def test_filtro_por_servicio_anterior(self):
        self._post_cambio('combo', 'internet', client_code='F1')
        self._post_cambio('internet', 'combo', client_code='F2')
        token = self._token(self.admin, 'pass1')
        r = self.client_.get('/api/sales?requestType=cambio_plan&serviceTypeFrom=combo_analog',
                             HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(r.status_code, 200)
        codigos = {i['clientCode'] for i in r.json()['items']}
        self.assertEqual(codigos, {'F1'})

    def test_reporte_excel_muestra_la_conversion(self):
        import io
        import openpyxl
        from .reports import build_sales_xlsx
        self._post_cambio('combo', 'internet')
        self._post_cambio('internet', 'combo', client_code='CP002')
        hoy = timezone.localdate().isoformat()
        buf = build_sales_xlsx(hoy, hoy, 'cambio_plan')
        ws = openpyxl.load_workbook(io.BytesIO(buf.getvalue())).active
        servicios = [r[3] for r in ws.iter_rows(min_row=2, values_only=True) if r[0]]
        self.assertIn('COMBO → INTERNET', servicios)
        self.assertIn('INTERNET → COMBO', servicios)

    def test_los_tres_formatos_generan_sin_error(self):
        from .reports import build_sales_pdf, build_sales_png, build_sales_xlsx
        self._post_cambio('combo', 'internet')
        hoy = timezone.localdate().isoformat()
        self.assertTrue(build_sales_pdf(hoy, hoy, 'cambio_plan').getvalue())
        self.assertTrue(build_sales_xlsx(hoy, hoy, 'cambio_plan').getvalue())
        self.assertTrue(build_sales_png(hoy, hoy, 'cambio_plan').getvalue())
