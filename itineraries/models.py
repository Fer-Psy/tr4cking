from django.db import models
from django.urls import reverse
from datetime import datetime, timedelta

from fleet.models import Parada, Empresa


class Itinerario(models.Model):
    """
    Define una ruta o recorrido de buses.
    Contiene la información general del itinerario y los días de operación.
    """
    empresa = models.ForeignKey(
        Empresa, 
        on_delete=models.CASCADE, 
        related_name='itinerarios',
        verbose_name="Empresa",
        null=True, blank=True  # Temporal para migración
    )
    nombre = models.CharField(
        max_length=100, 
        verbose_name="Nombre del itinerario",
        help_text="Ej: Asunción - CDE (Directo)"
    )
    ruta = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        verbose_name="Ruta",
        help_text="Código de ruta nacional (Ej: PY02, PY03)"
    )
    distancia_total_km = models.DecimalField(
        max_digits=6, decimal_places=2, 
        null=True, blank=True,
        verbose_name="Distancia total (km)"
    )
    duracion_estimada_hs = models.DecimalField(
        max_digits=4, decimal_places=2, 
        null=True, blank=True,
        verbose_name="Duración estimada (horas)"
    )
    dias_semana = models.CharField(
        max_length=7, 
        verbose_name="Días de la semana",
        help_text="Patrón binario: 1111100 = L-V, 1111111 = Todos"
    )
    activo = models.BooleanField(
        default=True, 
        verbose_name="Activo"
    )

    class Meta:
        verbose_name = "Itinerario"
        verbose_name_plural = "Itinerarios"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse('itineraries:itinerario_detail', kwargs={'pk': self.pk})

    @property
    def primera_parada(self):
        """Retorna el primer DetalleItinerario (parada de origen) si existe."""
        return self.detalles.order_by('orden').first()

    @property
    def dias_operacion_texto(self):
        """
        Retorna los días de operación en formato legible.
        Ej: 1111100 -> 'Lun, Mar, Mié, Jue, Vie'

        """
        dias_nombres = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
        dias_activos = []
        for i, dia in enumerate(self.dias_semana):
            if dia == '1' and i < len(dias_nombres):
                dias_activos.append(dias_nombres[i])
        return ', '.join(dias_activos) if dias_activos else 'Sin días asignados'

    def opera_en_dia(self, dia_semana):
        """
        Verifica si el itinerario opera en un día específico.
        dia_semana: 0=Lunes, 1=Martes, ..., 6=Domingo
        """
        if 0 <= dia_semana < len(self.dias_semana):
            return self.dias_semana[dia_semana] == '1'
        return False


class Horario(models.Model):
    """
    Representa un horario de salida para un itinerario.
    Ej: Itinerario "Asunción-Cnel. Oviedo" tiene horarios 11:00, 14:00, 17:00.
    Cada horario genera un Viaje distinto en la misma fecha.
    """
    itinerario = models.ForeignKey(
        Itinerario,
        on_delete=models.CASCADE,
        related_name='horarios',
        verbose_name="Itinerario"
    )
    hora_salida = models.TimeField(
        verbose_name="Hora de salida programada",
        help_text="Hora en que el bus parte de la primera parada"
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )

    class Meta:
        verbose_name = "Horario"
        verbose_name_plural = "Horarios"
        ordering = ['itinerario', 'hora_salida']
        unique_together = ['itinerario', 'hora_salida']
        constraints = [
            models.UniqueConstraint(
                fields=['itinerario', 'hora_salida'],
                name='unique_horario_por_itinerario'
            ),
        ]

    def __str__(self):
        return f"{self.itinerario.nombre} - {self.hora_salida.strftime('%H:%M')}"

    def get_absolute_url(self):
        return reverse('itineraries:itinerario_detail', kwargs={'pk': self.itinerario.pk})


class DetalleItinerario(models.Model):
    """
    Define la secuencia de paradas de un itinerario.
    Las horas se calculan dinámicamente según el Horario asignado al viaje.
    Ej: Asunción(1) -> San Lorenzo(2) -> Caacupé(3) -> CDE(4)
    """
    itinerario = models.ForeignKey(
        Itinerario, 
        on_delete=models.CASCADE, 
        related_name='detalles',
        verbose_name="Itinerario"
    )
    parada = models.ForeignKey(
        Parada, 
        on_delete=models.PROTECT, 
        related_name='detalles_itinerario',
        verbose_name="Parada"
    )
    orden = models.PositiveSmallIntegerField(
        verbose_name="Orden",
        help_text="Posición de la parada en la secuencia (1, 2, 3...)"
    )
    minutos_desde_origen = models.PositiveIntegerField(
        default=0,
        verbose_name="Minutos desde origen",
        help_text="Minutos estimados desde la primera parada. Ej: 0, 30, 60, 120"
    )
    distancia_desde_origen_km = models.DecimalField(
        max_digits=6, decimal_places=2,
        null=True, blank=True,
        verbose_name="Distancia desde origen (km)"
    )

    class Meta:
        verbose_name = "Detalle de itinerario"
        verbose_name_plural = "Detalles de itinerario"
        ordering = ['itinerario', 'orden']
        unique_together = [
            ('itinerario', 'orden'),
            ('itinerario', 'parada'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['itinerario', 'orden'],
                name='unique_orden_por_itinerario'
            ),
            models.UniqueConstraint(
                fields=['itinerario', 'parada'],
                name='unique_parada_por_itinerario'
            ),
        ]

    def __str__(self):
        return f"{self.itinerario.nombre} - {self.orden}. {self.parada.nombre}"

    def get_absolute_url(self):
        return reverse('itineraries:detalle_detail', kwargs={'pk': self.pk})

    def hora_estimada(self, hora_salida_origen):
        """
        Calcula la hora estimada de llegada a esta parada dado un horario de salida.
        hora_salida_origen: time object de la hora de salida de la primera parada.
        """
        dt = datetime.combine(datetime.today(), hora_salida_origen)
        dt += timedelta(minutes=self.minutos_desde_origen or 0)
        return dt.time()


class Precio(models.Model):
    """
    Define la matriz de precios de un itinerario.
    Almacena cuánto cuesta ir de una parada origen a una parada destino.
    """
    itinerario = models.ForeignKey(
        Itinerario, 
        on_delete=models.CASCADE, 
        related_name='precios',
        verbose_name="Itinerario"
    )
    origen = models.ForeignKey(
        Parada, 
        on_delete=models.PROTECT, 
        related_name='precios_como_origen',
        verbose_name="Parada origen"
    )
    destino = models.ForeignKey(
        Parada, 
        on_delete=models.PROTECT, 
        related_name='precios_como_destino',
        verbose_name="Parada destino"
    )
    precio = models.DecimalField(
        max_digits=12, decimal_places=2, 
        verbose_name="Precio",
        help_text="Precio del pasaje en guaraníes"
    )

    class Meta:
        verbose_name = "Precio"
        verbose_name_plural = "Precios"
        ordering = ['itinerario', 'origen', 'destino']
        unique_together = ['itinerario', 'origen', 'destino']
        constraints = [
            models.UniqueConstraint(
                fields=['itinerario', 'origen', 'destino'],
                name='unique_precio_por_tramo'
            )
        ]

    def __str__(self):
        return f"{self.itinerario.nombre}: {self.origen.nombre} -> {self.destino.nombre} = Gs. {self.precio:,.0f}"

    def get_absolute_url(self):
        return reverse('itineraries:precio_detail', kwargs={'pk': self.pk})
