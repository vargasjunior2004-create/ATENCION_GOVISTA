"""Seed de datos mock: usuarios, planes y ventas.

Uso:
    python manage.py seed            # solo si las tablas están vacías
    python manage.py seed --force    # borra y re-seedea
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import User, Plan, Sale

USERS = [
    ('Administrador', 'admin123', 'admin'),
    ('JUNIOR', 'admin123', 'admin'),
]

PLANS = [
    ('GO-BASIC', 'Internet Básico', 'internet', 50, 220, 180),
    ('GO-MAX', 'Internet Max', 'internet', 100, 300, 200),
    ('GO-ULTRA', 'Internet Ultra', 'internet', 200, 400, 250),
    ('TV-BASIC', 'TV Cable Básico', 'tv', None, 150, 150),
    ('TV-PREMIUM', 'TV Cable Premium', 'tv', None, 250, 200),
    ('COMBO-100', 'Combo Internet 100 + TV', 'combo', 100, 420, 250),
    ('COMBO-200', 'Combo Internet 200 + TV', 'combo', 200, 520, 300),
]

# (fecha_offset, código, nombre, tipo de plan)
SALES_SPEC = [
    (0, 'CLI-101', 'Luis Mamani', 'GO-BASIC'),
    (0, 'CLI-102', 'Carla Quispe', 'GO-MAX'),
    (0, 'CLI-103', 'Roberto Condori', 'COMBO-100'),
    (0, 'CLI-104', 'Ana Choque', 'TV-BASIC'),
    (1, 'CLI-105', 'Pedro Huanca', 'GO-ULTRA'),
    (1, 'CLI-106', 'Sonia Vargas', 'COMBO-200'),
    (1, 'CLI-107', 'Marcos Flores', 'GO-BASIC'),
    (2, 'CLI-108', 'Rosa Torrez', 'TV-PREMIUM'),
    (2, 'CLI-109', 'Diego Paredes', 'GO-MAX'),
    (3, 'CLI-110', 'Lucía Rivero', 'GO-BASIC'),
    (3, 'CLI-111', 'Jorge Añez', 'COMBO-100'),
    (4, 'CLI-112', 'Elena Roca', 'GO-ULTRA'),
    (4, 'CLI-113', 'Fabián Vargas', 'GO-BASIC'),
    (5, 'CLI-114', 'Natalia Suárez', 'TV-BASIC'),
    (5, 'CLI-115', 'Óscar Lima', 'COMBO-200'),
    (6, 'CLI-116', 'Gina Callisaya', 'GO-MAX'),
    (6, 'CLI-117', 'Hugo Ibañez', 'GO-BASIC'),
    (7, 'CLI-118', 'Iván Cruz', 'COMBO-100'),
    (7, 'CLI-119', 'Karla Menacho', 'GO-ULTRA'),
    (8, 'CLI-120', 'Mónica Ríos', 'TV-PREMIUM'),
    (8, 'CLI-121', 'Nelson Barrios', 'GO-MAX'),
    (9, 'CLI-122', 'Olga Siles', 'GO-BASIC'),
    (9, 'CLI-123', 'Pablo Rivero', 'COMBO-200'),
    (10, 'CLI-124', 'Sara Ortega', 'GO-ULTRA'),
    (10, 'CLI-125', 'Tomás Céspedes', 'GO-BASIC'),
    (11, 'CLI-126', 'Valeria Ticona', 'TV-BASIC'),
    (12, 'CLI-127', 'Wilson Guzmán', 'COMBO-100'),
    (13, 'CLI-128', 'Ximena Rueda', 'GO-MAX'),
    (13, 'CLI-129', 'Yuri Sandoval', 'GO-BASIC'),
    (14, 'CLI-130', 'Zulema Pinto', 'GO-ULTRA'),
]


class Command(BaseCommand):
    help = 'Carga datos mock de usuarios, planes y ventas.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Borra los datos existentes antes de seedear.')
        parser.add_argument('--users-only', action='store_true',
                            help='Solo crea usuarios si no existen (para produccion).')

    def handle(self, *args, **options):
        force = options['force']
        users_only = options['users_only']

        if users_only:
            created = 0
            for name, password, role in USERS:
                if not User.objects.filter(name__iexact=name).exists():
                    u = User(name=name, role=role)
                    u.set_password(password)
                    u.save()
                    created += 1
            self.stdout.write(self.style.SUCCESS(
                f'Usuarios garantizados (creados {created}).'))
            return

        has_data = (User.objects.exists() or Plan.objects.exists()
                    or Sale.objects.exists())
        if has_data and not force:
            self.stdout.write('Ya existen datos. Usa --force para re-seedear.')
            return
        if force:
            for model in (Sale, Plan, User):
                model.objects.all().delete()

        users = {}
        for name, password, role in USERS:
            u = User(name=name, role=role)
            u.set_password(password)
            u.save()
            users[role] = u
        admin, seller = users['admin'], users['ventas']

        plans_by_code = {}
        for code, label, ptype, speed, monthly, installation in PLANS:
            p = Plan(code=code, label=label, type=ptype, speed=speed,
                     monthly=monthly, installation=installation)
            p.save()
            plans_by_code[code] = p
        self.stdout.write(f'Creados {Plan.objects.count()} planes')

        today = timezone.localdate()
        for offset, code, name, plan_code in SALES_SPEC:
            d = today - timedelta(days=offset)
            plan = plans_by_code[plan_code]
            Sale.objects.create(
                date=d, clientCode=code, clientName=name,
                serviceType=plan.type, plan=plan, total=plan.total,
                createdBy=admin if d.weekday() < 3 else seller,
            )
        self.stdout.write(f'Creadas {Sale.objects.count()} ventas')
        self.stdout.write(self.style.SUCCESS('Seed completado.'))
