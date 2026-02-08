"""
Modelos principales del módulo Operations.
Gestión de viajes, pasajes, encomiendas, facturación y caja.
"""
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
import uuid


# =============================================================================
# VIAJES Y TRACKING
# =============================================================================

class Viaje(models.Model):
    """
    Representa una instancia ejecutable de un itinerario en una fecha específica.
    Es el viaje real que sale, con bus y chofer asignados.
    """
    ESTADO_CHOICES = [
        ('programado', 'Programado'),
        ('en_curso', 'En Curso'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]
    
    itinerario = models.ForeignKey(
        'itineraries.Itinerario',
        on_delete=models.PROTECT,
        related_name='viajes',
        verbose_name="Itinerario"
    )
    bus = models.ForeignKey(
        'fleet.Bus',
        on_delete=models.PROTECT,
        related_name='viajes',
        verbose_name="Bus"
    )
    chofer = models.ForeignKey(
        'users.Persona',
        on_delete=models.PROTECT,
        related_name='viajes_como_chofer',
        verbose_name="Chofer",
        limit_choices_to={'es_empleado': True}
    )
    fecha_viaje = models.DateField(
        verbose_name="Fecha del viaje"
    )
    hora_salida_real = models.TimeField(
        null=True, blank=True,
        verbose_name="Hora de salida real"
    )
    hora_llegada_real = models.TimeField(
        null=True, blank=True,
        verbose_name="Hora de llegada real"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='programado',
        verbose_name="Estado"
    )
    observaciones = models.TextField(
        blank=True, null=True,
        verbose_name="Observaciones"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Viaje"
        verbose_name_plural = "Viajes"
        ordering = ['-fecha_viaje', '-created_at']
        unique_together = ['itinerario', 'bus', 'fecha_viaje']
        constraints = [
            models.UniqueConstraint(
                fields=['itinerario', 'bus', 'fecha_viaje'],
                name='unique_viaje_por_dia'
            )
        ]

    def __str__(self):
        return f"{self.itinerario.nombre} - {self.fecha_viaje} ({self.bus.placa})"

    def get_absolute_url(self):
        return reverse('operations:viaje_detail', kwargs={'pk': self.pk})

    @property
    def asientos_disponibles(self):
        """Retorna la cantidad de asientos disponibles."""
        vendidos = self.pasajes.filter(
            estado__in=['vendido', 'reservado']
        ).count()
        return self.bus.capacidad_asientos - vendidos

    @property
    def porcentaje_ocupacion(self):
        """Retorna el porcentaje de ocupación del bus."""
        vendidos = self.pasajes.filter(
            estado__in=['vendido', 'reservado']
        ).count()
        if self.bus.capacidad_asientos > 0:
            return round((vendidos / self.bus.capacidad_asientos) * 100, 1)
        return 0


class TrackingViaje(models.Model):
    """
    Registra las posiciones GPS del viaje en tiempo real.
    Permite tracking y cálculo de ETA.
    """
    viaje = models.ForeignKey(
        Viaje,
        on_delete=models.CASCADE,
        related_name='trackings',
        verbose_name="Viaje"
    )
    latitud = models.DecimalField(
        max_digits=9, decimal_places=6,
        verbose_name="Latitud"
    )
    longitud = models.DecimalField(
        max_digits=9, decimal_places=6,
        verbose_name="Longitud"
    )
    velocidad_kmh = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name="Velocidad (km/h)"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha/Hora"
    )
    parada_actual = models.ForeignKey(
        'fleet.Parada',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='trackings',
        verbose_name="Parada actual o próxima"
    )
    eta_proxima_parada = models.DateTimeField(
        null=True, blank=True,
        verbose_name="ETA próxima parada"
    )

    class Meta:
        verbose_name = "Tracking de viaje"
        verbose_name_plural = "Trackings de viajes"
        ordering = ['-timestamp']

    def __str__(self):
        return f"Tracking {self.viaje} - {self.timestamp}"


# =============================================================================
# PASAJES Y RESERVAS
# =============================================================================

class Pasaje(models.Model):
    """
    Representa la venta/reserva de un asiento en un viaje específico.
    """
    ESTADO_CHOICES = [
        ('reservado', 'Reservado'),
        ('vendido', 'Vendido'),
        ('abordado', 'Abordado'),
        ('cancelado', 'Cancelado'),
        ('no_show', 'No se presentó'),
    ]

    viaje = models.ForeignKey(
        Viaje,
        on_delete=models.PROTECT,
        related_name='pasajes',
        verbose_name="Viaje"
    )
    asiento = models.ForeignKey(
        'fleet.Asiento',
        on_delete=models.PROTECT,
        related_name='pasajes',
        verbose_name="Asiento"
    )
    pasajero = models.ForeignKey(
        'users.Persona',
        on_delete=models.PROTECT,
        related_name='pasajes',
        verbose_name="Pasajero"
    )
    cliente = models.ForeignKey(
        'users.Persona',
        on_delete=models.PROTECT,
        related_name='pasajes_comprados',
        verbose_name="Cliente (quien paga)",
        null=True, blank=True,
        help_text="Si es el mismo que el pasajero, dejar vacío"
    )
    parada_origen = models.ForeignKey(
        'fleet.Parada',
        on_delete=models.PROTECT,
        related_name='pasajes_origen',
        verbose_name="Parada de origen"
    )
    parada_destino = models.ForeignKey(
        'fleet.Parada',
        on_delete=models.PROTECT,
        related_name='pasajes_destino',
        verbose_name="Parada de destino"
    )
    precio = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Precio"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='reservado',
        verbose_name="Estado"
    )
    codigo = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name="Código de pasaje"
    )
    vendedor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='pasajes_vendidos',
        verbose_name="Vendedor"
    )
    fecha_venta = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de venta"
    )
    fecha_cancelacion = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Fecha de cancelación"
    )
    motivo_cancelacion = models.TextField(
        blank=True, null=True,
        verbose_name="Motivo de cancelación"
    )

    class Meta:
        verbose_name = "Pasaje"
        verbose_name_plural = "Pasajes"
        ordering = ['-fecha_venta']
        unique_together = ['viaje', 'asiento']
        constraints = [
            models.UniqueConstraint(
                fields=['viaje', 'asiento'],
                name='unique_asiento_por_viaje',
                condition=models.Q(estado__in=['reservado', 'vendido', 'abordado'])
            )
        ]

    def __str__(self):
        return f"{self.codigo} - {self.pasajero.nombre_completo}"

    def get_absolute_url(self):
        return reverse('operations:pasaje_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        if not self.codigo:
            # Generar código único: PAS-YYYYMMDD-XXXX
            fecha = timezone.now().strftime('%Y%m%d')
            random_part = uuid.uuid4().hex[:4].upper()
            self.codigo = f"PAS-{fecha}-{random_part}"
        super().save(*args, **kwargs)

    @property
    def cliente_efectivo(self):
        """Retorna el cliente efectivo (pasajero si no hay cliente separado)."""
        return self.cliente if self.cliente else self.pasajero


# =============================================================================
# ENCOMIENDAS
# =============================================================================

class Encomienda(models.Model):
    """
    Representa un paquete o envío que se transporta en un viaje.
    """
    ESTADO_CHOICES = [
        ('registrado', 'Registrado'),
        ('en_transito', 'En Tránsito'),
        ('en_destino', 'En Destino'),
        ('entregado', 'Entregado'),
        ('devuelto', 'Devuelto'),
        ('cancelado', 'Cancelado'),
    ]

    TIPO_CHOICES = [
        ('paquete', 'Paquete'),
        ('documento', 'Documento'),
        ('valija', 'Valija'),
        ('carga', 'Carga'),
    ]

    viaje = models.ForeignKey(
        Viaje,
        on_delete=models.PROTECT,
        related_name='encomiendas',
        verbose_name="Viaje"
    )
    remitente = models.ForeignKey(
        'users.Persona',
        on_delete=models.PROTECT,
        related_name='encomiendas_enviadas',
        verbose_name="Remitente"
    )
    destinatario = models.ForeignKey(
        'users.Persona',
        on_delete=models.PROTECT,
        related_name='encomiendas_recibidas',
        verbose_name="Destinatario"
    )
    parada_origen = models.ForeignKey(
        'fleet.Parada',
        on_delete=models.PROTECT,
        related_name='encomiendas_origen',
        verbose_name="Parada de origen"
    )
    parada_destino = models.ForeignKey(
        'fleet.Parada',
        on_delete=models.PROTECT,
        related_name='encomiendas_destino',
        verbose_name="Parada de destino"
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='paquete',
        verbose_name="Tipo de encomienda"
    )
    descripcion = models.TextField(
        verbose_name="Descripción del contenido"
    )
    peso_kg = models.DecimalField(
        max_digits=8, decimal_places=2,
        null=True, blank=True,
        verbose_name="Peso (kg)"
    )
    precio = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Precio"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='registrado',
        verbose_name="Estado"
    )
    codigo = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name="Código de seguimiento"
    )
    registrador = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='encomiendas_registradas',
        verbose_name="Registrado por"
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de registro"
    )
    fecha_entrega = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Fecha de entrega"
    )
    receptor_nombre = models.CharField(
        max_length=100,
        blank=True, null=True,
        verbose_name="Nombre de quien recibe"
    )
    receptor_cedula = models.CharField(
        max_length=20,
        blank=True, null=True,
        verbose_name="Cédula de quien recibe"
    )

    class Meta:
        verbose_name = "Encomienda"
        verbose_name_plural = "Encomiendas"
        ordering = ['-fecha_registro']

    def __str__(self):
        return f"{self.codigo} - {self.tipo} ({self.estado})"

    def get_absolute_url(self):
        return reverse('operations:encomienda_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        if not self.codigo:
            # Generar código único: ENC-YYYYMMDD-XXXX
            fecha = timezone.now().strftime('%Y%m%d')
            random_part = uuid.uuid4().hex[:4].upper()
            self.codigo = f"ENC-{fecha}-{random_part}"
        super().save(*args, **kwargs)


# =============================================================================
# FACTURACIÓN
# =============================================================================

class Timbrado(models.Model):
    """
    Representa un timbrado fiscal habilitado por la SET.
    """
    empresa = models.ForeignKey(
        'fleet.Empresa',
        on_delete=models.CASCADE,
        related_name='timbrados',
        verbose_name="Empresa"
    )
    numero = models.CharField(
        max_length=20,
        verbose_name="Número de timbrado"
    )
    fecha_inicio = models.DateField(
        verbose_name="Fecha de inicio de vigencia"
    )
    fecha_fin = models.DateField(
        verbose_name="Fecha de fin de vigencia"
    )
    numero_desde = models.BigIntegerField(
        verbose_name="Número de factura desde"
    )
    numero_hasta = models.BigIntegerField(
        verbose_name="Número de factura hasta"
    )
    punto_expedicion = models.CharField(
        max_length=10,
        verbose_name="Punto de expedición",
        help_text="Ej: 001-001"
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )

    class Meta:
        verbose_name = "Timbrado"
        verbose_name_plural = "Timbrados"
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f"{self.numero} ({self.punto_expedicion})"

    @property
    def esta_vigente(self):
        """Verifica si el timbrado está vigente."""
        hoy = timezone.now().date()
        return self.fecha_inicio <= hoy <= self.fecha_fin and self.activo

    def get_siguiente_numero(self):
        """Obtiene el siguiente número de factura disponible."""
        ultima = self.facturas.order_by('-numero_factura').first()
        if ultima:
            siguiente = ultima.numero_factura + 1
        else:
            siguiente = self.numero_desde
        
        if siguiente > self.numero_hasta:
            raise ValueError("Se agotaron los números de factura para este timbrado")
        return siguiente


class Factura(models.Model):
    """
    Representa una factura fiscal emitida.
    """
    CONDICION_CHOICES = [
        ('contado', 'Contado'),
        ('credito', 'Crédito'),
    ]

    ESTADO_CHOICES = [
        ('emitida', 'Emitida'),
        ('anulada', 'Anulada'),
    ]

    timbrado = models.ForeignKey(
        Timbrado,
        on_delete=models.PROTECT,
        related_name='facturas',
        verbose_name="Timbrado"
    )
    numero_factura = models.BigIntegerField(
        verbose_name="Número de factura"
    )
    cliente = models.ForeignKey(
        'users.Persona',
        on_delete=models.PROTECT,
        related_name='facturas',
        verbose_name="Cliente"
    )
    condicion = models.CharField(
        max_length=10,
        choices=CONDICION_CHOICES,
        default='contado',
        verbose_name="Condición de venta"
    )
    fecha_emision = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de emisión"
    )
    subtotal_exenta = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Subtotal exenta"
    )
    subtotal_iva5 = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Subtotal IVA 5%"
    )
    subtotal_iva10 = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Subtotal IVA 10%"
    )
    total = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total"
    )
    iva_5 = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="IVA 5%"
    )
    iva_10 = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="IVA 10%"
    )
    total_iva = models.DecimalField(
        max_digits=15, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Total IVA"
    )
    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default='emitida',
        verbose_name="Estado"
    )
    cajero = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='facturas_emitidas',
        verbose_name="Cajero"
    )
    sesion_caja = models.ForeignKey(
        'SesionCaja',
        on_delete=models.PROTECT,
        related_name='facturas',
        verbose_name="Sesión de caja",
        null=True, blank=True
    )
    motivo_anulacion = models.TextField(
        blank=True, null=True,
        verbose_name="Motivo de anulación"
    )
    fecha_anulacion = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Fecha de anulación"
    )

    class Meta:
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"
        ordering = ['-fecha_emision']
        unique_together = ['timbrado', 'numero_factura']

    def __str__(self):
        return f"{self.timbrado.punto_expedicion}-{self.numero_factura:07d}"

    def get_absolute_url(self):
        return reverse('operations:factura_detail', kwargs={'pk': self.pk})

    @property
    def numero_completo(self):
        """Retorna el número de factura completo con punto de expedición."""
        return f"{self.timbrado.punto_expedicion}-{self.numero_factura:07d}"

    def calcular_totales(self):
        """Calcula los totales a partir de los detalles."""
        self.subtotal_exenta = Decimal('0.00')
        self.subtotal_iva5 = Decimal('0.00')
        self.subtotal_iva10 = Decimal('0.00')
        
        for detalle in self.detalles.all():
            if detalle.tasa_iva == 0:
                self.subtotal_exenta += detalle.subtotal
            elif detalle.tasa_iva == 5:
                self.subtotal_iva5 += detalle.subtotal
            elif detalle.tasa_iva == 10:
                self.subtotal_iva10 += detalle.subtotal
        
        # Calcular IVA incluido
        self.iva_5 = self.subtotal_iva5 * Decimal('5') / Decimal('105')
        self.iva_10 = self.subtotal_iva10 * Decimal('10') / Decimal('110')
        self.total_iva = self.iva_5 + self.iva_10
        self.total = self.subtotal_exenta + self.subtotal_iva5 + self.subtotal_iva10


class DetalleFactura(models.Model):
    """
    Línea de detalle de una factura.
    """
    TASA_IVA_CHOICES = [
        (0, 'Exenta'),
        (5, 'IVA 5%'),
        (10, 'IVA 10%'),
    ]

    factura = models.ForeignKey(
        Factura,
        on_delete=models.CASCADE,
        related_name='detalles',
        verbose_name="Factura"
    )
    cantidad = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=Decimal('1.00'),
        verbose_name="Cantidad"
    )
    descripcion = models.CharField(
        max_length=255,
        verbose_name="Descripción"
    )
    precio_unitario = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name="Precio unitario"
    )
    tasa_iva = models.IntegerField(
        choices=TASA_IVA_CHOICES,
        default=10,
        verbose_name="Tasa de IVA"
    )
    subtotal = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name="Subtotal"
    )
    # Referencias opcionales
    pasaje = models.ForeignKey(
        Pasaje,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='detalles_factura',
        verbose_name="Pasaje relacionado"
    )
    encomienda = models.ForeignKey(
        Encomienda,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='detalles_factura',
        verbose_name="Encomienda relacionada"
    )

    class Meta:
        verbose_name = "Detalle de factura"
        verbose_name_plural = "Detalles de factura"
        ordering = ['id']

    def __str__(self):
        return f"{self.cantidad} x {self.descripcion}"

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)


# =============================================================================
# CAJA
# =============================================================================

class SesionCaja(models.Model):
    """
    Representa una sesión de caja (apertura y cierre).
    """
    ESTADO_CHOICES = [
        ('abierta', 'Abierta'),
        ('cerrada', 'Cerrada'),
    ]

    cajero = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='sesiones_caja',
        verbose_name="Cajero"
    )
    fecha_apertura = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de apertura"
    )
    monto_apertura = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name="Monto de apertura"
    )
    fecha_cierre = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Fecha de cierre"
    )
    monto_cierre_esperado = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True,
        verbose_name="Monto de cierre esperado"
    )
    monto_cierre_real = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True,
        verbose_name="Monto de cierre real"
    )
    diferencia = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True,
        verbose_name="Diferencia"
    )
    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default='abierta',
        verbose_name="Estado"
    )
    observaciones = models.TextField(
        blank=True, null=True,
        verbose_name="Observaciones"
    )

    class Meta:
        verbose_name = "Sesión de caja"
        verbose_name_plural = "Sesiones de caja"
        ordering = ['-fecha_apertura']

    def __str__(self):
        return f"Caja {self.cajero.username} - {self.fecha_apertura.strftime('%d/%m/%Y %H:%M')}"

    def get_absolute_url(self):
        return reverse('operations:sesion_caja_detail', kwargs={'pk': self.pk})

    @property
    def total_ingresos(self):
        """Suma de ingresos de la sesión."""
        return self.movimientos.filter(tipo='ingreso').aggregate(
            total=models.Sum('monto')
        )['total'] or Decimal('0.00')

    @property
    def total_egresos(self):
        """Suma de egresos de la sesión."""
        return self.movimientos.filter(tipo='egreso').aggregate(
            total=models.Sum('monto')
        )['total'] or Decimal('0.00')

    def calcular_cierre(self):
        """Calcula el monto esperado al cierre."""
        self.monto_cierre_esperado = (
            self.monto_apertura + 
            self.total_ingresos - 
            self.total_egresos
        )
        return self.monto_cierre_esperado

    def cerrar(self, monto_real, observaciones=''):
        """Cierra la sesión de caja."""
        self.calcular_cierre()
        self.monto_cierre_real = monto_real
        self.diferencia = monto_real - self.monto_cierre_esperado
        self.fecha_cierre = timezone.now()
        self.estado = 'cerrada'
        self.observaciones = observaciones
        self.save()


class MovimientoCaja(models.Model):
    """
    Representa un movimiento de dinero en caja.
    """
    TIPO_CHOICES = [
        ('ingreso', 'Ingreso'),
        ('egreso', 'Egreso'),
    ]

    CONCEPTO_CHOICES = [
        ('venta_pasaje', 'Venta de pasaje'),
        ('venta_encomienda', 'Venta de encomienda'),
        ('anulacion', 'Anulación'),
        ('devolucion', 'Devolución'),
        ('gasto', 'Gasto'),
        ('retiro', 'Retiro'),
        ('deposito', 'Depósito'),
        ('otro', 'Otro'),
    ]

    sesion = models.ForeignKey(
        SesionCaja,
        on_delete=models.CASCADE,
        related_name='movimientos',
        verbose_name="Sesión de caja"
    )
    tipo = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
        verbose_name="Tipo"
    )
    concepto = models.CharField(
        max_length=20,
        choices=CONCEPTO_CHOICES,
        verbose_name="Concepto"
    )
    monto = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name="Monto"
    )
    descripcion = models.CharField(
        max_length=255,
        verbose_name="Descripción"
    )
    factura = models.ForeignKey(
        Factura,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='movimientos_caja',
        verbose_name="Factura relacionada"
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha"
    )

    class Meta:
        verbose_name = "Movimiento de caja"
        verbose_name_plural = "Movimientos de caja"
        ordering = ['-fecha']

    def __str__(self):
        signo = '+' if self.tipo == 'ingreso' else '-'
        return f"{signo} Gs. {self.monto:,.0f} - {self.descripcion}"


# =============================================================================
# INCIDENCIAS Y ALERTAS
# =============================================================================

class Incidencia(models.Model):
    """
    Registra incidencias durante un viaje.
    """
    TIPO_CHOICES = [
        ('mecanico', 'Problema Mecánico'),
        ('accidente', 'Accidente'),
        ('retraso', 'Retraso'),
        ('pasajero', 'Incidente con Pasajero'),
        ('clima', 'Condiciones Climáticas'),
        ('otro', 'Otro'),
    ]

    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('critica', 'Crítica'),
    ]

    ESTADO_CHOICES = [
        ('abierta', 'Abierta'),
        ('en_proceso', 'En Proceso'),
        ('resuelta', 'Resuelta'),
    ]

    viaje = models.ForeignKey(
        Viaje,
        on_delete=models.CASCADE,
        related_name='incidencias',
        verbose_name="Viaje"
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        verbose_name="Tipo"
    )
    prioridad = models.CharField(
        max_length=10,
        choices=PRIORIDAD_CHOICES,
        default='media',
        verbose_name="Prioridad"
    )
    descripcion = models.TextField(
        verbose_name="Descripción"
    )
    estado = models.CharField(
        max_length=15,
        choices=ESTADO_CHOICES,
        default='abierta',
        verbose_name="Estado"
    )
    reportador = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='incidencias_reportadas',
        verbose_name="Reportado por"
    )
    fecha_reporte = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de reporte"
    )
    fecha_resolucion = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Fecha de resolución"
    )
    resolucion = models.TextField(
        blank=True, null=True,
        verbose_name="Resolución"
    )

    class Meta:
        verbose_name = "Incidencia"
        verbose_name_plural = "Incidencias"
        ordering = ['-fecha_reporte']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.viaje}"
