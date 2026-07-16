"""
Vistas para la app Operations.
Dashboard operativo, gestión de viajes, pasajes, encomiendas, caja y reportes.
"""
from decimal import Decimal
from django.views.generic import (
    TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView, View
)
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.edit import FormView
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db.models import Q, Sum, Count, Avg
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from decimal import Decimal
from datetime import timedelta

from .models import (
    Viaje, TrackingViaje, Pasaje, Encomienda, Timbrado, 
    Factura, DetalleFactura, SesionCaja, MovimientoCaja, Incidencia,
    UbicacionAyudante
)
from .utils import (
    limpiar_reservas_expiradas, obtener_asientos_disponibles,
    obtener_mapa_ocupacion, obtener_orden_parada, 
    get_similar_paradas_ids, normalize_search
)
from .forms import (
    ViajeForm, ViajeEstadoForm, PasajeVentaForm, PasajeCancelacionForm,
    EncomiendaForm, EncomiendaEntregaForm, TimbradoForm, FacturaAnulacionForm,
    AperturaCajaForm, CierreCajaForm, MovimientoCajaForm,
    IncidenciaForm, IncidenciaResolucionForm, BusquedaViajeForm
)
from users.models import Persona
from fleet.models import Bus, Parada, Empresa
from itineraries.models import Itinerario, Precio, Horario, DetalleItinerario


# =============================================================================
# DASHBOARD OPERATIVO
# =============================================================================

class OperationsDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard principal de operaciones."""
    template_name = 'operations/dashboard.html'
    
    def get_context_data(self, **kwargs):
        from operations.utils import limpiar_reservas_expiradas
        limpiar_reservas_expiradas()
        
        context = super().get_context_data(**kwargs)
        hoy = timezone.localtime(timezone.now()).date()
        ahora = timezone.localtime(timezone.now())
        hace_7_dias = hoy - timedelta(days=7)
        
        # === VIAJES HOY ===
        viajes_hoy = Viaje.objects.filter(fecha_viaje=hoy, itinerario__activo=True)
        context['viajes_hoy'] = viajes_hoy.count()
        context['viajes_en_curso'] = viajes_hoy.filter(estado='en_curso').count()
        context['viajes_programados'] = viajes_hoy.filter(estado='programado').count()
        context['viajes_completados'] = viajes_hoy.filter(estado='completado').count()
        
        # === PASAJES HOY ===
        pasajes_hoy = Pasaje.objects.filter(fecha_venta__date=hoy)
        context['pasajes_vendidos_hoy'] = pasajes_hoy.filter(estado='vendido').count()
        context['ingresos_pasajes_hoy'] = pasajes_hoy.filter(
            estado='vendido'
        ).aggregate(total=Sum('precio'))['total'] or Decimal('0.00')
        
        # === ENCOMIENDAS HOY ===
        encomiendas_hoy = Encomienda.objects.filter(fecha_registro__date=hoy)
        encomiendas_pendientes = Encomienda.objects.filter(
            estado__in=['registrado', 'en_transito', 'en_destino']
        )
        persona = getattr(self.request.user, 'persona', None)
        if persona and (persona.es_ayudante or persona.es_chofer) and not self.request.user.is_superuser:
            encomiendas_hoy = encomiendas_hoy.filter(
                Q(viaje__chofer=persona) | Q(viaje__ayudantes=persona)
            ).filter(
                Q(viaje__estado='en_curso') | Q(viaje__fecha_viaje__gte=hoy)
            )
            encomiendas_pendientes = encomiendas_pendientes.filter(
                Q(viaje__chofer=persona) | Q(viaje__ayudantes=persona)
            ).filter(
                Q(viaje__estado='en_curso') | Q(viaje__fecha_viaje__gte=hoy)
            )
        context['encomiendas_hoy'] = encomiendas_hoy.count()
        context['encomiendas_pendientes'] = encomiendas_pendientes.count()
        
        # === CAJA ===
        try:
            sesion_caja = SesionCaja.objects.filter(
                cajero=self.request.user,
                estado='abierta'
            ).first()
            context['caja_abierta'] = sesion_caja is not None
            context['sesion_caja'] = sesion_caja
            if sesion_caja:
                context['total_caja'] = sesion_caja.monto_apertura + sesion_caja.total_ingresos - sesion_caja.total_egresos
        except Exception:
            context['caja_abierta'] = False
        
        # === INCIDENCIAS ABIERTAS ===
        context['incidencias_abiertas'] = Incidencia.objects.filter(
            estado__in=['abierta', 'en_proceso']
        ).count()
        context['incidencias_criticas'] = Incidencia.objects.filter(
            estado__in=['abierta', 'en_proceso'],
            prioridad='critica'
        ).count()
        
        # === PRÓXIMOS VIAJES ===
        context['proximos_viajes'] = Viaje.objects.filter(
            fecha_viaje=hoy,
            estado='programado',
            itinerario__activo=True
        ).select_related('itinerario', 'bus', 'chofer').order_by('horario__hora_salida')[:5]
        
        # === VIAJES EN CURSO ===
        context['viajes_activos'] = Viaje.objects.filter(
            estado='en_curso',
            itinerario__activo=True
        ).select_related('itinerario', 'bus', 'chofer')[:5]
        
        # === KPIs SEMANA ===
        pasajes_semana = Pasaje.objects.filter(
            fecha_venta__date__gte=hace_7_dias,
            estado='vendido'
        )
        context['pasajes_semana'] = pasajes_semana.count()
        context['ingresos_semana'] = pasajes_semana.aggregate(
            total=Sum('precio')
        )['total'] or Decimal('0.00')
        
        # Ocupación promedio
        viajes_semana = Viaje.objects.filter(fecha_viaje__gte=hace_7_dias, itinerario__activo=True)
        ocupaciones = []
        for viaje in viajes_semana:
            ocupaciones.append(viaje.porcentaje_ocupacion)
        context['ocupacion_promedio'] = round(sum(ocupaciones) / len(ocupaciones), 1) if ocupaciones else 0
        
        # === ALERTAS ===
        alertas = []
        # Buses en mantenimiento
        buses_mantenimiento = Bus.objects.filter(estado='mantenimiento').count()
        if buses_mantenimiento > 0:
            alertas.append({
                'tipo': 'warning',
                'mensaje': f'{buses_mantenimiento} bus(es) en mantenimiento',
                'icono': 'bi-tools'
            })
        # Incidencias críticas
        if context['incidencias_criticas'] > 0:
            alertas.append({
                'tipo': 'danger',
                'mensaje': f'{context["incidencias_criticas"]} incidencia(s) crítica(s)',
                'icono': 'bi-exclamation-triangle'
            })
        # Baja ocupación
        if context.get('ocupacion_promedio', 0) < 30:
            alertas.append({
                'tipo': 'info',
                'mensaje': f'Ocupación promedio baja: {context.get("ocupacion_promedio", 0)}%',
                'icono': 'bi-graph-down'
            })
            
        # Timbrados por vencer (Avisa 7 días antes, ej. desde el 25 dic para fin de año)
        from operations.models import Timbrado
        timbrados_activos = Timbrado.objects.filter(activo=True).select_related('empresa')
        for t in timbrados_activos:
            dias_restantes = (t.fecha_fin - hoy).days
            if 0 <= dias_restantes <= 7:
                alertas.append({
                    'tipo': 'warning',
                    'mensaje': f'El timbrado {t.numero} de {t.empresa.nombre} vence en {dias_restantes} días',
                    'icono': 'bi-receipt'
                })
            elif dias_restantes < 0:
                alertas.append({
                    'tipo': 'danger',
                    'mensaje': f'El timbrado {t.numero} de {t.empresa.nombre} ha vencido',
                    'icono': 'bi-receipt'
                })

        # === MIS VIAJES ASIGNADOS ===
        # Se muestra a cualquier usuario que esté asignado como chofer o ayudante
        persona = getattr(self.request.user, 'persona', None)
        if persona:
            viajes_asignados = Viaje.objects.filter(
                Q(ayudantes=persona) | Q(chofer=persona),
                estado='programado',
                fecha_viaje__gte=hoy,
                itinerario__activo=True
            ).select_related('itinerario', 'bus', 'chofer', 'empresa', 'horario').order_by('fecha_viaje', 'horario__hora_salida').distinct()
            
            if viajes_asignados.exists():
                context['es_ayudante'] = True  # Mantiene compatibilidad con el template
                context['mis_viajes_asignados'] = viajes_asignados
        
        context['alertas'] = alertas
            
        # Verificar viajes para mañana (alerta si faltan)
        mañana = hoy + timedelta(days=1)
        dia_semana_mañana = mañana.weekday()
        
        itinerarios_activos = Itinerario.objects.filter(activo=True)
        horarios_esperados = sum(
            it.horarios.filter(activo=True).count()
            for it in itinerarios_activos if it.opera_en_dia(dia_semana_mañana)
        )
        
        viajes_mañana = Viaje.objects.filter(fecha_viaje=mañana, itinerario__activo=True).count()
        
        if horarios_esperados > 0 and viajes_mañana < horarios_esperados:
            alertas.append({
                'tipo': 'warning',
                'mensaje': 'Faltan viajes programados para mañana. Clientes no pueden comprar pasajes aún.',
                'icono': 'bi-calendar-event'
            })
            context['mostrar_generador'] = True

        context['alertas'] = alertas
        return context


class DashboardAyudanteView(LoginRequiredMixin, TemplateView):
    """
    Panel de control específico para el Ayudante de transporte.
    Incluye rastreo, venta rápida, gestión de caja y encomiendas.
    """
    template_name = 'operations/dashboard_ayudante.html'

    def get_context_data(self, **kwargs):
        from operations.utils import limpiar_reservas_expiradas
        limpiar_reservas_expiradas()

        context = super().get_context_data(**kwargs)
        persona = getattr(self.request.user, 'persona', None)
        hoy = timezone.localtime(timezone.now()).date()
        ahora = timezone.localtime(timezone.now())

        if not persona or not (persona.es_ayudante or persona.es_chofer):
            messages.warning(self.request, "No tienes permisos de ayudante o empleado.")
            return context

        # 1. Viaje activo (en curso)
        viaje_activo = Viaje.objects.filter(
            Q(chofer=persona) | Q(ayudantes=persona),
            estado='en_curso',
            fecha_viaje=hoy,
            itinerario__activo=True
        ).select_related('itinerario', 'bus', 'horario').first()

        # Si no hay uno en curso, buscar el próximo programado para hoy o el futuro
        if not viaje_activo:
            viaje_activo = Viaje.objects.filter(
                Q(chofer=persona) | Q(ayudantes=persona),
                estado='programado',
                fecha_viaje__gte=hoy,
                itinerario__activo=True
            ).select_related('itinerario', 'bus', 'horario').order_by('fecha_viaje', 'horario__hora_salida').first()

        context['viaje_activo'] = viaje_activo

        # 2. Estado de rastreo
        tracking_activo = UbicacionAyudante.objects.filter(
            persona=persona,
            activo=True
        ).exists()
        context['tracking_activo'] = tracking_activo

        # 3. Estado de caja
        sesion_caja = SesionCaja.objects.filter(
            cajero=self.request.user,
            estado='abierta'
        ).first()
        context['sesion_caja'] = sesion_caja
        if sesion_caja:
            context['total_caja'] = sesion_caja.monto_apertura + sesion_caja.total_ingresos - sesion_caja.total_egresos

        # 4. Encomiendas asignadas al bus (pendientes de entrega)
        if viaje_activo:
            # Encomiendas que viajan en este bus y no han sido entregadas
            context['encomiendas_viaje'] = Encomienda.objects.filter(
                viaje=viaje_activo,
                estado__in=['registrado', 'en_transito', 'en_destino']
            ).select_related('remitente', 'destinatario', 'parada_destino').order_by('parada_destino__nombre')

            # Pasajes vendidos/reservados recientemente en este viaje
            context['pasajes_recientes'] = Pasaje.objects.filter(
                viaje=viaje_activo,
                estado__in=['vendido', 'reservado']
            ).select_related('pasajero', 'asiento', 'parada_origen', 'parada_destino').order_by('-fecha_venta', '-id')[:5]

            # 6. Mapa de Asientos para el Ayudante
            asientos = viaje_activo.bus.asientos.all().order_by('piso', 'numero_asiento')
            pasajes_activos = Pasaje.objects.filter(
                viaje=viaje_activo,
                estado__in=['reservado', 'vendido', 'abordado']
            ).select_related('asiento', 'pasajero', 'parada_destino').order_by('-orden_origen', '-orden_destino')
            
            asientos_dict = {p.asiento_id: p for p in pasajes_activos}
            asientos_data = []
            for a in asientos:
                pasaje = asientos_dict.get(a.id)
                asientos_data.append({
                    'id': a.id,
                    'numero': a.numero_asiento,
                    'piso': a.piso,
                    'ocupado': pasaje is not None,
                    'pasaje': pasaje,
                    'destino': pasaje.parada_destino.nombre if pasaje else None,
                    'pasajero': pasaje.pasajero.nombre_completo if pasaje else None,
                    'estado': pasaje.estado if pasaje else 'libre'
                })
            context['asientos_mapa'] = asientos_data
            context['piso_1'] = [a for a in asientos_data if a['piso'] == 1]
            context['piso_2'] = [a for a in asientos_data if a['piso'] == 2]

        # 5. Cronograma completo (Próximos viajes)
        context['proximos_viajes'] = Viaje.objects.filter(
            Q(chofer=persona) | Q(ayudantes=persona),
            estado='programado',
            fecha_viaje__gte=hoy
        ).select_related('itinerario', 'bus', 'chofer', 'empresa', 'horario').order_by('fecha_viaje', 'horario__hora_salida').distinct()

        # 6. Cliente Ocasional (para facturación rápida)
        try:
            cliente_ocasional = Persona.objects.get(cedula=99999999)
        except Persona.DoesNotExist:
            cliente_ocasional = Persona.objects.create(
                cedula=99999999,
                nombre='Cliente',
                apellido='Ocasional',
                es_cliente=True
            )
        context['cliente_ocasional'] = cliente_ocasional

        return context


class ViajeIniciarView(LoginRequiredMixin, View):
    """API para que el ayudante inicie el viaje rápidamente."""
    def post(self, request, pk):
        from django.utils import timezone
        viaje = get_object_or_404(Viaje, pk=pk)
        persona = getattr(request.user, 'persona', None)
        
        # Validar permisos (debe ser el chofer o ayudante del viaje)
        if not request.user.is_staff:
            is_ayudante = viaje.ayudantes.filter(pk=persona.pk).exists() if persona else False
            if not persona or (viaje.chofer != persona and not is_ayudante):
                return JsonResponse({'error': 'No autorizado para iniciar este viaje'}, status=403)
        
        if viaje.estado != 'programado':
            return JsonResponse({'error': 'El viaje ya ha sido iniciado o ya está completado'}, status=400)
            
        viaje.estado = 'en_curso'
        viaje.hora_salida_real = timezone.localtime().time()
        viaje.save()

        # Preparar localización: desactivar sesiones previas de esta persona
        if persona:
            UbicacionAyudante.objects.filter(persona=persona, activo=True).update(activo=False)
        
        return JsonResponse({
            'ok': True, 
            'mensaje': '¡Buen viaje! El viaje ahora está en curso y la localización activa.'
        })


class ViajeToggleReservaView(LoginRequiredMixin, View):
    """API para que el ayudante bloquee o desbloquee las reservas de un viaje."""
    def post(self, request, pk):
        import json
        viaje = get_object_or_404(Viaje, pk=pk)
        persona = getattr(request.user, 'persona', None)
        
        # Validar permisos (debe ser el chofer o ayudante del viaje)
        if not request.user.is_staff:
            is_ayudante = viaje.ayudantes.filter(pk=persona.pk).exists() if persona else False
            if not persona or (viaje.chofer != persona and not is_ayudante):
                return JsonResponse({'error': 'No autorizado para modificar este viaje'}, status=403)
        
        try:
            data = json.loads(request.body)
            bloquear = data.get('bloquear', not viaje.reservas_bloqueadas)
        except:
            bloquear = not viaje.reservas_bloqueadas
            
        if bloquear and viaje.asientos_disponibles > 0:
            return JsonResponse({'error': 'Solo se pueden bloquear las reservas si el bus está completamente lleno (0 asientos disponibles).'}, status=400)
            
        viaje.reservas_bloqueadas = bloquear
        viaje.save()

        return JsonResponse({
            'ok': True, 
            'bloqueadas': viaje.reservas_bloqueadas,
            'mensaje': 'Las reservas han sido bloqueadas.' if viaje.reservas_bloqueadas else 'Las reservas han sido desbloqueadas.'
        })


class ViajeCancelView(LoginRequiredMixin, View):
    """API para cancelar un viaje rápidamente."""
    def post(self, request, pk):
        viaje = get_object_or_404(Viaje, pk=pk)
        
        if viaje.estado == 'cancelado':
            return JsonResponse({'error': 'El viaje ya está cancelado'}, status=400)
        
        if viaje.estado == 'completado':
            return JsonResponse({'error': 'No se puede cancelar un viaje completado'}, status=400)
            
        if viaje.estado == 'en_curso':
            return JsonResponse({'error': 'No se puede cancelar un viaje que ya está en curso'}, status=400)

        # Verificar si hay pasajes vendidos/reservados
        pasajes_activos = viaje.pasajes.filter(estado__in=['vendido', 'reservado', 'abordado']).count()
        if pasajes_activos > 0:
            return JsonResponse({
                'error': f'No se puede cancelar porque tiene {pasajes_activos} pasajes activos. Debe reubicarlos o cancelarlos primero.'
            }, status=400)
            
        # Verificar si hay encomiendas asignadas
        encomiendas_activas = viaje.encomiendas.exclude(estado='cancelado').count()
        if encomiendas_activas > 0:
            return JsonResponse({
                'error': f'No se puede cancelar porque tiene {encomiendas_activas} encomiendas asignadas. Debe reubicarlas o cancelarlas primero.'
            }, status=400)

        viaje.estado = 'cancelado'
        viaje.save()
        
        messages.success(request, f"Viaje #{viaje.id} cancelado correctamente.")
        return JsonResponse({'ok': True, 'mensaje': f'Viaje #{viaje.id} cancelado correctamente.'})


class ViajeBulkCancelView(LoginRequiredMixin, View):
    """API para cancelar múltiples viajes."""
    def post(self, request):
        viaje_ids = request.POST.getlist('viaje_ids[]')
        if not viaje_ids:
            return JsonResponse({'error': 'No se seleccionaron viajes'}, status=400)
            
        viajes = Viaje.objects.filter(pk__in=viaje_ids)
        cancelados = 0
        omitidos = 0
        
        for viaje in viajes:
            if viaje.estado in ['cancelado', 'completado', 'en_curso']:
                omitidos += 1
                continue
                
            # No cancelar si tiene pasajes activos
            if viaje.pasajes.filter(estado__in=['vendido', 'reservado', 'abordado']).exists():
                omitidos += 1
                continue
                
            # No cancelar si tiene encomiendas asignadas
            if viaje.encomiendas.exclude(estado='cancelado').exists():
                omitidos += 1
                continue
                
            viaje.estado = 'cancelado'
            viaje.save()
            cancelados += 1
            
        if cancelados > 0:
            messages.success(request, f"Se han cancelado {cancelados} viaje(s) correctamente.")
        
        return JsonResponse({
            'ok': True, 
            'mensaje': f'Proceso completado. {cancelados} cancelados, {omitidos} omitidos.'
        })



class GenerarViajesAutomaticosView(LoginRequiredMixin, View):
    """Genera viajes para los próximos días basados en itinerarios y recursos predeterminados."""
    def post(self, request):
        dias = int(request.POST.get('dias', 8))
        ahora = timezone.localtime(timezone.now())
        hoy = ahora.date()
        
        itinerarios = Itinerario.objects.filter(
            activo=True
        ).prefetch_related('horarios').select_related('empresa', 'bus_predeterminado', 'chofer_predeterminado', 'ayudante_predeterminado')
        
        creados = 0
        errores = 0
        
        for i in range(dias + 1):
            fecha = hoy + timedelta(days=i)
            dia_semana = fecha.weekday()
            
            for it in itinerarios:
                if it.opera_en_dia(dia_semana):
                    for h in it.horarios.all():
                        if not h.activo:
                            continue
                        if not Viaje.objects.filter(itinerario=it, horario=h, fecha_viaje=fecha).exists():
                            try:
                                bus = it.bus_predeterminado
                                if bus and bus.estado != 'activo': bus = None
                                
                                chofer = it.chofer_predeterminado
                                ayudante = it.ayudante_predeterminado
                                
                                if bus and chofer:
                                    if Viaje.objects.filter(chofer=chofer, fecha_viaje=fecha).exclude(estado='cancelado').exists():
                                        continue
                                    if ayudante and Viaje.objects.filter(ayudantes=ayudante, fecha_viaje=fecha).exclude(estado='cancelado').exists():
                                        continue
                                    
                                    from django.db.models import Q
                                    last_trip = Viaje.objects.filter(
                                        chofer=chofer,
                                        estado__in=['programado', 'en_curso', 'completado']
                                    ).filter(
                                        Q(fecha_viaje__lt=fecha) | 
                                        Q(fecha_viaje=fecha, horario__hora_salida__lt=h.hora_salida)
                                    ).order_by('-fecha_viaje', '-horario__hora_salida').first()
                                    
                                    if last_trip and last_trip.itinerario == it:
                                        continue

                                    
                                    viaje = Viaje.objects.create(
                                        itinerario=it,
                                        horario=h,
                                        fecha_viaje=fecha,
                                        bus=bus,
                                        chofer=chofer,
                                        empresa=it.empresa,
                                        estado='programado'
                                    )
                                    if ayudante:
                                        viaje.ayudantes.add(ayudante)
                                    creados += 1
                            except Exception:
                                errores += 1
        
        if creados > 0:
            messages.success(request, f"Se han generado {creados} viajes para los próximos {dias} días.")
        else:
            messages.warning(request, "No se generaron viajes nuevos. Asegúrese de tener recursos predeterminados asignados en los Itinerarios.")
            
        return redirect('operations:dashboard')


# =============================================================================
# VIAJES
# =============================================================================

class ViajeListView(LoginRequiredMixin, ListView):
    """Lista de viajes con filtros."""
    model = Viaje
    template_name = 'operations/viaje_list.html'
    context_object_name = 'viajes'
    paginate_by = 15
    
    def get_queryset(self):
        from operations.utils import limpiar_reservas_expiradas
        limpiar_reservas_expiradas()
        
        queryset = super().get_queryset().select_related(
            'itinerario', 'bus', 'chofer', 'horario'
        ).prefetch_related('ayudantes').annotate(
            num_pasajes=Count('pasajes', filter=Q(pasajes__estado__in=['vendido', 'reservado']))
        )
        
        # Filtros
        fecha = self.request.GET.get('fecha')
        if fecha:
            queryset = queryset.filter(fecha_viaje=fecha)
        else:
            # Por defecto mostrar viajes de hoy en adelante
            queryset = queryset.filter(fecha_viaje__gte=timezone.localtime(timezone.now()).date())
        
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        else:
            # Por defecto ocultar los cancelados a menos que se filtre específicamente
            queryset = queryset.exclude(estado='cancelado')
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(itinerario__nombre__icontains=search) |
                Q(bus__placa__icontains=search) |
                Q(chofer__nombre__icontains=search)
            )
        
        return queryset.order_by('fecha_viaje', 'pk')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['fecha_filter'] = self.request.GET.get('fecha', '')
        context['estado_filter'] = self.request.GET.get('estado', '')
        context['search'] = self.request.GET.get('search', '')
        context['estados'] = Viaje.ESTADO_CHOICES
        return context


class ViajeDetailView(LoginRequiredMixin, DetailView):
    """Detalle de un viaje con pasajes y encomiendas."""
    model = Viaje
    template_name = 'operations/viaje_detail.html'
    context_object_name = 'viaje'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        viaje = self.object
        
        # Pasajes del viaje
        context['pasajes'] = viaje.pasajes.select_related(
            'pasajero', 'asiento', 'parada_origen', 'parada_destino'
        ).order_by('asiento__numero_asiento')
        
        # Encomiendas del viaje
        context['encomiendas'] = viaje.encomiendas.select_related(
            'remitente', 'destinatario', 'parada_origen', 'parada_destino'
        ).order_by('-fecha_registro')
        
        # Incidencias
        context['incidencias'] = viaje.incidencias.order_by('-fecha_reporte')
        
        # Mapa de asientos con info de segmentos
        context['asientos_bus'] = viaje.bus.asientos.all().order_by('piso', 'numero_asiento')
        
        # Obtener mapa de ocupación por segmentos
        from operations.utils import obtener_mapa_ocupacion
        context['mapa_ocupacion'] = obtener_mapa_ocupacion(viaje)
        
        # Lista de asientos con al menos un pasaje activo  
        context['asientos_ocupados'] = list(viaje.pasajes.filter(
            estado__in=['reservado', 'vendido', 'abordado']
        ).values_list('asiento_id', flat=True).distinct())
        
        # Detalles del itinerario (paradas en orden)
        context['detalles_itinerario'] = viaje.itinerario.detalles.select_related(
            'parada', 'parada__localidad'
        ).order_by('orden')
        
        # Hora de salida programada
        context['hora_salida_programada'] = viaje.hora_salida_programada
        
        # Estadísticas
        context['stats'] = {
            'total_pasajes': viaje.pasajes.filter(estado__in=['vendido', 'reservado']).count(),
            'total_encomiendas': viaje.encomiendas.count(),
            'ingresos_pasajes': viaje.pasajes.filter(estado='vendido').aggregate(
                total=Sum('precio')
            )['total'] or Decimal('0.00'),
            'ingresos_encomiendas': viaje.encomiendas.filter(
                estado__in=['registrado', 'en_transito', 'en_destino', 'entregado']
            ).aggregate(total=Sum('precio'))['total'] or Decimal('0.00'),
        }
        context['stats']['total_ingresos'] = context['stats']['ingresos_pasajes'] + context['stats']['ingresos_encomiendas']
        
        # Siguiente fecha sugerida para programar
        context['proxima_fecha_sugerida'] = (viaje.fecha_viaje + timedelta(days=1)).strftime('%Y-%m-%d')
        
        return context


class ViajeCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Crear un nuevo viaje (programado por 8 días)."""
    model = Viaje
    form_class = ViajeForm
    template_name = 'operations/viaje_form.html'
    success_url = reverse_lazy('operations:viaje_list')
    success_message = "Viaje(s) programado(s) exitosamente."

    def get_initial(self):
        initial = super().get_initial()
        itinerario_id = self.request.GET.get('itinerario')
        horario_id = self.request.GET.get('horario')
        fecha = self.request.GET.get('fecha')
        
        if itinerario_id:
            try:
                it = Itinerario.objects.get(pk=itinerario_id)
                initial['itinerario'] = it.pk
                if it.empresa:
                    initial['empresa'] = it.empresa_id
                
                # Recursos predeterminados del itinerario
                if it.bus_predeterminado and it.bus_predeterminado.estado == 'activo':
                    initial['bus'] = it.bus_predeterminado_id
                if it.chofer_predeterminado:
                    initial['chofer'] = it.chofer_predeterminado_id
                if it.ayudante_predeterminado:
                    initial['ayudantes'] = [it.ayudante_predeterminado_id]
            except Itinerario.DoesNotExist:
                pass

        if horario_id:
            try:
                h = Horario.objects.get(pk=horario_id)
                initial['horario'] = h.pk
            except Horario.DoesNotExist:
                pass
        
        if fecha:
            initial['fecha_viaje'] = fecha
        elif not initial.get('fecha_viaje'):
            # Por defecto hoy
            initial['fecha_viaje'] = timezone.localtime(timezone.now()).date()
            
        return initial

    def form_valid(self, form):
        """
        Al programar un viaje se crean viajes para los próximos 8 días
        con el mismo bus, chofer y ayudantes, respetando los días de operación.
        """
        viaje_base = form.save(commit=False)
        itinerario = viaje_base.itinerario
        horario = viaje_base.horario
        bus = viaje_base.bus
        chofer = viaje_base.chofer
        empresa = form.cleaned_data.get('empresa') or itinerario.empresa
        ayudantes_ids = form.cleaned_data.get('ayudantes', [])
        observaciones = viaje_base.observaciones
        fecha_inicio = viaje_base.fecha_viaje
        
        creados = 0
        omitidos = 0
        errores_lista = []
        
        for i in range(8):
            fecha = fecha_inicio + timedelta(days=i)
            dia_semana = fecha.weekday()
            
            # Solo crear en días que opera el itinerario
            if not itinerario.opera_en_dia(dia_semana):
                omitidos += 1
                continue
            
            # No crear si ya existe un viaje para ese itinerario+horario+fecha
            if horario and Viaje.objects.filter(
                itinerario=itinerario, horario=horario, fecha_viaje=fecha
            ).exists():
                omitidos += 1
                continue
            
            # No crear si el chofer ya tiene un viaje en esa fecha y horario
            if chofer and Viaje.objects.filter(chofer=chofer, horario=horario, fecha_viaje=fecha).exists():
                errores_lista.append(f"{fecha.strftime('%d/%m')}: Chofer {chofer.get_full_name()} ya asignado a otro viaje a esta hora")
                continue
                
            # No crear si algún ayudante ya tiene un viaje en esa fecha y horario
            ayudante_conflicto = False
            if ayudantes_ids:
                for ayudante_id in ayudantes_ids:
                    if Viaje.objects.filter(ayudantes=ayudante_id, horario=horario, fecha_viaje=fecha).exists():
                        ayudante_conflicto = True
                        break
            
            if ayudante_conflicto:
                errores_lista.append(f"{fecha.strftime('%d/%m')}: Un ayudante ya asignado a otro viaje a esta hora")
                continue
            
            # Validar fecha pasada
            ahora = timezone.localtime(timezone.now())
            if fecha < ahora.date():
                continue
            if fecha == ahora.date() and horario and horario.hora_salida < ahora.time():
                continue
            
            try:
                nuevo_viaje = Viaje.objects.create(
                    itinerario=itinerario,
                    horario=horario,
                    bus=bus,
                    chofer=chofer,
                    empresa=empresa,
                    fecha_viaje=fecha,
                    estado='programado',
                    observaciones=observaciones,
                )
                if ayudantes_ids:
                    nuevo_viaje.ayudantes.set(ayudantes_ids)
                creados += 1
            except Exception as e:
                errores_lista.append(f"{fecha.strftime('%d/%m')}: {str(e)}")
        
        if creados > 0:
            messages.success(
                self.request,
                f"Se programaron {creados} viaje(s) para los próximos 8 días "
                f"({itinerario.nombre} - Bus: {bus.placa})."
            )
        
        if omitidos > 0:
            messages.info(
                self.request,
                f"{omitidos} día(s) omitidos (no opera o ya existe viaje programado)."
            )
        
        if errores_lista:
            messages.warning(
                self.request,
                f"Errores en {len(errores_lista)} día(s): {'; '.join(errores_lista[:3])}"
            )
        
        if creados == 0 and not errores_lista:
            messages.warning(self.request, "No se creó ningún viaje. Verifique que el itinerario opera en los próximos días.")
        
        return redirect(self.success_url)


class ViajeUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar un viaje."""
    model = Viaje
    form_class = ViajeForm
    template_name = 'operations/viaje_form.html'
    success_message = "Viaje actualizado exitosamente."
    
    def get_success_url(self):
        return reverse('operations:viaje_detail', kwargs={'pk': self.object.pk})


class ViajeEstadoUpdateView(LoginRequiredMixin, UpdateView):
    """Cambiar estado de un viaje."""
    model = Viaje
    form_class = ViajeEstadoForm
    template_name = 'operations/viaje_estado_form.html'
    
    def form_valid(self, form):
        viaje = form.save(commit=False)
        nuevo_estado = form.cleaned_data['estado']
        
        if nuevo_estado == 'en_curso' and not viaje.hora_salida_real:
            viaje.hora_salida_real = timezone.localtime(timezone.now()).time()
        elif nuevo_estado == 'completado' and not viaje.hora_llegada_real:
            viaje.hora_llegada_real = timezone.localtime(timezone.now()).time()
        
        viaje.save()
        messages.success(self.request, f"Estado del viaje actualizado a '{viaje.get_estado_display()}'")
        return redirect('operations:viaje_detail', pk=viaje.pk)


# =============================================================================
# PASAJES
# =============================================================================

class PasajeListView(LoginRequiredMixin, ListView):
    """Lista de pasajes."""
    model = Pasaje
    template_name = 'operations/pasaje_list.html'
    context_object_name = 'pasajes'
    paginate_by = 15
    
    def get_queryset(self):
        from operations.utils import limpiar_reservas_expiradas
        limpiar_reservas_expiradas()
        
        queryset = super().get_queryset().select_related(
            'viaje__itinerario', 'pasajero', 'asiento', 'parada_origen', 'parada_destino'
        )
        
        # Filtro de seguridad: Ayudantes y Choferes SOLO ven sus propias ventas
        persona = getattr(self.request.user, 'persona', None)
        es_personal = persona and (persona.es_ayudante or persona.es_chofer or persona.es_agente)
        es_admin = self.request.user.is_superuser
        
        if es_personal and not es_admin:
            queryset = queryset.filter(vendedor=self.request.user)
        else:
            # Si es admin, permitir filtrar por un vendedor específico vía URL (?vendedor=username)
            vendedor_username = self.request.GET.get('vendedor')
            if vendedor_username:
                queryset = queryset.filter(vendedor__username=vendedor_username)
        
        # Filtros
        fecha = self.request.GET.get('fecha')
        if fecha:
            queryset = queryset.filter(viaje__fecha_viaje=fecha)
        
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(codigo__icontains=search) |
                Q(pasajero__cedula__icontains=search) |
                Q(pasajero__nombre__icontains=search) |
                Q(pasajero__apellido__icontains=search) |
                Q(vendedor__username__icontains=search)
            )
        
        return queryset.order_by('-id')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = Pasaje.ESTADO_CHOICES
        context['fecha_filter'] = self.request.GET.get('fecha', '')
        context['estado_filter'] = self.request.GET.get('estado', '')
        context['search'] = self.request.GET.get('search', '')
        return context


class PasajeDetailView(LoginRequiredMixin, DetailView):
    """Detalle de un pasaje."""
    model = Pasaje
    template_name = 'operations/pasaje_detail.html'
    context_object_name = 'pasaje'


class PasajeVentaView(LoginRequiredMixin, CreateView):
    """Vista para venta de pasajes."""
    model = Pasaje
    form_class = PasajeVentaForm
    template_name = 'operations/pasaje_venta.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not SesionCaja.objects.filter(cajero=request.user, estado='abierta').exists():
            messages.error(request, "Debe abrir la caja antes de poder vender pasajes.")
            return redirect('operations:caja_dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        viaje_pk = self.kwargs.get('viaje_pk')
        if viaje_pk:
            kwargs['viaje'] = get_object_or_404(Viaje, pk=viaje_pk)
        return kwargs
    
    def get_initial(self):
        initial = super().get_initial()
        cliente_cedula = self.request.GET.get('cliente')
        if cliente_cedula:
            cedula_limpia = cliente_cedula.replace(' ', '').replace('\xa0', '').replace('.', '')
            persona = Persona.objects.filter(cedula=cedula_limpia).first()
            if persona:
                initial['cedula_pasajero'] = persona.cedula
                initial['nombre_pasajero'] = persona.nombre
                initial['apellido_pasajero'] = persona.apellido
                initial['telefono_pasajero'] = persona.telefono
                
        origen_id = self.request.GET.get('origen')
        destino_id = self.request.GET.get('destino')
        if origen_id:
            initial['parada_origen'] = origen_id
        if destino_id:
            initial['parada_destino'] = destino_id
            
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        viaje_pk = self.kwargs.get('viaje_pk')
        if viaje_pk:
            context['viaje'] = get_object_or_404(Viaje, pk=viaje_pk)
        return context
    
    def form_valid(self, form):
        pasaje = form.save(commit=False)
        
        # Obtener o crear pasajero
        cedula_pasajero = form.cleaned_data.get('cedula_pasajero')
        nombre_pasajero = form.cleaned_data.get('nombre_pasajero')
        apellido_pasajero = form.cleaned_data.get('apellido_pasajero')
        telefono_pasajero = form.cleaned_data.get('telefono_pasajero')

        try:
            pasajero = Persona.objects.get(cedula=cedula_pasajero)
            # Actualizar datos si viene del formulario
            actualizado = False
            if nombre_pasajero and pasajero.nombre != nombre_pasajero:
                pasajero.nombre = nombre_pasajero
                actualizado = True
            if apellido_pasajero and pasajero.apellido != apellido_pasajero:
                pasajero.apellido = apellido_pasajero
                actualizado = True
            if telefono_pasajero and pasajero.telefono != telefono_pasajero:
                pasajero.telefono = telefono_pasajero
                actualizado = True
            if actualizado:
                pasajero.save()
        except Persona.DoesNotExist:
            pasajero = Persona.objects.create(
                cedula=cedula_pasajero,
                nombre=nombre_pasajero or 'Sin nombre',
                apellido=apellido_pasajero or '',
                telefono=telefono_pasajero or ''
            )
        
        pasaje.pasajero = pasajero
        
        # Obtener opcionalmente el cliente (quien paga)
        cedula_cliente = form.cleaned_data.get('cedula_cliente')
        if cedula_cliente and cedula_cliente != cedula_pasajero:
            try:
                cliente = Persona.objects.get(cedula=cedula_cliente)
                pasaje.cliente = cliente
            except Persona.DoesNotExist:
                # Si el cliente no existe, lo creamos con datos mínimos (se completarán en facturación)
                pasaje.cliente = Persona.objects.create(
                    cedula=cedula_cliente,
                    nombre='Cliente',
                    apellido='Registrado',
                    es_cliente=True
                )
        
        pasaje.vendedor = self.request.user
        
        # Si el vendedor es personal de bus, marcar como reservado inicialmente.
        # Se marcará como abordado recién al generar la factura.
        persona_vendedor = getattr(self.request.user, 'persona', None)
        if persona_vendedor and (persona_vendedor.es_ayudante or persona_vendedor.es_chofer):
            pasaje.estado = 'reservado'
        else:
            pasaje.estado = 'vendido'
        
        # Asignar órdenes de origen/destino para gestión por segmentos
        pasaje.orden_origen = form.cleaned_data.get('orden_origen', 1)
        pasaje.orden_destino = form.cleaned_data.get('orden_destino', 2)
        
        # Obtener precio del itinerario
        try:
            precio_obj = Precio.objects.get(
                origen=pasaje.parada_origen,
                destino=pasaje.parada_destino
            )
            pasaje.precio = precio_obj.precio
        except Precio.DoesNotExist:
            # Si no hay precio fijo, usamos el del formulario (que el vendedor puede haber editado)
            if not pasaje.precio or pasaje.precio == 0:
                messages.warning(self.request, "No se encontró precio configurado. Se usó el precio manual.")
                # pasaje.precio ya viene del form.precio si se ingresó
        
        pasaje.save()
        
        # NOTA: El ingreso en caja se registra al momento de generar la factura,
        # no al vender el pasaje
        
        messages.success(self.request, f"Pasaje {pasaje.codigo} vendido exitosamente.")
        
        # Si es una venta rápida (viene con parámetro cliente), redirigir directamente a facturación
        if self.request.GET.get('cliente'):
            return redirect(f"{reverse('operations:factura_create')}?pasaje={pasaje.pk}")
        
        # Si el vendedor es ayudante/chofer/agente o superusuario, redirigir directamente a facturación
        persona_vendedor = getattr(self.request.user, 'persona', None)
        is_staff_or_role = self.request.user.is_superuser or (persona_vendedor and (
            persona_vendedor.es_ayudante or 
            persona_vendedor.es_chofer or 
            persona_vendedor.es_agente
        ))
        
        if is_staff_or_role:
            # Los ayudantes y choferes imprimen directo el ticket (formato rollo)
            print_param = "&print=1" if (persona_vendedor and (persona_vendedor.es_ayudante or persona_vendedor.es_chofer)) else ""
            return redirect(f"{reverse('operations:factura_create')}?pasaje={pasaje.pk}{print_param}")
            
        return redirect('operations:pasaje_detail', pk=pasaje.pk)


class PasajeCancelacionView(LoginRequiredMixin, View):
    """Vista para cancelar un pasaje."""
    
    def get(self, request, pk):
        pasaje = get_object_or_404(Pasaje, pk=pk)
        if pasaje.estado != 'reservado':
            messages.error(request, "Solo se pueden cancelar pasajes en estado Reservado.")
            return redirect('operations:pasaje_list')
        initial = {}
        if pasaje.estado == 'reservado':
            initial['devolver_dinero'] = False
        form = PasajeCancelacionForm(initial=initial)
        return render(request, 'operations/pasaje_cancelacion.html', {
            'pasaje': pasaje,
            'form': form
        })
    
    def post(self, request, pk):
        pasaje = get_object_or_404(Pasaje, pk=pk)
        if pasaje.estado != 'reservado':
            messages.error(request, "Solo se pueden cancelar pasajes en estado Reservado.")
            return redirect('operations:pasaje_list')
        form = PasajeCancelacionForm(request.POST)
        
        if form.is_valid():
            estado_original = pasaje.estado
            pasaje.estado = 'cancelado'
            pasaje.fecha_cancelacion = timezone.now()
            pasaje.motivo_cancelacion = form.cleaned_data['motivo']
            pasaje.save()
            
            # Registrar devolución si corresponde (solo si no era una reserva)
            if form.cleaned_data.get('devolver_dinero') and estado_original != 'reservado':
                try:
                    sesion_caja = SesionCaja.objects.get(
                        cajero=request.user,
                        estado='abierta'
                    )
                    MovimientoCaja.objects.create(
                        sesion=sesion_caja,
                        tipo='egreso',
                        concepto='devolucion',
                        monto=pasaje.precio,
                        descripcion=f"Devolución pasaje {pasaje.codigo}"
                    )
                    messages.success(request, f"Pasaje cancelado y dinero devuelto: Gs. {pasaje.precio:,.0f}")
                except SesionCaja.DoesNotExist:
                    messages.warning(request, "Pasaje cancelado pero no hay caja abierta para registrar devolución.")
            else:
                if estado_original == 'reservado':
                    messages.success(request, "Reserva cancelada exitosamente sin devolución de dinero.")
                else:
                    messages.success(request, "Pasaje cancelado exitosamente.")
            
            return redirect('operations:pasaje_list')
        
        return render(request, 'operations/pasaje_cancelacion.html', {
            'pasaje': pasaje,
            'form': form
        })


class PasajeAbordarView(LoginRequiredMixin, View):
    """Marca un pasaje como abordado (el pasajero ya subió)."""
    def post(self, request, pk):
        pasaje = get_object_or_404(Pasaje, pk=pk)
        if pasaje.estado == 'vendido':
            pasaje.estado = 'abordado'
            pasaje.save()
            return JsonResponse({'ok': True, 'mensaje': 'Pasajero marcado como abordado.'})
        elif pasaje.estado == 'reservado':
            return JsonResponse({'ok': False, 'error': 'El cliente no puede abordar sin haber pagado el pasaje antes.'}, status=400)
        return JsonResponse({'ok': False, 'error': 'El estado del pasaje no permite abordaje.'}, status=400)


# =============================================================================
# ENCOMIENDAS
# =============================================================================

class EncomiendaListView(LoginRequiredMixin, ListView):
    """Lista de encomiendas."""
    model = Encomienda
    template_name = 'operations/encomienda_list.html'
    context_object_name = 'encomiendas'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'viaje__itinerario', 'remitente', 'destinatario',
            'parada_origen', 'parada_destino'
        )
        
        # Restricción para ayudantes y choferes
        persona = getattr(self.request.user, 'persona', None)
        if persona and (persona.es_ayudante or persona.es_chofer) and not self.request.user.is_superuser:
            hoy = timezone.localtime(timezone.now()).date()
            queryset = queryset.filter(
                Q(viaje__chofer=persona) | Q(viaje__ayudantes=persona)
            ).filter(
                Q(viaje__estado='en_curso') | Q(viaje__fecha_viaje__gte=hoy)
            )
        
        # Filtros
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(codigo__icontains=search) |
                Q(remitente__cedula__icontains=search) |
                Q(destinatario__cedula__icontains=search) |
                Q(remitente__nombre__icontains=search) |
                Q(destinatario__nombre__icontains=search)
            )
        
        return queryset.order_by('-fecha_registro')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = Encomienda.ESTADO_CHOICES
        context['estado_filter'] = self.request.GET.get('estado', '')
        context['search'] = self.request.GET.get('search', '')
        return context


class EncomiendaDetailView(LoginRequiredMixin, DetailView):
    """Detalle de una encomienda."""
    model = Encomienda
    template_name = 'operations/encomienda_detail.html'
    context_object_name = 'encomienda'

    def get_queryset(self):
        queryset = super().get_queryset()
        persona = getattr(self.request.user, 'persona', None)
        if persona and (persona.es_ayudante or persona.es_chofer) and not self.request.user.is_superuser:
            hoy = timezone.localtime(timezone.now()).date()
            queryset = queryset.filter(
                Q(viaje__chofer=persona) | Q(viaje__ayudantes=persona)
            ).filter(
                Q(viaje__estado='en_curso') | Q(viaje__fecha_viaje__gte=hoy)
            )
        return queryset


class EncomiendaCreateView(LoginRequiredMixin, CreateView):
    """Registrar una nueva encomienda."""
    model = Encomienda
    form_class = EncomiendaForm
    template_name = 'operations/encomienda_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        persona = getattr(request.user, 'persona', None)
        if persona and persona.es_ayudante and not request.user.is_superuser:
            from django.contrib import messages
            messages.error(request, "Los ayudantes no tienen permiso para registrar encomiendas.")
            return redirect('operations:encomienda_list')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        from django.core.exceptions import PermissionDenied
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        viaje_pk = self.kwargs.get('viaje_pk')
        if viaje_pk:
            viaje = get_object_or_404(Viaje, pk=viaje_pk)
            persona = getattr(self.request.user, 'persona', None)
            if persona and (persona.es_ayudante or persona.es_chofer) and not self.request.user.is_superuser:
                is_assigned = (viaje.chofer == persona) or (viaje.ayudantes.filter(pk=persona.pk).exists())
                hoy = timezone.localtime(timezone.now()).date()
                is_active = (viaje.estado == 'en_curso') or (viaje.fecha_viaje >= hoy)
                if not is_assigned or not is_active:
                    raise PermissionDenied("No tienes permiso para registrar encomiendas en este bus.")
            kwargs['viaje'] = viaje
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        viaje_pk = self.kwargs.get('viaje_pk')
        if viaje_pk:
            context['viaje'] = get_object_or_404(Viaje, pk=viaje_pk)
        return context
    
    def form_valid(self, form):
        encomienda = form.save(commit=False)
        
        # Obtener remitente por ID (desde el campo oculto del modal)
        remitente_id = form.cleaned_data.get('remitente_id')
        cedula_remitente = form.cleaned_data.get('cedula_remitente')
        
        if remitente_id:
            try:
                remitente = Persona.objects.get(cedula=remitente_id)
            except Persona.DoesNotExist:
                messages.error(self.request, f"No se encontró persona con cédula {remitente_id}")
                return self.form_invalid(form)
        elif cedula_remitente:
            try:
                remitente = Persona.objects.get(cedula=cedula_remitente)
            except Persona.DoesNotExist:
                messages.error(self.request, f"No se encontró persona con cédula {cedula_remitente}")
                return self.form_invalid(form)
        else:
            messages.error(self.request, "Debe seleccionar un remitente")
            return self.form_invalid(form)
        
        # Obtener o crear destinatario
        cedula_destinatario = form.cleaned_data.get('cedula_destinatario')
        nombre_destinatario = form.cleaned_data.get('nombre_destinatario')
        apellido_destinatario = form.cleaned_data.get('apellido_destinatario')
        telefono_destinatario = form.cleaned_data.get('telefono_destinatario')
        direccion_destinatario = form.cleaned_data.get('direccion_destinatario', '')
        
        if not cedula_destinatario:
            import random
            while True:
                cedula_destinatario = str(random.randint(999000000000000, 999999999999999))
                if not Persona.objects.filter(cedula=cedula_destinatario).exists():
                    break
        
        try:
            destinatario = Persona.objects.get(cedula=cedula_destinatario)
            # Actualizar datos si se proporcionaron nuevos
            actualizado = False
            if nombre_destinatario and destinatario.nombre != nombre_destinatario:
                destinatario.nombre = nombre_destinatario
                actualizado = True
            if apellido_destinatario and destinatario.apellido != apellido_destinatario:
                destinatario.apellido = apellido_destinatario
                actualizado = True
            if telefono_destinatario and destinatario.telefono != telefono_destinatario:
                destinatario.telefono = telefono_destinatario
                actualizado = True
            if direccion_destinatario and destinatario.direccion != direccion_destinatario:
                destinatario.direccion = direccion_destinatario
                actualizado = True
            if actualizado:
                destinatario.save()
        except Persona.DoesNotExist:
            # Crear nuevo destinatario sin marcarlo como cliente
            destinatario = Persona.objects.create(
                cedula=cedula_destinatario,
                nombre=nombre_destinatario,
                apellido=apellido_destinatario,
                telefono=telefono_destinatario,
                direccion=direccion_destinatario
            )
        
        encomienda.remitente = remitente
        encomienda.destinatario = destinatario
        encomienda.registrador = self.request.user
        encomienda.save()
        
        
        return redirect(f"{reverse('operations:encomienda_ticket', kwargs={'pk': encomienda.pk})}?print=1")


class EncomiendaEntregarView(LoginRequiredMixin, View):
    """Marcar encomienda como entregada."""
    
    def get(self, request, pk):
        encomienda = get_object_or_404(Encomienda, pk=pk)
        persona = getattr(request.user, 'persona', None)
        if persona and (persona.es_ayudante or persona.es_chofer) and not request.user.is_superuser:
            is_assigned = (encomienda.viaje.chofer == persona) or (encomienda.viaje.ayudantes.filter(pk=persona.pk).exists())
            if not is_assigned:
                messages.error(request, "No tienes permiso para ver o entregar encomiendas de otro bus.")
                return redirect('operations:encomienda_list')
            if encomienda.viaje.estado == 'programado':
                messages.error(request, "No puedes entregar encomiendas si el viaje aún no ha iniciado.")
                return redirect('operations:encomienda_detail', pk=encomienda.pk)
        form = EncomiendaEntregaForm()
        return render(request, 'operations/encomienda_entrega.html', {
            'encomienda': encomienda,
            'form': form
        })
    
    def post(self, request, pk):
        encomienda = get_object_or_404(Encomienda, pk=pk)
        persona = getattr(request.user, 'persona', None)
        if persona and (persona.es_ayudante or persona.es_chofer) and not request.user.is_superuser:
            is_assigned = (encomienda.viaje.chofer == persona) or (encomienda.viaje.ayudantes.filter(pk=persona.pk).exists())
            if not is_assigned:
                messages.error(request, "No tienes permiso para entregar encomiendas de otro bus.")
                return redirect('operations:encomienda_list')
            if encomienda.viaje.estado == 'programado':
                messages.error(request, "No puedes entregar encomiendas si el viaje aún no ha iniciado.")
                return redirect('operations:encomienda_detail', pk=encomienda.pk)
        form = EncomiendaEntregaForm(request.POST)
        
        if form.is_valid():
            encomienda.estado = 'entregado'
            encomienda.fecha_entrega = timezone.now()
            encomienda.receptor_nombre = form.cleaned_data['receptor_nombre']
            encomienda.receptor_cedula = form.cleaned_data['receptor_cedula']
            encomienda.receptor_telefono = form.cleaned_data['receptor_telefono']
            encomienda.save()
            
            messages.success(request, f"Encomienda {encomienda.codigo} entregada exitosamente.")
            if persona and (persona.es_ayudante or persona.es_chofer) and not request.user.is_superuser:
                return redirect('operations:dashboard_ayudante')
            return redirect('operations:encomienda_detail', pk=encomienda.pk)
        
        return render(request, 'operations/encomienda_entrega.html', {
            'encomienda': encomienda,
            'form': form
        })
 
 
class EncomiendaAbordarView(LoginRequiredMixin, View):
    """Marca una encomienda como recibida en el bus (En Tránsito)."""
    def post(self, request, pk):
        encomienda = get_object_or_404(Encomienda, pk=pk)
        persona = getattr(request.user, 'persona', None)
        if persona and (persona.es_ayudante or persona.es_chofer) and not request.user.is_superuser:
            is_assigned = (encomienda.viaje.chofer == persona) or (encomienda.viaje.ayudantes.filter(pk=persona.pk).exists())
            if not is_assigned:
                return JsonResponse({'ok': False, 'error': 'No autorizado para esta encomienda.'}, status=403)
        if encomienda.estado == 'registrado':
            encomienda.estado = 'en_transito'
            encomienda.fecha_en_transito = timezone.now()
            encomienda.save()
            return JsonResponse({'ok': True, 'mensaje': 'Encomienda marcada como en tránsito.'})
        return JsonResponse({'ok': False, 'error': 'El estado de la encomienda no permite esta acción.'}, status=400)
 
 
class EncomiendaRecibirTerminalView(LoginRequiredMixin, View):
    """Marca una encomienda como recibida en la terminal de destino (En Destino)."""
    def post(self, request, pk):
        encomienda = get_object_or_404(Encomienda, pk=pk)
        persona = getattr(request.user, 'persona', None)
        if persona and (persona.es_ayudante or persona.es_chofer) and not request.user.is_superuser:
            is_assigned = (encomienda.viaje.chofer == persona) or (encomienda.viaje.ayudantes.filter(pk=persona.pk).exists())
            if not is_assigned:
                return JsonResponse({'ok': False, 'error': 'No autorizado para esta encomienda.'}, status=403)
            if encomienda.viaje.estado == 'programado':
                return JsonResponse({'ok': False, 'error': 'No puedes entregar en destino si el viaje aún no ha iniciado.'}, status=400)
        if encomienda.estado == 'en_transito':
            encomienda.estado = 'en_destino'
            encomienda.fecha_en_destino = timezone.now()
            encomienda.save()
            return JsonResponse({'ok': True, 'mensaje': 'Encomienda entregada en destino. Lista para retiro.'})
        return JsonResponse({'ok': False, 'error': 'El estado de la encomienda no permite esta acción.'}, status=400)


class EncomiendaCambiarEstadoView(LoginRequiredMixin, View):
    """Cambiar estado de una encomienda."""
    
    def post(self, request, pk):
        encomienda = get_object_or_404(Encomienda, pk=pk)
        persona = getattr(request.user, 'persona', None)
        if persona and persona.es_ayudante and not request.user.is_superuser:
            messages.error(request, "Los ayudantes no tienen permiso para cambiar el estado de las encomiendas.")
            return redirect('operations:encomienda_detail', pk=pk)
        if persona and (persona.es_ayudante or persona.es_chofer) and not request.user.is_superuser:
            is_assigned = (encomienda.viaje.chofer == persona) or (encomienda.viaje.ayudantes.filter(pk=persona.pk).exists())
            if not is_assigned:
                messages.error(request, "No autorizado para esta encomienda.")
                return redirect('operations:encomienda_list')
        nuevo_estado = request.POST.get('estado')
        
        if nuevo_estado in dict(Encomienda.ESTADO_CHOICES):
            encomienda.estado = nuevo_estado
            if nuevo_estado == 'en_transito' and not encomienda.fecha_en_transito:
                encomienda.fecha_en_transito = timezone.now()
            elif nuevo_estado == 'en_destino' and not encomienda.fecha_en_destino:
                encomienda.fecha_en_destino = timezone.now()
            elif nuevo_estado == 'entregado' and not encomienda.fecha_entrega:
                encomienda.fecha_entrega = timezone.now()
            encomienda.save()
            messages.success(request, f"Estado actualizado a '{encomienda.get_estado_display()}'")
        
        return redirect('operations:encomienda_detail', pk=pk)


class EncomiendaTicketView(LoginRequiredMixin, DetailView):
    """Vista de encomienda en formato ticket térmico con QR."""
    model = Encomienda
    template_name = 'operations/encomienda_ticket.html'
    context_object_name = 'encomienda'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Usar el servicio de ticket para preparar el contexto
        from .services import EncomiendaTicketService
        ticket_context = EncomiendaTicketService.preparar_contexto_ticket(self.object)
        context.update(ticket_context)
        
        return context



class MisEncomiendasClienteView(LoginRequiredMixin, ListView):
    """Lista detallada de encomiendas enviadas o recibidas por el cliente."""
    model = Encomienda
    template_name = 'operations/mis_encomiendas_cliente.html'
    context_object_name = 'encomiendas'
    paginate_by = 10

    def get_queryset(self):
        persona = getattr(self.request.user, 'persona', None)
        if not persona:
            return Encomienda.objects.none()
        
        return Encomienda.objects.filter(
            Q(remitente=persona) | Q(destinatario=persona)
        ).select_related(
            'parada_origen', 'parada_destino', 'remitente', 'destinatario', 'viaje'
        ).order_by('-fecha_registro')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        persona = getattr(self.request.user, 'persona', None)
        context['persona'] = persona
        
        # Evaluar si la encomienda puede ser rastreada (valida si origen/destino están en el itinerario)
        from operations.utils import obtener_orden_parada
        encomiendas = context.get('encomiendas', [])
        for enc in encomiendas:
            enc.puede_rastrearse = False
            if enc.viaje and enc.viaje.estado == 'en_curso' and enc.factura and enc.estado not in ['entregado', 'en_destino', 'cancelado']:
                orden_o = obtener_orden_parada(enc.viaje, enc.parada_origen)
                orden_d = obtener_orden_parada(enc.viaje, enc.parada_destino)
                if orden_o is not None and orden_d is not None and orden_o < orden_d:
                    enc.puede_rastrearse = True
                    
        return context


class MisPasajesClienteView(LoginRequiredMixin, ListView):
    """Lista detallada de pasajes reservados o comprados por el cliente."""
    model = Pasaje
    template_name = 'operations/mis_pasajes_cliente.html'
    context_object_name = 'pasajes'
    paginate_by = 10

    def get_queryset(self):
        persona = getattr(self.request.user, 'persona', None)
        if not persona:
            return Pasaje.objects.none()
        
        return Pasaje.objects.filter(
            Q(pasajero=persona) | Q(cliente=persona)
        ).select_related(
            'viaje__itinerario', 'viaje__bus', 'asiento', 'parada_origen', 'parada_destino'
        ).order_by('-fecha_venta')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        persona = getattr(self.request.user, 'persona', None)
        context['persona'] = persona
        return context


# =============================================================================
# TRACKING
# =============================================================================

class TrackingPublicoView(TemplateView):
    """Vista pública para tracking de encomiendas."""
    template_name = 'operations/tracking_publico.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        codigo = self.request.GET.get('codigo')
        
        if codigo:
            try:
                encomienda = Encomienda.objects.select_related(
                    'viaje__itinerario', 'parada_origen', 'parada_destino'
                ).get(codigo=codigo.upper())
                context['encomienda'] = encomienda
                
                # Obtener último tracking del viaje si existe
                if encomienda.viaje:
                    context['ultimo_tracking'] = encomienda.viaje.trackings.first()
            except Encomienda.DoesNotExist:
                context['error'] = 'No se encontró encomienda con ese código'
        
        return context


# =============================================================================
# CAJA
# =============================================================================

class CajaDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard de caja del usuario actual."""
    template_name = 'operations/caja_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Buscar sesión abierta del usuario
        try:
            sesion = SesionCaja.objects.get(
                cajero=self.request.user,
                estado='abierta'
            )
            context['sesion_abierta'] = True
            context['sesion'] = sesion
            all_movimientos = sesion.movimientos.select_related(
                'factura__timbrado__empresa'
            ).prefetch_related(
                'factura__detalles__pasaje__viaje__itinerario',
                'factura__detalles__pasaje__asiento',
                'factura__detalles__pasaje__pasajero',
                'factura__detalles__encomienda__parada_destino',
                'factura__detalles__encomienda__remitente'
            ).order_by('-fecha')
            context['movimientos'] = all_movimientos[:20]
            context['todos_movimientos'] = all_movimientos
            context['total_actual'] = (
                sesion.monto_apertura + 
                sesion.total_ingresos - 
                sesion.total_egresos
            )
        except SesionCaja.DoesNotExist:
            context['sesion_abierta'] = False
        
        # Sesiones recientes (propias o todas si es staff/admin)
        sesiones_base = SesionCaja.objects.select_related('cajero', 'cajero__persona')
        if self.request.user.is_staff or self.request.user.is_superuser:
            context['sesiones_recientes'] = sesiones_base.order_by('-fecha_apertura')[:5]
        else:
            context['sesiones_recientes'] = sesiones_base.filter(
                cajero=self.request.user
            ).order_by('-fecha_apertura')[:5]
        
        return context


class AperturaCajaView(LoginRequiredMixin, FormView):
    """Abrir una nueva sesión de caja."""
    template_name = 'operations/caja_apertura.html'
    form_class = AperturaCajaForm
    
    def get(self, request, *args, **kwargs):
        # Verificar que no tenga caja abierta
        if SesionCaja.objects.filter(cajero=request.user, estado='abierta').exists():
            messages.warning(request, "Ya tiene una caja abierta.")
            return redirect('operations:caja_dashboard')
        return super().get(request, *args, **kwargs)
    
    def form_valid(self, form):
        sesion = SesionCaja.objects.create(
            cajero=self.request.user,
            monto_apertura=form.cleaned_data['monto_apertura'],
            observaciones=form.cleaned_data.get('observaciones', '')
        )
        messages.success(self.request, f"Caja abierta con Gs. {sesion.monto_apertura:,.0f}")
        return redirect('operations:caja_dashboard')


class CierreCajaView(LoginRequiredMixin, FormView):
    """Cerrar sesión de caja."""
    template_name = 'operations/caja_cierre.html'
    form_class = CierreCajaForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Detectar si es cierre forzado (redirigido por middleware)
        context['cierre_forzado'] = self.request.GET.get('forzado') == '1'
        try:
            sesion = SesionCaja.objects.get(
                cajero=self.request.user,
                estado='abierta'
            )
            context['sesion'] = sesion
            context['monto_esperado'] = sesion.calcular_cierre()
            context['movimientos'] = sesion.movimientos.order_by('-fecha')
        except SesionCaja.DoesNotExist:
            messages.warning(self.request, "No tiene caja abierta.")
            return redirect('operations:caja_dashboard')
        return context
    
    def form_valid(self, form):
        try:
            sesion = SesionCaja.objects.get(
                cajero=self.request.user,
                estado='abierta'
            )
            sesion.cerrar(
                monto_real=form.cleaned_data['monto_real'],
                observaciones=form.cleaned_data.get('observaciones', '')
            )
            
            if sesion.diferencia == 0:
                messages.success(self.request, "Caja cerrada correctamente. Sin diferencias.")
            elif sesion.diferencia > 0:
                messages.warning(
                    self.request, 
                    f"Caja cerrada con sobrante de Gs. {sesion.diferencia:,.0f}"
                )
            else:
                messages.error(
                    self.request,
                    f"Caja cerrada con faltante de Gs. {abs(sesion.diferencia):,.0f}"
                )
            
            # Finalizar automáticamente viajes en curso si el usuario es chofer o ayudante
            if hasattr(self.request.user, 'persona'):
                persona = self.request.user.persona
                if persona.es_chofer or persona.es_ayudante:
                    from operations.models import Viaje
                    from django.db.models import Q
                    from django.utils import timezone
                    
                    viajes_en_curso = Viaje.objects.filter(
                        Q(chofer=persona) | Q(ayudantes=persona),
                        estado='en_curso'
                    ).distinct()
                    
                    for viaje in viajes_en_curso:
                        viaje.estado = 'completado'
                        if not viaje.hora_llegada_real:
                            viaje.hora_llegada_real = timezone.localtime().time()
                        viaje.save()
                        messages.info(self.request, f"El viaje {viaje} se marcó como completado automáticamente al cerrar su caja.")

            return redirect('operations:sesion_caja_detail', pk=sesion.pk)
        except SesionCaja.DoesNotExist:
            messages.error(self.request, "No se encontró sesión de caja abierta.")
            return redirect('operations:caja_dashboard')


class MovimientoCajaCreateView(LoginRequiredMixin, CreateView):
    """Registrar movimiento de caja manual."""
    model = MovimientoCaja
    form_class = MovimientoCajaForm
    template_name = 'operations/movimiento_caja_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['sesion'] = SesionCaja.objects.get(
                cajero=self.request.user,
                estado='abierta'
            )
        except SesionCaja.DoesNotExist:
            pass
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        try:
            kwargs['sesion'] = SesionCaja.objects.get(
                cajero=self.request.user,
                estado='abierta'
            )
        except SesionCaja.DoesNotExist:
            kwargs['sesion'] = None
        return kwargs
    
    def form_valid(self, form):
        try:
            sesion = SesionCaja.objects.get(
                cajero=self.request.user,
                estado='abierta'
            )
            movimiento = form.save(commit=False)
            movimiento.sesion = sesion
            movimiento.save()
            messages.success(self.request, "Movimiento registrado exitosamente.")
            return redirect('operations:caja_dashboard')
        except SesionCaja.DoesNotExist:
            messages.error(self.request, "No tiene caja abierta.")
            return redirect('operations:caja_dashboard')


class SesionCajaDetailView(LoginRequiredMixin, DetailView):
    """Detalle de una sesión de caja cerrada."""
    model = SesionCaja
    template_name = 'operations/sesion_caja_detail.html'
    context_object_name = 'sesion'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['movimientos'] = self.object.movimientos.select_related(
            'factura__timbrado__empresa'
        ).prefetch_related(
            'factura__detalles__pasaje__viaje__itinerario',
            'factura__detalles__pasaje__asiento',
            'factura__detalles__pasaje__pasajero',
            'factura__detalles__encomienda__parada_destino',
            'factura__detalles__encomienda__remitente'
        ).order_by('fecha')
        return context


# =============================================================================
# FACTURACIÓN
# =============================================================================

class TimbradoListView(LoginRequiredMixin, ListView):
    """Lista de timbrados."""
    model = Timbrado
    template_name = 'operations/timbrado_list.html'
    context_object_name = 'timbrados'
    
    def get_queryset(self):
        return Timbrado.objects.select_related('empresa').order_by('-fecha_inicio')


class TimbradoCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Crear nuevo timbrado."""
    model = Timbrado
    form_class = TimbradoForm
    template_name = 'operations/timbrado_form.html'
    success_url = reverse_lazy('operations:timbrado_list')
    success_message = "Timbrado creado exitosamente."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['empresas'] = Empresa.objects.all()
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class TimbradoUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar timbrado."""
    model = Timbrado
    form_class = TimbradoForm
    template_name = 'operations/timbrado_form.html'
    success_url = reverse_lazy('operations:timbrado_list')
    success_message = "Timbrado actualizado exitosamente."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        timbrado = self.get_object()
        if timbrado.facturas.exists():
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, "No se puede editar un timbrado que ya tiene facturaciones o movimientos asociados.")
            return redirect('operations:timbrado_list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['empresas'] = Empresa.objects.all()
        return context

class TimbradoDeleteView(LoginRequiredMixin, SuccessMessageMixin, DeleteView):
    """Eliminar timbrado."""
    model = Timbrado
    template_name = 'operations/timbrado_confirm_delete.html'
    success_url = reverse_lazy('operations:timbrado_list')
    success_message = "Timbrado eliminado exitosamente."

    def dispatch(self, request, *args, **kwargs):
        timbrado = self.get_object()
        if timbrado.facturas.exists():
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, "No se puede eliminar un timbrado que ya tiene facturas asociadas.")
            return redirect('operations:timbrado_list')
        return super().dispatch(request, *args, **kwargs)

class TimbradoInhabilitarView(LoginRequiredMixin, View):
    """Inhabilitar timbrado."""
    def post(self, request, pk, *args, **kwargs):
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        timbrado = get_object_or_404(Timbrado, pk=pk)
        timbrado.activo = False
        timbrado.save(update_fields=['activo'])
        messages.success(request, f"Timbrado {timbrado.numero} inhabilitado exitosamente.")
        return redirect('operations:timbrado_list')


class FacturaListView(LoginRequiredMixin, ListView):
    """Lista de facturas."""
    model = Factura
    template_name = 'operations/factura_list.html'
    context_object_name = 'facturas'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'timbrado__empresa', 'cliente', 'cajero'
        )

        # Filtro por usuario para ayudantes/choferes/agentes
        persona = getattr(self.request.user, 'persona', None)
        if persona and (persona.es_ayudante or persona.es_chofer or persona.es_agente) and not self.request.user.is_superuser:
            queryset = queryset.filter(cajero=self.request.user)
        
        # Filtros
        fecha = self.request.GET.get('fecha')
        if fecha:
            queryset = queryset.filter(fecha_emision__date=fecha)
        
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(numero_factura__icontains=search) |
                Q(cliente__cedula__icontains=search) |
                Q(cliente__nombre__icontains=search) |
                Q(timbrado__empresa__nombre__icontains=search)
            )
            
        cajero_id = self.request.GET.get('cajero')
        if cajero_id:
            # Si el usuario es admin/empleado, puede filtrar por cajero
            if not (persona and (persona.es_ayudante or persona.es_chofer or persona.es_agente) and not self.request.user.is_superuser):
                queryset = queryset.filter(cajero_id=cajero_id)
        
        return queryset.order_by('-fecha_emision')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = Factura.ESTADO_CHOICES
        context['fecha_filter'] = self.request.GET.get('fecha', '')
        context['estado_filter'] = self.request.GET.get('estado', '')
        context['search'] = self.request.GET.get('search', '')
        context['cajero_filter'] = self.request.GET.get('cajero', '')
        
        persona = getattr(self.request.user, 'persona', None)
        context['es_ayudante_o_chofer'] = persona and (persona.es_ayudante or persona.es_chofer or persona.es_agente) and not self.request.user.is_superuser
        
        if not context['es_ayudante_o_chofer']:
            from django.contrib.auth.models import User
            context['cajeros'] = User.objects.filter(facturas_emitidas__isnull=False).distinct()
            
        return context


class ClientesPendientesFacturaView(LoginRequiredMixin, TemplateView):
    """Lista de clientes con pasajes o encomiendas pendientes de facturar."""
    template_name = 'operations/clientes_pendientes_factura.html'
    
    def dispatch(self, request, *args, **kwargs):
        persona = getattr(request.user, 'persona', None)
        if persona and (persona.es_ayudante or persona.es_chofer) and not request.user.is_superuser:
            messages.error(request, 'No tienes permiso para acceder a esta vista. Solo administradores y empleados pueden ver los pendientes de facturación.')
            return redirect('operations:dashboard_ayudante')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        ahora = timezone.localtime(timezone.now())
        hoy = ahora.date()
        hora_actual = ahora.time()
        
        # Obtener pasajes vendidos, reservados o abordados no facturados
        pasajes_sin_factura = Pasaje.objects.filter(
            estado__in=['vendido', 'reservado', 'abordado']
        ).exclude(
            detalles_factura__factura__estado='emitida'
        ).select_related('pasajero', 'viaje__itinerario', 'asiento')
        
        persona_req = getattr(self.request.user, 'persona', None)
        is_ayudante_chofer = persona_req and (persona_req.es_ayudante or persona_req.es_chofer)
        if is_ayudante_chofer and not self.request.user.is_superuser:
            pasajes_sin_factura = pasajes_sin_factura.filter(vendedor=self.request.user)
        
        # Obtener encomiendas no facturadas (ocultas para ayudantes/choferes)
        persona = getattr(self.request.user, 'persona', None)
        es_ayudante_o_chofer = persona and (persona.es_ayudante or persona.es_chofer) and not self.request.user.is_superuser
        
        if es_ayudante_o_chofer:
            encomiendas_sin_factura = Encomienda.objects.none()
        else:
            encomiendas_sin_factura = Encomienda.objects.filter(
                estado__in=['registrado', 'en_transito', 'en_destino', 'entregado']
            ).exclude(
                detalles_factura__factura__estado='emitida'
            ).select_related('remitente', 'parada_destino')
        
        # Filtro de búsqueda
        search = self.request.GET.get('search', '').strip()
        if search:
            import re
            # Limpiar palabras comunes
            search_clean = re.sub(r'(?i)\b(pasaje|encomienda|reserva|ticket)\b', '', search).strip()
            if not search_clean:
                search_clean = search
            
            for term in search_clean.split():
                pasajes_sin_factura = pasajes_sin_factura.filter(
                    Q(pasajero__nombre__icontains=term) |
                    Q(pasajero__apellido__icontains=term) |
                    Q(pasajero__cedula__icontains=term) |
                    Q(cliente__nombre__icontains=term) |
                    Q(cliente__apellido__icontains=term) |
                    Q(cliente__cedula__icontains=term) |
                    Q(codigo__icontains=term)
                )
                encomiendas_sin_factura = encomiendas_sin_factura.filter(
                    Q(remitente__nombre__icontains=term) |
                    Q(remitente__apellido__icontains=term) |
                    Q(remitente__cedula__icontains=term) |
                    Q(codigo__icontains=term)
                )
        
        # Agrupar por cliente y empresa
        clientes_dict = {}
        
        for pasaje in pasajes_sin_factura:
            # Priorizar al cliente pagador definido en la reserva
            cliente = pasaje.cliente or pasaje.pasajero
            empresa = pasaje.viaje.empresa or (pasaje.viaje.bus.empresa if pasaje.viaje.bus else None) if pasaje.viaje else None
            empresa_id = empresa.pk if empresa else 0
            
            key = f"{cliente.pk}_{empresa_id}"
            
            if key not in clientes_dict:
                clientes_dict[key] = {
                    'cliente': cliente,
                    'empresa': empresa,
                    'pasajes': [],
                    'encomiendas': [],
                    'total_pasajes': Decimal('0'),
                    'total_encomiendas': Decimal('0'),
                }
            clientes_dict[key]['pasajes'].append(pasaje)
            clientes_dict[key]['total_pasajes'] += pasaje.precio
        
        for encomienda in encomiendas_sin_factura:
            cliente = encomienda.remitente
            empresa = encomienda.viaje.empresa or (encomienda.viaje.bus.empresa if encomienda.viaje.bus else None) if encomienda.viaje else None
            empresa_id = empresa.pk if empresa else 0
            
            key = f"{cliente.pk}_{empresa_id}"
            
            if key not in clientes_dict:
                clientes_dict[key] = {
                    'cliente': cliente,
                    'empresa': empresa,
                    'pasajes': [],
                    'encomiendas': [],
                    'total_pasajes': Decimal('0'),
                    'total_encomiendas': Decimal('0'),
                }
            clientes_dict[key]['encomiendas'].append(encomienda)
            clientes_dict[key]['total_encomiendas'] += encomienda.precio
        
        # Calcular total por cliente
        clientes = []
        for data in clientes_dict.values():
            data['total'] = data['total_pasajes'] + data['total_encomiendas']
            data['cant_items'] = len(data['pasajes']) + len(data['encomiendas'])
            clientes.append(data)
        
        # Ordenar por total descendente
        clientes.sort(key=lambda x: x['total'], reverse=True)
        
        context['clientes'] = clientes
        context['total_clientes'] = len(clientes)
        context['total_pasajes'] = pasajes_sin_factura.count()
        context['total_encomiendas'] = encomiendas_sin_factura.count()
        context['search'] = search
        
        # Obtener timbrado vigente (Guaireña) y próximo número
        from .services import FacturacionService
        empresa_gua = Empresa.objects.filter(nombre__icontains='Guaireña').first()
        context['empresa_gua'] = empresa_gua
        
        timbrado = FacturacionService.obtener_timbrado_vigente(empresa=empresa_gua)
        context['timbrado_vigente'] = timbrado
        if timbrado:
            try:
                context['proximo_numero'] = f"{timbrado.punto_expedicion}-{timbrado.get_siguiente_numero():07d}"
            except ValueError:
                context['proximo_numero'] = "Sin números disponibles"

        # Timbrado específico de Ybyturuzu
        empresa_yby = Empresa.objects.filter(nombre__icontains='Ybyturuzu').first()
        context['empresa_yby'] = empresa_yby
        if empresa_yby:
            timbrado_yby = FacturacionService.obtener_timbrado_vigente(empresa=empresa_yby)
            context['timbrado_ybyturuzu'] = timbrado_yby
            if timbrado_yby:
                try:
                    context['proximo_numero_ybyturuzu'] = f"{timbrado_yby.punto_expedicion}-{timbrado_yby.get_siguiente_numero():07d}"
                except ValueError:
                    context['proximo_numero_ybyturuzu'] = "Sin números disponibles"
        
        return context


            
        return redirect('operations:pasaje_list')


class CancelarReservaRapidaView(LoginRequiredMixin, View):
    """Cancela una reserva rápidamente desde la lista de pendientes."""
    
    def post(self, request, pk):
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        from django.utils import timezone
        
        pasaje = get_object_or_404(Pasaje, pk=pk)
        
        if pasaje.estado != 'reservado':
            messages.error(request, "Este pasaje no puede ser cancelado porque no es una reserva.")
            return redirect('operations:clientes_pendientes_factura')
            
        pasaje.estado = 'cancelado'
        pasaje.fecha_cancelacion = timezone.now()
        pasaje.motivo_cancelacion = "Cancelación rápida desde lista de pendientes de factura"
        pasaje.save()
        
        messages.success(request, f"Reserva {pasaje.codigo} cancelada. El asiento {pasaje.asiento.numero_asiento} ha sido liberado.")
        return redirect('operations:clientes_pendientes_factura')


class CancelarEncomiendaRapidaView(LoginRequiredMixin, View):
    """Cancela una encomienda rápidamente desde la lista de pendientes."""
    
    def post(self, request, pk):
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        from django.utils import timezone
        
        encomienda = get_object_or_404(Encomienda, pk=pk)
        persona = getattr(request.user, 'persona', None)
        if persona and persona.es_ayudante and not request.user.is_superuser:
            messages.error(request, "Los ayudantes no tienen permiso para realizar esta acción.")
            return redirect('operations:encomienda_detail', pk=pk)
        if persona and (persona.es_ayudante or persona.es_chofer) and not request.user.is_superuser:
            is_assigned = (encomienda.viaje.chofer == persona) or (encomienda.viaje.ayudantes.filter(pk=persona.pk).exists())
            if not is_assigned:
                messages.error(request, "No autorizado para esta encomienda.")
                return redirect('operations:clientes_pendientes_factura')
        
        if encomienda.estado != 'registrado':
            messages.error(request, "Esta encomienda ya está en tránsito o entregada, no se puede cancelar.")
            return redirect('operations:clientes_pendientes_factura')
        
        # Verificar si la encomienda tiene factura emitida
        factura_activa = encomienda.factura
        if factura_activa:
            messages.warning(
                request,
                f"No se puede cancelar la encomienda {encomienda.codigo} porque tiene la factura "
                f"{factura_activa.numero_completo} emitida. Primero debe anular la factura."
            )
            return redirect(request.META.get('HTTP_REFERER', reverse('operations:encomienda_list')))
            
        encomienda.estado = 'cancelado'
        encomienda.save()
        
        messages.success(request, f"Encomienda {encomienda.codigo} cancelada correctamente.")
        return redirect('operations:clientes_pendientes_factura')


class CancelarTodoPendienteView(LoginRequiredMixin, View):
    """Cancela todos los items pendientes de un cliente."""
    
    def post(self, request, cedula):
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        from django.db.models import Q
        
        persona = get_object_or_404(Persona, cedula=cedula)
        
        # Cancelar pasajes
        pasajes = Pasaje.objects.filter(
            Q(pasajero=persona) | Q(cliente=persona),
            estado='reservado'
        ).exclude(
            detalles_factura__factura__estado='emitida'
        )
        
        count_pasajes = pasajes.count()
        for p in pasajes:
            p.estado = 'cancelado'
            p.save()
            
        # Cancelar encomiendas
        encomiendas = Encomienda.objects.filter(
            remitente=persona,
            estado='registrado'
        ).exclude(
            detalles_factura__factura__estado='emitida'
        )
        
        count_encomiendas = encomiendas.count()
        for e in encomiendas:
            e.estado = 'cancelado'
            e.save()
            
        messages.success(request, f"Se han cancelado {count_pasajes} pasajes y {count_encomiendas} encomiendas de {persona.nombre_completo}.")
        return redirect('operations:clientes_pendientes_factura')


class FacturaDetailView(LoginRequiredMixin, DetailView):
    """Detalle de una factura."""
    model = Factura
    template_name = 'operations/factura_detail.html'
    context_object_name = 'factura'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['detalles'] = self.object.detalles.select_related(
            'pasaje__viaje', 'pasaje__asiento', 'encomienda'
        ).all()
        return context


class FacturaTicketView(LoginRequiredMixin, DetailView):
    """Vista de factura en formato ticket térmico con QR."""
    model = Factura
    template_name = 'operations/factura_ticket.html'
    context_object_name = 'factura'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Usar el servicio de ticket para preparar el contexto
        from .services import TicketService
        ticket_context = TicketService.preparar_contexto_ticket(self.object)
        context.update(ticket_context)
        
        return context


class FacturaPdfView(LoginRequiredMixin, View):
    """Descargar factura como PDF."""
    
    def get(self, request, pk):
        from .services import FacturacionService
        
        factura = get_object_or_404(Factura, pk=pk)
        
        try:
            pdf = FacturacionService.generar_pdf_factura(factura)
            
            response = HttpResponse(pdf, content_type='application/pdf')
            filename = f"factura_{factura.numero_completo.replace('-', '_')}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        except ImportError as e:
            messages.error(request, f"No se pudo generar el PDF: {str(e)}")
            return redirect('operations:factura_ticket', pk=pk)


class FacturaCreateView(LoginRequiredMixin, View):
    """Crear una nueva factura desde pasajes/encomiendas."""
    
    def get(self, request):
        # Verificar que el usuario tenga una caja abierta antes de facturar
        if not SesionCaja.objects.filter(cajero=request.user, estado='abierta').exists():
            messages.error(request, "Debe abrir una sesión de caja antes de realizar una facturación.")
            return redirect('operations:caja_dashboard')

        from .forms import FacturaForm
        
        # Obtener cliente si viene en query params
        cliente_cedula = request.GET.get('cliente')
        pasaje_pk = request.GET.get('pasaje')
        encomienda_pk = request.GET.get('encomienda')
        
        pasaje = None
        encomienda = None
        
        if pasaje_pk:
            pasaje = get_object_or_404(Pasaje, pk=pasaje_pk)
            cliente_cedula = pasaje.pasajero.cedula
        
        if encomienda_pk:
            encomienda = get_object_or_404(Encomienda, pk=encomienda_pk)
            cliente_cedula = encomienda.remitente.cedula
        
        from .forms import FacturaForm, EncomiendaForm
        
        # ... logic ...
        form = FacturaForm(cliente=cliente_cedula, pasaje=pasaje, encomienda=encomienda, user=request.user)
        
        empresa_factura = None
        if pasaje and pasaje.viaje:
            empresa_factura = pasaje.viaje.empresa_operadora
        elif encomienda and encomienda.viaje:
            empresa_factura = encomienda.viaje.empresa_operadora
        else:
            empresa_id = request.GET.get('empresa')
            if empresa_id:
                try:
                    from fleet.models import Empresa
                    empresa_factura = Empresa.objects.get(pk=empresa_id)
                except Empresa.DoesNotExist:
                    pass
            
        encomienda_form = EncomiendaForm(empresa=empresa_factura)
        
        return render(request, 'operations/factura_form.html', {
            'form': form,
            'encomienda_form': encomienda_form,
            'cliente_cedula': cliente_cedula,
            'empresa_id': request.GET.get('empresa', '')
        })
    
    def post(self, request):
        from .forms import FacturaForm
        from .services import FacturacionService
        
        # Obtener la cédula del cliente del POST para construir el formulario correctamente
        cedula_cliente = request.POST.get('cedula_cliente', '').strip()
        
        # Construir el formulario con el cliente para que los querysets sean válidos
        form = FacturaForm(request.POST, cliente=cedula_cliente, user=request.user)
        
        # Verificar caja abierta en el POST también
        if not SesionCaja.objects.filter(cajero=request.user, estado='abierta').exists():
            messages.error(request, "No puede facturar sin una sesión de caja abierta.")
            return render(request, 'operations/factura_form.html', {'form': form})
        
        if form.is_valid():
            try:
                # Obtener cliente
                cedula = form.cleaned_data['cedula_cliente']
                cliente = get_object_or_404(Persona, cedula=cedula)
                
                # Obtener sesión de caja activa
                sesion_caja = None
                try:
                    sesion_caja = SesionCaja.objects.get(
                        cajero=request.user,
                        estado='abierta'
                    )
                except SesionCaja.DoesNotExist:
                    pass
                
                # Crear factura usando el servicio
                factura = FacturacionService.crear_factura(
                    timbrado=form.cleaned_data['timbrado'],
                    cliente=cliente,
                    cajero=request.user,
                    pasajes=list(form.cleaned_data.get('pasajes', [])),
                    encomiendas=list(form.cleaned_data.get('encomiendas', [])),
                    condicion=form.cleaned_data['condicion'],
                    sesion_caja=sesion_caja
                )
                
                messages.success(request, f"Factura {factura.numero_completo} generada exitosamente.")
                
                # Redirigir al ticket si viene ?print=1
                if request.GET.get('print') == '1':
                    return redirect(f"{reverse('operations:factura_ticket', kwargs={'pk': factura.pk})}?print=1")
                
                return redirect('operations:factura_detail', pk=factura.pk)
                
            except ValueError as e:
                messages.error(request, str(e))
            except Persona.DoesNotExist:
                messages.error(request, "Cliente no encontrado con esa cédula.")
        
        return render(request, 'operations/factura_form.html', {'form': form})




class FacturaAnularView(LoginRequiredMixin, View):
    """Anular una factura con reversión de caja."""
    
    def get(self, request, pk):
        factura = get_object_or_404(Factura, pk=pk)
        
        from django.utils import timezone
        import datetime
        
        if timezone.now() > factura.fecha_emision + datetime.timedelta(hours=1):
            messages.error(request, "No se puede anular la factura. Ha pasado más de 1 hora desde su emisión.")
            return redirect('operations:factura_detail', pk=pk)
            
        form = FacturaAnulacionForm()
        
        # Verificar si hay caja abierta para revertir
        tiene_caja = SesionCaja.objects.filter(
            cajero=request.user,
            estado='abierta'
        ).exists()
        
        return render(request, 'operations/factura_anulacion.html', {
            'factura': factura,
            'form': form,
            'tiene_caja_abierta': tiene_caja
        })
    
    def post(self, request, pk):
        from .services import FacturacionService
        from django.utils import timezone
        import datetime
        
        factura = get_object_or_404(Factura, pk=pk)
        
        if timezone.now() > factura.fecha_emision + datetime.timedelta(hours=1):
            messages.error(request, "No se puede anular la factura. Ha pasado más de 1 hora desde su emisión.")
            return redirect('operations:factura_detail', pk=pk)
            
        form = FacturaAnulacionForm(request.POST)
        
        if form.is_valid():
            try:
                FacturacionService.anular_factura(
                    factura=factura,
                    motivo=form.cleaned_data['motivo'],
                    usuario=request.user,
                    revertir_caja=True
                )
                
                messages.success(request, f"Factura {factura.numero_completo} anulada.")
                messages.info(request, "Se registró un egreso en caja para revertir el pago.")
                
                return redirect('operations:factura_detail', pk=pk)
                
            except ValueError as e:
                messages.error(request, str(e))
        
        return render(request, 'operations/factura_anulacion.html', {
            'factura': factura,
            'form': form
        })


class TimbradoSiguienteNumeroView(LoginRequiredMixin, View):
    """API para obtener el siguiente número de factura de un timbrado."""
    
    def get(self, request, pk):
        timbrado = get_object_or_404(Timbrado, pk=pk)
        try:
            numero = timbrado.get_siguiente_numero()
            return JsonResponse({
                'numero': f"{timbrado.punto_expedicion}-{numero:07d}",
                'numero_raw': numero
            })
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)


# =============================================================================
# INCIDENCIAS
# =============================================================================

class IncidenciaListView(LoginRequiredMixin, ListView):
    """Lista de incidencias."""
    model = Incidencia
    template_name = 'operations/incidencia_list.html'
    context_object_name = 'incidencias'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('viaje__itinerario', 'reportador')
        
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        prioridad = self.request.GET.get('prioridad')
        if prioridad:
            queryset = queryset.filter(prioridad=prioridad)
        
        return queryset.order_by('-fecha_reporte')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = Incidencia.ESTADO_CHOICES
        context['prioridades'] = Incidencia.PRIORIDAD_CHOICES
        context['estado_filter'] = self.request.GET.get('estado', '')
        context['prioridad_filter'] = self.request.GET.get('prioridad', '')
        return context


class IncidenciaCreateView(LoginRequiredMixin, CreateView):
    """Reportar nueva incidencia."""
    model = Incidencia
    form_class = IncidenciaForm
    template_name = 'operations/incidencia_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        viaje_pk = self.kwargs.get('viaje_pk')
        if viaje_pk:
            kwargs['viaje'] = get_object_or_404(Viaje, pk=viaje_pk)
        return kwargs
    
    def form_valid(self, form):
        incidencia = form.save(commit=False)
        incidencia.reportador = self.request.user
        incidencia.save()
        messages.success(self.request, "Incidencia reportada exitosamente.")
        return redirect('operations:incidencia_list')


class IncidenciaDetailView(LoginRequiredMixin, DetailView):
    """Detalle de una incidencia."""
    model = Incidencia
    template_name = 'operations/incidencia_detail.html'
    context_object_name = 'incidencia'


class IncidenciaResolverView(LoginRequiredMixin, View):
    """Resolver una incidencia."""
    
    def get(self, request, pk):
        incidencia = get_object_or_404(Incidencia, pk=pk)
        form = IncidenciaResolucionForm()
        return render(request, 'operations/incidencia_resolver.html', {
            'incidencia': incidencia,
            'form': form
        })
    
    def post(self, request, pk):
        incidencia = get_object_or_404(Incidencia, pk=pk)
        form = IncidenciaResolucionForm(request.POST)
        
        if form.is_valid():
            incidencia.estado = 'resuelta'
            incidencia.fecha_resolucion = timezone.now()
            incidencia.resolucion = form.cleaned_data['resolucion']
            incidencia.save()
            
            messages.success(request, "Incidencia resuelta exitosamente.")
            return redirect('operations:incidencia_detail', pk=pk)
        
        return render(request, 'operations/incidencia_resolver.html', {
            'incidencia': incidencia,
            'form': form
        })


# =============================================================================
# REPORTES
# =============================================================================

class ReporteDiarioView(LoginRequiredMixin, TemplateView):
    """Hub central de reportes con múltiples pestañas."""
    template_name = 'operations/reporte_diario.html'

    def _parse_dates(self):
        from datetime import datetime
        fecha_desde = self.request.GET.get('desde')
        fecha_hasta = self.request.GET.get('hasta')
        if fecha_desde:
            fecha_desde = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
        else:
            fecha_desde = timezone.localtime(timezone.now()).date()
        if fecha_hasta:
            fecha_hasta = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
        else:
            fecha_hasta = fecha_desde
        return fecha_desde, fecha_hasta

    def get_context_data(self, **kwargs):
        import json
        from datetime import datetime
        from django.contrib.auth.models import User as AuthUser

        context = super().get_context_data(**kwargs)
        fecha_desde, fecha_hasta = self._parse_dates()
        tab = self.request.GET.get('tab', 'flujo')

        context['fecha_desde'] = fecha_desde
        context['fecha_hasta'] = fecha_hasta
        context['tab'] = tab

        # Filtro de empresa
        from fleet.models import Empresa
        context['empresas_disponibles'] = Empresa.objects.all().order_by('nombre')
        empresa_id = self.request.GET.get('empresa', '')
        context['empresa_filter'] = empresa_id
        empresa_obj = None
        if empresa_id:
            try:
                empresa_obj = Empresa.objects.get(pk=empresa_id)
                context['empresa_seleccionada'] = empresa_obj
            except Empresa.DoesNotExist:
                empresa_obj = None

        # Detectar rol del usuario
        persona = getattr(self.request.user, 'persona', None)
        es_admin = self.request.user.is_superuser
        es_personal = persona and (persona.es_ayudante or persona.es_chofer or persona.es_agente)
        context['es_admin'] = es_admin
        context['es_personal'] = es_personal

        # Restricción de empresa para personal (ayudantes/choferes)
        if not es_admin and es_personal and not persona.es_agente and persona and persona.empresa:
            empresa_obj = persona.empresa
            context['empresa_filter'] = str(empresa_obj.pk)
            context['empresa_seleccionada'] = empresa_obj
            # Opcional: no permitir cambiar la empresa en el contexto si se quiere ser estricto
            context['empresas_disponibles'] = context['empresas_disponibles'].filter(pk=empresa_obj.pk)

        # =====================================================================
        # TAB 1: FLUJO DE INGRESOS DIARIO
        # =====================================================================
        if tab == 'flujo':
            # Pasajes vendidos en el rango
            pasajes = Pasaje.objects.filter(
                fecha_venta__date__gte=fecha_desde,
                fecha_venta__date__lte=fecha_hasta,
                estado__in=['vendido', 'abordado']
            )
            if empresa_obj:
                pasajes = pasajes.filter(viaje__empresa=empresa_obj)
            # Si es personal (ayudante/chofer), solo sus ventas
            if es_personal and not es_admin:
                pasajes = pasajes.filter(vendedor=self.request.user)

            ingresos_pasajes = pasajes.aggregate(total=Sum('precio'))['total'] or Decimal('0.00')
            total_pasajes = pasajes.count()

            encomiendas = Encomienda.objects.filter(
                fecha_registro__date__gte=fecha_desde,
                fecha_registro__date__lte=fecha_hasta,
            ).exclude(estado='cancelado')
            if empresa_obj:
                encomiendas = encomiendas.filter(viaje__empresa=empresa_obj)
            if es_personal and not es_admin:
                encomiendas = encomiendas.filter(registrador=self.request.user)

            ingresos_encomiendas = encomiendas.aggregate(total=Sum('precio'))['total'] or Decimal('0.00')
            total_encomiendas = encomiendas.count()

            context['total_pasajes'] = total_pasajes
            context['ingresos_pasajes'] = ingresos_pasajes
            context['total_encomiendas'] = total_encomiendas
            context['ingresos_encomiendas'] = ingresos_encomiendas
            context['total_ingresos'] = ingresos_pasajes + ingresos_encomiendas

            # Viajes del rango
            viajes = Viaje.objects.filter(
                fecha_viaje__gte=fecha_desde,
                fecha_viaje__lte=fecha_hasta,
            ).select_related('itinerario', 'bus', 'chofer', 'horario', 'empresa')
            if empresa_obj:
                viajes = viajes.filter(empresa=empresa_obj)
            if es_personal and not es_admin:
                viajes = viajes.filter(Q(chofer=persona) | Q(ayudantes=persona)).distinct()
            viajes_list = []
            total_viajes_monto = Decimal('0')
            for v in viajes:
                # Calculate income for pasajes in this trip ONLY for the selected date range
                pasajes_viaje = v.pasajes.filter(
                    estado__in=['vendido', 'abordado'],
                    fecha_venta__date__gte=fecha_desde,
                    fecha_venta__date__lte=fecha_hasta
                )
                if es_personal and not es_admin:
                    pasajes_viaje = pasajes_viaje.filter(vendedor=self.request.user)
                ing_p = pasajes_viaje.aggregate(t=Sum('precio'))['t'] or Decimal('0')

                # Calculate income for encomiendas in this trip ONLY for the selected date range
                encomiendas_viaje = v.encomiendas.filter(
                    fecha_registro__date__gte=fecha_desde,
                    fecha_registro__date__lte=fecha_hasta
                ).exclude(estado='cancelado')
                if es_personal and not es_admin:
                    encomiendas_viaje = encomiendas_viaje.filter(registrador=self.request.user)
                ing_e = encomiendas_viaje.aggregate(t=Sum('precio'))['t'] or Decimal('0')

                total_v = ing_p + ing_e
                setattr(v, 'monto_pasajes', ing_p)
                setattr(v, 'monto_encomiendas', ing_e)
                setattr(v, 'monto_total', total_v)
                viajes_list.append(v)
                total_viajes_monto += total_v

            context['viajes'] = viajes_list
            context['total_viajes'] = len(viajes_list)
            context['total_viajes_monto'] = total_viajes_monto

            # Facturas emitidas
            facturas = Factura.objects.filter(
                fecha_emision__date__gte=fecha_desde,
                fecha_emision__date__lte=fecha_hasta,
                estado='emitida'
            )
            if es_personal and not es_admin:
                facturas = facturas.filter(cajero=self.request.user)
            context['total_facturas'] = facturas.count()
            context['total_facturado'] = facturas.aggregate(total=Sum('total'))['total'] or Decimal('0.00')

            # --- Datos para gráfico de barras: ingresos por día ---
            from datetime import date as dt_date
            delta_days = (fecha_hasta - fecha_desde).days + 1
            chart_labels = []
            chart_pasajes = []
            chart_encomiendas = []
            for i in range(delta_days):
                d = fecha_desde + timedelta(days=i)
                chart_labels.append(d.strftime('%d/%m'))
                p_day = Pasaje.objects.filter(fecha_venta__date=d, estado__in=['vendido', 'abordado'])
                e_day = Encomienda.objects.filter(fecha_registro__date=d).exclude(estado='cancelado')
                if es_personal and not es_admin:
                    p_day = p_day.filter(vendedor=self.request.user)
                    e_day = e_day.filter(registrador=self.request.user)
                chart_pasajes.append(float(p_day.aggregate(t=Sum('precio'))['t'] or 0))
                chart_encomiendas.append(float(e_day.aggregate(t=Sum('precio'))['t'] or 0))

            context['chart_flujo_labels'] = json.dumps(chart_labels)
            context['chart_flujo_pasajes'] = json.dumps(chart_pasajes)
            context['chart_flujo_encomiendas'] = json.dumps(chart_encomiendas)

        # =====================================================================
        # TAB 2: CIERRES DE CAJA
        # =====================================================================
        elif tab == 'caja':
            sesiones = SesionCaja.objects.filter(
                fecha_apertura__date__gte=fecha_desde,
                fecha_apertura__date__lte=fecha_hasta,
            ).select_related('cajero').order_by('-fecha_apertura')
            if es_personal and not es_admin:
                sesiones = sesiones.filter(cajero=self.request.user)

            context['sesiones_caja'] = sesiones
            # Chart data: montos de apertura vs cierre
            chart_caja_labels = []
            chart_caja_apertura = []
            chart_caja_ingresos = []
            chart_caja_egresos = []
            for s in sesiones:
                chart_caja_labels.append(f"{s.cajero.username} {s.fecha_apertura.strftime('%d/%m %H:%M')}")
                chart_caja_apertura.append(float(s.monto_apertura))
                chart_caja_ingresos.append(float(s.total_ingresos))
                chart_caja_egresos.append(float(s.total_egresos))
            context['chart_caja_labels'] = json.dumps(chart_caja_labels)
            context['chart_caja_apertura'] = json.dumps(chart_caja_apertura)
            context['chart_caja_ingresos'] = json.dumps(chart_caja_ingresos)
            context['chart_caja_egresos'] = json.dumps(chart_caja_egresos)

        # =====================================================================
        # TAB 3: ENCOMIENDAS (por rango, destino y cliente)
        # =====================================================================
        elif tab == 'encomiendas':
            enc_qs = Encomienda.objects.filter(
                fecha_registro__date__gte=fecha_desde,
                fecha_registro__date__lte=fecha_hasta,
            ).select_related(
                'remitente', 'destinatario', 'parada_origen', 'parada_destino', 'viaje__itinerario', 'registrador'
            ).order_by('-fecha_registro')
            if es_personal and not es_admin:
                enc_qs = enc_qs.filter(registrador=self.request.user)

            # Filtro destino
            destino_nombre = self.request.GET.get('destino')
            if destino_nombre:
                enc_qs = enc_qs.filter(parada_destino__nombre=destino_nombre)
            # Filtro cliente (remitente)
            cliente_ci = self.request.GET.get('cliente_ci')
            if cliente_ci:
                enc_qs = enc_qs.filter(
                    Q(remitente__cedula__icontains=cliente_ci) |
                    Q(remitente__nombre__icontains=cliente_ci) |
                    Q(remitente__apellido__icontains=cliente_ci) |
                    Q(destinatario__cedula__icontains=cliente_ci) |
                    Q(destinatario__nombre__icontains=cliente_ci) |
                    Q(destinatario__apellido__icontains=cliente_ci)
                )
            context['encomiendas_reporte'] = enc_qs
            context['destino_filter'] = destino_nombre or ''
            context['cliente_ci_filter'] = cliente_ci or ''
            context['paradas_disponibles'] = Parada.objects.values_list('nombre', flat=True).distinct().order_by('nombre')

            # Resumen por estado
            resumen_estados = {}
            for enc in enc_qs:
                label = enc.get_estado_display()
                if label not in resumen_estados:
                    resumen_estados[label] = {'count': 0, 'total': Decimal('0')}
                resumen_estados[label]['count'] += 1
                resumen_estados[label]['total'] += enc.precio
            context['enc_resumen_estados'] = resumen_estados
            context['enc_total'] = enc_qs.aggregate(total=Sum('precio'))['total'] or Decimal('0')
            context['enc_count'] = enc_qs.count()

            # Chart por destino
            destinos_data = {}
            for enc in enc_qs:
                dest_name = enc.parada_destino.nombre if enc.parada_destino else 'Sin destino'
                if dest_name not in destinos_data:
                    destinos_data[dest_name] = 0
                destinos_data[dest_name] += 1
            context['chart_enc_destino_labels'] = json.dumps(list(destinos_data.keys()))
            context['chart_enc_destino_data'] = json.dumps(list(destinos_data.values()))

        # =====================================================================
        # TAB 4: SITUACIÓN DIARIA (encomiendas + reservaciones de pasajes)
        # =====================================================================
        elif tab == 'situacion':
            # Pasajes del rango
            pasajes_sit = Pasaje.objects.filter(
                fecha_venta__date__gte=fecha_desde,
                fecha_venta__date__lte=fecha_hasta,
            ).select_related('viaje__itinerario', 'pasajero', 'asiento', 'parada_origen', 'parada_destino', 'vendedor')
            if es_personal and not es_admin:
                pasajes_sit = pasajes_sit.filter(vendedor=self.request.user)

            # Resumen pasajes por estado
            pasaje_estados = {}
            total_pasajes_sit = Decimal('0')
            for p in pasajes_sit:
                label = p.get_estado_display()
                if label not in pasaje_estados:
                    pasaje_estados[label] = {'count': 0, 'total': Decimal('0')}
                pasaje_estados[label]['count'] += 1
                pasaje_estados[label]['total'] += p.precio
                total_pasajes_sit += p.precio
            context['pasaje_estados'] = pasaje_estados
            context['pasajes_situacion'] = pasajes_sit.order_by('-fecha_venta')[:50]
            context['total_pasajes_sit'] = total_pasajes_sit

            # Encomiendas del rango
            enc_sit = Encomienda.objects.filter(
                fecha_registro__date__gte=fecha_desde,
                fecha_registro__date__lte=fecha_hasta,
            ).select_related('remitente', 'destinatario', 'parada_destino', 'registrador')
            if es_personal and not es_admin:
                enc_sit = enc_sit.filter(registrador=self.request.user)

            enc_estados = {}
            total_enc_sit = Decimal('0')
            for e in enc_sit:
                label = e.get_estado_display()
                if label not in enc_estados:
                    enc_estados[label] = {'count': 0, 'total': Decimal('0')}
                enc_estados[label]['count'] += 1
                enc_estados[label]['total'] += e.precio
                total_enc_sit += e.precio
            context['enc_estados_sit'] = enc_estados
            context['encomiendas_situacion'] = enc_sit.order_by('-fecha_registro')[:50]
            context['total_enc_sit'] = total_enc_sit

            # Chart donut: pasajes por estado
            context['chart_sit_pasaje_labels'] = json.dumps(list(pasaje_estados.keys()))
            context['chart_sit_pasaje_data'] = json.dumps([v['count'] for v in pasaje_estados.values()])
            # Chart donut: encomiendas por estado
            context['chart_sit_enc_labels'] = json.dumps(list(enc_estados.keys()))
            context['chart_sit_enc_data'] = json.dumps([v['count'] for v in enc_estados.values()])

        # =====================================================================
        # TAB 5: COMISIONES MENSUALES (solo admin)
        # =====================================================================
        elif tab == 'comisiones':
            # Utilizar el rango de fechas seleccionado
            mes_inicio = fecha_desde
            mes_fin = fecha_hasta
            context['mes_inicio'] = mes_inicio
            context['mes_fin'] = mes_fin

            COMISION_POR_BOLETA = 5000  # Valor por defecto
            comision_param = self.request.GET.get('comision_valor', '')
            if comision_param:
                try:
                    COMISION_POR_BOLETA = int(comision_param)
                except (ValueError, TypeError):
                    pass

            # Obtener todos los vendedores con ventas en el rango
            pasajes_mes = Pasaje.objects.filter(
                fecha_venta__date__gte=mes_inicio,
                fecha_venta__date__lte=mes_fin,
                estado__in=['vendido', 'abordado']
            ).exclude(
                vendedor__is_superuser=True  # Excluir administradores
            ).select_related('vendedor', 'vendedor__persona', 'viaje__empresa')
            if empresa_obj:
                pasajes_mes = pasajes_mes.filter(viaje__empresa=empresa_obj)

            # Agrupar por vendedor
            vendedores_data = {}
            for p in pasajes_mes:
                if not p.vendedor:
                    continue
                # Solo comisionan vendedores con rol empleado o ayudante
                vend_persona = getattr(p.vendedor, 'persona', None)
                if not vend_persona:
                    continue  # Sin perfil de persona, no comisiona
                if not vend_persona.es_ayudante:
                    continue  # No es ayudante (ej: cliente), no comisiona
                
                uid = p.vendedor_id
                if uid not in vendedores_data:
                    vendedores_data[uid] = {
                        'usuario': p.vendedor.get_full_name() or p.vendedor.username,
                        'username': p.vendedor.username,
                        'boletas': 0,
                        'total_vendido': Decimal('0'),
                        'comision': Decimal('0'),
                    }
                vendedores_data[uid]['boletas'] += 1
                vendedores_data[uid]['total_vendido'] += p.precio

            # Calcular comisiones
            for uid, data in vendedores_data.items():
                data['comision'] = Decimal(str(data['boletas'] * COMISION_POR_BOLETA))

            comisiones_list = sorted(vendedores_data.values(), key=lambda x: x['comision'], reverse=True)
            context['comisiones'] = comisiones_list
            context['comision_por_boleta'] = COMISION_POR_BOLETA
            context['total_comisiones'] = sum(c['comision'] for c in comisiones_list)
            context['total_boletas_mes'] = sum(c['boletas'] for c in comisiones_list)
            context['total_vendido_mes'] = sum(c['total_vendido'] for c in comisiones_list)

            # Chart: comisiones por vendedor
            context['chart_com_labels'] = json.dumps([c['usuario'] for c in comisiones_list])
            context['chart_com_data'] = json.dumps([float(c['comision']) for c in comisiones_list])
            context['chart_com_boletas'] = json.dumps([c['boletas'] for c in comisiones_list])

        # =====================================================================
        # TAB 6: VENTAS (reporte de ventas pasajes + encomiendas con desglose por día)
        # =====================================================================
        elif tab == 'ventas':
            delta_days = (fecha_hasta - fecha_desde).days + 1
            ventas_por_dia = []
            for i in range(delta_days):
                d = fecha_desde + timedelta(days=i)
                p_day = Pasaje.objects.filter(fecha_venta__date=d, estado__in=['vendido', 'abordado'])
                e_day = Encomienda.objects.filter(fecha_registro__date=d).exclude(estado='cancelado')
                f_day = Factura.objects.filter(fecha_emision__date=d, estado='emitida')
                if es_personal and not es_admin:
                    p_day = p_day.filter(vendedor=self.request.user)
                    e_day = e_day.filter(registrador=self.request.user)
                    f_day = f_day.filter(cajero=self.request.user)

                ing_p = p_day.aggregate(t=Sum('precio'))['t'] or Decimal('0')
                ing_e = e_day.aggregate(t=Sum('precio'))['t'] or Decimal('0')
                ventas_por_dia.append({
                    'fecha': d,
                    'pasajes': p_day.count(),
                    'encomiendas': e_day.count(),
                    'facturas': f_day.count(),
                    'ingresos_pasajes': ing_p,
                    'ingresos_encomiendas': ing_e,
                    'total': ing_p + ing_e,
                })

            context['ventas_por_dia'] = ventas_por_dia
            context['total_pasajes'] = sum(v['pasajes'] for v in ventas_por_dia)
            context['total_encomiendas'] = sum(v['encomiendas'] for v in ventas_por_dia)
            context['total_facturas'] = sum(v['facturas'] for v in ventas_por_dia)
            context['ingresos_pasajes'] = sum(v['ingresos_pasajes'] for v in ventas_por_dia)
            context['ingresos_encomiendas'] = sum(v['ingresos_encomiendas'] for v in ventas_por_dia)
            context['total_ingresos'] = sum(v['total'] for v in ventas_por_dia)

            # % distribución
            ti = context['total_ingresos']
            context['porcentaje_pasajes'] = round(float(context['ingresos_pasajes']) / float(ti) * 100, 1) if ti else 0
            context['porcentaje_encomiendas'] = round(float(context['ingresos_encomiendas']) / float(ti) * 100, 1) if ti else 0

            # Chart: ventas por día
            context['chart_ventas_labels'] = json.dumps([v['fecha'].strftime('%d/%m') for v in ventas_por_dia])
            context['chart_ventas_pasajes'] = json.dumps([float(v['ingresos_pasajes']) for v in ventas_por_dia])
            context['chart_ventas_encomiendas'] = json.dumps([float(v['ingresos_encomiendas']) for v in ventas_por_dia])

        return context


class ReporteVentasView(LoginRequiredMixin, TemplateView):
    """Redirige al hub de reportes con tab de ventas."""
    def get(self, request, *args, **kwargs):
        desde = request.GET.get('desde', '')
        hasta = request.GET.get('hasta', '')
        url = reverse('operations:reporte_diario') + f'?tab=ventas&desde={desde}&hasta={hasta}'
        return redirect(url)


# =============================================================================
# HTMX PARTIALS
# =============================================================================

class BuscarPersonaView(LoginRequiredMixin, View):
    """Buscar persona por cédula (HTMX)."""
    
    def get(self, request):
        cedula = request.GET.get('cedula')
        if cedula:
            # Limpiar espacios y puntos
            cedula_limpia = cedula.replace(' ', '').replace('\xa0', '').replace('.', '')
            try:
                persona = Persona.objects.get(cedula=cedula_limpia)
                return render(request, 'operations/partials/persona_encontrada.html', {
                    'persona': persona
                })
            except Persona.DoesNotExist:
                return render(request, 'operations/partials/persona_no_encontrada.html', {
                    'cedula': cedula
                })
        return HttpResponse('')


class AsientosDisponiblesView(LoginRequiredMixin, View):
    """Obtener asientos disponibles de un viaje (HTMX)."""
    
    def get(self, request, viaje_pk):
        viaje = get_object_or_404(Viaje, pk=viaje_pk)
        
        pasajes_ocupados = Pasaje.objects.filter(
            viaje=viaje,
            estado__in=['reservado', 'vendido', 'abordado']
        ).select_related('parada_destino')
        
        asientos_ocupados_info = {}
        for p in pasajes_ocupados:
            dest = p.parada_destino.nombre
            if p.asiento_id in asientos_ocupados_info:
                asientos_ocupados_info[p.asiento_id] += f" / {dest}"
            else:
                asientos_ocupados_info[p.asiento_id] = dest
        
        asientos = viaje.bus.asientos.all().order_by('piso', 'numero_asiento')
        
        return render(request, 'operations/partials/mapa_asientos.html', {
            'viaje': viaje,
            'asientos': asientos,
            'asientos_ocupados': list(asientos_ocupados_info.keys()),
            'asientos_ocupados_info': asientos_ocupados_info
        })


class ObtenerPrecioView(LoginRequiredMixin, View):
    """Obtener precio de un tramo (HTMX/AJAX)."""
    
    def get(self, request):
        viaje_pk = request.GET.get('viaje')
        origen_pk = request.GET.get('origen')
        destino_pk = request.GET.get('destino')
        
        if viaje_pk and origen_pk and destino_pk:
            try:
                # 1. Intento por IDs exactos
                precio_obj = Precio.objects.filter(
                    origen_id=origen_pk,
                    destino_id=destino_pk
                ).first()
                
                if not precio_obj:
                    # 2. Intento por LOCALIDADES (IDs)
                    from fleet.models import Parada
                    p_origen = Parada.objects.filter(pk=origen_pk).first()
                    p_destino = Parada.objects.filter(pk=destino_pk).first()

                    def clean_text(t):
                        return t.lower().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
                    
                    if p_origen and p_destino and p_origen.localidad and p_destino.localidad:
                        precio_obj = Precio.objects.filter(
                            origen__localidad=p_origen.localidad,
                            destino__localidad=p_destino.localidad
                        ).first()
                        
                        if not precio_obj:
                            # 3. Intento por NOMBRES DE LOCALIDAD (IExact)
                            precio_obj = Precio.objects.filter(
                                origen__localidad__nombre__iexact=p_origen.localidad.nombre,
                                destino__localidad__nombre__iexact=p_destino.localidad.nombre
                            ).first()
                        
                        if not precio_obj:
                            # 4. Intento FUZZY por nombres (más agresivo)
                            o_base = clean_text(p_origen.localidad.nombre.replace('Terminal', '').replace('de', '').strip())
                            d_base = clean_text(p_destino.localidad.nombre.replace('Terminal', '').replace('de', '').strip())
                            
                            precio_obj = Precio.objects.filter(
                                (Q(origen__localidad__nombre__icontains=o_base) | Q(origen__nombre__icontains=o_base)),
                                (Q(destino__localidad__nombre__icontains=d_base) | Q(destino__nombre__icontains=d_base))
                            ).first()

                        if not precio_obj:
                            # 5. CASO ESPECIAL ASUNCION / CDE (Búsqueda por palabras clave)
                            q_o = Q(origen__nombre__icontains='asuncion') | Q(origen__localidad__nombre__icontains='asuncion')
                            q_d = Q(destino__nombre__icontains='ciudad del este') | Q(destino__nombre__icontains='cde') | Q(destino__localidad__nombre__icontains='ciudad del este')
                            precio_obj = Precio.objects.filter(q_o, q_d).first()

                        if not precio_obj:
                            # 6. INTENTO POR SUMATORIA DE TRAMOS (Ruta con trasbordo lógico)
                            # Si existe A -> Oviedo y Oviedo -> CDE, sumarlos.
                            # Primero buscamos todos los precios que salgan del origen
                            precios_desde_origen = Precio.objects.filter(
                                Q(origen__localidad=p_origen.localidad) | Q(origen=p_origen)
                            )
                            for p1 in precios_desde_origen:
                                # Por cada destino de p1, buscar si hay precio hasta el destino final
                                p2 = Precio.objects.filter(
                                    origen=p1.destino,
                                    destino__localidad=p_destino.localidad
                                ).first()
                                if p2:
                                    return JsonResponse({'precio': float(p1.precio + p2.precio), 'info': 'Calculado por tramos'})

                if precio_obj:
                    return JsonResponse({'precio': float(precio_obj.precio)})
                
                return JsonResponse({'precio': 0, 'error': 'No encontrado'})
                
            except Exception as e:
                return JsonResponse({'precio': 0, 'error': str(e)})
        
        return JsonResponse({'precio': 0})


class BuscarClientesFacturaView(LoginRequiredMixin, View):
    """API para buscar clientes con items pendientes de facturar."""
    
    def get(self, request):
        query = request.GET.get('q', '').strip()
        
        if len(query) < 2:
            return JsonResponse({'clientes': []})
        
        # Buscar clientes que tengan pasajes o encomiendas pendientes de facturar
        # Primero buscar personas que coincidan con la búsqueda
        personas = Persona.objects.filter(
            Q(cedula__icontains=query) |
            Q(nombre__icontains=query) |
            Q(apellido__icontains=query)
        )[:20]
        
        clientes = []
        for persona in personas:
            # Verificar si tiene pasajes pendientes (vendidos o reservados)
            pasajes_pendientes = Pasaje.objects.filter(
                Q(pasajero=persona) | Q(cliente=persona),
                estado__in=['vendido', 'reservado']
            ).exclude(
                detalles_factura__factura__estado='emitida'
            ).count()
            
            # Verificar si tiene encomiendas pendientes
            encomiendas_pendientes = Encomienda.objects.filter(
                remitente=persona,
                estado__in=['registrado', 'en_transito', 'en_destino', 'entregado']
            ).exclude(
                detalles_factura__factura__estado='emitida'
            ).count()
            
            total_pendientes = pasajes_pendientes + encomiendas_pendientes
            
            if total_pendientes > 0:
                clientes.append({
                    'cedula': str(persona.cedula),
                    'nombre': persona.nombre_completo,
                    'pasajes_pendientes': pasajes_pendientes,
                    'encomiendas_pendientes': encomiendas_pendientes,
                    'total_pendientes': total_pendientes
                })
        
        return JsonResponse({'clientes': clientes})


class BuscarClientesRegistradosView(LoginRequiredMixin, View):
    """API para buscar clientes registrados (para el modal de remitente)."""
    
    def get(self, request):
        query = request.GET.get('q', '').strip()
        
        if len(query) < 2:
            return JsonResponse({'clientes': []})
        
        # Buscar personas que coincidan con la búsqueda
        personas = Persona.objects.filter(
            Q(cedula__icontains=query) |
            Q(nombre__icontains=query) |
            Q(apellido__icontains=query)
        ).filter(
            activo=True
        ).filter(
            Q(es_cliente=True) |
            Q(es_chofer=True) |
            Q(es_ayudante=True) |
            Q(es_agente=True) |
            Q(es_empleado=True)
        ).order_by('apellido', 'nombre')[:30]
        
        clientes = []
        for persona in personas:
            clientes.append({
                'id': persona.pk,
                'cedula': str(persona.cedula),
                'nombre_completo': persona.nombre_completo,
                'nombre': persona.nombre,
                'apellido': persona.apellido,
                'telefono': persona.telefono or '',
                'direccion': persona.direccion or ''
            })
        
        return JsonResponse({'clientes': clientes})


class CrearClienteAjaxView(LoginRequiredMixin, View):
    """API para registrar un nuevo cliente desde el formulario modal."""
    
    def post(self, request):
        cedula = request.POST.get('cedula', '').strip()
        nombre = request.POST.get('nombre', '').strip()
        apellido = request.POST.get('apellido', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        email = request.POST.get('email', '').strip()
        direccion = request.POST.get('direccion', '').strip()
        
        if not cedula or not nombre:
            return JsonResponse({'success': False, 'error': 'Cédula y Nombre son obligatorios.'}, status=400)
            
        cedula_clean = cedula.replace('.', '').replace(' ', '').upper()
        cedula_base = cedula_clean.split('-')[0]
        
        if not cedula_base.isdigit():
            return JsonResponse({'success': False, 'error': 'La cédula debe contener números válidos.'}, status=400)
            
        from django.db.models import Q
        if Persona.objects.filter(Q(cedula=cedula_clean) | Q(cedula=cedula_base) | Q(cedula__startswith=cedula_base + '-')).exists():
            return JsonResponse({'success': False, 'error': 'Ya existe una persona registrada con esta cédula o RUC.'}, status=400)
            
        try:
            persona = Persona.objects.create(
                cedula=cedula_clean,
                nombre=nombre,
                apellido=apellido,
                telefono=telefono,
                email=email,
                direccion=direccion,
                es_cliente=True
            )
            return JsonResponse({
                'success': True,
                'cliente': {
                    'cedula': str(persona.cedula),
                    'nombre': persona.nombre,
                    'apellido': persona.apellido,
                    'telefono': persona.telefono,
                    'nombre_completo': persona.nombre_completo
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error al registrar el cliente: {str(e)}'}, status=500)


class ObtenerItemsPendientesClienteView(LoginRequiredMixin, View):
    """API para obtener pasajes y encomiendas pendientes de un cliente."""
    
    def get(self, request):
        cedula = request.GET.get('cedula', '').strip()
        empresa_id = request.GET.get('empresa', '').strip()
        
        if not cedula:
            return JsonResponse({'error': 'Cédula requerida'}, status=400)
        
        # Limpiar espacios y puntos
        cedula_limpia = cedula.replace(' ', '').replace('\xa0', '').replace('.', '')
        
        try:
            persona = Persona.objects.get(cedula=cedula_limpia)
        except (Persona.DoesNotExist, ValueError):
            return JsonResponse({'error': 'Cliente no encontrado'}, status=404)
        
        ahora = timezone.localtime(timezone.now())
        hoy = ahora.date()
        hora_actual = ahora.time()

        # Obtener pasajes pendientes (vendidos, reservados o abordados, solo futuros o vigentes)
        pasajes = Pasaje.objects.filter(
            Q(pasajero=persona) | Q(cliente=persona),
            estado__in=['vendido', 'reservado', 'abordado']
        ).exclude(
            detalles_factura__factura__estado='emitida'
        )
        
        # Los pasajes vendidos, reservados o abordados pendientes se muestran siempre
        # para dar oportunidad a cobrar/facturar casos de último momento o buses retrasados.
        # Si el usuario actual es un ayudante/chofer, solo ve sus propias ventas. 
        # Los empleados y administradores pueden ver todo.
        persona_req = getattr(request.user, 'persona', None)
        is_ayudante_chofer = persona_req and (persona_req.es_ayudante or persona_req.es_chofer)
        
        if is_ayudante_chofer and not request.user.is_superuser:
            pasajes = pasajes.filter(vendedor=request.user)
        
        if empresa_id:
            pasajes = pasajes.filter(Q(viaje__empresa_id=empresa_id) | Q(viaje__bus__empresa_id=empresa_id))
            
        pasajes = pasajes.select_related('viaje__itinerario', 'asiento')
        
        pasajes_data = []
        for p in pasajes:
            pasajes_data.append({
                'pk': p.pk,
                'codigo': p.codigo,
                'viaje': f"{p.viaje.itinerario.nombre} - {p.viaje.fecha_viaje.strftime('%d/%m')}",
                'pasajero': p.pasajero.nombre_completo,
                'asiento': p.asiento.numero_asiento if p.asiento else '-',
                'precio': float(p.precio),
                'empresa_id': p.viaje.empresa_operadora.id if (p.viaje and p.viaje.empresa_operadora) else None
            })
        
        # Obtener encomiendas pendientes
        encomiendas = Encomienda.objects.filter(
            remitente=persona,
            estado__in=['registrado', 'en_transito', 'en_destino', 'entregado']
        ).exclude(
            detalles_factura__factura__estado='emitida'
        )
        
        if empresa_id:
            encomiendas = encomiendas.filter(Q(viaje__empresa_id=empresa_id) | Q(viaje__bus__empresa_id=empresa_id) | Q(viaje__itinerario__empresa_id=empresa_id))
            
        encomiendas = encomiendas.select_related('viaje', 'parada_destino')
        
        encomiendas_data = []
        for e in encomiendas:
            encomiendas_data.append({
                'pk': e.pk,
                'codigo': e.codigo,
                'tipo': e.get_tipo_display(),
                'descripcion': e.descripcion[:30] if e.descripcion else '-',
                'destino': e.parada_destino.nombre if e.parada_destino else '-',
                'precio': float(e.precio),
                'empresa_id': e.viaje.empresa_operadora.id if (e.viaje and e.viaje.empresa_operadora) else None
            })
        
        return JsonResponse({
            'cliente': {
                'cedula': str(persona.cedula),
                'nombre': persona.nombre_completo
            },
            'pasajes': pasajes_data,
            'encomiendas': encomiendas_data
        })


class APIItinerariosEmpresaView(LoginRequiredMixin, View):
    """API JSON para obtener itinerarios filtrados por empresa."""
    
    def get(self, request):
        empresa_id = request.GET.get('empresa_id')
        
        if not empresa_id:
            itinerarios = Itinerario.objects.filter(activo=True).order_by('nombre')
        else:
            try:
                itinerarios = Itinerario.objects.filter(
                    empresa_id=int(empresa_id),
                    activo=True
                ).order_by('nombre')
            except (ValueError, TypeError):
                itinerarios = Itinerario.objects.filter(activo=True).order_by('nombre')
        
        data = [{'id': it.pk, 'nombre': it.nombre} for it in itinerarios]
        return JsonResponse({'itinerarios': data})


class APIHorariosItinerarioView(LoginRequiredMixin, View):
    """API JSON para obtener horarios filtrados por itinerario (Many2Many)."""
    
    def get(self, request):
        itinerario_id = request.GET.get('itinerario_id')
        
        if not itinerario_id:
            horarios = Horario.objects.filter(activo=True).order_by('hora_salida')
        else:
            try:
                itinerario = Itinerario.objects.get(pk=int(itinerario_id))
                horarios = itinerario.horarios.filter(activo=True).order_by('hora_salida')
            except (ValueError, TypeError, Itinerario.DoesNotExist):
                horarios = Horario.objects.filter(activo=True).order_by('hora_salida')
        
        data = [{'id': h.pk, 'hora': h.hora_salida.strftime('%H:%M')} for h in horarios]
        return JsonResponse({'horarios': data})


class APIBuscarItinerariosView(LoginRequiredMixin, View):
    """API JSON para buscar itinerarios con datos tabulares para modal."""
    
    def get(self, request):
        empresa_id = request.GET.get('empresa_id')
        search = request.GET.get('search', '').strip()
        
        qs = Itinerario.objects.filter(activo=True).select_related('empresa').prefetch_related('horarios')
        
        if empresa_id:
            try:
                qs = qs.filter(empresa_id=int(empresa_id))
            except (ValueError, TypeError):
                pass
        
        if search:
            qs = qs.filter(
                Q(nombre__icontains=search) |
                Q(ruta__icontains=search) |
                Q(empresa__nombre__icontains=search)
            )
        
        qs = qs.order_by('nombre')[:50]
        
        data = []
        for it in qs:
            data.append({
                'id': it.pk,
                'nombre': it.nombre,
                'ruta': it.ruta or '-',
                'empresa': it.empresa.nombre if it.empresa else '-',
                'dias': it.dias_operacion_texto,
                'origen': it.parada_origen,
                'destino': it.parada_destino,
                'horarios_count': it.horarios.count(),
            })
        
        return JsonResponse({'results': data})


class APIBuscarBusesView(LoginRequiredMixin, View):
    """API JSON para buscar buses con datos tabulares para modal."""
    
    def get(self, request):
        empresa_id = request.GET.get('empresa_id')
        search = request.GET.get('search', '').strip()
        
        qs = Bus.objects.filter(estado='activo').select_related('empresa')
        
        if empresa_id:
            try:
                qs = qs.filter(empresa_id=int(empresa_id))
            except (ValueError, TypeError):
                pass
        
        if search:
            qs = qs.filter(
                Q(placa__icontains=search) |
                Q(numero_bus__icontains=search) |
                Q(marca__icontains=search) |
                Q(modelo__icontains=search)
            )
        
        qs = qs.order_by('placa')[:50]
        
        data = []
        for bus in qs:
            label = str(bus)
            data.append({
                'id': bus.pk,
                'placa': bus.placa,
                'numero_bus': bus.numero_bus or '-',
                'marca': bus.marca or '-',
                'modelo': bus.modelo or '-',
                'capacidad': bus.capacidad_asientos,
                'empresa': bus.empresa.nombre if bus.empresa else '-',
                'label': label,
            })
        
        return JsonResponse({'results': data})


class APIBuscarChoferesView(LoginRequiredMixin, View):
    """API JSON para buscar choferes con datos tabulares para modal."""
    
    def get(self, request):
        empresa_id = request.GET.get('empresa_id')
        search = request.GET.get('search', '').strip()
        
        qs = Persona.objects.filter(es_chofer=True, activo=True)
        
        if empresa_id:
            try:
                qs = qs.filter(empresa_id=int(empresa_id))
            except (ValueError, TypeError):
                pass
        
        if search:
            qs = qs.filter(
                Q(nombre__icontains=search) |
                Q(apellido__icontains=search) |
                Q(cedula__icontains=search)
            )
        
        qs = qs.order_by('apellido', 'nombre')[:50]
        
        data = []
        for p in qs:
            data.append({
                'cedula': p.cedula,
                'nombre': p.nombre,
                'apellido': p.apellido,
                'telefono': p.telefono or '-',
                'label': f"{p.apellido}, {p.nombre} ({p.cedula})",
            })
        
        return JsonResponse({'results': data})


class APIBuscarAyudantesView(LoginRequiredMixin, View):
    """API JSON para buscar ayudantes con datos tabulares para modal."""
    
    def get(self, request):
        empresa_id = request.GET.get('empresa_id')
        search = request.GET.get('search', '').strip()
        
        qs = Persona.objects.filter(es_ayudante=True, activo=True)
        
        if empresa_id:
            try:
                qs = qs.filter(empresa_id=int(empresa_id))
            except (ValueError, TypeError):
                pass
        
        if search:
            qs = qs.filter(
                Q(nombre__icontains=search) |
                Q(apellido__icontains=search) |
                Q(cedula__icontains=search)
            )
        
        qs = qs.order_by('apellido', 'nombre')[:50]
        
        data = []
        for p in qs:
            data.append({
                'cedula': p.cedula,
                'nombre': p.nombre,
                'apellido': p.apellido,
                'telefono': p.telefono or '-',
                'label': f"{p.apellido}, {p.nombre} ({p.cedula})",
            })
        
        return JsonResponse({'results': data})


class ViajeParadasView(LoginRequiredMixin, View):
    """API para obtener las paradas de un viaje específico."""
    
    def get(self, request, viaje_pk):
        viaje = get_object_or_404(Viaje, pk=viaje_pk)
        
        # Obtener paradas del itinerario
        paradas_ids = viaje.itinerario.detalles.values_list('parada_id', flat=True)
        paradas = Parada.objects.filter(id__in=list(paradas_ids))
        
        if request.GET.get('solo_agencias') == '1':
            paradas = paradas.filter(es_agencia=True)
            
        paradas = paradas.order_by('nombre')
        
        paradas_data = [
            {'id': p.id, 'nombre': p.nombre}
            for p in paradas
        ]
        
        # Mapear origen y destino actuales al nuevo itinerario
        origen_id = request.GET.get('origen')
        destino_id = request.GET.get('destino')
        
        mapped_origen = None
        mapped_destino = None
        
        from operations.utils import get_similar_paradas_ids
        from fleet.models import Parada
        
        if origen_id:
            try:
                parada_o = Parada.objects.get(pk=int(origen_id))
                similares_o = get_similar_paradas_ids(parada_o, parada_o.id)
                for pid in similares_o:
                    if pid in paradas_ids:
                        mapped_origen = pid
                        break
            except (ValueError, Parada.DoesNotExist):
                pass
                
        if destino_id:
            try:
                parada_d = Parada.objects.get(pk=int(destino_id))
                similares_d = get_similar_paradas_ids(parada_d, parada_d.id)
                for pid in similares_d:
                    if pid in paradas_ids:
                        mapped_destino = pid
                        break
            except (ValueError, Parada.DoesNotExist):
                pass
        
        return JsonResponse({
            'viaje': {
                'id': viaje.pk,
                'nombre': viaje.itinerario.nombre,
                'fecha': viaje.fecha_viaje.strftime('%d/%m/%Y'),
                'bus': viaje.bus.placa
            },
            'paradas': paradas_data,
            'mapped_origen': mapped_origen,
            'mapped_destino': mapped_destino
        })


class ObtenerHorariosItinerarioView(LoginRequiredMixin, View):
    """Retorna las opciones de horario y buses para un itinerario específico (HTMX)."""
    def get(self, request):
        itinerario_id = request.GET.get('itinerario')
        fecha_str = request.GET.get('fecha_viaje')
        empresa_id = request.GET.get('empresa')
        
        # Filtros iniciales vacíos
        horarios_data = []
        itinerarios = Itinerario.objects.filter(activo=True)
        buses = Bus.objects.none()
        choferes = Persona.objects.none()
        ayudantes = Persona.objects.none()
        
        # Si se seleccionó empresa, filtrar todo por esa empresa
        if empresa_id:
            try:
                from django.db.models import Q
                emp_id = int(empresa_id)
                itinerarios = itinerarios.filter(empresa_id=emp_id)
                buses = Bus.objects.filter(empresa_id=emp_id).order_by('placa')
                choferes = Persona.objects.filter(
                    Q(es_chofer=True),
                    empresa_id=emp_id
                ).order_by('apellido', 'nombre')
                ayudantes = Persona.objects.filter(
                    Q(es_ayudante=True),
                    empresa_id=emp_id
                ).order_by('apellido', 'nombre')
            except (ValueError, TypeError):
                pass
        
        # Obtener recursos predeterminados del itinerario
        bus_pred_id = None
        chofer_pred_cedula = None
        ayudante_pred_cedula = None
        horario_id = request.GET.get('horario')

        if itinerario_id:
            try:
                itinerario = Itinerario.objects.get(pk=itinerario_id)
                
                # Cargar predeterminados del itinerario
                if itinerario.bus_predeterminado and itinerario.bus_predeterminado.estado == 'activo':
                    bus_pred_id = itinerario.bus_predeterminado_id
                if itinerario.chofer_predeterminado:
                    chofer_pred_cedula = itinerario.chofer_predeterminado.cedula
                if itinerario.ayudante_predeterminado:
                    ayudante_pred_cedula = itinerario.ayudante_predeterminado.cedula

                # Obtener solo los horarios asignados a este itinerario
                todos_horarios = itinerario.horarios.filter(activo=True).order_by('hora_salida')

                # Filtrar si la fecha es hoy
                ahora = timezone.localtime(timezone.now())
                hoy = ahora.date()
                fecha_viaje = None
                
                if fecha_str:
                    try:
                        from datetime import datetime
                        fecha_viaje = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                    except (ValueError, TypeError):
                        pass

                # Analizar horarios
                for h in todos_horarios:
                    es_pasado = False
                    if fecha_viaje == hoy:
                        if h.hora_salida < ahora.time():
                            es_pasado = True
                    
                    horarios_data.append({
                        'id': h.id,
                        'hora': h.hora_salida.strftime('%H:%M'),
                        'es_pasado': es_pasado
                    })
                
                # Si no se seleccionó empresa explícitamente, filtrar por la empresa del itinerario
                if not empresa_id and itinerario.empresa:
                    buses = Bus.objects.filter(empresa=itinerario.empresa).order_by('placa')
                    choferes = Persona.objects.filter(
                        Q(es_chofer=True),
                        empresa=itinerario.empresa
                    ).order_by('apellido', 'nombre')
                    ayudantes = Persona.objects.filter(
                        Q(es_ayudante=True),
                        empresa=itinerario.empresa
                    ).order_by('apellido', 'nombre')
            except (ValueError, TypeError, Itinerario.DoesNotExist):
                pass
                
        # Excluir recursos ya asignados en los próximos 8 días (o solo ese día si es un viaje único)
        if fecha_str and horario_id:
            try:
                from datetime import datetime, timedelta
                fecha_v = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                fecha_fin = fecha_v + timedelta(days=7) # El creador genera 8 días de viajes consecutivos
                
                viajes_ocupados = Viaje.objects.filter(
                    fecha_viaje__range=[fecha_v, fecha_fin],
                    horario_id=horario_id,
                    estado__in=['programado', 'en_curso']
                ).prefetch_related('ayudantes')
                
                viaje_id = request.GET.get('viaje_id')
                if viaje_id:
                    viajes_ocupados = viajes_ocupados.exclude(pk=viaje_id)
                
                buses_ocupados = viajes_ocupados.values_list('bus_id', flat=True)
                choferes_ocupados = viajes_ocupados.values_list('chofer_id', flat=True)
                
                ayudantes_ocupados = set()
                for v in viajes_ocupados:
                    ayudantes_ocupados.update(v.ayudantes.values_list('cedula', flat=True))
                
                if buses is not None:
                    buses = buses.exclude(id__in=buses_ocupados)
                if choferes is not None:
                    choferes = choferes.exclude(cedula__in=choferes_ocupados)
                if ayudantes is not None:
                    ayudantes = ayudantes.exclude(cedula__in=ayudantes_ocupados)
            except (ValueError, TypeError):
                pass
        
        viaje_id = request.GET.get('viaje_id')
        
        return render(request, 'operations/partials/horario_options.html', {
            'horarios': horarios_data,
            'itinerarios': itinerarios,
            'buses': buses,
            'choferes': choferes,
            'ayudantes': ayudantes,
            'empresa_id': empresa_id,
            'itinerario_id': itinerario_id,
            'horario_id': horario_id,
            'bus_pred_id': bus_pred_id,
            'chofer_pred_cedula': chofer_pred_cedula,
            'ayudante_pred_cedula': ayudante_pred_cedula,
            'viaje_id': viaje_id,
        })


# =============================================================================
# RASTREO EN TIEMPO REAL
# =============================================================================

class RastreoMapaView(LoginRequiredMixin, TemplateView):
    """Vista principal del mapa de rastreo en tiempo real estilo Bolt (MODO ADMIN)."""
    template_name = 'operations/rastreo_mapa.html'

    def dispatch(self, request, *args, **kwargs):
        # Si es un cliente común y no es staff, redirigir a la vista pública
        if not request.user.is_staff and not request.user.is_superuser:
            persona = getattr(request.user, 'persona', None)
            if persona and persona.es_cliente:
                return redirect('operations:rastreo_publico')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        hoy = timezone.localtime(timezone.now()).date()

        # Viajes en curso hoy
        viajes_en_curso = Viaje.objects.filter(
            estado='en_curso',
            fecha_viaje=hoy
        ).select_related(
            'itinerario', 'bus', 'chofer', 'horario', 'empresa'
        ).prefetch_related('ayudantes')

        context['viajes_en_curso'] = viajes_en_curso
        context['total_en_curso'] = viajes_en_curso.count()
        return context


class APIViajosEnCursoView(LoginRequiredMixin, View):
    """API JSON para obtener viajes en curso con ubicaciones del personal (ADMIN)."""

    def get(self, request):
        hoy = timezone.localtime(timezone.now()).date()
        viajes_en_curso = Viaje.objects.filter(
            estado='en_curso', fecha_viaje=hoy
        ).select_related(
            'itinerario', 'bus', 'chofer', 'horario', 'empresa'
        ).prefetch_related('ayudantes', 'itinerario__detalles__parada__localidad')

        data = []
        for viaje in viajes_en_curso:
            ubicacion = None
            personas = [viaje.chofer] + list(viaje.ayudantes.all())
            for p in personas:
                # Intentar buscar la ubicación específica de este viaje en curso, de lo contrario la activa general
                ub = UbicacionAyudante.objects.filter(persona=p, viaje=viaje).order_by('-timestamp').first()
                if not ub:
                    ub = UbicacionAyudante.objects.filter(persona=p, activo=True).first()
                if ub:
                    ubicacion = ub
                    break

            pasajes_qs = viaje.pasajes.filter(
                estado__in=['vendido', 'reservado', 'abordado']
            ).values('asiento_id', 'estado').distinct()
            
            abordados = 0
            vendidos = 0
            reservados = 0
            asientos_vistos = set()
            
            for p in pasajes_qs:
                if p['asiento_id'] in asientos_vistos: continue
                asientos_vistos.add(p['asiento_id'])
                if p['estado'] == 'abordado': abordados += 1
                elif p['estado'] == 'vendido': vendidos += 1
                elif p['estado'] == 'reservado': reservados += 1

            ocupados = abordados + vendidos
            libres = viaje.bus.capacidad_asientos - (ocupados + reservados)

            detalles = viaje.itinerario.detalles.select_related('parada', 'parada__localidad').order_by('orden')
            paradas = []
            for d in detalles:
                # Auto-fix para paradas principales sin coordenadas
                if not d.parada.latitud_gps or not d.parada.longitud_gps:
                    coords_map = {
                        'asunci': ('-25.312918', '-57.564998'),
                        'san lorenzo': ('-25.3396', '-57.5097'),
                        'capiat': ('-25.3615', '-57.4339'),
                        'itaugu': ('-25.3854', '-57.3414'),
                        'ypacara': ('-25.3995', '-57.2831'),
                        'caacup': ('-25.3872', '-57.1420'),
                        'eusebio': ('-25.3721', '-56.9634'),
                        'san jos': ('-25.4054', '-56.5401'),
                        'coronel oviedo': ('-25.4443', '-56.4428'),
                        'oviedo': ('-25.4443', '-56.4428'),
                        'aguapety': ('-25.5794', '-56.4542'),
                        'caaguaz': ('-25.452684', '-56.015243'),
                        'caazap': ('-26.1966', '-56.3679'),
                        'nepomuceno': ('-26.1078', '-55.9411'),
                        'yuty': ('-26.6194', '-56.2503'),
                        'santa rosa del mi': ('-26.8892', '-56.8544'),
                        'santa rosa': ('-26.8892', '-56.8544'),
                        'coronel bogado': ('-27.1798', '-56.2581'),
                        'bogado': ('-27.1798', '-56.2581'),
                        'obligado': ('-27.2617', '-55.8417'),
                        'fram': ('-27.0022', '-55.9739'),
                        'encarnaci': ('-27.3358', '-55.8680'),
                        'mbocayaty': ('-25.7289', '-56.4116'),
                        'mbocajaty': ('-25.7289', '-56.4116'),
                        'villarrica': ('-25.779770', '-56.444738'),
                        'cde': ('-25.5097', '-54.6111'),
                        'ciudad del este': ('-25.5097', '-54.6111'),
                    }
                    nombre_parada = d.parada.nombre.lower()
                    if d.parada.localidad:
                        nombre_parada += ' ' + d.parada.localidad.nombre.lower()
                        
                    for key, (lat, lng) in coords_map.items():
                        if key in nombre_parada:
                            d.parada.latitud_gps = lat
                            d.parada.longitud_gps = lng
                            d.parada.save()
                            break
                    
                paradas.append({
                    'nombre': d.parada.nombre,
                    'orden': d.orden,
                    'lat': float(d.parada.latitud_gps) if d.parada.latitud_gps else None,
                    'lng': float(d.parada.longitud_gps) if d.parada.longitud_gps else None,
                })

            viaje_data = {
                'id': viaje.pk,
                'itinerario': viaje.itinerario.nombre,
                'empresa': viaje.empresa.nombre if viaje.empresa else '',
                'bus_numero': viaje.bus.numero_bus,
                'bus_placa': viaje.bus.placa,
                'bus_marca': f"{viaje.bus.marca or ''} {viaje.bus.modelo or ''}".strip(),
                'chofer': viaje.chofer.nombre_completo,
                'hora_salida': viaje.horario.hora_salida.strftime('%H:%M') if viaje.horario else '--:--',
                'asientos_total': viaje.bus.capacidad_asientos,
                'asientos_ocupados': ocupados,
                'asientos_reservados': reservados,
                'asientos_libres': max(0, libres),
                'porcentaje_ocupacion': viaje.porcentaje_ocupacion,
                'paradas': paradas,
                'ubicacion': {
                    'lat': float(ubicacion.latitud),
                    'lng': float(ubicacion.longitud),
                    'velocidad': float(ubicacion.velocidad_kmh) if ubicacion.velocidad_kmh else 0,
                    'heading': float(ubicacion.heading) if ubicacion.heading else 0,
                } if ubicacion else None,
            }
            data.append(viaje_data)

        return JsonResponse({'viajes': data, 'total': len(data)})


def asegurar_usuarios():
    try:
        from django.contrib.auth.models import User
        from users.models import Persona
        from django.utils import timezone
        from operations.models import Viaje

        # Asegurar Ivan (cliente)
        u_ivan, created = User.objects.get_or_create(username='Ivan')
        if created or not u_ivan.check_password('123'):
            u_ivan.set_password('123')
            u_ivan.save()
        p_ivan, _ = Persona.objects.get_or_create(
            cedula='9999991',
            defaults={
                'user': u_ivan,
                'nombre': 'Ivan',
                'apellido': 'Cliente',
                'telefono': '0981111111',
                'es_cliente': True
            }
        )
        if p_ivan.user != u_ivan:
            p_ivan.user = u_ivan
            p_ivan.save()
        if not p_ivan.es_cliente:
            p_ivan.es_cliente = True
            p_ivan.save()

        # Asegurar JorgeIrala (ayudante/chofer)
        u_jorge, created = User.objects.get_or_create(username='JorgeIrala')
        if created or not u_jorge.check_password('jorge123'):
            u_jorge.set_password('jorge123')
            u_jorge.save()
        p_jorge, _ = Persona.objects.get_or_create(
            cedula='9999992',
            defaults={
                'user': u_jorge,
                'nombre': 'Jorge',
                'apellido': 'Irala',
                'telefono': '0981222222',
                'es_ayudante': True,
                'es_chofer': True
            }
        )
        if p_jorge.user != u_jorge:
            p_jorge.user = u_jorge
            p_jorge.save()
        if not p_jorge.es_ayudante or not p_jorge.es_chofer:
            p_jorge.es_ayudante = True
            p_jorge.es_chofer = True
            p_jorge.save()

        # Asignar JorgeIrala a los viajes en curso de hoy
        hoy = timezone.localtime(timezone.now()).date()
        for viaje in Viaje.objects.filter(estado='en_curso', fecha_viaje=hoy):
            if viaje.chofer != p_jorge and not viaje.ayudantes.filter(pk=p_jorge.pk).exists():
                viaje.ayudantes.add(p_jorge)
    except Exception:
        pass


class RastreoPublicoView(LoginRequiredMixin, TemplateView):

    """Vista del mapa para clientes (público interno)."""
    template_name = 'users/rastreo_publico.html'

    def get_context_data(self, **kwargs):
        asegurar_usuarios()
        context = super().get_context_data(**kwargs)
        hoy = timezone.localtime(timezone.now()).date()
        viajes_en_curso = Viaje.objects.filter(estado='en_curso', fecha_viaje=hoy)
        context['viajes_en_curso'] = viajes_en_curso
        context['total_en_curso'] = viajes_en_curso.count()
        context['viaje_id_focus'] = self.request.GET.get('viaje_id')
        return context


class APIViajesPublicosView(LoginRequiredMixin, View):
    """API JSON para clientes. Oculta datos sensibles y calcula ETAs."""

    def get(self, request):
        asegurar_usuarios()
        import math
        def calcular_km(lat1, lon1, lat2, lon2):
            R = 6371.0
            phi1, phi2 = math.radians(lat1), math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlambda = math.radians(lon2 - lon1)
            a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
            return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        hoy = timezone.localtime(timezone.now()).date()
        viajes_en_curso = Viaje.objects.filter(
            estado='en_curso', fecha_viaje=hoy
        ).select_related(
            'itinerario', 'bus', 'horario', 'empresa'
        ).prefetch_related('ayudantes', 'itinerario__detalles__parada__localidad')

        data = []
        for viaje in viajes_en_curso:
            ubicacion = None
            personas = [viaje.chofer] + list(viaje.ayudantes.all())
            for p in personas:
                # Intentar buscar la ubicación específica de este viaje en curso, de lo contrario la activa general
                ub = UbicacionAyudante.objects.filter(persona=p, viaje=viaje).order_by('-timestamp').first()
                if not ub:
                    ub = UbicacionAyudante.objects.filter(persona=p, activo=True).first()
                if ub:
                    ubicacion = ub
                    break

            pasajes_activos = viaje.pasajes.filter(
                estado__in=['vendido', 'reservado', 'abordado']
            ).values('asiento_id').distinct().count()
            asientos_libres = viaje.bus.capacidad_asientos - pasajes_activos

            detalles = viaje.itinerario.detalles.select_related('parada', 'parada__localidad').order_by('orden')
            paradas = []
            proxima_parada = None
            eta_minutos = None

            for d in detalles:
                # Auto-fix coordenadas para paradas principales sin datos GPS
                if not d.parada.latitud_gps or not d.parada.longitud_gps:
                    coords_map = {
                        'asunci': ('-25.312918', '-57.564998'),
                        'san lorenzo': ('-25.3396', '-57.5097'),
                        'capiat': ('-25.3615', '-57.4339'),
                        'itaugu': ('-25.3854', '-57.3414'),
                        'ypacara': ('-25.3995', '-57.2831'),
                        'caacup': ('-25.3872', '-57.1420'),
                        'eusebio': ('-25.3721', '-56.9634'),
                        'san jos': ('-25.4054', '-56.5401'),
                        'coronel oviedo': ('-25.4443', '-56.4428'),
                        'oviedo': ('-25.4443', '-56.4428'),
                        'aguapety': ('-25.5794', '-56.4542'),
                        'caaguaz': ('-25.452684', '-56.015243'),
                        'caazap': ('-26.1966', '-56.3679'),
                        'nepomuceno': ('-26.1078', '-55.9411'),
                        'yuty': ('-26.6194', '-56.2503'),
                        'santa rosa del mi': ('-26.8892', '-56.8544'),
                        'santa rosa': ('-26.8892', '-56.8544'),
                        'coronel bogado': ('-27.1798', '-56.2581'),
                        'bogado': ('-27.1798', '-56.2581'),
                        'obligado': ('-27.2617', '-55.8417'),
                        'fram': ('-27.0022', '-55.9739'),
                        'encarnaci': ('-27.3358', '-55.8680'),
                        'mbocayaty': ('-25.7289', '-56.4116'),
                        'mbocajaty': ('-25.7289', '-56.4116'),
                        'villarrica': ('-25.779770', '-56.444738'),
                        'cde': ('-25.5097', '-54.6111'),
                        'ciudad del este': ('-25.5097', '-54.6111'),
                    }
                    nombre_parada = d.parada.nombre.lower()
                    if d.parada.localidad:
                        nombre_parada += ' ' + d.parada.localidad.nombre.lower()
                    for key, (lat, lng) in coords_map.items():
                        if key in nombre_parada:
                            d.parada.latitud_gps = lat
                            d.parada.longitud_gps = lng
                            d.parada.save()
                            break

                p_data = {
                    'nombre': d.parada.nombre,
                    'orden': d.orden,
                    'lat': float(d.parada.latitud_gps) if d.parada.latitud_gps else None,
                    'lng': float(d.parada.longitud_gps) if d.parada.longitud_gps else None,
                }
                paradas.append(p_data)

            # Calcular próxima parada basada en la ubicación real del bus
            if ubicacion and paradas:
                # Filtrar paradas con coordenadas válidas
                paradas_validas = [p for p in paradas if p['lat'] is not None and p['lng'] is not None]
                if paradas_validas:
                    bus_lat = float(ubicacion.latitud)
                    bus_lng = float(ubicacion.longitud)
                    
                    # 1. Calcular distancia del bus a cada parada
                    distancias = []
                    for p in paradas_validas:
                        d_bus = calcular_km(bus_lat, bus_lng, p['lat'], p['lng'])
                        distancias.append(d_bus)
                    
                    # 2. Verificar si está muy cerca de alguna parada (<= 0.5 km)
                    cerca_idx = None
                    for idx, d_bus in enumerate(distancias):
                        if d_bus <= 0.5:
                            cerca_idx = idx
                            break
                    
                    if cerca_idx is not None:
                        # Si está en la parada final, ya llegó
                        if cerca_idx == len(paradas_validas) - 1:
                            proxima_parada = paradas_validas[cerca_idx]['nombre']
                            eta_minutos = 0
                        else:
                            # Si está en una parada intermedia, la próxima es la siguiente
                            proxima_parada = paradas_validas[cerca_idx + 1]['nombre']
                            dist_next = distancias[cerca_idx + 1]
                            velocidad = float(ubicacion.velocidad_kmh) if ubicacion.velocidad_kmh and ubicacion.velocidad_kmh > 10 else 40
                            eta_minutos = math.ceil((dist_next / velocidad) * 60)
                    else:
                        # 3. Si no está cerca de ninguna parada, encontrar el segmento activo
                        # calculando el score para cada segmento consecutivo P_j -> P_{j+1}
                        if len(paradas_validas) >= 2:
                            best_segment_idx = 0
                            min_score = float('inf')
                            
                            for j in range(len(paradas_validas) - 1):
                                p_j = paradas_validas[j]
                                p_next = paradas_validas[j+1]
                                d_segment = calcular_km(p_j['lat'], p_j['lng'], p_next['lat'], p_next['lng'])
                                d_to_j = distancias[j]
                                d_to_next = distancias[j+1]
                                
                                # score = d_to_j + d_to_next - d_segment
                                score = d_to_j + d_to_next - d_segment
                                if score < min_score:
                                    min_score = score
                                    best_segment_idx = j
                            
                            # El bus está entre best_segment_idx y best_segment_idx + 1,
                            # por lo que la próxima parada es best_segment_idx + 1
                            next_p = paradas_validas[best_segment_idx + 1]
                            proxima_parada = next_p['nombre']
                            dist_next = distancias[best_segment_idx + 1]
                            velocidad = float(ubicacion.velocidad_kmh) if ubicacion.velocidad_kmh and ubicacion.velocidad_kmh > 10 else 40
                            eta_minutos = math.ceil((dist_next / velocidad) * 60)
                        else:
                            # Fallback si solo hay una parada con coords
                            proxima_parada = paradas_validas[0]['nombre']
                            eta_minutos = math.ceil((distancias[0] / 40) * 60)

            viaje_data = {
                'id': viaje.pk,
                'itinerario': viaje.itinerario.nombre,
                'empresa': viaje.empresa.nombre if viaje.empresa else '',
                'bus_placa': viaje.bus.placa,
                'hora_salida': viaje.horario.hora_salida.strftime('%H:%M') if viaje.horario else '--:--',
                'asientos_libres': asientos_libres,
                'asientos_ocupados': pasajes_activos,
                'asientos_totales': viaje.bus.capacidad_asientos,
                'proxima_parada': proxima_parada,
                'eta': eta_minutos,
                'paradas': paradas,
                'ubicacion': {
                    'lat': float(ubicacion.latitud),
                    'lng': float(ubicacion.longitud),
                    'velocidad': float(ubicacion.velocidad_kmh) if ubicacion.velocidad_kmh else 0,
                    'heading': float(ubicacion.heading) if ubicacion.heading else 0,
                } if ubicacion else None,
            }
            data.append(viaje_data)

        return JsonResponse({'viajes': data, 'total': len(data)})



class APIActualizarUbicacionView(LoginRequiredMixin, View):
    """API para que los ayudantes/choferes actualicen su ubicación GPS."""

    def post(self, request):
        import json
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)

        lat = body.get('latitud')
        lng = body.get('longitud')
        velocidad = body.get('velocidad')
        heading = body.get('heading')

        if lat is None or lng is None:
            return JsonResponse({'error': 'latitud y longitud son requeridos'}, status=400)

        persona = getattr(request.user, 'persona', None)
        if not persona:
            return JsonResponse({'error': 'Usuario sin perfil persona'}, status=403)

        if not (persona.es_ayudante or persona.es_chofer):
            return JsonResponse({'error': 'No autorizado para enviar ubicación'}, status=403)

        # Buscar viaje en curso asignado a esta persona
        hoy = timezone.localtime(timezone.now()).date()
        viaje_actual = None

        # Primero buscar como chofer
        viaje_como_chofer = Viaje.objects.filter(
            chofer=persona, estado='en_curso', fecha_viaje=hoy
        ).first()
        if viaje_como_chofer:
            viaje_actual = viaje_como_chofer
        else:
            # Buscar como ayudante
            viaje_como_ayudante = Viaje.objects.filter(
                ayudantes=persona, estado='en_curso', fecha_viaje=hoy
            ).first()
            if viaje_como_ayudante:
                viaje_actual = viaje_como_ayudante

        try:
            # Convertir a Decimal manejando posibles valores nulos o floats
            from decimal import Decimal
            
            lat_str = str(lat) if lat is not None else '0'
            lng_str = str(lng) if lng is not None else '0'
            vel_str = str(velocidad) if velocidad is not None else '0'
            head_str = str(heading) if heading is not None else '0'
            
            # Limitar decimales para evitar "decimal out of range"
            lat_dec = round(Decimal(lat_str), 6)
            lng_dec = round(Decimal(lng_str), 6)
            vel_dec = round(Decimal(vel_str), 2)
            head_dec = round(Decimal(head_str), 2)
            
            # Actualizar o crear ubicación
            ub, created = UbicacionAyudante.objects.update_or_create(
                persona=persona,
                activo=True,
                defaults={
                    'latitud': lat_dec,
                    'longitud': lng_dec,
                    'velocidad_kmh': vel_dec,
                    'heading': head_dec,
                    'viaje': viaje_actual,
                }
            )
        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            with open('error_ubicacion.txt', 'w') as f:
                f.write(error_msg)
            return JsonResponse({'error': f'Excepción: {str(e)}', 'traceback': error_msg}, status=400)

        return JsonResponse({
            'ok': True,
            'viaje_id': viaje_actual.pk if viaje_actual else None,
            'timestamp': ub.timestamp.isoformat(),
        })


class APIDesactivarUbicacionView(LoginRequiredMixin, View):
    """Desactiva la ubicación cuando el ayudante cierra sesión o sale."""

    def post(self, request):
        persona = getattr(request.user, 'persona', None)
        if persona:
            UbicacionAyudante.objects.filter(persona=persona, activo=True).update(activo=False)
        return JsonResponse({'ok': True})


# =============================================================================
# RESERVAS DE PASAJES PARA CLIENTES
# =============================================================================

class BuscarViajesClienteView(LoginRequiredMixin, TemplateView):
    """Vista para que el cliente busque viajes disponibles."""
    template_name = 'users/buscar_viajes.html'
    
    def get(self, request, *args, **kwargs):
        # Limpiar reservas expiradas antes de mostrar resultados
        from .utils import limpiar_reservas_expiradas
        limpiar_reservas_expiradas()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from django.db.models import Q, F, Subquery, OuterRef
        context = super().get_context_data(**kwargs)
        ahora = timezone.localtime(timezone.now())
        hoy = ahora.date()
        hora_actual = ahora.time()

        # Itinerarios activos (para el selector)
        context['itinerarios'] = Itinerario.objects.filter(activo=True).order_by('nombre')

        # Obtener filtros
        itinerario_id = self.request.GET.get('itinerario')
        origen_id = self.request.GET.get('origen_id')
        destino_id = self.request.GET.get('destino_id')
        origen_text = self.request.GET.get('origen_text', '').strip()
        destino_text = self.request.GET.get('destino_text', '').strip()
        fecha = self.request.GET.get('fecha')

        # Determinar si se ha realizado una búsqueda activa
        ha_buscado = any([itinerario_id, origen_id, destino_id, origen_text, destino_text, fecha])
        context['ha_buscado'] = ha_buscado

        if not ha_buscado:
            # Si no ha buscado, retornar lista vacía y terminar
            context['viajes'] = []
            context['viajes_count'] = 0
            return context

        # Consulta base (solo si hay filtros)
        viajes = Viaje.objects.filter(
            Q(fecha_viaje__gt=hoy) | 
            Q(fecha_viaje=hoy, horario__hora_salida__gt=hora_actual) |
            Q(fecha_viaje=hoy, estado='en_curso'),
            estado__in=['programado', 'en_curso'],
        ).select_related(
            'itinerario', 'bus', 'chofer', 'horario', 'empresa'
        ).prefetch_related('itinerario__detalles__parada__localidad')

        # Procesar identificadores virtuales (text_) del autocompletado
        if origen_id and origen_id.startswith('text_'):
            origen_text = origen_id.replace('text_', '')
            origen_id = ''
        
        if destino_id and destino_id.startswith('text_'):
            destino_text = destino_id.replace('text_', '')
            destino_id = ''


        # Filtrado por tramo (Origen -> Destino) mejorado
        if origen_id and destino_id:
            from itineraries.models import DetalleItinerario
            from fleet.models import Parada
            
            origen_p = Parada.objects.filter(pk=origen_id).first()
            destino_p = Parada.objects.filter(pk=destino_id).first()

            origen_ids = get_similar_paradas_ids(origen_p, origen_id) if origen_p else [origen_id]
            destino_ids = get_similar_paradas_ids(destino_p, destino_id) if destino_p else [destino_id]
            
            # Subconsulta para obtener el orden del origen
            sub_origen = DetalleItinerario.objects.filter(
                itinerario_id=OuterRef('itinerario_id'),
                parada_id__in=origen_ids
            ).values('orden')[:1]
            
            # Subconsulta para obtener el orden del destino
            sub_destino = DetalleItinerario.objects.filter(
                itinerario_id=OuterRef('itinerario_id'),
                parada_id__in=destino_ids
            ).values('orden')[:1]
            
            # Aplicar anotaciones y filtrar por secuencia correcta o por fallback si el itinerario no tiene paradas
            viajes = viajes.annotate(
                orden_o=Subquery(sub_origen),
                orden_d=Subquery(sub_destino)
            ).filter(
                (Q(orden_o__isnull=False) & Q(orden_d__isnull=False) & Q(orden_o__lt=F('orden_d'))) |
                (
                    Q(itinerario__detalles__isnull=True) &
                    Q(itinerario__nombre__icontains=normalize_search(origen_p.nombre if origen_p else origen_text)) &
                    Q(itinerario__nombre__icontains=normalize_search(destino_p.nombre if destino_p else destino_text))
                )
            ).distinct()
            
            context['origen_nombre'] = origen_p.nombre if origen_p else ''
            context['destino_nombre'] = destino_p.nombre if destino_p else ''
            context['origen_id'] = origen_id
            context['destino_id'] = destino_id
        elif origen_id:
            from fleet.models import Parada
            origen_p = Parada.objects.filter(pk=origen_id).first()
            
            origen_ids = get_similar_paradas_ids(origen_p, origen_id) if origen_p else [origen_id]
            viajes = viajes.filter(
                Q(itinerario__detalles__parada_id__in=origen_ids) |
                (
                    Q(itinerario__detalles__isnull=True) &
                    Q(itinerario__nombre__icontains=normalize_search(origen_p.nombre if origen_p else ''))
                )
            ).distinct()
            context['origen_id'] = origen_id
            context['origen_nombre'] = origen_p.nombre if origen_p else ''
        elif destino_id:
            from fleet.models import Parada
            destino_p = Parada.objects.filter(pk=destino_id).first()
            
            destino_ids = get_similar_paradas_ids(destino_p, destino_id) if destino_p else [destino_id]
            viajes = viajes.filter(
                Q(itinerario__detalles__parada_id__in=destino_ids) |
                (
                    Q(itinerario__detalles__isnull=True) &
                    Q(itinerario__nombre__icontains=normalize_search(destino_p.nombre if destino_p else ''))
                )
            ).distinct()
            context['destino_id'] = destino_id
            context['destino_nombre'] = destino_p.nombre if destino_p else ''
            
        # Filtro de respaldo si el usuario escribe texto pero no selecciona parada del autocompletado
        if origen_text and not origen_id:
            viajes = viajes.filter(itinerario__nombre__icontains=normalize_search(origen_text)).distinct()
            context['origen_nombre'] = origen_text
        if destino_text and not destino_id:
            viajes = viajes.filter(itinerario__nombre__icontains=normalize_search(destino_text)).distinct()
            context['destino_nombre'] = destino_text

        if itinerario_id:
            viajes = viajes.filter(itinerario_id=itinerario_id)
            context['itinerario_seleccionado'] = itinerario_id

        if fecha:
            viajes = viajes.filter(fecha_viaje=fecha)
            context['fecha_seleccionada'] = fecha

        # Ordenar y contar
        context['viajes'] = viajes.order_by('fecha_viaje', 'horario__hora_salida')
        context['viajes_count'] = context['viajes'].count()

        # Agregar info de ocupación a cada viaje
        viajes_con_info = []
        for viaje in viajes[:20]:
            pasajes_activos = viaje.pasajes.filter(
                estado__in=['vendido', 'reservado']
            ).values('asiento_id').distinct().count()
            
            viaje_origen_id = ''
            viaje_destino_id = ''
            
            # Use prefetched data and sort in memory
            detalles = list(viaje.itinerario.detalles.all())
            detalles.sort(key=lambda x: x.orden)
            
            # Buscar el mejor origen específico para este itinerario
            if origen_text or origen_id:
                for d in detalles:
                    if origen_id and str(d.parada_id) == str(origen_id):
                        viaje_origen_id = d.parada_id
                        break
                    norm_nombre = normalize_search(d.parada.nombre)
                    norm_loc = normalize_search(d.parada.localidad.nombre if d.parada.localidad else '')
                    search_term = normalize_search(origen_text)
                    if search_term and (search_term in norm_nombre or search_term in norm_loc or norm_nombre in search_term or norm_loc in search_term):
                        viaje_origen_id = d.parada_id
                        break
                        
            # Buscar el mejor destino específico para este itinerario
            if destino_text or destino_id:
                detalles_rev = list(reversed(detalles))
                for d in detalles_rev:
                    if destino_id and str(d.parada_id) == str(destino_id):
                        viaje_destino_id = d.parada_id
                        break
                    norm_nombre = normalize_search(d.parada.nombre)
                    norm_loc = normalize_search(d.parada.localidad.nombre if d.parada.localidad else '')
                    search_term = normalize_search(destino_text)
                    if search_term and (search_term in norm_nombre or search_term in norm_loc or norm_nombre in search_term or norm_loc in search_term):
                        viaje_destino_id = d.parada_id
                        break

            hora_estimada_origen = None
            if viaje_origen_id and viaje.horario:
                detalle = next((d for d in detalles if str(d.parada_id) == str(viaje_origen_id)), None)
                if detalle:
                    hora_estimada_origen = detalle.hora_estimada(viaje.horario.hora_salida)

            viajes_con_info.append({
                'viaje': viaje,
                'asientos_libres': viaje.bus.capacidad_asientos - pasajes_activos,
                'asientos_total': viaje.bus.capacidad_asientos,
                'porcentaje_ocupacion': viaje.porcentaje_ocupacion,
                'origen_id': viaje_origen_id,
                'destino_id': viaje_destino_id,
                'hora_estimada_origen': hora_estimada_origen,
            })

        context['viajes'] = viajes_con_info
        return context


class ReservarPasajeView(LoginRequiredMixin, TemplateView):
    """Vista de reserva de pasaje para clientes con selector gráfico de asientos."""
    template_name = 'users/reservar_pasaje.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        viaje_pk = self.kwargs.get('viaje_pk')
        viaje = get_object_or_404(
            Viaje.objects.select_related('itinerario', 'bus', 'horario', 'empresa', 'chofer'),
            pk=viaje_pk
        )
        context['viaje'] = viaje

        # Paradas del itinerario en orden
        detalles = list(viaje.itinerario.detalles.select_related(
            'parada', 'parada__localidad'
        ).order_by('orden'))

        # Calcular hora estimada de llegada para cada parada
        for detalle in detalles:
            if viaje.horario and viaje.horario.hora_salida:
                from datetime import datetime, timedelta
                dt = datetime.combine(viaje.fecha_viaje, viaje.horario.hora_salida)
                dt += timedelta(minutes=detalle.minutos_desde_origen or 0)
                detalle.hora_llegada_estimada = dt.strftime("%H:%M hs")
            else:
                detalle.hora_llegada_estimada = "--:--"
        context['detalles_itinerario'] = detalles

        # Todos los asientos del bus
        asientos = viaje.bus.asientos.all().order_by('piso', 'numero_asiento')
        context['asientos'] = asientos

        # Origen y destino sugeridos (desde búsqueda)
        context['initial_origen_id'] = self.request.GET.get('origen')
        context['initial_destino_id'] = self.request.GET.get('destino')

        # Obtener la última ubicación del bus/chofer/ayudante para la advertencia de proximidad
        bus_lat = None
        bus_lng = None
        personas = [viaje.chofer] + list(viaje.ayudantes.all())
        for p in personas:
            if not p:
                continue
            ub = UbicacionAyudante.objects.filter(persona=p, viaje=viaje).order_by('-timestamp').first()
            if not ub:
                ub = UbicacionAyudante.objects.filter(persona=p, activo=True).first()
            if ub:
                bus_lat = float(ub.latitud)
                bus_lng = float(ub.longitud)
                break
        # Convert to string to avoid localization comma in Javascript
        context['bus_lat'] = str(bus_lat).replace(',', '.') if bus_lat is not None else None
        context['bus_lng'] = str(bus_lng).replace(',', '.') if bus_lng is not None else None

        # Verificar si ya tiene una reserva previa (para mostrar alerta al cargar)
        persona = getattr(self.request.user, 'persona', None)
        if persona:
            # 1. Misma reserva específica
            tiene_misma = Pasaje.objects.filter(
                viaje=viaje,
                pasajero=persona,
                estado__in=['reservado', 'vendido', 'abordado']
            ).exists()
            
            # 2. Otras reservas el mismo día (otra empresa o viaje)
            otras_reservas = Pasaje.objects.filter(
                viaje__fecha_viaje=viaje.fecha_viaje,
                pasajero=persona,
                estado__in=['reservado', 'vendido', 'abordado']
            ).exclude(viaje=viaje).select_related('viaje__empresa', 'viaje__itinerario')
            
            empresa_actual = viaje.empresa.nombre if viaje.empresa else (viaje.bus.empresa.nombre if viaje.bus.empresa else "la empresa")
            
            if tiene_misma:
                context['tiene_reserva_previa'] = True
                context['reserva_previa_msg'] = f"Usted ya cuenta con una reserva activa para este viaje con {empresa_actual}."
            elif otras_reservas.exists():
                r_otra = otras_reservas.first()
                empresa_otra = r_otra.viaje.empresa.nombre if r_otra.viaje.empresa else "otra empresa"
                context['tiene_reserva_previa'] = True
                context['reserva_previa_msg'] = (
                    f"¡Atención! Usted ya tiene una reserva para el día {viaje.fecha_viaje.strftime('%d/%m/%Y')} "
                    f"con la empresa {empresa_otra}. ¿Está seguro de que desea reservar también con {empresa_actual}?"
                )

        return context


class APIAsientosSegmentoView(LoginRequiredMixin, View):
    """API que devuelve la disponibilidad de asientos para un segmento origen→destino."""

    def get(self, request, viaje_pk):
        viaje = get_object_or_404(Viaje, pk=viaje_pk)
        parada_origen_id = request.GET.get('origen')
        parada_destino_id = request.GET.get('destino')

        if not parada_origen_id or not parada_destino_id:
            return JsonResponse({'error': 'origen y destino requeridos'}, status=400)

        try:
            parada_origen = Parada.objects.get(pk=parada_origen_id)
            parada_destino = Parada.objects.get(pk=parada_destino_id)
        except Parada.DoesNotExist:
            return JsonResponse({'error': 'Parada no encontrada'}, status=404)

        from .utils import obtener_orden_parada, obtener_asientos_disponibles, obtener_mapa_ocupacion

        orden_origen = obtener_orden_parada(viaje, parada_origen)
        orden_destino = obtener_orden_parada(viaje, parada_destino)

        if orden_origen is None or orden_destino is None:
            return JsonResponse({'error': 'Las paradas no pertenecen al itinerario'}, status=400)

        if orden_origen >= orden_destino:
            return JsonResponse({'error': 'El origen debe estar antes del destino'}, status=400)

        # Asientos disponibles para el segmento
        asientos_disponibles = obtener_asientos_disponibles(viaje, orden_origen, orden_destino)
        asientos_disponibles_ids = set(asientos_disponibles.values_list('id', flat=True))

        # Todos los asientos del bus (usando distinct por si acaso)
        todos = viaje.bus.asientos.all().order_by('piso', 'numero_asiento').distinct()

        # Mapa de ocupación
        mapa_ocupacion = obtener_mapa_ocupacion(viaje)

        # Precio
        precio = None
        # 1. Intento exacto: Por paradas directas
        precio_alternativo = Precio.objects.filter(
            origen=parada_origen,
            destino=parada_destino
        ).first()

        if precio_alternativo:
            precio = float(precio_alternativo.precio)
        else:
            # 2. Intento por NOMBRES (cuando hay paradas duplicadas para distintas empresas)
            precio_por_nombre = Precio.objects.filter(
                origen__nombre=parada_origen.nombre,
                destino__nombre=parada_destino.nombre
            ).first()
            if precio_por_nombre:
                precio = float(precio_por_nombre.precio)
            else:
                # 3. Intento por NOMBRES DE LOCALIDAD (Exacto)
                precio_localidad = Precio.objects.filter(
                    origen__localidad__nombre__iexact=parada_origen.localidad.nombre,
                    destino__localidad__nombre__iexact=parada_destino.localidad.nombre
                ).first()
                if precio_localidad:
                    precio = float(precio_localidad.precio)
                else:
                    # 4. Intento SUPER FUZZY (Parcial)
                    o_search = parada_origen.localidad.nombre.replace('Terminal', '').replace('de', '').strip()
                    d_search = parada_destino.localidad.nombre.replace('Terminal', '').replace('de', '').strip()

                    if len(o_search) > 3 and len(d_search) > 3:
                        precio_fuzzy = Precio.objects.filter(
                            Q(origen__localidad__nombre__icontains=o_search) | Q(origen__nombre__icontains=o_search),
                            Q(destino__localidad__nombre__icontains=d_search) | Q(destino__nombre__icontains=d_search)
                        ).first()
                        if precio_fuzzy:
                            precio = float(precio_fuzzy.precio)

        # 5. Intento por SUMA DE SEGMENTOS (Multi-hop)
        # Si aún no hay precio, intentamos sumar los tramos definidos en el itinerario
        if precio is None and orden_origen is not None and orden_destino is not None:
            detalles_ruta = list(DetalleItinerario.objects.filter(
                itinerario=viaje.itinerario,
                orden__gte=orden_origen,
                orden__lte=orden_destino
            ).order_by('orden').select_related('parada'))

            if len(detalles_ruta) >= 2:
                total_acumulado = 0
                idx_actual = 0
                error_ruta = False
                
                while idx_actual < len(detalles_ruta) - 1:
                    p_orig = detalles_ruta[idx_actual].parada
                    hallado_tramo = False
                    
                    # Intentamos buscar el tramo más largo posible desde la parada actual
                    for idx_dest in range(len(detalles_ruta) - 1, idx_actual, -1):
                        p_dest = detalles_ruta[idx_dest].parada
                        
                        # Buscar precio para este tramo intermedio
                        # Usamos la misma lógica de lookup (ID, luego Nombre)
                        pr_tramo = Precio.objects.filter(
                            Q(origen=p_orig, destino=p_dest) |
                            Q(origen__nombre=p_orig.nombre, destino__nombre=p_dest.nombre)
                        ).first()
                        
                        if pr_tramo:
                            total_acumulado += float(pr_tramo.precio)
                            idx_actual = idx_dest # Saltamos hasta el destino encontrado
                            hallado_tramo = True
                            break
                    
                    if not hallado_tramo:
                        error_ruta = True
                        break
                
                if not error_ruta and total_acumulado > 0:
                    precio = total_acumulado

        asientos_data = []
        for asiento in todos:
            info = {
                'id': asiento.pk,
                'numero': asiento.numero_asiento,
                'piso': asiento.piso,
                'tipo': asiento.get_tipo_asiento_display(),
                'disponible': asiento.pk in asientos_disponibles_ids,
            }
            # Info de ocupación para asientos no disponibles
            if asiento.pk in mapa_ocupacion:
                ocupaciones = mapa_ocupacion[asiento.pk]
                info['ocupaciones'] = []
                for oc in ocupaciones:
                    info['ocupaciones'].append({
                        'pasajero': oc['pasajero'],
                        'desde': oc['parada_origen'],
                        'hasta': oc['parada_destino'],
                        'orden_origen': oc['orden_origen'],
                        'orden_destino': oc['orden_destino'],
                        'estado': oc['estado'],
                        'vendedor_id': oc.get('vendedor_id'),
                    })
            asientos_data.append(info)

        # Determinar si el usuario es ayudante/chofer (no agente ni admin)
        # para bloquear asientos ocupados en el frontend
        persona_actual = getattr(request.user, 'persona', None)
        es_ayudante = bool(
            persona_actual and 
            (persona_actual.es_ayudante or persona_actual.es_chofer) and 
            not persona_actual.es_agente and 
            not request.user.is_superuser
        )

        return JsonResponse({
            'asientos': asientos_data,
            'disponibles': len(asientos_disponibles_ids),
            'total': todos.count(),
            'precio': precio,
            'orden_origen': orden_origen,
            'orden_destino': orden_destino,
            'es_ayudante': es_ayudante,
            'usuario_actual_id': request.user.id,
        })


class CrearReservaClienteView(LoginRequiredMixin, View):
    """Crea una reserva de pasaje para un cliente. Le da 30 min para pagar."""

    def post(self, request, viaje_pk):
        import json
        from django.db import transaction

        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)

        with transaction.atomic():
            # Lock the viaje row to serialize bookings and prevent concurrent race conditions
            try:
                viaje = Viaje.objects.select_for_update().get(pk=viaje_pk)
            except Viaje.DoesNotExist:
                return JsonResponse({'error': 'Viaje no encontrado'}, status=404)

        if viaje.reservas_bloqueadas:
            return JsonResponse({'error': 'Este viaje ya no admite nuevas reservas (bus lleno).'}, status=403)

        asiento_ids = body.get('asiento_ids', [])
        # Caso retrocompatible
        if not asiento_ids and body.get('asiento_id'):
            asiento_ids = [body.get('asiento_id')]

        parada_origen_id = body.get('parada_origen_id')
        parada_destino_id = body.get('parada_destino_id')

        if not all([asiento_ids, parada_origen_id, parada_destino_id]):
            return JsonResponse({
                'error': 'Asiento, parada origen y parada destino son requeridos'
            }, status=400)

        persona = getattr(request.user, 'persona', None)
        if not persona:
            return JsonResponse({'error': 'Usuario sin perfil persona'}, status=403)

        # Verificar si ya tiene una reserva para este viaje o para el mismo día
        confirmar = body.get('confirmar', False)
        if not confirmar:
            # 1. Misma reserva específica
            tiene_misma = Pasaje.objects.filter(
                viaje=viaje,
                pasajero=persona,
                estado__in=['reservado', 'vendido', 'abordado']
            ).exists()
            
            # 2. Otras reservas el mismo día
            otras_reservas = Pasaje.objects.filter(
                viaje__fecha_viaje=viaje.fecha_viaje,
                pasajero=persona,
                estado__in=['reservado', 'vendido', 'abordado']
            ).exclude(viaje=viaje).select_related('viaje__empresa')

            empresa_actual = viaje.empresa.nombre if viaje.empresa else (viaje.bus.empresa.nombre if viaje.bus.empresa else "la empresa")
            
            if tiene_misma:
                return JsonResponse({
                    'warning': f'Usted ya cuenta con una reserva o pasaje activo para este viaje con {empresa_actual}.',
                    'confirmacion_requerida': True
                })
            elif otras_reservas.exists():
                r_otra = otras_reservas.first()
                empresa_otra = r_otra.viaje.empresa.nombre if r_otra.viaje.empresa else "otra empresa"
                return JsonResponse({
                    'warning': (
                        f'Usted ya tiene una reserva para este mismo día ({viaje.fecha_viaje.strftime("%d/%m/%Y")}) '
                        f'con la empresa {empresa_otra}.'
                    ),
                    'confirmacion_requerida': True
                })

        # Validar paradas
        from .utils import obtener_orden_parada, asiento_disponible_en_tramo
        from fleet.models import Asiento

        try:
            parada_origen = Parada.objects.get(pk=parada_origen_id)
            parada_destino = Parada.objects.get(pk=parada_destino_id)
        except Parada.DoesNotExist:
            return JsonResponse({'error': 'Parada no encontrada'}, status=404)

        orden_origen = obtener_orden_parada(viaje, parada_origen)
        orden_destino = obtener_orden_parada(viaje, parada_destino)

        if orden_origen is None or orden_destino is None:
            return JsonResponse({'error': 'Paradas no pertenecen al itinerario'}, status=400)

        if orden_origen >= orden_destino:
            return JsonResponse({'error': 'Origen debe ser anterior al destino'}, status=400)

        # Validar disponibilidad de TODOS los asientos solicitados
        asientos = []
        for a_id in asiento_ids:
            try:
                asiento = Asiento.objects.get(pk=a_id, bus=viaje.bus)
                if not asiento_disponible_en_tramo(viaje, asiento, orden_origen, orden_destino):
                    return JsonResponse({
                        'error': f'El asiento {asiento.numero_asiento} ya no está disponible en ese tramo'
                    }, status=409)
                asientos.append(asiento)
            except Asiento.DoesNotExist:
                 return JsonResponse({'error': f'Asiento ID {a_id} no encontrado'}, status=404)

        # Calcular precio (Lookup flexible con fallbacks)
        precio = None
        # 1. Intento por paradas directas
        precio_alternativo = Precio.objects.filter(
            origen=parada_origen,
            destino=parada_destino
        ).first()
        if precio_alternativo:
            precio = precio_alternativo.precio
        else:
            # 2. Intento por NOMBRES
            precio_por_nombre = Precio.objects.filter(
                origen__nombre=parada_origen.nombre,
                destino__nombre=parada_destino.nombre
            ).first()
            if precio_por_nombre:
                precio = precio_por_nombre.precio
            else:
                # 3. Intento por LOCALIDADES
                precio_localidad = Precio.objects.filter(
                    origen__localidad__nombre__iexact=parada_origen.localidad.nombre,
                    destino__localidad__nombre__iexact=parada_destino.localidad.nombre
                ).first()
                if precio_localidad:
                    precio = precio_localidad.precio
                else:
                    # 4. Intento Fuzzy
                    o_search = parada_origen.localidad.nombre.replace('Terminal', '').replace('de', '').strip()
                    d_search = parada_destino.localidad.nombre.replace('Terminal', '').replace('de', '').strip()
                    if len(o_search) > 3 and len(d_search) > 3:
                        precio_fuzzy = Precio.objects.filter(
                            Q(origen__localidad__nombre__icontains=o_search) | Q(origen__nombre__icontains=o_search),
                            Q(destino__localidad__nombre__icontains=d_search) | Q(destino__nombre__icontains=d_search)
                        ).first()
                        if precio_fuzzy:
                            precio = precio_fuzzy.precio

        if precio is None:
            return JsonResponse({
                'error': 'No hay precio definido para ese tramo. Contacte a la empresa.'
            }, status=400)

        from datetime import datetime, timedelta
        
        detalle_origen = viaje.itinerario.detalles.filter(parada=parada_origen).first()
        minutos_origen = detalle_origen.minutos_desde_origen if detalle_origen and detalle_origen.minutos_desde_origen else 0

        if viaje.horario:
            fecha_hora_salida_origen = timezone.make_aware(
                datetime.combine(viaje.fecha_viaje, viaje.horario.hora_salida)
            )
            fecha_hora_llegada_parada = fecha_hora_salida_origen + timedelta(minutes=minutos_origen)
            limite_pago = fecha_hora_llegada_parada - timedelta(minutes=30)
            hora_salida_str = viaje.horario.hora_salida.strftime("%H:%M")
        else:
            fecha_hora_llegada_parada = timezone.now() + timedelta(minutes=minutos_origen)
            limite_pago = fecha_hora_llegada_parada - timedelta(minutes=30)
            hora_salida_str = "--:--"
            
        if timezone.now() >= limite_pago:
            return JsonResponse({
                'error': 'Ya no es posible realizar reservas, el plazo (hasta 30 min antes de la llegada del bus a su parada) ha concluido.'
            }, status=400)

        # Manejar datos de facturación (cliente pagador opcional)
        facturacion_data = body.get('facturacion', {})
        cliente_pagador = None
        if facturacion_data.get('usar_otros_datos'):
            ruc_ci_raw = facturacion_data.get('ruc', '')
            razon_social = facturacion_data.get('nombre', '')
            
            import re
            ruc_ci_clean = re.sub(r'[^0-9]', '', str(ruc_ci_raw))
            
            if ruc_ci_clean and razon_social:
                from users.models import Persona
                try:
                    cliente_pagador = Persona.objects.get(cedula=int(ruc_ci_clean))
                except Persona.DoesNotExist:
                    # Crear nueva persona para facturación
                    parts = razon_social.split(' ', 1)
                    if len(parts) > 1:
                        p_nom, p_ape = parts[0], parts[1]
                    else:
                        p_nom, p_ape = razon_social, '.'
                    cliente_pagador = Persona.objects.create(
                        cedula=int(ruc_ci_clean),
                        nombre=p_nom,
                        apellido=p_ape,
                        es_cliente=True
                    )
                except (ValueError, TypeError):
                    pass

        # Crear reservas
        pasajes = []
        for asiento in asientos:
            pasaje = Pasaje(
                viaje=viaje,
                asiento=asiento,
                pasajero=persona,
                cliente=cliente_pagador,
                parada_origen=parada_origen,
                parada_destino=parada_destino,
                orden_origen=orden_origen,
                orden_destino=orden_destino,
                precio=precio,
                estado='reservado',
                vendedor=request.user,
                fecha_limite_pago=limite_pago,
            )
            pasaje.save()
            pasajes.append(pasaje)

        # Generar data de respuesta (usamos el primer pasaje para la cabecera)
        p_main = pasajes[0]
        codigos = ", ".join([p.codigo for p in pasajes])
        numero_asientos = ", ".join([str(p.asiento.numero_asiento) for p in pasajes])
        precio_total = sum([p.precio for p in pasajes])

        comprobante_url = reverse('operations:pasaje_comprobante', kwargs={'pk': p_main.pk})
        if len(pasajes) > 1:
             # Nota: Se podría crear una vista de comprobante grupal, por ahora permitimos ver el primero
             # y listamos todos los códigos si es necesario.
             pass

        nombre_origen_itinerario = viaje.itinerario.nombre_origen
        hora_llegada_str = fecha_hora_llegada_parada.strftime('%H:%M')
        hora_limite_str = p_main.fecha_limite_pago.strftime('%H:%M')

        return JsonResponse({
            'ok': True,
            'pasaje': {
                'id': p_main.pk,
                'codigo': codigos,
                'descripcion': p_main.descripcion,
                'asiento': numero_asientos,
                'origen': parada_origen.nombre,
                'destino': parada_destino.nombre,
                'cliente_nombre': p_main.cliente.nombre_completo if p_main.cliente else None,
                'precio': float(precio_total),
                'fecha_limite_pago': p_main.fecha_limite_pago.strftime('%d/%m/%Y %H:%M'),
                'estado': 'reservado',
                'comprobante_url': comprobante_url,
                'cantidad': len(pasajes),
            },
            'mensaje': (
                f'¡Reserva confirmada de {len(pasajes)} asiento(s)! Asientos: {numero_asientos}. '
                f'El bus saldrá de {nombre_origen_itinerario} a las {hora_salida_str} hs. '
                f'De acuerdo a los minutos de viaje, su hora estimada de abordaje en {parada_origen.nombre} es a las {hora_llegada_str} hs. '
                f'Por favor, acérquese a su parada hasta 30 minutos antes (Límite: {hora_limite_str} hs) para abonar, '
                f'de lo contrario su reserva se cancela automáticamente y los asientos quedarán libres.'
            )
        })


class PasajeComprobanteView(LoginRequiredMixin, DetailView):
    """Vista simplificada para imprimir el comprobante de reserva."""
    model = Pasaje
    template_name = 'operations/pasaje_comprobante.html'
    context_object_name = 'pasaje'

    def get_queryset(self):
        if self.request.user.is_staff:
            return super().get_queryset()
        persona = getattr(self.request.user, 'persona', None)
        return super().get_queryset().filter(pasajero=persona)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pasaje = self.object
        
        # Calcular hora origen
        detalle_origen = pasaje.viaje.itinerario.detalles.filter(parada=pasaje.parada_origen).first()
        if pasaje.viaje.horario and pasaje.viaje.horario.hora_salida and detalle_origen:
            from datetime import datetime, timedelta
            dt = datetime.combine(pasaje.viaje.fecha_viaje, pasaje.viaje.horario.hora_salida)
            dt += timedelta(minutes=detalle_origen.minutos_desde_origen or 0)
            context['hora_origen'] = dt.strftime("%H:%M")
            
        # Calcular hora destino
        detalle_destino = pasaje.viaje.itinerario.detalles.filter(parada=pasaje.parada_destino).first()
        if pasaje.viaje.horario and pasaje.viaje.horario.hora_salida and detalle_destino:
            from datetime import datetime, timedelta
            dt = datetime.combine(pasaje.viaje.fecha_viaje, pasaje.viaje.horario.hora_salida)
            dt += timedelta(minutes=detalle_destino.minutos_desde_origen or 0)
            context['hora_destino'] = dt.strftime("%H:%M")
            
        return context


class PasajeEnviarCorreoView(LoginRequiredMixin, View):
    """Vista para enviar el comprobante de reserva por correo."""

    def post(self, request, pk):
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings

        pasaje = get_object_or_404(Pasaje, pk=pk)
        persona = getattr(request.user, 'persona', None)

        if not persona or (pasaje.pasajero != persona and not request.user.is_staff):
            return JsonResponse({'error': 'No tiene permiso para realizar esta acción'}, status=403)

        if not persona.email:
            return JsonResponse({'error': 'Su perfil no tiene un correo electrónico registrado'}, status=400)

        # Renderizar mensaje
        mensaje_html = f"""
        Hola {persona.nombre},
        
        Su reserva ha sido confirmada con éxito.
        
        CÓDIGO: {pasaje.codigo}
        ASIENTO: {pasaje.asiento.numero_asiento}
        VIAJE: {pasaje.viaje.itinerario.nombre}
        FECHA: {pasaje.viaje.fecha_viaje.strftime('%d/%m/%Y')} a las {pasaje.viaje.horario.hora_salida.strftime('%H:%M')} HS
        PRECIO: Gs. {int(pasaje.precio)}
        LÍMITE DE PAGO: {pasaje.fecha_limite_pago.strftime('%d/%m/%Y %H:%M')}
        
        Recuerde abonar antes del límite, de lo contrario la reserva será cancelada.
        
        Gracias por viajar con TR4CKING.
        """

        try:
            send_mail(
                subject='Comprobante de Reserva - TR4CKING',
                message=mensaje_html,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[persona.email],
                fail_silently=False,
            )
            return JsonResponse({'ok': True, 'mensaje': f'El comprobante ha sido enviado a {persona.email}'})
        except Exception as e:
            return JsonResponse({'error': f'Error al enviar el correo: {str(e)}'}, status=500)

class APICrearEncomiendaFacturacionView(LoginRequiredMixin, View):
    """API para crear una encomienda rápidamente desde la pantalla de facturación."""

    def post(self, request):
        import json
        from .forms import EncomiendaForm
        
        # El formulario espera un QueryDict o similar, pero podemos pasarle el POST directamente
        form = EncomiendaForm(request.POST)
        
        if form.is_valid():
            encomienda = form.save(commit=False)
            
            # Obtener remitente
            remitente_id = form.cleaned_data.get('remitente_id')
            try:
                remitente = Persona.objects.get(cedula=remitente_id)
            except Persona.DoesNotExist:
                return JsonResponse({'error': 'Remitente no encontrado'}, status=404)
            
            # Obtener o crear destinatario
            cedula_destinatario = form.cleaned_data.get('cedula_destinatario')
            if not cedula_destinatario:
                import random
                while True:
                    cedula_destinatario = str(random.randint(999000000000000, 999999999999999))
                    if not Persona.objects.filter(cedula=cedula_destinatario).exists():
                        break
            
            try:
                destinatario = Persona.objects.get(cedula=cedula_destinatario)
            except Persona.DoesNotExist:
                destinatario = Persona.objects.create(
                    cedula=cedula_destinatario,
                    nombre=form.cleaned_data.get('nombre_destinatario'),
                    apellido=form.cleaned_data.get('apellido_destinatario'),
                    telefono=form.cleaned_data.get('telefono_destinatario')
                )
            
            encomienda.remitente = remitente
            encomienda.destinatario = destinatario
            encomienda.registrador = request.user
            encomienda.save()
            
            return JsonResponse({
                'ok': True,
                'encomienda': {
                    'pk': encomienda.pk,
                    'codigo': encomienda.codigo,
                    'tipo': encomienda.get_tipo_display(),
                    'descripcion': encomienda.descripcion[:30] if encomienda.descripcion else '-',
                    'destino': encomienda.parada_destino.nombre if encomienda.parada_destino else '-',
                    'precio': float(encomienda.precio)
                }
            })
        else:
            # Retornar errores de validación
            errors = {field: error_list[0]['message'] for field, error_list in form.errors.get_json_data().items()}
            return JsonResponse({'error': 'Datos inválidos', 'details': errors}, status=400)


class APIObtenerViajesCompatiblesView(LoginRequiredMixin, View):
    """API que devuelve los viajes que cubren el tramo origen -> destino."""
    def get(self, request):
        origen_id = request.GET.get('origen')
        destino_id = request.GET.get('destino')
        fecha_desde = request.GET.get('fecha_desde')
        fecha_hasta = request.GET.get('fecha_hasta')
        
        from django.utils import timezone
        
        # Obtener fecha y hora local actual
        ahora_local = timezone.localtime(timezone.now())
        hoy = ahora_local.date()
        hora_actual = ahora_local.time()
        
        viajes = Viaje.objects.filter(estado__in=['programado', 'en_curso'])
        
        if fecha_desde:
            viajes = viajes.filter(fecha_viaje__gte=fecha_desde)
        else:
            viajes = viajes.filter(fecha_viaje__gte=hoy)
            
        if fecha_hasta:
            viajes = viajes.filter(fecha_viaje__lte=fecha_hasta)

        if origen_id and destino_id:
            from fleet.models import Parada
            origen_p = Parada.objects.filter(pk=origen_id).first()
            destino_p = Parada.objects.filter(pk=destino_id).first()
    
            origen_ids = get_similar_paradas_ids(origen_p, origen_id) if origen_p else [origen_id]
            destino_ids = get_similar_paradas_ids(destino_p, destino_id) if destino_p else [destino_id]
            
            # 1. Encontrar itinerarios que tengan ambas paradas en el orden correcto
            from itineraries.models import DetalleItinerario
            from django.db.models import OuterRef, Subquery, F
            
            # Subconsulta para obtener el orden del origen para cada itinerario
            sub_origen = DetalleItinerario.objects.filter(
                itinerario_id=OuterRef('itinerario_id'),
                parada_id__in=origen_ids
            ).values('orden')[:1]
            
            # Subconsulta para obtener el orden del destino para cada itinerario
            sub_destino = DetalleItinerario.objects.filter(
                itinerario_id=OuterRef('itinerario_id'),
                parada_id__in=destino_ids
            ).values('orden')[:1]
    
            # Obtener IDs de itinerarios compatibles
            itinerarios_compatibles_ids = DetalleItinerario.objects.annotate(
                orden_o=Subquery(sub_origen),
                orden_d=Subquery(sub_destino)
            ).filter(
                orden_o__isnull=False,
                orden_d__isnull=False,
                orden_o__lt=F('orden_d')
            ).values_list('itinerario_id', flat=True).distinct()
            
            if not itinerarios_compatibles_ids:
                return JsonResponse({'viajes': []})
                
            viajes = viajes.filter(itinerario_id__in=itinerarios_compatibles_ids)
            
        viajes = viajes.select_related('itinerario', 'bus', 'horario', 'empresa').order_by('fecha_viaje', 'horario__hora_salida')
        
        viajes_data = []
        for v in viajes:
            # Filtrado por tiempo
            if v.fecha_viaje < hoy:
                continue
                
            is_today = (v.fecha_viaje == hoy)
            
            if is_today and origen_id and v.horario:
                detalle_origen = v.itinerario.detalles.filter(parada_id__in=origen_ids).first()
                if detalle_origen:
                    hora_estimada_origen = detalle_origen.hora_estimada(v.horario.hora_salida)
                    if hora_estimada_origen < hora_actual:
                        continue
            
            # NOTA: Ya no filtramos por hora_salida < hora_actual para permitir que las sucursales 
            # intermedias puedan ver los viajes en curso aunque ya hayan partido de la ciudad de origen.
            
            # Los viajes de mañana en adelante (v.fecha_viaje > hoy) se muestran siempre
            try:
                hora_str = v.horario.hora_salida.strftime('%H:%M') if v.horario else 'Sin horario'
                
                # Obtener nombre de empresa de forma segura
                if v.empresa:
                    empresa_nombre = v.empresa.nombre
                elif v.bus and v.bus.empresa:
                    empresa_nombre = v.bus.empresa.nombre
                # Determinar el nombre del bus mostrando el número si lo tiene
                bus_info = f"Nº {v.bus.numero_bus} ({v.bus.placa})" if v.bus and v.bus.numero_bus else (v.bus.placa if v.bus else "Sin Bus")
                
                label = f"{v.fecha_viaje.strftime('%d/%m/%Y')} - {empresa_nombre} - {v.itinerario.nombre} - Bus: {bus_info} ({hora_str})"
                viajes_data.append({
                    'id': v.id,
                    'label': label,
                    'fecha': v.fecha_viaje.strftime('%d/%m/%Y'),
                    'hora': hora_str,
                    'empresa': empresa_nombre,
                    'itinerario': v.itinerario.nombre,
                    'bus': bus_info
                })
            except Exception:
                continue
            
        return JsonResponse({'viajes': viajes_data})


class FixCoordsParadasView(LoginRequiredMixin, View):
    """Vista temporal (solo superusuarios) para cargar coordenadas GPS en paradas sin datos."""

    COORDS_MAP = {
        # Gran Asuncion
        'asunci':               (-25.312918, -57.564998),
        'san lorenzo':          (-25.339600, -57.509700),
        'capiat':               (-25.361500, -57.433900),
        'itaugu':               (-25.385400, -57.341400),
        'ypacara':              (-25.399500, -57.283100),
        'caacup':               (-25.387200, -57.142000),
        'eusebio ayala':        (-25.372100, -56.963400),
        'eusebio':              (-25.372100, -56.963400),
        'san jos':              (-25.405400, -56.540100),
        # Coronel Oviedo
        'coronel oviedo':       (-25.444300, -56.442800),
        'oviedo':               (-25.444300, -56.442800),
        # Tramo Oviedo -> Encarnacion
        'caaguaz':              (-25.452684, -56.015243),
        'aguapety':             (-25.579400, -56.454200),
        'juan nepomuceno':      (-26.107800, -55.941100),
        'san juan nepomu':      (-26.107800, -55.941100),
        'nepomuceno':           (-26.107800, -55.941100),
        'caazap':               (-26.196600, -56.367900),
        'yuty':                 (-26.619400, -56.250300),
        'santa rosa del mi':    (-26.889200, -56.854400),
        'santa rosa':           (-26.889200, -56.854400),
        'coronel bogado':       (-27.179800, -56.258100),
        'bogado':               (-27.179800, -56.258100),
        'obligado':             (-27.261700, -55.841700),
        'fram':                 (-27.002200, -55.973900),
        'encarnaci':            (-27.335800, -55.868000),
        # Tramo Este
        'mbocayaty':            (-25.728900, -56.411600),
        'mbocajaty':            (-25.728900, -56.411600),
        'villarrica':           (-25.779770, -56.444738),
        'cde':                  (-25.509700, -54.611100),
        'ciudad del este':      (-25.509700, -54.611100),
        'hernandarias':         (-25.397700, -54.619500),
        'minga guazu':          (-25.480000, -54.730000),
        # Norte
        'concepci':             (-23.412300, -57.434200),
        'pedro juan':           (-22.544700, -55.729100),
        'horqueta':             (-23.344900, -57.055600),
        # Sur / Misiones / Itapua
        'natalio':              (-26.665800, -55.461400),
        'bella vista sur':      (-27.042500, -55.581900),
        'bella vista':          (-27.042500, -55.581900),
        'ayolas':               (-27.372800, -56.897800),
        'san cosme':            (-27.286100, -56.415300),
        'pilar':                (-26.862000, -58.302800),
        'san miguel':           (-26.475800, -57.098100),
        'san juan bautista':    (-26.683000, -57.143000),
        'san ignacio':          (-26.882900, -57.024700),
        'santiago':             (-26.772700, -56.762800),
        'coronel martinez':     (-25.694800, -56.060400),
        # Canindeyu
        'salto del guaira':     (-24.063700, -54.318000),
        'curuguaty':            (-24.510200, -55.710300),
    }

    def get(self, request):
        if not request.user.is_superuser:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("Solo superusuarios.")

        from fleet.models import Parada
        actualizadas = []
        sin_match = []

        qs = Parada.objects.filter(activo=True, latitud_gps__isnull=True)
        for parada in qs:
            texto = parada.nombre.lower()
            if parada.localidad:
                texto += ' ' + parada.localidad.nombre.lower()

            matched = False
            for key, (lat, lng) in self.COORDS_MAP.items():
                if key in texto:
                    parada.latitud_gps = lat
                    parada.longitud_gps = lng
                    parada.save(update_fields=['latitud_gps', 'longitud_gps'])
                    actualizadas.append(f"{parada.nombre} ({parada.localidad}) → ({lat}, {lng})")
                    matched = True
                    break

            if not matched:
                sin_match.append(f"{parada.nombre} ({parada.localidad})")

        html = f"""
        <!DOCTYPE html><html><head><meta charset='utf-8'>
        <title>Fix Coordenadas</title>
        <style>body{{font-family:monospace;padding:20px;}}
        h2{{color:#206bc4;}} .ok{{color:green;}} .warn{{color:orange;}} .box{{background:#f8f9fa;padding:12px;border-radius:6px;margin:8px 0;}}</style>
        </head><body>
        <h2>✅ Coordenadas actualizadas: {len(actualizadas)}</h2>
        {''.join(f'<div class="box ok">✓ {a}</div>' for a in actualizadas) if actualizadas else '<div class="box">Ninguna parada sin coordenadas (o todas ya las tenían).</div>'}
        <h2 style="color:orange;">⚠️ Sin match ({len(sin_match)}) — cargar manualmente en Admin</h2>
        {''.join(f'<div class="box warn">✗ {s}</div>' for s in sin_match) if sin_match else '<div class="box ok">Todas las paradas tienen coordenadas 🎉</div>'}
        <br><a href="/operations/rastreo-mapa/">← Volver al mapa</a>
        </body></html>"""
        from django.http import HttpResponse
        return HttpResponse(html)
