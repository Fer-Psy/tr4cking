from django.contrib import admin

from .models import Itinerario, DetalleItinerario, Precio


class DetalleItinerarioInline(admin.TabularInline):
    """Inline para ver/editar paradas de un itinerario."""
    model = DetalleItinerario
    extra = 1
    fields = ('orden', 'parada', 'hora_salida', 'minutos_desde_origen')
    ordering = ('orden',)
    autocomplete_fields = ('parada',)


class PrecioInline(admin.TabularInline):
    """Inline para ver/editar precios de un itinerario."""
    model = Precio
    extra = 1
    fields = ('origen', 'destino', 'precio')
    autocomplete_fields = ('origen', 'destino')


@admin.register(Itinerario)
class ItinerarioAdmin(admin.ModelAdmin):
    """Admin para gestionar itinerarios/rutas."""
    list_display = ('nombre', 'ruta', 'distancia_total_km', 'duracion_estimada_hs', 'dias_operacion_texto', 'activo')
    list_filter = ('activo', 'ruta')
    search_fields = ('nombre', 'ruta')
    ordering = ('nombre',)
    inlines = [DetalleItinerarioInline, PrecioInline]
    fieldsets = (
        ('Información General', {
            'fields': ('nombre', 'ruta', 'activo')
        }),
        ('Distancia y Duración', {
            'fields': ('distancia_total_km', 'duracion_estimada_hs'),
        }),
        ('Días de Operación', {
            'fields': ('dias_semana',),
            'description': 'Patrón binario: 1=opera, 0=no opera. Ej: 1111100 = Lun-Vie'
        }),
    )

    def dias_operacion_texto(self, obj):
        return obj.dias_operacion_texto
    dias_operacion_texto.short_description = 'Días de operación'


@admin.register(DetalleItinerario)
class DetalleItinerarioAdmin(admin.ModelAdmin):
    """Admin para gestionar detalles de itinerario."""
    list_display = ('itinerario', 'orden', 'parada', 'hora_salida', 'minutos_desde_origen')
    list_filter = ('itinerario',)
    search_fields = ('itinerario__nombre', 'parada__nombre')
    ordering = ('itinerario', 'orden')
    autocomplete_fields = ('itinerario', 'parada')


@admin.register(Precio)
class PrecioAdmin(admin.ModelAdmin):
    """Admin para gestionar matriz de precios."""
    list_display = ('itinerario', 'origen', 'destino', 'precio')
    list_filter = ('itinerario',)
    search_fields = ('itinerario__nombre', 'origen__nombre', 'destino__nombre')
    ordering = ('itinerario', 'origen', 'destino')
    autocomplete_fields = ('itinerario', 'origen', 'destino')
