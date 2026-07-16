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
    path('ayudante/', views.DashboardAyudanteView.as_view(), name='dashboard_ayudante'),

    
    # ==========================================================================
    # VIAJES
    # ==========================================================================
    path('viajes/', views.ViajeListView.as_view(), name='viaje_list'),
    path('viajes/nuevo/', views.ViajeCreateView.as_view(), name='viaje_create'),
    path('viajes/<int:pk>/', views.ViajeDetailView.as_view(), name='viaje_detail'),
    path('viajes/<int:pk>/editar/', views.ViajeUpdateView.as_view(), name='viaje_update'),
    path('viajes/<int:pk>/estado/', views.ViajeEstadoUpdateView.as_view(), name='viaje_estado'),
    path('viajes/<int:pk>/iniciar/', views.ViajeIniciarView.as_view(), name='viaje_iniciar'),
    path('viajes/<int:pk>/toggle-reservas/', views.ViajeToggleReservaView.as_view(), name='viaje_toggle_reservas'),
    path('viajes/<int:pk>/cancelar/', views.ViajeCancelView.as_view(), name='viaje_cancel'),
    path('viajes/bulk-cancelar/', views.ViajeBulkCancelView.as_view(), name='viaje_bulk_cancel'),
    path('viajes/generar-automaticos/', views.GenerarViajesAutomaticosView.as_view(), name='generar_viajes_automaticos'),
    
    # ==========================================================================
    # PASAJES
    # ==========================================================================
    path('pasajes/', views.PasajeListView.as_view(), name='pasaje_list'),
    path('pasajes/<int:pk>/', views.PasajeDetailView.as_view(), name='pasaje_detail'),
    path('pasajes/<int:pk>/comprobante/', views.PasajeComprobanteView.as_view(), name='pasaje_comprobante'),
    path('pasajes/<int:pk>/cancelar/', views.PasajeCancelacionView.as_view(), name='pasaje_cancelar'),
    path('pasajes/<int:pk>/cancelar-rapida/', views.CancelarReservaRapidaView.as_view(), name='cancelar_reserva_rapida'),
    path('pasajes/<int:pk>/abordar/', views.PasajeAbordarView.as_view(), name='pasaje_abordar'),
    
    # Venta de pasajes (desde un viaje)
    path('viajes/<int:viaje_pk>/vender-pasaje/', views.PasajeVentaView.as_view(), name='pasaje_venta'),
    
    # ==========================================================================
    # ENCOMIENDAS
    # ==========================================================================
    path('encomiendas/', views.EncomiendaListView.as_view(), name='encomienda_list'),
    path('encomiendas/<int:pk>/', views.EncomiendaDetailView.as_view(), name='encomienda_detail'),
    path('encomiendas/<int:pk>/entregar/', views.EncomiendaEntregarView.as_view(), name='encomienda_entregar'),
    path('encomiendas/<int:pk>/estado/', views.EncomiendaCambiarEstadoView.as_view(), name='encomienda_estado'),
    path('encomiendas/<int:pk>/ticket/', views.EncomiendaTicketView.as_view(), name='encomienda_ticket'),
    path('encomiendas/<int:pk>/cancelar-rapida/', views.CancelarEncomiendaRapidaView.as_view(), name='cancelar_encomienda_rapida'),
    path('encomiendas/<int:pk>/abordar/', views.EncomiendaAbordarView.as_view(), name='encomienda_abordar'),
    path('encomiendas/<int:pk>/recibir-terminal/', views.EncomiendaRecibirTerminalView.as_view(), name='encomienda_recibir_terminal'),
    path('encomiendas/nueva/', views.EncomiendaCreateView.as_view(), name='encomienda_create_direct'),
    
    # Registro de encomiendas (desde un viaje)
    path('viajes/<int:viaje_pk>/encomienda/', views.EncomiendaCreateView.as_view(), name='encomienda_create'),
    
    # Tracking público (sin login)
    path('rastreo/', views.TrackingPublicoView.as_view(), name='tracking_publico'),
    
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
    path('timbrados/<int:pk>/eliminar/', views.TimbradoDeleteView.as_view(), name='timbrado_delete'),
    path('timbrados/<int:pk>/inhabilitar/', views.TimbradoInhabilitarView.as_view(), name='timbrado_inhabilitar'),
    path('timbrados/<int:pk>/siguiente-numero/', views.TimbradoSiguienteNumeroView.as_view(), name='timbrado_siguiente'),
    
    path('facturacion/pendientes/', views.ClientesPendientesFacturaView.as_view(), name='clientes_pendientes_factura'),
    path('facturas/', views.FacturaListView.as_view(), name='factura_list'),
    path('facturas/nueva/', views.FacturaCreateView.as_view(), name='factura_create'),
    path('facturas/<int:pk>/', views.FacturaDetailView.as_view(), name='factura_detail'),
    path('facturas/<int:pk>/ticket/', views.FacturaTicketView.as_view(), name='factura_ticket'),
    path('facturas/<int:pk>/pdf/', views.FacturaPdfView.as_view(), name='factura_pdf'),
    path('facturas/<int:pk>/anular/', views.FacturaAnularView.as_view(), name='factura_anular'),
    path('facturacion/cancelar-todo/<str:cedula>/', views.CancelarTodoPendienteView.as_view(), name='cancelar_todo_pendiente'),
    
    # ==========================================================================
    # INCIDENCIAS
    # ==========================================================================
    # path('incidencias/', views.IncidenciaListView.as_view(), name='incidencia_list'),
    # path('incidencias/nueva/', views.IncidenciaCreateView.as_view(), name='incidencia_create'),
    # path('incidencias/<int:pk>/', views.IncidenciaDetailView.as_view(), name='incidencia_detail'),
    # path('incidencias/<int:pk>/resolver/', views.IncidenciaResolverView.as_view(), name='incidencia_resolver'),
    
    # Incidencia desde viaje
    # path('viajes/<int:viaje_pk>/incidencia/', views.IncidenciaCreateView.as_view(), name='incidencia_viaje_create'),
    
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
    
    # APIs para facturación
    path('api/buscar-clientes/', views.BuscarClientesFacturaView.as_view(), name='api_buscar_clientes'),
    path('api/items-pendientes/', views.ObtenerItemsPendientesClienteView.as_view(), name='api_items_pendientes'),
    path('api/crear-encomienda-quick/', views.APICrearEncomiendaFacturacionView.as_view(), name='api_crear_encomienda_quick'),
    path('api/buscar-clientes-registrados/', views.BuscarClientesRegistradosView.as_view(), name='api_buscar_clientes_registrados'),
    path('api/crear-cliente/', views.CrearClienteAjaxView.as_view(), name='api_crear_cliente'),
    
    # API para obtener paradas de un viaje
    path('viajes/<int:viaje_pk>/paradas/', views.ViajeParadasView.as_view(), name='viaje_paradas'),
    path('api/itinerarios-por-empresa/', views.APIItinerariosEmpresaView.as_view(), name='api_itinerarios_empresa'),
    path('api/horarios-por-itinerario/', views.APIHorariosItinerarioView.as_view(), name='api_horarios_itinerario'),
    path('api/buscar-itinerarios/', views.APIBuscarItinerariosView.as_view(), name='api_buscar_itinerarios'),
    path('api/buscar-buses/', views.APIBuscarBusesView.as_view(), name='api_buscar_buses'),
    path('api/buscar-choferes/', views.APIBuscarChoferesView.as_view(), name='api_buscar_choferes'),
    path('api/buscar-ayudantes/', views.APIBuscarAyudantesView.as_view(), name='api_buscar_ayudantes'),
    path('obtener-horarios/', views.ObtenerHorariosItinerarioView.as_view(), name='obtener_horarios'),
    
    # ==========================================================================
    # RASTREO EN TIEMPO REAL
    # ==========================================================================
    path('rastreo-mapa/', views.RastreoMapaView.as_view(), name='rastreo_mapa'),
    path('api/viajes-en-curso/', views.APIViajosEnCursoView.as_view(), name='api_viajes_en_curso'),
    path('api/viajes-publico/', views.APIViajesPublicosView.as_view(), name='api_viajes_publico'),
    path('rastreo-publico/', views.RastreoPublicoView.as_view(), name='rastreo_publico'),
    path('fix-coords-paradas/', views.FixCoordsParadasView.as_view(), name='fix_coords_paradas'),  # temporal

    path('api/actualizar-ubicacion/', views.APIActualizarUbicacionView.as_view(), name='api_actualizar_ubicacion'),
    path('api/desactivar-ubicacion/', views.APIDesactivarUbicacionView.as_view(), name='api_desactivar_ubicacion'),
    
    # ==========================================================================
    # RESERVAS CLIENTES
    # ==========================================================================
    path('buscar-viajes/', views.BuscarViajesClienteView.as_view(), name='buscar_viajes'),
    path('reservar/<int:viaje_pk>/', views.ReservarPasajeView.as_view(), name='reservar_pasaje'),
    path('api/asientos-segmento/<int:viaje_pk>/', views.APIAsientosSegmentoView.as_view(), name='api_asientos_segmento'),
    path('api/enviar-comprobante/<int:pk>/', views.PasajeEnviarCorreoView.as_view(), name='api_enviar_comprobante'),
    path('api/crear-reserva/<int:viaje_pk>/', views.CrearReservaClienteView.as_view(), name='api_crear_reserva'),
    path('api/viajes-compatibles/', views.APIObtenerViajesCompatiblesView.as_view(), name='api_viajes_compatibles'),
    path('mis-encomiendas/', views.MisEncomiendasClienteView.as_view(), name='mis_encomiendas_cliente'),
    path('mis-pasajes/', views.MisPasajesClienteView.as_view(), name='mis_pasajes_cliente'),
]

