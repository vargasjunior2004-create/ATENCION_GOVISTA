from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password


class User(models.Model):
    """Usuario del sistema. Modelo mock: la contraseña se guarda hasheada
    con el hasher estándar de Django."""
    ROLE_CHOICES = [('admin', 'admin'), ('ventas', 'ventas')]

    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='ventas')
    active = models.BooleanField(default=True)

    def set_password(self, raw):
        self.password = make_password(raw)

    def check_password(self, raw):
        return check_password(raw, self.password)

    @property
    def is_authenticated(self):
        return self.active

    @property
    def is_anonymous(self):
        return False

    def __str__(self):
        return f'{self.name} ({self.role})'


class Plan(models.Model):
    """Plan de servicio. total = monthly + installation (regla de negocio)."""
    TYPE_CHOICES = [('internet', 'internet'), ('tv', 'tv'), ('combo', 'combo')]

    code = models.CharField(max_length=30, unique=True)
    label = models.CharField(max_length=120)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    speed = models.PositiveIntegerField(null=True, blank=True)
    monthly = models.DecimalField(max_digits=12, decimal_places=2)
    installation = models.DecimalField(max_digits=12, decimal_places=2)
    active = models.BooleanField(default=True)
    legacy = models.BooleanField(
        default=False,
        help_text='Plan del catalogo anterior; solo se ofrece en retiros.')

    @property
    def total(self):
        return self.monthly + self.installation

    def __str__(self):
        return f'{self.code} - {self.label}'


class Customer(models.Model):
    """Cliente maestro (KARDEX). Clave natural: code."""
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=160)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.code} {self.name}'


class Sale(models.Model):
    """Venta registrada. total se calcula SIEMPRE en el servidor a partir
    del plan, nunca se acepta del cliente."""
    TYPE_CHOICES = [('internet', 'internet'), ('tv', 'tv'), ('combo', 'combo')]
    REQUEST_CHOICES = [
        ('nuevo_contrato', 'NUEVO CONTRATO'),
        ('cambio_plan', 'CAMBIO DE PLAN'),
        ('recontratacion', 'RECONTRATACION'),
        ('retiro', 'RETIRO'),
        ('adicion', 'ADICIÓN'),
        ('baja_temporal', 'BAJA TEMPORAL'),
        ('otro', 'OTRO'),
    ]

    date = models.DateField()
    clientCode = models.CharField(max_length=40)
    clientName = models.CharField(max_length=160)
    customer = models.ForeignKey(
        Customer, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='sales')
    serviceType = models.CharField(max_length=10, choices=TYPE_CHOICES)
    requestType = models.CharField(
        max_length=20, choices=REQUEST_CHOICES, default='nuevo_contrato')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='sales')
    changeReason = models.CharField(max_length=120, blank=True, default='')
    planFrom = models.CharField(max_length=60, blank=True, default='')
    totalFrom = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True, default='')
    total = models.DecimalField(max_digits=12, decimal_places=2)
    createdBy = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='sales_created')
    lastEditedBy = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='sales_edited')
    lastEditedAt = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.date} {self.clientName}'


class CashCount(models.Model):
    """Arqueo de caja diario: conteo de efectivo por denominación."""
    date = models.DateField(unique=True)
    coin_050 = models.PositiveIntegerField(default=0)
    coin_1 = models.PositiveIntegerField(default=0)
    coin_2 = models.PositiveIntegerField(default=0)
    coin_5 = models.PositiveIntegerField(default=0)
    bill_10 = models.PositiveIntegerField(default=0)
    bill_20 = models.PositiveIntegerField(default=0)
    bill_50 = models.PositiveIntegerField(default=0)
    bill_100 = models.PositiveIntegerField(default=0)
    bill_200 = models.PositiveIntegerField(default=0)
    createdBy = models.ForeignKey(
        User, null=True, on_delete=models.SET_NULL)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total(self):
        return (
            self.coin_050 * 0.50 + self.coin_1 * 1 + self.coin_2 * 2
            + self.coin_5 * 5 + self.bill_10 * 10 + self.bill_20 * 20
            + self.bill_50 * 50 + self.bill_100 * 100 + self.bill_200 * 200
        )

    def __str__(self):
        return f'Arqueo {self.date}'


class Outflow(models.Model):
    """Salida de efectivo del arqueo de caja."""
    date = models.DateField()
    personName = models.CharField(max_length=160)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    concept = models.CharField(max_length=255, blank=True, default='')
    createdBy = models.ForeignKey(
        User, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f'{self.date} {self.personName} -{self.amount}'
