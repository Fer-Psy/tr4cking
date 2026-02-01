from django.db import models
from django.urls import reverse

from users.models import Localidad


class Empresa(models.Model):
    """
    Representa una empresa de transporte de buses.
    Contiene información legal y de contacto de la empresa.
    """
    nombre = models.CharField(
        max_length=100, 
        unique=True, 
        verbose_name="Nombre de la empresa"
    )
    ruc = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name="RUC",
        help_text="Registro Único de Contribuyente"
    )
    telefono = models.CharField(
        max_length=30, 
        blank=True, 
        null=True, 
        verbose_name="Teléfono"
    )
    email = models.EmailField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name="Email"
    )
    direccion_legal = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Dirección legal"
    )

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse('fleet:empresa_detail', kwargs={'pk': self.pk})


class Parada(models.Model):
    """
    Representa una parada o terminal de buses.
    Puede ser una sucursal de la empresa o simplemente un punto de parada.
    """
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.CASCADE, 
        related_name='paradas',
        verbose_name="Empresa"
    )
    localidad = models.ForeignKey(
        Localidad, 
        on_delete=models.PROTECT, 
        related_name='paradas',
        verbose_name="Localidad"
    )
    nombre = models.CharField(
        max_length=200, 
        verbose_name="Nombre",
        help_text="Ej: Terminal de Oviedo"
    )
    direccion = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Dirección"
    )
    # Coordenadas GPS exactas de la parada
    latitud_gps = models.DecimalField(
        max_digits=9, decimal_places=6, 
        null=True, blank=True,
        verbose_name="Latitud GPS"
    )
    longitud_gps = models.DecimalField(
        max_digits=9, decimal_places=6, 
        null=True, blank=True,
        verbose_name="Longitud GPS"
    )
    es_sucursal = models.BooleanField(
        default=False, 
        verbose_name="Es sucursal",
        help_text="Indica si esta parada es una sucursal de la empresa"
    )

    class Meta:
        verbose_name = "Parada"
        verbose_name_plural = "Paradas"
        ordering = ['empresa', 'localidad', 'nombre']

    def __str__(self):
        return f"{self.nombre} ({self.localidad})"

    def get_absolute_url(self):
        return reverse('fleet:parada_detail', kwargs={'pk': self.pk})


class Bus(models.Model):
    """
    Representa un bus de la flota de una empresa.
    Incluye información del vehículo y su estado actual.
    """
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('mantenimiento', 'En Mantenimiento'),
        ('inactivo', 'Inactivo'),
    ]

    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.CASCADE, 
        related_name='buses',
        verbose_name="Empresa"
    )
    placa = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name="Placa",
        help_text="Número de placa del vehículo"
    )
    marca = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name="Marca"
    )
    modelo = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name="Modelo"
    )
    capacidad_pisos = models.PositiveSmallIntegerField(
        default=1, 
        verbose_name="Cantidad de pisos",
        help_text="Número de pisos del bus (1 o 2)"
    )
    capacidad_asientos = models.PositiveIntegerField(
        verbose_name="Capacidad de asientos",
        help_text="Número total de asientos del bus"
    )
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES, 
        default='activo',
        verbose_name="Estado"
    )

    class Meta:
        verbose_name = "Bus"
        verbose_name_plural = "Buses"
        ordering = ['empresa', 'placa']

    def __str__(self):
        return f"{self.placa} - {self.marca} {self.modelo}"

    def get_absolute_url(self):
        return reverse('fleet:bus_detail', kwargs={'pk': self.pk})

    @property
    def esta_disponible(self):
        """Retorna True si el bus está activo y disponible."""
        return self.estado == 'activo'


class Asiento(models.Model):
    """
    Representa la configuración física de un asiento en un bus.
    No almacena disponibilidad (eso se calcula en tiempo real).
    """
    TIPO_ASIENTO_CHOICES = [
        ('cama', 'Cama'),
        ('semi_cama', 'Semi-Cama'),
        ('convencional', 'Convencional'),
    ]

    bus = models.ForeignKey(
        Bus, 
        on_delete=models.CASCADE, 
        related_name='asientos',
        verbose_name="Bus"
    )
    numero_asiento = models.PositiveSmallIntegerField(
        verbose_name="Número de asiento"
    )
    piso = models.PositiveSmallIntegerField(
        default=1, 
        verbose_name="Piso",
        help_text="Piso donde se encuentra el asiento (1 o 2)"
    )
    tipo_asiento = models.CharField(
        max_length=20, 
        choices=TIPO_ASIENTO_CHOICES, 
        default='convencional',
        verbose_name="Tipo de asiento"
    )

    class Meta:
        verbose_name = "Asiento"
        verbose_name_plural = "Asientos"
        ordering = ['bus', 'piso', 'numero_asiento']
        unique_together = ['bus', 'numero_asiento']
        # Constraint para asegurar unicidad
        constraints = [
            models.UniqueConstraint(
                fields=['bus', 'numero_asiento'],
                name='unique_asiento_por_bus'
            )
        ]

    def __str__(self):
        return f"Asiento {self.numero_asiento} (Piso {self.piso}) - {self.bus.placa}"

    def get_absolute_url(self):
        return reverse('fleet:asiento_detail', kwargs={'pk': self.pk})
