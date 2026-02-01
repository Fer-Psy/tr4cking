from django.contrib import admin

from .models import Empresa, Parada, Bus, Asiento


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    """Admin para gestionar empresas de transporte."""
    list_display = ('nombre', 'ruc', 'telefono', 'email')
    search_fields = ('nombre', 'ruc', 'email')
    ordering = ('nombre',)


@admin.register(Parada)
class ParadaAdmin(admin.ModelAdmin):
    """Admin para gestionar paradas y terminales."""
    list_display = ('nombre', 'empresa', 'localidad', 'es_sucursal')
    list_filter = ('empresa', 'localidad', 'es_sucursal')
    search_fields = ('nombre', 'direccion')
    ordering = ('empresa', 'localidad', 'nombre')
    autocomplete_fields = ('empresa', 'localidad')


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    """Admin para gestionar buses de la flota."""
    list_display = ('placa', 'empresa', 'marca', 'modelo', 'capacidad_asientos', 'estado')
    list_filter = ('empresa', 'estado', 'capacidad_pisos')
    search_fields = ('placa', 'marca', 'modelo')
    ordering = ('empresa', 'placa')
    autocomplete_fields = ('empresa',)


class AsientoInline(admin.TabularInline):
    """Inline para ver/editar asientos de un bus."""
    model = Asiento
    extra = 0
    fields = ('numero_asiento', 'piso', 'tipo_asiento')
    ordering = ('piso', 'numero_asiento')


@admin.register(Asiento)
class AsientoAdmin(admin.ModelAdmin):
    """Admin para gestionar asientos individuales."""
    list_display = ('bus', 'numero_asiento', 'piso', 'tipo_asiento')
    list_filter = ('bus__empresa', 'piso', 'tipo_asiento')
    search_fields = ('bus__placa', 'numero_asiento')
    ordering = ('bus', 'piso', 'numero_asiento')
    autocomplete_fields = ('bus',)


# Añadir inline de asientos al admin de Bus
BusAdmin.inlines = [AsientoInline]
