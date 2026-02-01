from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse


class Localidad(models.Model):
    """
    Representa una localidad o ciudad.
    Las coordenadas se almacenan como latitud/longitud para compatibilidad con SQLite.
    """
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    latitud = models.DecimalField(
        max_digits=9, decimal_places=6, 
        null=True, blank=True,
        verbose_name="Latitud",
        help_text="Coordenada latitud (ej: -25.2867)"
    )
    longitud = models.DecimalField(
        max_digits=9, decimal_places=6, 
        null=True, blank=True,
        verbose_name="Longitud",
        help_text="Coordenada longitud (ej: -57.3333)"
    )

    class Meta:
        verbose_name = "Localidad"
        verbose_name_plural = "Localidades"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse('users:localidad_detail', kwargs={'pk': self.pk})


class Persona(models.Model):
    """
    Modelo de persona que extiende al usuario de Django.
    Representa a clientes, empleados y pasajeros del sistema.
    La cédula es la clave primaria (identificador único de Paraguay).
    """
    cedula = models.BigIntegerField(
        primary_key=True, 
        verbose_name="Cédula",
        help_text="Número de cédula de identidad"
    )
    user = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='persona',
        verbose_name="Usuario del sistema",
        help_text="Relación opcional con cuenta de usuario"
    )
    nombre = models.CharField(max_length=50, verbose_name="Nombre")
    apellido = models.CharField(max_length=50, verbose_name="Apellido")
    telefono = models.CharField(max_length=30, verbose_name="Teléfono")
    email = models.EmailField(max_length=254, blank=True, null=True, verbose_name="Email")
    direccion = models.TextField(blank=True, null=True, verbose_name="Dirección")
    
    # Roles (booleanos para simplificar permisos rápidos)
    es_empleado = models.BooleanField(default=False, verbose_name="Es empleado")
    es_cliente = models.BooleanField(default=False, verbose_name="Es cliente")
    es_pasajero = models.BooleanField(default=False, verbose_name="Es pasajero")

    class Meta:
        verbose_name = "Persona"
        verbose_name_plural = "Personas"
        ordering = ['apellido', 'nombre']

    def __str__(self):
        return f"{self.apellido}, {self.nombre} ({self.cedula})"

    def get_absolute_url(self):
        return reverse('users:persona_detail', kwargs={'pk': self.pk})

    @property
    def nombre_completo(self):
        """Retorna el nombre completo de la persona."""
        return f"{self.nombre} {self.apellido}"
