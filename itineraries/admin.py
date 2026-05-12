from django.contrib import admin

from .models import Itinerario, DetalleItinerario, Precio, Horario


class DetalleItinerarioInline(admin.TabularInline):
    """Inline para ver/editar paradas de un itinerario."""
    model = DetalleItinerario
    extra = 1
    fields = ('orden', 'parada', 'minutos_desde_origen', 'distancia_desde_origen_km')
    ordering = ('orden',)
    autocomplete_fields = ('parada',)



@admin.register(Itinerario)
class ItinerarioAdmin(admin.ModelAdmin):
    """Admin para gestionar itinerarios/rutas."""
    list_display = ('nombre', 'empresa', 'ruta', 'distancia_total_km', 'duracion_estimada_hs', 'dias_operacion_texto', 'activo')
    list_filter = ('empresa', 'activo', 'ruta')
    search_fields = ('nombre', 'ruta', 'empresa__nombre')
    ordering = ('nombre',)
    inlines = [DetalleItinerarioInline]
    fieldsets = (
        ('Información General', {
            'fields': ('empresa', 'nombre', 'ruta', 'activo')
        }),
        ('Distancia y Duración', {
            'fields': ('distancia_total_km', 'duracion_estimada_hs'),
        }),
        ('Días de Operación', {
            'fields': ('dias_semana', 'horarios'),
            'description': 'Patrón binario: 1=opera, 0=no opera. Ej: 1111100 = Lun-Vie'
        }),
    )
    filter_horizontal = ('horarios',)

    def dias_operacion_texto(self, obj):
        return obj.dias_operacion_texto
    dias_operacion_texto.short_description = 'Días de operación'


@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    """Admin para gestionar horarios de salida."""
    list_display = ('hora_salida', 'activo')
    list_filter = ('activo',)
    ordering = ('hora_salida',)


@admin.register(DetalleItinerario)
class DetalleItinerarioAdmin(admin.ModelAdmin):
    """Admin para gestionar detalles de itinerario."""
    list_display = ('itinerario', 'orden', 'parada', 'minutos_desde_origen')
    list_filter = ('itinerario',)
    search_fields = ('itinerario__nombre', 'parada__nombre')
    ordering = ('itinerario', 'orden')
    autocomplete_fields = ('itinerario', 'parada')


@admin.register(Precio)
class PrecioAdmin(admin.ModelAdmin):
    """Admin para gestionar matriz de precios."""
    list_display = ('origen', 'destino', 'precio')
    search_fields = ('origen__nombre', 'destino__nombre')
    ordering = ('origen', 'destino')
    autocomplete_fields = ('origen', 'destino')
