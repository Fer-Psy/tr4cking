from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse


class Localidad(models.Model):
    """
    Representa una localidad o ciudad.
    Las coordenadas se almacenan como latitud/longitud para compatibilidad con SQLite.
    """
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre")
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


from django.core.validators import MinValueValidator, RegexValidator

cedula_validator = RegexValidator(
    regex=r'^\d+(-\d)?$',
    message="La cédula debe contener solo números, opcionalmente seguidos de un guion y un dígito (ej: 1234567 o 1234567-8)."
)

class Persona(models.Model):
    """
    Modelo de persona que extiende al usuario de Django.
    Representa a clientes, empleados y pasajeros del sistema.
    La cédula es la clave primaria (identificador único de Paraguay).
    """
    cedula = models.CharField(
        max_length=20,
        primary_key=True, 
        verbose_name="Cédula/RUC",
        help_text="Número de cédula de identidad o RUC (ej: 1234567 o 1234567-8)",
        validators=[cedula_validator]
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
    latitud = models.DecimalField(
        max_digits=9, decimal_places=6, 
        null=True, blank=True,
        verbose_name="Latitud",
        help_text="Coordenada latitud de la dirección"
    )
    longitud = models.DecimalField(
        max_digits=9, decimal_places=6, 
        null=True, blank=True,
        verbose_name="Longitud",
        help_text="Coordenada longitud de la dirección"
    )
    
    empresa = models.ForeignKey(
        'fleet.Empresa', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='personas',
        verbose_name="Empresa",
        help_text="Empresa a la que pertenece (choferes/ayudantes)"
    )
    
    # Roles (booleanos para simplificar permisos rápidos)
    es_chofer = models.BooleanField(default=False, verbose_name="Es chofer")
    es_ayudante = models.BooleanField(default=False, verbose_name="Es ayudante de transporte")
    es_cliente = models.BooleanField(default=False, verbose_name="Es cliente")
    es_agente = models.BooleanField(default=False, verbose_name="Es agente comercial")
    es_empleado = models.BooleanField(default=False, verbose_name="Es empleado (Legacy)")
    activo = models.BooleanField(default=True, verbose_name="Activo")


    class Meta:
        verbose_name = "Persona"
        verbose_name_plural = "Personas"
        ordering = ['apellido', 'nombre']

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.user and self.user.is_active != self.activo:
            self.user.is_active = self.activo
            self.user.save(update_fields=['is_active'])

    def __str__(self):
        return f"{self.apellido}, {self.nombre} ({self.cedula})"

    def get_absolute_url(self):
        return reverse('users:persona_detail', kwargs={'pk': self.pk})

    @property
    def nombre_completo(self):
        """Retorna el nombre completo de la persona."""
        return f"{self.nombre} {self.apellido}"

    def get_full_name(self):
        """Retorna el nombre completo (alias para compatibilidad con auth.User)."""
        return self.nombre_completo

    @property
    def es_cedula_autogenerada(self):
        """Indica si la cédula fue autogenerada por el sistema (empieza con 999 y tiene 15 caracteres)."""
        c = str(self.cedula)
        return len(c) >= 15 and c.startswith('999')
