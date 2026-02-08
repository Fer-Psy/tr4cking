"""
URLs para la app Operations.
"""
from django.urls import path
from . import views

app_name = 'operations'

urlpatterns = [
    # ==========================================================================
    # DASHBOARD
    # ==========================================================================
    path('', views.OperationsDashboardView.as_view(), name='dashboard'),
    
    # ==========================================================================
    # VIAJES
    # ==========================================================================
    path('viajes/', views.ViajeListView.as_view(), name='viaje_list'),
    path('viajes/nuevo/', views.ViajeCreateView.as_view(), name='viaje_create'),
    path('viajes/<int:pk>/', views.ViajeDetailView.as_view(), name='viaje_detail'),
    path('viajes/<int:pk>/editar/', views.ViajeUpdateView.as_view(), name='viaje_update'),
    path('viajes/<int:pk>/estado/', views.ViajeEstadoUpdateView.as_view(), name='viaje_estado'),
    
    # ==========================================================================
    # PASAJES
    # ==========================================================================
    path('pasajes/', views.PasajeListView.as_view(), name='pasaje_list'),
    path('pasajes/<int:pk>/', views.PasajeDetailView.as_view(), name='pasaje_detail'),
    path('pasajes/<int:pk>/cancelar/', views.PasajeCancelacionView.as_view(), name='pasaje_cancelar'),
    
    # Venta de pasajes (desde un viaje)
    path('viajes/<int:viaje_pk>/vender-pasaje/', views.PasajeVentaView.as_view(), name='pasaje_venta'),
    
    # ==========================================================================
    # ENCOMIENDAS
    # ==========================================================================
    path('encomiendas/', views.EncomiendaListView.as_view(), name='encomienda_list'),
    path('encomiendas/<int:pk>/', views.EncomiendaDetailView.as_view(), name='encomienda_detail'),
    path('encomiendas/<int:pk>/entregar/', views.EncomiendaEntregarView.as_view(), name='encomienda_entregar'),
    path('encomiendas/<int:pk>/estado/', views.EncomiendaCambiarEstadoView.as_view(), name='encomienda_estado'),
    
    # Registro de encomiendas (desde un viaje)
    path('viajes/<int:viaje_pk>/encomienda/', views.EncomiendaCreateView.as_view(), name='encomienda_create'),
    
    # Tracking público (sin login)
    path('tracking/', views.TrackingPublicoView.as_view(), name='tracking_publico'),
    
    # ==========================================================================
    # CAJA
    # ==========================================================================
    path('caja/', views.CajaDashboardView.as_view(), name='caja_dashboard'),
    path('caja/abrir/', views.AperturaCajaView.as_view(), name='caja_abrir'),
    path('caja/cerrar/', views.CierreCajaView.as_view(), name='caja_cerrar'),
    path('caja/movimiento/', views.MovimientoCajaCreateView.as_view(), name='movimiento_caja_create'),
    path('caja/sesion/<int:pk>/', views.SesionCajaDetailView.as_view(), name='sesion_caja_detail'),
    
    # ==========================================================================
    # FACTURACIÓN
    # ==========================================================================
    path('timbrados/', views.TimbradoListView.as_view(), name='timbrado_list'),
    path('timbrados/nuevo/', views.TimbradoCreateView.as_view(), name='timbrado_create'),
    path('timbrados/<int:pk>/editar/', views.TimbradoUpdateView.as_view(), name='timbrado_update'),
    path('timbrados/<int:pk>/siguiente-numero/', views.TimbradoSiguienteNumeroView.as_view(), name='timbrado_siguiente'),
    
    path('facturacion/pendientes/', views.ClientesPendientesFacturaView.as_view(), name='clientes_pendientes_factura'),
    path('facturas/', views.FacturaListView.as_view(), name='factura_list'),
    path('facturas/nueva/', views.FacturaCreateView.as_view(), name='factura_create'),
    path('facturas/<int:pk>/', views.FacturaDetailView.as_view(), name='factura_detail'),
    path('facturas/<int:pk>/ticket/', views.FacturaTicketView.as_view(), name='factura_ticket'),
    path('facturas/<int:pk>/pdf/', views.FacturaPdfView.as_view(), name='factura_pdf'),
    path('facturas/<int:pk>/anular/', views.FacturaAnularView.as_view(), name='factura_anular'),
    
    # ==========================================================================
    # INCIDENCIAS
    # ==========================================================================
    path('incidencias/', views.IncidenciaListView.as_view(), name='incidencia_list'),
    path('incidencias/nueva/', views.IncidenciaCreateView.as_view(), name='incidencia_create'),
    path('incidencias/<int:pk>/', views.IncidenciaDetailView.as_view(), name='incidencia_detail'),
    path('incidencias/<int:pk>/resolver/', views.IncidenciaResolverView.as_view(), name='incidencia_resolver'),
    
    # Incidencia desde viaje
    path('viajes/<int:viaje_pk>/incidencia/', views.IncidenciaCreateView.as_view(), name='incidencia_viaje_create'),
    
    # ==========================================================================
    # REPORTES
    # ==========================================================================
    path('reportes/diario/', views.ReporteDiarioView.as_view(), name='reporte_diario'),
    path('reportes/ventas/', views.ReporteVentasView.as_view(), name='reporte_ventas'),
    
    # ==========================================================================
    # HTMX PARTIALS
    # ==========================================================================
    path('buscar-persona/', views.BuscarPersonaView.as_view(), name='buscar_persona'),
    path('viajes/<int:viaje_pk>/asientos/', views.AsientosDisponiblesView.as_view(), name='asientos_disponibles'),
    path('obtener-precio/', views.ObtenerPrecioView.as_view(), name='obtener_precio'),
]
