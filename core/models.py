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


class TipoSolicitud(models.Model):
    """Catalogo de tipos de solicitud, administrable desde el panel.

    `code` es solo la llave que se guarda en Sale.requestType. `modo` es
    lo que decide las reglas de cobro, y por eso estan separados: rename
    de un tipo no debe romper el historial de movimientos.

    Todo tipo nuevo nace en SIMPLE, o sea sin reglas especiales, y hay
    que cambiarlo a mano. Eso es deliberado: un tipo nuevo que nadie
    reviso nunca debe cobrar una instalacion que la operacion no espera.
    """

    class Modo(models.TextChoices):
        """Reglas de negocio que dispara el tipo de solicitud."""
        NUEVO = 'nuevo', 'Nuevo contrato'
        RETIRO = 'retiro', 'Retiro'
        CAMBIO_PLAN = 'cambio_plan', 'Cambio de plan'
        ADICION = 'adicion', 'Adicion'
        TRASLADO = 'traslado', 'Traslado externo'
        SIMPLE = 'simple', 'Sin reglas especiales'

    code = models.SlugField(max_length=20, unique=True)
    nombre = models.CharField(max_length=120)
    descripcion = models.CharField(max_length=255, blank=True, default='')
    modo = models.CharField(max_length=12, choices=Modo, default=Modo.SIMPLE)
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre


class Motivo(models.Model):
    """Catalogo administrable de motivos de movimiento.

    Reemplaza a las listas fijas que vivian en el formulario. Cada motivo
    pertenece a UNA categoria y esa categoria decide en que formulario se
    ofrece: 'cambio' solo en cambios de plan, 'retiro' solo en retiros.

    Igual que TipoSolicitud, un motivo NUNCA se borra fisicamente si tiene
    movimientos: se desactiva. Asi el historial conserva su trazabilidad.
    """

    CATEGORIA_CHOICES = [
        ('cambio', 'Motivo del cambio'),
        ('retiro', 'Motivo del retiro'),
    ]

    categoria = models.CharField(max_length=10, choices=CATEGORIA_CHOICES)
    nombre = models.CharField(max_length=120)
    descripcion = models.CharField(max_length=255, blank=True, default='')
    activo = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['categoria', 'orden', 'nombre']

    def __str__(self):
        return f'{self.get_categoria_display()}: {self.nombre}'


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


class TarifaTraslado(models.Model):
    """Catalogo de tarifas comerciales para traslados externos."""
    SERVICE_CHOICES = [
        ('combo', 'Combo'),
        ('internet', 'Internet individual'),
        ('tv', 'TV cable individual'),
    ]

    service_type = models.CharField(max_length=20, choices=SERVICE_CHOICES,
                                    unique=True)
    name = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='transfer_tariffs_created')
    updated_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='transfer_tariffs_updated')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} - {self.amount:.2f} Bs'


class TarifaTrasladoHistorial(models.Model):
    """Historial append-only de cambios del catalogo de tarifas."""
    tarifa = models.ForeignKey(
        TarifaTraslado, on_delete=models.PROTECT, related_name='history')
    previous_amount = models.DecimalField(max_digits=12, decimal_places=2)
    new_amount = models.DecimalField(max_digits=12, decimal_places=2)
    previous_active = models.BooleanField()
    new_active = models.BooleanField()
    action = models.CharField(max_length=30)
    changed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='transfer_tariff_changes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']


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
        max_length=20, blank=True, default='nuevo_contrato',
        help_text='Codigo de TipoSolicitud; el catalogo vive en esa tabla')
    additionType = models.CharField(
        max_length=20, choices=ADDITION_TYPE_CHOICES, blank=True, default='',
        help_text='Sub-tipo de adicion: internet o tv')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='sales')
    planName = models.CharField(
        max_length=120, blank=True, default='',
        help_text='Snapshot del nombre del plan al momento del registro')
    changeReason = models.CharField(
        max_length=120, blank=True, default='',
        help_text='Snapshot del nombre del motivo al momento del registro')
    motivo = models.ForeignKey(
        Motivo, null=True, blank=True, on_delete=models.PROTECT,
        related_name='sales',
        help_text='Motivo del cambio o del retiro, segun la categoria')
    planFrom = models.CharField(max_length=60, blank=True, default='')
    serviceTypeFrom = models.CharField(
        max_length=20, choices=TYPE_CHOICES, null=True, blank=True,
        help_text='Servicio anterior (cambio de plan entre servicios)')
    # PROTECT y no SET_NULL a proposito: si el plan anterior se borrara del
    # catalogo, el movimiento historico perderia su origen sin avisar.
    planFromId = models.ForeignKey(
        Plan, null=True, blank=True, on_delete=models.PROTECT,
        related_name='sales_from', help_text='Plan anterior (cambio de plan)')
    totalFrom = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True, default='')
    total = models.DecimalField(max_digits=12, decimal_places=2)
    version = models.PositiveIntegerField(default=1)
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
    equipment_retained = models.BooleanField(
        null=True, blank=True,
        help_text='Si la recontratacion conserva el router/ONU')
    requires_technical_visit = models.BooleanField(
        null=True, blank=True,
        help_text='Si la recontratacion requiere una visita tecnica')
    debt_applies = models.BooleanField(
        default=False,
        help_text='Si la recontratacion incluye un adeudo pendiente')
    debt_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text='Adeudo registrado al momento de la recontratacion')
    equipment_delivered = models.BooleanField(
        null=True, blank=True,
        help_text='Si el cliente entrego equipo durante el retiro')
    equipment_serial = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Serie del equipo declarado en el retiro')
    createdBy = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='sales_created')
    lastEditedBy = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='sales_edited')
    lastEditedAt = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Fecha de baja logica; el movimiento se conserva para auditoria')

    class Meta:
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.date} {self.clientName}'


class SaleIdempotencyKey(models.Model):
    """Resultado de un POST de venta protegido contra reintentos."""
    STATUS_CHOICES = [
        ('processing', 'En proceso'),
        ('completed', 'Completado'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='sale_idempotency_keys')
    key = models.CharField(max_length=128)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES)
    response_payload = models.JSONField(default=dict)
    response_status = models.PositiveSmallIntegerField(default=201)
    sale = models.ForeignKey(
        Sale, null=True, blank=True, on_delete=models.PROTECT,
        related_name='idempotency_keys')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'key'], name='unique_sale_idempotency_user_key')
        ]
        indexes = [models.Index(fields=['expires_at'])]


class InventarioMovimiento(models.Model):
    """Cola de movimientos físicos vinculados a una solicitud comercial."""
    TIPO_DEVOLUCION_DECLARADA = 'DEVOLUCION_DECLARADA'
    ESTADO_PENDIENTE = 'PENDIENTE_RECEPCION'
    ESTADO_CONFIRMADO = 'RECEPCION_CONFIRMADA'

    sale = models.ForeignKey(
        Sale, on_delete=models.PROTECT, related_name='inventario_movimientos')
    serie = models.CharField(max_length=255)
    tipo = models.CharField(max_length=40, default=TIPO_DEVOLUCION_DECLARADA)
    estado = models.CharField(max_length=40, default=ESTADO_PENDIENTE)
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='inventario_movimientos_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['serie', 'estado'])]


class AuditLog(models.Model):
    """Registro append-only de acciones sensibles del sistema."""
    actor = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='audit_events')
    action = models.CharField(max_length=40)
    entity = models.CharField(max_length=60)
    entity_id = models.CharField(max_length=80)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['entity', 'entity_id']),
            models.Index(fields=['actor', 'created_at']),
        ]


class TrasladoExterno(models.Model):
    """Detalle comercial de un traslado, separado del flujo operativo."""
    STATUS_CHOICES = [
        ('recibido', 'Recibido'),
        ('pendiente_ubicacion', 'Pendiente de ubicación'),
        ('pendiente_operativa', 'Pendiente de Operaciones'),
    ]

    sale = models.OneToOneField(
        Sale, on_delete=models.PROTECT, related_name='traslado_externo')
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name='external_transfers')
    tariff = models.ForeignKey(
        TarifaTraslado, on_delete=models.PROTECT, related_name='transfers')
    tariff_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_address = models.CharField(max_length=255, blank=True, default='')
    new_address = models.CharField(max_length=255)
    zone = models.CharField(max_length=120, blank=True, default='')
    references = models.CharField(max_length=500, blank=True, default='')
    has_physical_sketch = models.BooleanField()
    status = models.CharField(
        max_length=24, choices=STATUS_CHOICES, default='recibido')
    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='external_transfers_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'Traslado {self.sale_id} - {self.customer.code}'


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
