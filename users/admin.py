from django.contrib import admin

from .models import Localidad, Persona


@admin.register(Localidad)
class LocalidadAdmin(admin.ModelAdmin):
    """Admin para gestionar localidades."""
    list_display = ('nombre', 'latitud', 'longitud')
    search_fields = ('nombre',)
    ordering = ('nombre',)


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    """Admin para gestionar personas (clientes, empleados, pasajeros)."""
    list_display = (
        'cedula', 'nombre_completo', 'telefono', 'email',
        'es_empleado', 'es_cliente', 'es_pasajero'
    )
    list_filter = ('es_empleado', 'es_cliente', 'es_pasajero')
    search_fields = ('cedula', 'nombre', 'apellido', 'telefono', 'email')
    ordering = ('apellido', 'nombre')
    fieldsets = (
        ('Información Personal', {
            'fields': ('cedula', 'nombre', 'apellido', 'telefono', 'email', 'direccion')
        }),
        ('Usuario del Sistema', {
            'fields': ('user',),
            'classes': ('collapse',),
        }),
        ('Roles', {
            'fields': ('es_empleado', 'es_cliente', 'es_pasajero'),
        }),
    )

    def nombre_completo(self, obj):
        return obj.nombre_completo
    nombre_completo.short_description = 'Nombre Completo'
