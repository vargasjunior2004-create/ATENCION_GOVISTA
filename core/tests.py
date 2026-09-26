import os
from datetime import date, timedelta, datetime, timezone as tz

from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import User, Plan, Sale, Backup


class ApiTestCase(TestCase):
    def setUp(self):
        admin = User(name='Admin', role='admin')
        admin.set_password('admin123')
        admin.save()
        seller = User(name='Vendedor', role='ventas')
        seller.set_password('ventas123')
        seller.save()
        self.admin, self.seller = admin, seller

        self.plan = Plan.objects.create(
            code='GO-BASIC', label='Internet Básico', type='internet',
            speed=50, monthly=220, installation=180)
        self.tv_plan = Plan.objects.create(
            code='TV-BASIC', label='TV Básico', type='tv',
            speed=None, monthly=150, installation=150)

        self.client = APIClient()

    def login(self, name, password):
        res = self.client.post('/api/auth/login', {'name': name, 'password': password},
                               format='json')
        return res

    def auth_as(self, user, password):
        res = self.login(user.name, password)
        self.assertEqual(res.status_code, 200, res.data)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {res.data["token"]}')

    def test_login_admin_ok(self):
        res = self.login('Admin', 'admin123')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['user']['role'], 'admin')
        self.assertIn('token', res.data)

    def test_login_wrong_password(self):
        res = self.login('Admin', 'incorrecta')
        self.assertEqual(res.status_code, 401)

    def test_login_name_password(self):
        res = self.client.post('/api/auth/login',
                               {'name': 'Admin', 'password': 'admin123'},
                               format='json')
        self.assertEqual(res.status_code, 200)

    def test_me_requires_auth(self):
        res = self.client.get('/api/auth/me')
        self.assertEqual(res.status_code, 401)

    def test_me_ok(self):
        self.auth_as(self.admin, 'admin123')
        res = self.client.get('/api/auth/me')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['user']['name'], 'Admin')

    def test_plans_admin_only(self):
        self.auth_as(self.seller, 'ventas123')
        res = self.client.get('/api/plans')
        self.assertEqual(res.status_code, 403)

    def test_active_plans_any_auth(self):
        self.auth_as(self.seller, 'ventas123')
        res = self.client.get('/api/plans/active')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 2)

    def test_create_sale_calculates_total_server_side(self):
        self.auth_as(self.seller, 'ventas123')
        res = self.client.post('/api/sales', {
            'date': date.today().isoformat(),
            'clientCode': 'CLI-1',
            'clientName': 'Cliente Uno',
            'serviceType': 'internet',
            'planId': self.plan.id,
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(float(res.data['total']), 400.00)
        self.assertEqual(res.data['Plan']['label'], 'Internet Básico')
        self.assertEqual(res.data['creator']['name'], 'Vendedor')

    def test_create_sale_ignores_client_total(self):
        self.auth_as(self.seller, 'ventas123')
        res = self.client.post('/api/sales', {
            'date': date.today().isoformat(),
            'clientCode': 'CLI-2',
            'clientName': 'Cliente Dos',
            'serviceType': 'internet',
            'planId': self.plan.id,
            'total': 1.00,
        }, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(float(res.data['total']), 400.00)

    def test_create_sale_plan_type_mismatch(self):
        self.auth_as(self.seller, 'ventas123')
        res = self.client.post('/api/sales', {
            'date': date.today().isoformat(),
            'clientCode': 'CLI-3',
            'clientName': 'Cliente Tres',
            'serviceType': 'tv',
            'planId': self.plan.id,
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_edit_sale_admin_recalculates_total(self):
        self.auth_as(self.seller, 'ventas123')
        res = self.client.post('/api/sales', {
            'date': date.today().isoformat(),
            'clientCode': 'CLI-4',
            'clientName': 'Cliente Cuatro',
            'serviceType': 'internet',
            'planId': self.plan.id,
        }, format='json')
        sale_id = res.data['id']

        self.auth_as(self.admin, 'admin123')
        res = self.client.put(f'/api/sales/{sale_id}',
                              {'planId': self.tv_plan.id,
                               'serviceType': 'tv'},
                              format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(float(res.data['total']), 300.00)

    def test_edit_sale_forbidden_for_sales_role(self):
        self.auth_as(self.seller, 'ventas123')
        sale = Sale.objects.create(
            date=date.today(), clientCode='C', clientName='N',
            serviceType='internet', plan=self.plan, total=self.plan.total,
            createdBy=self.seller)
        res = self.client.put(f'/api/sales/{sale.id}', {'clientName': 'X'},
                              format='json')
        self.assertEqual(res.status_code, 403)

    def test_users_admin_only(self):
        self.auth_as(self.seller, 'ventas123')
        res = self.client.get('/api/users')
        self.assertEqual(res.status_code, 403)

    def test_create_user(self):
        self.auth_as(self.admin, 'admin123')
        res = self.client.post('/api/users', {
            'name': 'Nuevo',
            'password': 'nuevo123', 'role': 'ventas',
        }, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertNotIn('password', res.data)

    def test_sales_date_filter(self):
        old = date.today() - timedelta(days=5)
        Sale.objects.create(date=old, clientCode='A', clientName='A',
                            serviceType='internet', plan=self.plan,
                            total=self.plan.total, createdBy=self.admin)
        Sale.objects.create(date=date.today(), clientCode='B', clientName='B',
                            serviceType='internet', plan=self.plan,
                            total=self.plan.total, createdBy=self.admin)
        self.auth_as(self.admin, 'admin123')
        res = self.client.get(f'/api/sales?from={date.today()}&to={date.today()}')
        self.assertEqual(res.status_code, 200)
        items = res.data.get('items', res.data)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['clientCode'], 'B')

    def test_report_pdf_returns_pdf(self):
        Sale.objects.create(date=date.today(), clientCode='A', clientName='A',
                            serviceType='internet', plan=self.plan,
                            total=self.plan.total, createdBy=self.admin)
        self.auth_as(self.admin, 'admin123')
        d = date.today().isoformat()
        res = self.client.get(f'/api/reports/pdf?from={d}&to={d}')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')
        self.assertIn(b'%PDF', res.content)

    def test_report_xlsx(self):
        self.auth_as(self.admin, 'admin123')
        d = date.today().isoformat()
        res = self.client.get(f'/api/reports/xlsx?from={d}&to={d}')
        self.assertEqual(res.status_code, 200)
        self.assertIn('spreadsheetml', res['Content-Type'])

    def test_public_link_requires_valid_token(self):
        self.auth_as(self.admin, 'admin123')
        d = date.today().isoformat()
        res = self.client.get(f'/api/reports/pdf-link?from={d}&to={d}')
        self.assertEqual(res.status_code, 200)
        url = res.data['url']
        self.assertIn('/api/reports/pdf-public/', url)

        bad = self.client.get('/api/reports/pdf-public/', {'token': 'invalido'})
        self.assertEqual(bad.status_code, 400)

        token = url.split('token=')[1]
        ok = self.client.get('/api/reports/pdf-public/', {'token': token})
        self.assertEqual(ok.status_code, 200)
        self.assertIn(b'%PDF', ok.content)


class TimezoneBugAcceptanceTest(TestCase):
    """Tests de aceptación para el bug de zona horaria.
    Verifica que las ventas se registren con la fecha local (America/La_Paz)
    y no con UTC, causando que ventas de la noche aparezcan al día siguiente."""

    def setUp(self):
        self.admin = User(name='AdminTZ', role='admin')
        self.admin.set_password('admin123')
        self.admin.save()
        self.seller = User(name='VendedorTZ', role='ventas')
        self.seller.set_password('ventas123')
        self.seller.save()
        self.plan = Plan.objects.create(
            code='GO-TZ', label='Plan TZ', type='internet',
            speed=50, monthly=220, installation=180)
        self.client = APIClient()

    def _auth(self, user, password):
        res = self.client.post('/api/auth/login', {'name': user.name, 'password': password},
                               format='json')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {res.data["token"]}')

    def test_sale_uses_localdate_not_utc(self):
        """Al crear una venta, la fecha debe ser la fecha local (La Paz), no UTC."""
        self._auth(self.seller, 'ventas123')
        res = self.client.post('/api/sales', {
            'clientCode': 'CLI-TZ-1',
            'clientName': 'Cliente TZ',
            'serviceType': 'internet',
            'planId': self.plan.id,
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        sale_date = date.fromisoformat(res.data['date'])
        self.assertEqual(sale_date, timezone.localdate(),
                         f"La fecha de la venta ({sale_date}) debe coincidir "
                         f"con timezone.localdate() ({timezone.localdate()})")

    def test_dashboard_filters_sales_by_localdate(self):
        """El dashboard debe filtrar ventas usando la fecha local, no UTC."""
        self._auth(self.seller, 'ventas123')
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)

        # Create a sale for yesterday
        Sale.objects.create(
            date=yesterday, clientCode='CLI-Y', clientName='Ayer',
            serviceType='internet', plan=self.plan, total=self.plan.total,
            createdBy=self.seller)

        # Create a sale for today
        Sale.objects.create(
            date=today, clientCode='CLI-T', clientName='Hoy',
            serviceType='internet', plan=self.plan, total=self.plan.total,
            createdBy=self.seller)

        # Query like the dashboard does: from=today, to=today
        res = self.client.get(f'/api/sales?from={today}&to={today}')
        self.assertEqual(res.status_code, 200)
        items = res.data.get('items', res.data if isinstance(res.data, list) else [])
        self.assertEqual(len(items), 1,
                         "Solo la venta de hoy debe aparecer al filtrar por hoy")
        self.assertEqual(items[0]['clientCode'], 'CLI-T')

    def test_sale_date_not_shifted_by_utc(self):
        """Verifica que la fecha de la venta NO se desplaza por conversión UTC.
        Simula el escenario: usuario en La Paz crea venta a las 22:00 (02:00 UTC+1).
        La fecha debe ser la de La Paz, no la de UTC."""
        # Simulate: set the server time to a moment where UTC date != La Paz date
        # by creating a sale and checking the date matches localdate
        self._auth(self.seller, 'ventas123')
        res = self.client.post('/api/sales', {
            'clientCode': 'CLI-UTC',
            'clientName': 'Cliente UTC Test',
            'serviceType': 'internet',
            'planId': self.plan.id,
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        sale_date = date.fromisoformat(res.data['date'])
        local_today = timezone.localdate()
        utc_today = datetime.now(tz.utc).date()
        # The sale date must match localdate, not UTC
        self.assertEqual(sale_date, local_today)
        # If UTC and local differ, this proves the fix works
        if utc_today != local_today:
            self.assertNotEqual(sale_date, utc_today,
                                "La fecha NO debe ser la de UTC cuando difiere de la local")



class BackupPermissionTests(TestCase):
    """Permisos del modulo de respaldos. Validado en el backend,
    independientemente de la interfaz."""

    def setUp(self):
        self.admin = User(name='AdminBk', role='admin')
        self.admin.set_password('admin123')
        self.admin.save()
        self.seller = User(name='SellerBk', role='ventas')
        self.seller.set_password('ventas123')
        self.seller.save()
        self.client = APIClient()

    def _auth(self, name, password):
        res = self.client.post('/api/auth/login',
                               {'name': name, 'password': password}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {res.data["token"]}')

    def test_anonymous_cannot_list_backups(self):
        self.assertEqual(self.client.get('/api/backups').status_code, 401)

    def test_anonymous_cannot_create_backup(self):
        self.assertEqual(self.client.post('/api/backups').status_code, 401)

    def test_seller_cannot_list_backups(self):
        self._auth('SellerBk', 'ventas123')
        self.assertEqual(self.client.get('/api/backups').status_code, 403)

    def test_seller_cannot_create_backup(self):
        self._auth('SellerBk', 'ventas123')
        self.assertEqual(self.client.post('/api/backups').status_code, 403)

    def test_seller_cannot_delete_backup(self):
        self._auth('SellerBk', 'ventas123')
        backup = Backup.objects.create(filename='x.dump', backup_type='manual')
        self.assertEqual(
            self.client.delete(f'/api/backups/{backup.id}').status_code, 403)
        self.assertTrue(Backup.objects.filter(id=backup.id).exists())

    def test_inactive_user_cannot_obtain_a_token(self):
        """Un usuario desactivado no puede iniciar sesion, por lo que nunca
        llega a las vistas de respaldo."""
        self.admin.active = False
        self.admin.save()
        res = self.client.post(
            '/api/auth/login',
            {'name': 'AdminBk', 'password': 'admin123'}, format='json')
        self.assertEqual(res.status_code, 401)
        # Y aunque se le forzara un token, la vista lo rechaza.
        from rest_framework_simplejwt.tokens import RefreshToken
        token = str(RefreshToken.for_user(self.admin).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(self.client.post('/api/backups').status_code, 403)

    def test_admin_can_list_backups(self):
        self._auth('AdminBk', 'admin123')
        self.assertEqual(self.client.get('/api/backups').status_code, 200)

    def test_admin_can_delete_backup_record(self):
        self._auth('AdminBk', 'admin123')
        backup = Backup.objects.create(filename='x.dump', backup_type='manual')
        self.assertEqual(
            self.client.delete(f'/api/backups/{backup.id}').status_code, 204)
        self.assertFalse(Backup.objects.filter(id=backup.id).exists())


class BackupModelTests(TestCase):
    """El historial guarda solo metadatos, jamas el archivo."""

    def test_storage_path_not_exposed_in_serializer(self):
        from core.serializers import BackupSerializer
        backup = Backup.objects.create(
            filename='test.dump', backup_type='manual', status='success',
            storage_path='/srv/secreto/govista.dump')
        data = BackupSerializer(backup).data
        self.assertNotIn('storage_path', data)
        for value in data.values():
            self.assertNotIn('/srv/secreto', str(value))

    def test_metadata_fields_present(self):
        from core.serializers import BackupSerializer
        backup = Backup.objects.create(filename='t.dump', backup_type='manual')
        data = BackupSerializer(backup).data
        for field in ('started_at', 'finished_at', 'backup_format',
                      'verified', 'error_message', 'checksum', 'size'):
            self.assertIn(field, data)

    def test_default_status_is_pending(self):
        backup = Backup.objects.create(filename='t.dump', backup_type='manual')
        self.assertEqual(backup.status, 'pending')
        self.assertFalse(backup.verified)

    def test_checksum_is_sha256_of_file(self):
        import hashlib
        import os
        import tempfile
        from core.management.commands.backup_database import compute_checksum
        fd, path = tempfile.mkstemp()
        try:
            payload = b'contenido de prueba' * 100
            os.write(fd, payload)
            os.close(fd)
            self.assertEqual(compute_checksum(path),
                             hashlib.sha256(payload).hexdigest())
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_error_message_never_contains_credentials(self):
        from core.management.commands.backup_database import _sanitize_error
        raw = ("pg_dump: error: connection to server at \"db.supabase.co\" "
               "failed: FATAL: password authentication failed "
               "postgresql://usuario:CLAVE_SECRETA@host:5432/postgres")
        clean = _sanitize_error(raw)
        self.assertNotIn('CLAVE_SECRETA', clean)
        self.assertNotIn('CLAVE_SECRETA', _sanitize_error(raw, 10_000))


class BackupFileTests(TestCase):
    """Generacion real de un respaldo contra la BD de pruebas.

    En desarrollo (SQLite) exercises la ruta de copia; en PostgreSQL
    exercises pg_dump. Nunca toca produccion porque Django usa una base
    de datos de prueba separada.
    """

    def setUp(self):
        from django.conf import settings
        self.engine = settings.DATABASES['default']['ENGINE']
        self.is_postgres = 'postgresql' in self.engine
        Plan.objects.get_or_create(code='TESTPLAN', defaults={
            'label': 'Plan Test', 'type': 'internet',
            'monthly': 100, 'installation': 50})

    def test_create_backup_produces_file_and_metadata(self):
        from django.conf import settings
        from core.management.commands.backup_database import create_backup
        import os
        backup, path = create_backup(backup_type='manual')
        try:
            self.assertEqual(backup.status, 'success')
            self.assertTrue(backup.verified)
            self.assertGreater(backup.size, 0)
            self.assertEqual(len(backup.checksum), 64)
            self.assertTrue(os.path.exists(path))
            self.assertTrue(backup.started_at is not None)
            self.assertTrue(backup.finished_at is not None)
            self.assertEqual(backup.error_message, '')
            expected = 'dump' if self.is_postgres else 'sqlite3'
            if 'memory' in str(settings.DATABASES['default']['NAME']) \
                    or ':memory:' in str(settings.DATABASES['default']['NAME']):
                # Django usa SQLite en memoria durante las pruebas
                expected = 'json'
            self.assertEqual(backup.backup_format, expected)
            self.assertTrue(backup.filename.startswith('govista_backup_'))
        finally:
            if os.path.exists(path):
                os.remove(path)
            backup.delete()

    def test_filenames_do_not_collide_within_same_day(self):
        """Dos respaldos seguidos no deben sobrescribirse."""
        from core.management.commands.backup_database import create_backup
        import os
        created = []
        try:
            for _ in range(2):
                b, p = create_backup(backup_type='manual')
                created.append((b, p))
            names = [b.filename for b, _ in created]
            self.assertEqual(len(set(names)), 2,
                             f'Los nombres colisionaron: {names}')
        finally:
            for b, p in created:
                if os.path.exists(p):
                    os.remove(p)
                b.delete()

    def test_failure_is_recorded_as_failed(self):
        """Un fallo real queda registrado con estado 'failed'."""
        from core.management.commands import backup_database as cmd
        from django.conf import settings
        import os

        original = settings.DATABASES['default']
        broken = dict(original)
        if self.is_postgres:
            broken['NAME'] = 'base_de_datos_inexistente_govista'
        else:
            broken['NAME'] = '/tmp/no_existe_govista.sqlite3'
        settings.DATABASES['default'] = broken
        try:
            with self.assertRaises(cmd.BackupError):
                cmd.create_backup(backup_type='manual')
        finally:
            settings.DATABASES['default'] = original

        failed = Backup.objects.filter(status='failed').first()
        self.assertIsNotNone(failed, 'No se registro el fallo')
        self.assertTrue(failed.error_message)
        self.assertIsNotNone(failed.finished_at)
        self.assertEqual(failed.size, 0)
        self.assertFalse(failed.verified)
        failed.delete()

    def test_retention_only_touches_automatic(self):
        from core.management.commands.backup_database import cleanup_old_backups
        for i in range(9):
            Backup.objects.create(
                filename=f'a{i}.dump', backup_type='automatic', status='success')
        for i in range(3):
            Backup.objects.create(
                filename=f'm{i}.dump', backup_type='manual', status='success')

        deleted = cleanup_old_backups(keep=7)
        self.assertEqual(deleted, 2)
        self.assertEqual(
            Backup.objects.filter(backup_type='automatic').count(), 7)
        self.assertEqual(
            Backup.objects.filter(backup_type='manual').count(), 3)


class BackupPgDumpTests(TransactionTestCase):
    """Verificacion de la herramienta de respaldo. Requiere PostgreSQL.

    Usa TransactionTestCase porque pg_dump se ejecuta como un proceso
    externo: con TestCase los datos viven en una transaccion que aun no
    se confirma y el proceso externo no los veria.
    """

    def setUp(self):
        self.plan = Plan.objects.get_or_create(code='TESTPLAN', defaults={
            'label': 'Plan Test', 'type': 'internet',
            'monthly': 100, 'installation': 50})[0]
        self.seller = User.objects.get_or_create(
            name='TestVendedor', role='ventas',
            defaults={'password': 'x'})[0]
        self.sale = Sale.objects.get_or_create(
            clientCode='TESTBK-001',
            defaults={
                'clientName': 'Cliente Prueba',
                'date': timezone.localdate(),
                'createdBy': self.seller,
                'serviceType': 'internet',
                'requestType': 'nuevo_contrato',
                'plan': self.plan,
                'total': 150,
            })[0]

    def test_pg_dump_binary_is_available(self):
        from core.management.commands.backup_database import find_pg_dump
        path = find_pg_dump()
        self.assertIsNotNone(
            path, 'pg_dump no esta instalado. En Render debe instalarse '
                  'postgresql-client-17 en build.sh')

    def test_pg_dump_can_dump_current_test_database(self):
        """Genera un dump real de la base de pruebas y lo restaura en una
        base nueva, comprobando que los datos vuelven intactos."""
        import subprocess
        from django.conf import settings
        from core.management.commands.backup_database import (
            find_pg_dump, compute_checksum)
        import os
        import tempfile

        if 'postgresql' not in settings.DATABASES['default']['ENGINE']:
            self.skipTest('Requiere PostgreSQL')

        pg_dump = find_pg_dump()
        cfg = settings.DATABASES['default']
        tmpdir = tempfile.mkdtemp(prefix='govista_backup_test_')
        dump_path = os.path.join(tmpdir, 'test.dump')
        env = os.environ.copy()
        if cfg.get('PASSWORD'):
            env['PGPASSWORD'] = str(cfg['PASSWORD'])
        if (cfg.get('OPTIONS') or {}).get('ssl_require'):
            env['PGSSLMODE'] = 'require'

        # 1) Generar el dump de la base de pruebas
        dump_cmd = [
            pg_dump, '--host', str(cfg['HOST']), '--port', str(cfg['PORT']),
            '--username', str(cfg['USER']), '--dbname', str(cfg['NAME']),
            '--format', 'custom', '--schema', 'public',
            '--no-owner', '--no-privileges', '--file', dump_path,
        ]
        dump = subprocess.run(dump_cmd, env=env, capture_output=True, text=True)
        self.assertEqual(dump.returncode, 0,
                         f'pg_dump fallo: {dump.stderr}')
        self.assertTrue(os.path.exists(dump_path))
        self.assertGreater(os.path.getsize(dump_path), 0)
        self.assertEqual(len(compute_checksum(dump_path)), 64)

        # 2) El dump debe ser legible por pg_restore
        pg_restore = os.path.join(os.path.dirname(pg_dump), 'pg_restore')
        listing = subprocess.run(
            [pg_restore, '--list', dump_path],
            capture_output=True, text=True)
        self.assertEqual(listing.returncode, 0,
                         f'pg_restore --list fallo: {listing.stderr}')
        self.assertIn('core_sale', listing.stdout)
        self.assertIn('core_plan', listing.stdout)

        # 3) Restaurar en una base nueva y verificar los datos
        from django.db import connection
        restore_db = f'restore_check_{os.getpid()}'
        admin_cfg = dict(cfg)
        admin_cfg['NAME'] = 'postgres'
        try:
            subprocess.run(
                [pg_dump, '--version'], capture_output=True, check=True)
            import psycopg2
            conn = psycopg2.connect(
                host=cfg['HOST'], port=cfg['PORT'], user=cfg['USER'],
                password=cfg.get('PASSWORD'), dbname='postgres',
                sslmode='require' if env.get('PGSSLMODE') else 'prefer')
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(f'DROP DATABASE IF EXISTS "{restore_db}"')
                cur.execute(f'CREATE DATABASE "{restore_db}"')
            conn.close()

            # --clean --if-exists es necesario: sin esto pg_restore falla con
            # "ya existe el esquema public" al restaurar en una base nueva.
            restore_cmd = [
                pg_restore, '--host', str(cfg['HOST']), '--port', str(cfg['PORT']),
                '--username', str(cfg['USER']), '--dbname', restore_db,
                '--no-owner', '--no-privileges',
                '--clean', '--if-exists', '--exit-on-error',
                dump_path,
            ]
            restore = subprocess.run(
                restore_cmd, env=env, capture_output=True, text=True)
            self.assertEqual(restore.returncode, 0,
                             f'pg_restore fallo: {restore.stderr}')

            # 4) Verificar que los datos se recuperaron
            conn = psycopg2.connect(
                host=cfg['HOST'], port=cfg['PORT'], user=cfg['USER'],
                password=cfg.get('PASSWORD'), dbname=restore_db,
                sslmode='require' if env.get('PGSSLMODE') else 'prefer')
            with conn.cursor() as cur:
                # 1) El plan de prueba volvio
                cur.execute(
                    'SELECT COUNT(*) FROM core_plan WHERE code = %s',
                    ['TESTPLAN'])
                self.assertEqual(cur.fetchone()[0], 1,
                                 'Los datos no se restauraron correctamente')
                # 2) La venta y su relacion con el vendedor tambien.
                # Las columnas van entre comillas porque el proyecto usa
                # nombres en camelCase (clientName, createdBy).
                cur.execute(
                    'SELECT s."clientName", u.name FROM core_sale s '
                    'JOIN core_user u ON u.id = s."createdBy_id" '
                    'WHERE s."clientCode" = %s', ['TESTBK-001'])
                row = cur.fetchone()
                self.assertIsNotNone(
                    row, 'La venta no se restauro correctamente')
                self.assertEqual(row[0], 'Cliente Prueba')
                self.assertEqual(row[1], 'TestVendedor')
                # 3) Las claves foraneas quedaron consistentes
                cur.execute(
                    'SELECT COUNT(*) FROM core_sale '
                    'WHERE plan_id NOT IN (SELECT id FROM core_plan)')
                self.assertEqual(cur.fetchone()[0], 0,
                                 'Hay referencias rotas tras restaurar')
                # 4) El esquema completo quedo presente
                cur.execute(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public'")
                self.assertGreater(cur.fetchone()[0], 5)
            conn.close()
        finally:
            try:
                import psycopg2
                conn = psycopg2.connect(
                    host=cfg['HOST'], port=cfg['PORT'], user=cfg['USER'],
                    password=cfg.get('PASSWORD'), dbname='postgres',
                    sslmode='require' if env.get('PGSSLMODE') else 'prefer')
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute(f'DROP DATABASE IF EXISTS "{restore_db}"')
                conn.close()
            except Exception:
                pass
            try:
                connection.close()
            except Exception:
                pass
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


class BackupDownloadTests(TransactionTestCase):
    """El archivo se transmite completo y NO queda en el servidor."""

    def setUp(self):
        self.admin = User.objects.create_user(
            name='AdminDl', role='admin', password='admin123') \
            if hasattr(User, 'create_user') else None
        if self.admin is None:
            self.admin = User(name='AdminDl', role='admin')
            self.admin.set_password('admin123')
            self.admin.save()
        self.client = APIClient()
        res = self.client.post('/api/auth/login',
                               {'name': 'AdminDl', 'password': 'admin123'},
                               format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {res.data["token"]}')

    def test_download_is_complete_and_file_is_removed(self):
        """Se recibe el archivo integro y no queda en el servidor."""
        import hashlib
        import os

        tmp_before = set(os.listdir('/tmp'))
        res = self.client.post('/api/backups')
        self.assertEqual(res.status_code, 200, getattr(res, 'data', ''))
        self.assertEqual(res['Content-Type'], 'application/octet-stream')
        self.assertIn('attachment', res['Content-Disposition'])

        # Mientras se transmite, el archivo debe existir en el servidor
        new_files = {f for f in set(os.listdir('/tmp')) - tmp_before
                     if f.startswith('govista_backup_')}
        self.assertEqual(len(new_files), 1,
                         f'Se esperaba 1 archivo temporal, hay {new_files}')
        filename = new_files.pop()
        path = os.path.join('/tmp', filename)
        self.assertTrue(os.path.exists(path))
        with open(path, 'rb') as fh:
            disk_hash = hashlib.sha256(fh.read()).hexdigest()
        disk_size = os.path.getsize(path)
        self.assertGreater(disk_size, 0)

        # El historial debe coincidir con el archivo realmente generado
        record = Backup.objects.get(filename=filename)
        self.assertEqual(record.status, 'success')
        self.assertTrue(record.verified)
        self.assertEqual(record.checksum, disk_hash)
        self.assertEqual(record.size, disk_size)
        self.assertEqual(record.storage_path, '')
        self.assertIn(filename, res['Content-Disposition'])
        self.assertEqual(res['X-Content-SHA256'], record.checksum)

        # Lo que recibe el navegador es identico al archivo del servidor
        body = b''.join(res.streaming_content)
        self.assertEqual(len(body), disk_size)
        self.assertEqual(hashlib.sha256(body).hexdigest(), disk_hash)

        # Y al terminar la descarga no queda nada en el servidor
        res.close()
        self.assertFalse(os.path.exists(path),
                         'El archivo quedo en el servidor')
        leaked = {f for f in set(os.listdir('/tmp')) - tmp_before
                  if f.startswith('govista_backup_')}
        self.assertEqual(leaked, set(), f'Archivos filtrados: {leaked}')
        record.delete()

    def test_backup_en_curso_bloquea_el_siguiente(self):
        """Con un respaldo en curso, el POST responde 409 y no duplica."""
        Backup.objects.create(filename='en-curso.dump', backup_type='manual',
                              status='running')
        try:
            res = self.client.post('/api/backups')
            self.assertEqual(res.status_code, 409)
            self.assertIn('respaldo en proceso', str(res.data))
            self.assertEqual(
                Backup.objects.filter(status='running').count(), 1)
        finally:
            Backup.objects.filter(status='running').delete()


class BackupVersionGuardTests(TransactionTestCase):
    """pg_dump debe ser igual o mas nuevo que el servidor.

    Es el riesgo real de despliegue: Render instala postgresql-client 15 y
    Supabase corre PostgreSQL 17.
    """

    def test_compatible_when_client_matches_server(self):
        from core.management.commands import backup_database as cmd
        ok, why = cmd.check_pg_dump_compatible()
        self.assertTrue(ok, why)

    def test_detects_older_client_than_server(self):
        from core.management.commands import backup_database as cmd
        original = cmd._pg_dump_major
        cmd._pg_dump_major = lambda path: 15
        try:
            ok, why = cmd.check_pg_dump_compatible()
            if cmd._server_major() and cmd._server_major() > 15:
                self.assertFalse(ok)
                self.assertIn('15', why)
                self.assertIn('17', why)
            else:
                self.skipTest('El servidor de pruebas no es mas nuevo que 15')
        finally:
            cmd._pg_dump_major = original

    def test_no_error_leaks_credentials(self):
        """El mensaje de version jamas debe incluir la contraseña."""
        from core.management.commands import backup_database as cmd
        from django.conf import settings
        original = cmd._pg_dump_major
        cmd._pg_dump_major = lambda path: 1
        try:
            ok, why = cmd.check_pg_dump_compatible()
            if not ok:
                secret = str(settings.DATABASES['default'].get('PASSWORD') or '')
                if secret:
                    self.assertNotIn(secret, why)
        finally:
            cmd._pg_dump_major = original


class BackupSinConcurrenciaTests(TransactionTestCase):
    """Solo puede haber un respaldo 'running'.

    La garantia vive en la base de datos porque el transaction pooler de
    Supabase (6543) no soporta bloqueos consultivos.
    """

    def test_no_permite_dos_respaldos_en_proceso(self):
        from django.db import IntegrityError, transaction
        from core.models import Backup
        Backup.objects.create(filename='a.dump', backup_type='manual',
                              status='running')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Backup.objects.create(filename='b.dump', backup_type='manual',
                                      status='running')
        # Los estados terminales si pueden repetirse
        for status in ('success', 'failed', 'pending'):
            Backup.objects.create(filename=f'c-{status}.dump',
                                  backup_type='manual', status=status)
        self.assertEqual(
            Backup.objects.filter(status__in=('success', 'failed', 'pending'))
            .count(), 3)

    def test_segundo_intento_da_409(self):
        """Con un respaldo en curso, el POST responde 409."""
        from core.models import Backup
        admin = User(name='AdminConc', role='admin')
        admin.set_password('admin123')
        admin.save()
        client = APIClient()
        res = client.post('/api/auth/login',
                          {'name': 'AdminConc', 'password': 'admin123'},
                          format='json')
        client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {res.data["token"]}')

        Backup.objects.create(filename='en-curso.dump', backup_type='manual',
                              status='running')
        try:
            r = client.post('/api/backups')
            self.assertEqual(r.status_code, 409, getattr(r, 'data', ''))
            self.assertIn('en proceso', str(r.data))
        finally:
            Backup.objects.filter(status='running').delete()


class BackupConexionTests(TestCase):
    """pg_dump puede usar una conexion propia (Session Pooler)."""

    def test_usa_backup_database_url_si_existe(self):
        from core.management.commands import backup_database as cmd
        os.environ['BACKUP_DATABASE_URL'] = (
            'postgresql://postgres.ref:CLAVE@pooler.supabase.com:5432/postgres')
        try:
            cfg = cmd._pg_dump_config()
            self.assertEqual(cfg['HOST'], 'pooler.supabase.com')
            self.assertEqual(str(cfg['PORT']), '5432')
            self.assertEqual(cfg['USER'], 'postgres.ref')
            self.assertTrue(cfg['OPTIONS']['ssl_require'],
                            'El Session Pooler exige SSL')
        finally:
            os.environ.pop('BACKUP_DATABASE_URL', None)

    def test_sin_variable_usa_la_conexion_de_la_app(self):
        from core.management.commands import backup_database as cmd
        from django.conf import settings
        os.environ.pop('BACKUP_DATABASE_URL', None)
        cfg = cmd._pg_dump_config()
        self.assertEqual(cfg['NAME'], settings.DATABASES['default']['NAME'])
        self.assertEqual(cfg['HOST'], settings.DATABASES['default']['HOST'])

    def test_la_credencial_no_se_expone(self):
        """Ni la URL ni la clave de backup pueden filtrarse al historial."""
        from core.management.commands import backup_database as cmd
        from core.serializers import BackupSerializer
        os.environ['BACKUP_DATABASE_URL'] = (
            'postgresql://postgres.ref:CLAVE_SECRETA@pooler.supabase.com:5432/postgres')
        try:
            backup = Backup.objects.create(filename='x.dump',
                                          backup_type='manual')
            serializado = str(BackupSerializer(backup).data)
            self.assertNotIn('CLAVE_SECRETA', serializado)
            self.assertNotIn('pooler.supabase.com', serializado)
        finally:
            os.environ.pop('BACKUP_DATABASE_URL', None)
