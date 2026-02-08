"""
Configuración del Admin para la app Operations.
"""
from django.contrib import admin
from .models import (
    Viaje, TrackingViaje, Pasaje, Encomienda, 
    Timbrado, Factura, DetalleFactura,
    SesionCaja, MovimientoCaja, Incidencia
)


# =============================================================================
# INLINES
# =============================================================================

class TrackingViajeInline(admin.TabularInline):
    model = TrackingViaje
    extra = 0
    readonly_fields = ['timestamp']


class PasajeInline(admin.TabularInline):
    model = Pasaje
    extra = 0
    readonly_fields = ['codigo', 'fecha_venta']
    raw_id_fields = ['pasajero', 'cliente', 'asiento']


class EncomiendaInline(admin.TabularInline):
    model = Encomienda
    extra = 0
    readonly_fields = ['codigo', 'fecha_registro']
    raw_id_fields = ['remitente', 'destinatario']


class DetalleFacturaInline(admin.TabularInline):
    model = DetalleFactura
    extra = 0
    readonly_fields = ['subtotal']


class MovimientoCajaInline(admin.TabularInline):
    model = MovimientoCaja
    extra = 0
    readonly_fields = ['fecha']


# =============================================================================
# VIAJES
# =============================================================================

@admin.register(Viaje)
class ViajeAdmin(admin.ModelAdmin):
    list_display = ['id', 'itinerario', 'bus', 'chofer', 'fecha_viaje', 'estado', 'asientos_disponibles']
    list_filter = ['estado', 'fecha_viaje', 'itinerario']
    search_fields = ['itinerario__nombre', 'bus__placa', 'chofer__nombre', 'chofer__apellido']
    date_hierarchy = 'fecha_viaje'
    raw_id_fields = ['itinerario', 'bus', 'chofer']
    inlines = [PasajeInline, EncomiendaInline, TrackingViajeInline]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(TrackingViaje)
class TrackingViajeAdmin(admin.ModelAdmin):
    list_display = ['viaje', 'latitud', 'longitud', 'velocidad_kmh', 'timestamp']
    list_filter = ['timestamp']
    raw_id_fields = ['viaje', 'parada_actual']


# =============================================================================
# PASAJES
# =============================================================================

@admin.register(Pasaje)
class PasajeAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'viaje', 'pasajero', 'asiento', 'estado', 'precio', 'fecha_venta']
    list_filter = ['estado', 'fecha_venta', 'viaje__fecha_viaje']
    search_fields = ['codigo', 'pasajero__nombre', 'pasajero__apellido', 'pasajero__cedula']
    date_hierarchy = 'fecha_venta'
    raw_id_fields = ['viaje', 'pasajero', 'cliente', 'asiento', 'parada_origen', 'parada_destino']
    readonly_fields = ['codigo', 'fecha_venta']


# =============================================================================
# ENCOMIENDAS
# =============================================================================

@admin.register(Encomienda)
class EncomiendaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'tipo', 'remitente', 'destinatario', 'estado', 'precio', 'fecha_registro']
    list_filter = ['estado', 'tipo', 'fecha_registro']
    search_fields = ['codigo', 'remitente__nombre', 'destinatario__nombre', 'descripcion']
    date_hierarchy = 'fecha_registro'
    raw_id_fields = ['viaje', 'remitente', 'destinatario', 'parada_origen', 'parada_destino']
    readonly_fields = ['codigo', 'fecha_registro']


# =============================================================================
# FACTURACIÓN
# =============================================================================

@admin.register(Timbrado)
class TimbradoAdmin(admin.ModelAdmin):
    list_display = ['numero', 'empresa', 'punto_expedicion', 'fecha_inicio', 'fecha_fin', 'activo', 'esta_vigente']
    list_filter = ['activo', 'empresa', 'fecha_inicio']
    search_fields = ['numero', 'empresa__nombre']


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ['numero_completo', 'cliente', 'total', 'condicion', 'estado', 'fecha_emision', 'cajero']
    list_filter = ['estado', 'condicion', 'fecha_emision', 'timbrado']
    search_fields = ['numero_factura', 'cliente__nombre', 'cliente__cedula']
    date_hierarchy = 'fecha_emision'
    raw_id_fields = ['timbrado', 'cliente', 'cajero', 'sesion_caja']
    readonly_fields = ['fecha_emision', 'subtotal_exenta', 'subtotal_iva5', 'subtotal_iva10', 'total', 'iva_5', 'iva_10', 'total_iva']
    inlines = [DetalleFacturaInline]


@admin.register(DetalleFactura)
class DetalleFacturaAdmin(admin.ModelAdmin):
    list_display = ['factura', 'cantidad', 'descripcion', 'precio_unitario', 'tasa_iva', 'subtotal']
    list_filter = ['tasa_iva']
    search_fields = ['descripcion', 'factura__numero_factura']
    raw_id_fields = ['factura', 'pasaje', 'encomienda']


# =============================================================================
# CAJA
# =============================================================================

@admin.register(SesionCaja)
class SesionCajaAdmin(admin.ModelAdmin):
    list_display = ['id', 'cajero', 'fecha_apertura', 'monto_apertura', 'estado', 'monto_cierre_real', 'diferencia']
    list_filter = ['estado', 'fecha_apertura', 'cajero']
    search_fields = ['cajero__username']
    date_hierarchy = 'fecha_apertura'
    readonly_fields = ['fecha_apertura', 'monto_cierre_esperado']
    inlines = [MovimientoCajaInline]


@admin.register(MovimientoCaja)
class MovimientoCajaAdmin(admin.ModelAdmin):
    list_display = ['sesion', 'tipo', 'concepto', 'monto', 'descripcion', 'fecha']
    list_filter = ['tipo', 'concepto', 'fecha']
    search_fields = ['descripcion']
    date_hierarchy = 'fecha'
    raw_id_fields = ['sesion', 'factura']


# =============================================================================
# INCIDENCIAS
# =============================================================================

@admin.register(Incidencia)
class IncidenciaAdmin(admin.ModelAdmin):
    list_display = ['id', 'viaje', 'tipo', 'prioridad', 'estado', 'reportador', 'fecha_reporte']
    list_filter = ['tipo', 'prioridad', 'estado', 'fecha_reporte']
    search_fields = ['descripcion', 'viaje__itinerario__nombre']
    date_hierarchy = 'fecha_reporte'
    raw_id_fields = ['viaje', 'reportador']
    readonly_fields = ['fecha_reporte']
