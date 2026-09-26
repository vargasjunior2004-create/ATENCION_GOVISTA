from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password


class User(models.Model):
    """Usuario del sistema. Modelo mock: la contraseña se guarda hasheada
    con el hasher estándar de Django."""
    ROLE_CHOICES = [('admin', 'admin'), ('ventas', 'ventas')]

    name = models.CharField(max_length=120)
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


class Promotion(models.Model):
    """Promocion asociada a un plan. Permite ofrecer precios especiales
    durante un periodo de vigencia sin crear planes duplicados."""
    name = models.CharField(max_length=120)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='promotions')

    apply_installation = models.BooleanField(
        default=False, help_text='Si aplica precio promocional a instalacion')
    apply_monthly = models.BooleanField(
        default=False, help_text='Si aplica precio promocional a mensualidad')

    installation_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='Precio promocional de instalacion (solo si apply_installation)')
    monthly_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='Precio promocional de mensualidad (solo si apply_monthly)')

    start_date = models.DateField()
    end_date = models.DateField()
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='promotions_created')

    class Meta:
        ordering = ['-start_date', '-id']

    def __str__(self):
        return f'{self.name} ({self.plan.code})'

    @property
    def is_current(self):
        from django.utils import timezone as tz
        today = tz.localdate()
        return self.active and self.start_date <= today <= self.end_date


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
    TYPE_CHOICES = [
        ('internet', 'INTERNET'),
        ('tv', 'TV ANALOGA'),
        ('tv_digital', 'TV DIGITAL'),
        ('combo_analog', 'INTERNET + TV ANALOGA'),
        ('combo_digital', 'INTERNET + TV DIGITAL'),
    ]
    REQUEST_CHOICES = [
        ('nuevo_contrato', 'NUEVO CONTRATO'),
        ('cambio_plan', 'CAMBIO DE PLAN'),
        ('recontratacion', 'RECONTRATACION'),
        ('retiro', 'RETIRO'),
        ('adicion', 'ADICION'),
        ('otro', 'OTRO'),
    ]
    ADDITION_TYPE_CHOICES = [
        ('adicion_internet', 'ADICION INTERNET'),
        ('adicion_tv', 'ADICION TV'),
    ]

    date = models.DateField()
    clientCode = models.CharField(max_length=40)
    clientName = models.CharField(max_length=160)
    customer = models.ForeignKey(
        Customer, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='sales')
    serviceType = models.CharField(max_length=20, choices=TYPE_CHOICES)
    requestType = models.CharField(
        max_length=20, choices=REQUEST_CHOICES, default='nuevo_contrato')
    additionType = models.CharField(
        max_length=20, choices=ADDITION_TYPE_CHOICES, blank=True, default='',
        help_text='Sub-tipo de adicion: internet o tv')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='sales')
    changeReason = models.CharField(max_length=120, blank=True, default='')
    planFrom = models.CharField(max_length=60, blank=True, default='')
    planFromId = models.ForeignKey(
        Plan, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='sales_from', help_text='Plan anterior (cambio de plan)')
    totalFrom = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True, default='')
    total = models.DecimalField(max_digits=12, decimal_places=2)
    promotion = models.ForeignKey(
        Promotion, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='sales', help_text='Promocion utilizada (snapshot)')
    promotion_name = models.CharField(
        max_length=120, blank=True, default='',
        help_text='Nombre de la promocion al momento del registro')
    applied_installation = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='Precio de instalacion aplicado')
    applied_monthly = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='Mensualidad aplicada')
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


class Backup(models.Model):
    """Metadatos de una copia de seguridad. NUNCA almacena el archivo:
    el dump se genera en un temporal, se transmite al navegador y se
    borra. Aqui solo queda constancia de la operacion."""
    TYPE_CHOICES = [('automatic', 'Automatico'), ('manual', 'Manual')]
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('running', 'En proceso'),
        ('success', 'Completado'),
        ('failed', 'Fallido'),
    ]
    FORMAT_CHOICES = [
        ('dump', 'PostgreSQL dump (pg_dump)'),
        ('sqlite3', 'SQLite'),
        ('json', 'JSON (solo desarrollo)'),
    ]

    filename = models.CharField(max_length=255)
    backup_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='pending')
    backup_format = models.CharField(
        max_length=10, choices=FORMAT_CHOICES, default='dump')
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    size = models.BigIntegerField(default=0)
    storage_path = models.CharField(max_length=500, blank=True, default='')
    checksum = models.CharField(max_length=64, blank=True, default='')
    verified = models.BooleanField(
        default=False,
        help_text='La integridad del archivo fue verificada tras generarse')
    error_message = models.CharField(max_length=500, blank=True, default='')
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='backups')

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # Garantiza un solo respaldo en curso. Es la unica proteccion
            # fiable: el transaction pooler de Supabase (puerto 6543) no
            # soporta bloqueos consultivos, y Render usa 2 workers.
            models.UniqueConstraint(
                fields=['status'],
                condition=models.Q(status='running'),
                name='backup_unico_en_proceso',
            ),
        ]

    def __str__(self):
        return f'{self.filename} ({self.get_backup_type_display()})'
