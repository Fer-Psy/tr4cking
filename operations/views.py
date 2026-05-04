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
        hoy = timezone.now().date()
        ahora = timezone.now()
        hace_7_dias = hoy - timedelta(days=7)
        
        # === VIAJES HOY ===
        viajes_hoy = Viaje.objects.filter(fecha_viaje=hoy)
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
        context['encomiendas_hoy'] = encomiendas_hoy.count()
        context['encomiendas_pendientes'] = Encomienda.objects.filter(
            estado__in=['registrado', 'en_transito', 'en_destino']
        ).count()
        
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
            estado='programado'
        ).select_related('itinerario', 'bus', 'chofer').order_by('horario__hora_salida')[:5]
        
        # === VIAJES EN CURSO ===
        context['viajes_activos'] = Viaje.objects.filter(
            estado='en_curso'
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
        viajes_semana = Viaje.objects.filter(fecha_viaje__gte=hace_7_dias)
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
            
        # Verificar viajes para mañana (alerta si faltan)
        mañana = hoy + timedelta(days=1)
        dia_semana_mañana = mañana.weekday()
        
        itinerarios_activos = Itinerario.objects.filter(activo=True)
        horarios_esperados = sum(
            it.horarios.filter(activo=True).count()
            for it in itinerarios_activos if it.opera_en_dia(dia_semana_mañana)
        )
        
        viajes_mañana = Viaje.objects.filter(fecha_viaje=mañana).count()
        
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
        hoy = timezone.now().date()
        ahora = timezone.now()

        if not persona or not (persona.es_ayudante or persona.es_chofer or persona.es_empleado):
            messages.warning(self.request, "No tienes permisos de ayudante o empleado.")
            return context

        # 1. Viaje activo (en curso)
        viaje_activo = Viaje.objects.filter(
            Q(chofer=persona) | Q(ayudantes=persona),
            estado='en_curso',
            fecha_viaje=hoy
        ).select_related('itinerario', 'bus', 'horario').first()

        # Si no hay uno en curso, buscar el próximo programado para hoy
        if not viaje_activo:
            viaje_activo = Viaje.objects.filter(
                Q(chofer=persona) | Q(ayudantes=persona),
                estado='programado',
                fecha_viaje=hoy
            ).select_related('itinerario', 'bus', 'horario').order_by('horario__hora_salida').first()

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
            ).select_related('remitente', 'destinatario', 'parada_destino')

            # Pasajes vendidos recientemente en este viaje
            context['pasajes_recientes'] = Pasaje.objects.filter(
                viaje=viaje_activo,
                estado='vendido'
            ).select_related('pasajero', 'asiento').order_by('-fecha_venta')[:5]

        # 5. Cliente Ocasional (para facturación rápida)
        # Buscamos si existe la persona con CI 4444440
        try:
            cliente_ocasional = Persona.objects.get(cedula=4444440)
        except Persona.DoesNotExist:
            cliente_ocasional = Persona.objects.create(
                cedula=4444440,
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

        # También activar ubicación si no está activa
        if persona:
            UbicacionAyudante.objects.update_or_create(
                persona=persona,
                defaults={'activo': True, 'viaje': viaje}
            )
        
        return JsonResponse({
            'ok': True, 
            'mensaje': '¡Buen viaje! El viaje ahora está en curso y la localización activa.'
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
            queryset = queryset.filter(fecha_viaje__gte=timezone.now().date())
        
        estado = self.request.GET.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)
        
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
            initial['fecha_viaje'] = timezone.now().date()
            
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
            viaje.hora_salida_real = timezone.now().time()
        elif nuevo_estado == 'completado' and not viaje.hora_llegada_real:
            viaje.hora_llegada_real = timezone.now().time()
        
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
    paginate_by = 20
    
    def get_queryset(self):
        from operations.utils import limpiar_reservas_expiradas
        limpiar_reservas_expiradas()
        
        queryset = super().get_queryset().select_related(
            'viaje__itinerario', 'pasajero', 'asiento', 'parada_origen', 'parada_destino'
        )
        
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
                Q(pasajero__apellido__icontains=search)
            )
        
        return queryset.order_by('-fecha_venta')
    
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
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        viaje_pk = self.kwargs.get('viaje_pk')
        if viaje_pk:
            kwargs['viaje'] = get_object_or_404(Viaje, pk=viaje_pk)
        return kwargs
    
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
        pasaje.estado = 'vendido'
        
        # Asignar órdenes de origen/destino para gestión por segmentos
        pasaje.orden_origen = form.cleaned_data.get('orden_origen', 1)
        pasaje.orden_destino = form.cleaned_data.get('orden_destino', 2)
        
        # Obtener precio del itinerario
        try:
            precio_obj = Precio.objects.get(
                itinerario=pasaje.viaje.itinerario,
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
        return redirect('operations:pasaje_detail', pk=pasaje.pk)


class PasajeCancelacionView(LoginRequiredMixin, View):
    """Vista para cancelar un pasaje."""
    
    def get(self, request, pk):
        pasaje = get_object_or_404(Pasaje, pk=pk)
        form = PasajeCancelacionForm()
        return render(request, 'operations/pasaje_cancelacion.html', {
            'pasaje': pasaje,
            'form': form
        })
    
    def post(self, request, pk):
        pasaje = get_object_or_404(Pasaje, pk=pk)
        form = PasajeCancelacionForm(request.POST)
        
        if form.is_valid():
            pasaje.estado = 'cancelado'
            pasaje.fecha_cancelacion = timezone.now()
            pasaje.motivo_cancelacion = form.cleaned_data['motivo']
            pasaje.save()
            
            # Registrar devolución si corresponde
            if form.cleaned_data.get('devolver_dinero'):
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
                messages.success(request, "Pasaje cancelado exitosamente.")
            
            return redirect('operations:pasaje_list')
        
        return render(request, 'operations/pasaje_cancelacion.html', {
            'pasaje': pasaje,
            'form': form
        })


# =============================================================================
# ENCOMIENDAS
# =============================================================================

class EncomiendaListView(LoginRequiredMixin, ListView):
    """Lista de encomiendas."""
    model = Encomienda
    template_name = 'operations/encomienda_list.html'
    context_object_name = 'encomiendas'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'viaje__itinerario', 'remitente', 'destinatario',
            'parada_origen', 'parada_destino'
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


class EncomiendaCreateView(LoginRequiredMixin, CreateView):
    """Registrar una nueva encomienda."""
    model = Encomienda
    form_class = EncomiendaForm
    template_name = 'operations/encomienda_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        viaje_pk = self.kwargs.get('viaje_pk')
        if viaje_pk:
            kwargs['viaje'] = get_object_or_404(Viaje, pk=viaje_pk)
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
            # Crear nuevo destinatario
            destinatario = Persona.objects.create(
                cedula=cedula_destinatario,
                nombre=nombre_destinatario,
                apellido=apellido_destinatario,
                telefono=telefono_destinatario,
                direccion=direccion_destinatario,
                es_cliente=True
            )
        
        encomienda.remitente = remitente
        encomienda.destinatario = destinatario
        encomienda.registrador = self.request.user
        encomienda.save()
        
        # NOTA: El ingreso en caja se registra al momento de generar la factura,
        # no al crear la encomienda
        
        messages.success(self.request, f"Encomienda {encomienda.codigo} registrada exitosamente.")
        # Redirigir al ticket con auto-print para imprimir inmediatamente
        return redirect(f"{reverse('operations:encomienda_ticket', kwargs={'pk': encomienda.pk})}?print=1")


class EncomiendaEntregarView(LoginRequiredMixin, View):
    """Marcar encomienda como entregada."""
    
    def get(self, request, pk):
        encomienda = get_object_or_404(Encomienda, pk=pk)
        form = EncomiendaEntregaForm()
        return render(request, 'operations/encomienda_entrega.html', {
            'encomienda': encomienda,
            'form': form
        })
    
    def post(self, request, pk):
        encomienda = get_object_or_404(Encomienda, pk=pk)
        form = EncomiendaEntregaForm(request.POST)
        
        if form.is_valid():
            encomienda.estado = 'entregado'
            encomienda.fecha_entrega = timezone.now()
            encomienda.receptor_nombre = form.cleaned_data['receptor_nombre']
            encomienda.receptor_cedula = form.cleaned_data['receptor_cedula']
            encomienda.save()
            
            messages.success(request, f"Encomienda {encomienda.codigo} entregada exitosamente.")
            return redirect('operations:encomienda_detail', pk=encomienda.pk)
        
        return render(request, 'operations/encomienda_entrega.html', {
            'encomienda': encomienda,
            'form': form
        })


class EncomiendaCambiarEstadoView(LoginRequiredMixin, View):
    """Cambiar estado de una encomienda."""
    
    def post(self, request, pk):
        encomienda = get_object_or_404(Encomienda, pk=pk)
        nuevo_estado = request.POST.get('estado')
        
        if nuevo_estado in dict(Encomienda.ESTADO_CHOICES):
            encomienda.estado = nuevo_estado
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
            context['movimientos'] = sesion.movimientos.select_related(
                'factura__timbrado__empresa'
            ).prefetch_related(
                'factura__detalles__pasaje__viaje__itinerario',
                'factura__detalles__pasaje__asiento',
                'factura__detalles__pasaje__pasajero',
                'factura__detalles__encomienda__parada_destino',
                'factura__detalles__encomienda__remitente'
            ).order_by('-fecha')[:20]
            context['total_actual'] = (
                sesion.monto_apertura + 
                sesion.total_ingresos - 
                sesion.total_egresos
            )
        except SesionCaja.DoesNotExist:
            context['sesion_abierta'] = False
        
        # Últimas sesiones del usuario
        context['sesiones_recientes'] = SesionCaja.objects.filter(
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
        context['movimientos'] = self.object.movimientos.order_by('fecha')
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


class TimbradoUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar timbrado."""
    model = Timbrado
    form_class = TimbradoForm
    template_name = 'operations/timbrado_form.html'
    success_url = reverse_lazy('operations:timbrado_list')
    success_message = "Timbrado actualizado exitosamente."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['empresas'] = Empresa.objects.all()
        return context


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
        
        return queryset.order_by('-fecha_emision')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estados'] = Factura.ESTADO_CHOICES
        context['fecha_filter'] = self.request.GET.get('fecha', '')
        context['estado_filter'] = self.request.GET.get('estado', '')
        context['search'] = self.request.GET.get('search', '')
        return context


class ClientesPendientesFacturaView(LoginRequiredMixin, TemplateView):
    """Lista de clientes con pasajes o encomiendas pendientes de facturar."""
    template_name = 'operations/clientes_pendientes_factura.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener pasajes vendidos o reservados no facturados
        pasajes_sin_factura = Pasaje.objects.filter(
            estado__in=['vendido', 'reservado']
        ).exclude(
            detalles_factura__factura__estado='emitida'
        ).select_related('pasajero', 'viaje__itinerario', 'asiento')
        
        # Obtener encomiendas no facturadas
        encomiendas_sin_factura = Encomienda.objects.filter(
            estado__in=['registrado', 'en_transito', 'en_destino', 'entregado']
        ).exclude(
            detalles_factura__factura__estado='emitida'
        ).select_related('remitente', 'parada_destino')
        
        # Filtro de búsqueda
        search = self.request.GET.get('search', '').strip()
        if search:
            pasajes_sin_factura = pasajes_sin_factura.filter(
                Q(pasajero__nombre__icontains=search) |
                Q(pasajero__apellido__icontains=search) |
                Q(pasajero__cedula__icontains=search) |
                Q(cliente__nombre__icontains=search) |
                Q(cliente__apellido__icontains=search) |
                Q(cliente__cedula__icontains=search) |
                Q(codigo__icontains=search)
            )
            encomiendas_sin_factura = encomiendas_sin_factura.filter(
                Q(remitente__nombre__icontains=search) |
                Q(remitente__apellido__icontains=search) |
                Q(remitente__cedula__icontains=search) |
                Q(codigo__icontains=search)
            )
        
        # Agrupar por cliente
        clientes_dict = {}
        
        for pasaje in pasajes_sin_factura:
            # Priorizar al cliente pagador definido en la reserva
            cliente = pasaje.cliente or pasaje.pasajero
            if cliente.pk not in clientes_dict:
                clientes_dict[cliente.pk] = {
                    'cliente': cliente,
                    'pasajes': [],
                    'encomiendas': [],
                    'total_pasajes': Decimal('0'),
                    'total_encomiendas': Decimal('0'),
                }
            clientes_dict[cliente.pk]['pasajes'].append(pasaje)
            clientes_dict[cliente.pk]['total_pasajes'] += pasaje.precio
        
        for encomienda in encomiendas_sin_factura:
            cliente = encomienda.remitente
            if cliente.pk not in clientes_dict:
                clientes_dict[cliente.pk] = {
                    'cliente': cliente,
                    'pasajes': [],
                    'encomiendas': [],
                    'total_pasajes': Decimal('0'),
                    'total_encomiendas': Decimal('0'),
                }
            clientes_dict[cliente.pk]['encomiendas'].append(encomienda)
            clientes_dict[cliente.pk]['total_encomiendas'] += encomienda.precio
        
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
        
        # Obtener timbrado vigente y próximo número
        from .services import FacturacionService
        timbrado = FacturacionService.obtener_timbrado_vigente()
        context['timbrado_vigente'] = timbrado
        if timbrado:
            try:
                context['proximo_numero'] = f"{timbrado.punto_expedicion}-{timbrado.get_siguiente_numero():07d}"
            except ValueError:
                context['proximo_numero'] = "Sin números disponibles"
        
        return context


class CancelarReservaRapidaView(LoginRequiredMixin, View):
    """Cancela una reserva rápidamente desde la lista de pendientes."""
    
    def post(self, request, pk):
        from django.shortcuts import get_object_or_404, redirect
        from django.contrib import messages
        from django.utils import timezone
        
        pasaje = get_object_or_404(Pasaje, pk=pk)
        
        if pasaje.estado not in ['reservado', 'vendido']:
            messages.error(request, "Este pasaje no puede ser cancelado.")
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
        
        if encomienda.estado != 'registrado':
            messages.error(request, "Esta encomienda ya está en tránsito o entregada, no se puede cancelar.")
            return redirect('operations:clientes_pendientes_factura')
            
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
            estado__in=['reservado', 'vendido']
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
        form = FacturaForm(cliente=cliente_cedula, pasaje=pasaje, encomienda=encomienda)
        encomienda_form = EncomiendaForm()
        
        return render(request, 'operations/factura_form.html', {
            'form': form,
            'encomienda_form': encomienda_form,
            'cliente_cedula': cliente_cedula
        })
    
    def post(self, request):
        from .forms import FacturaForm
        from .services import FacturacionService
        
        # Obtener la cédula del cliente del POST para construir el formulario correctamente
        cedula_cliente = request.POST.get('cedula_cliente', '').strip()
        
        # Construir el formulario con el cliente para que los querysets sean válidos
        form = FacturaForm(request.POST, cliente=cedula_cliente)
        
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
        
        factura = get_object_or_404(Factura, pk=pk)
        form = FacturaAnulacionForm(request.POST)
        
        if form.is_valid():
            try:
                revertir_caja = form.cleaned_data.get('revertir_caja', True)
                
                FacturacionService.anular_factura(
                    factura=factura,
                    motivo=form.cleaned_data['motivo'],
                    usuario=request.user,
                    revertir_caja=revertir_caja
                )
                
                messages.success(request, f"Factura {factura.numero_completo} anulada.")
                
                if revertir_caja:
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
    """Reporte diario de operaciones."""
    template_name = 'operations/reporte_diario.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        fecha = self.request.GET.get('fecha')
        
        if fecha:
            from datetime import datetime
            fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
        else:
            fecha = timezone.now().date()
        
        context['fecha'] = fecha
        
        # Viajes del día
        viajes = Viaje.objects.filter(fecha_viaje=fecha).select_related(
            'itinerario', 'bus', 'chofer'
        )
        context['viajes'] = viajes
        context['total_viajes'] = viajes.count()
        
        # Pasajes del día
        pasajes = Pasaje.objects.filter(fecha_venta__date=fecha)
        context['total_pasajes'] = pasajes.filter(estado='vendido').count()
        context['ingresos_pasajes'] = pasajes.filter(estado='vendido').aggregate(
            total=Sum('precio')
        )['total'] or Decimal('0.00')
        
        # Encomiendas del día
        encomiendas = Encomienda.objects.filter(fecha_registro__date=fecha)
        context['total_encomiendas'] = encomiendas.count()
        context['ingresos_encomiendas'] = encomiendas.exclude(
            estado='cancelado'
        ).aggregate(total=Sum('precio'))['total'] or Decimal('0.00')
        
        # Total ingresos
        context['total_ingresos'] = context['ingresos_pasajes'] + context['ingresos_encomiendas']
        
        # Sesiones de caja del día
        context['sesiones_caja'] = SesionCaja.objects.filter(
            fecha_apertura__date=fecha
        ).select_related('cajero')
        
        return context


class ReporteVentasView(LoginRequiredMixin, TemplateView):
    """Reporte de ventas por período."""
    template_name = 'operations/reporte_ventas.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        desde = self.request.GET.get('desde')
        hasta = self.request.GET.get('hasta')
        
        if desde and hasta:
            from datetime import datetime
            desde = datetime.strptime(desde, '%Y-%m-%d').date()
            hasta = datetime.strptime(hasta, '%Y-%m-%d').date()
        else:
            hasta = timezone.now().date()
            desde = hasta - timedelta(days=30)
        
        context['desde'] = desde
        context['hasta'] = hasta
        
        # Ventas por día
        pasajes_por_dia = Pasaje.objects.filter(
            fecha_venta__date__gte=desde,
            fecha_venta__date__lte=hasta,
            estado='vendido'
        ).annotate(
            dia=TruncDate('fecha_venta')
        ).values('dia').annotate(
            count=Count('id'),
            total=Sum('precio')
        ).order_by('dia')
        
        context['ventas_por_dia'] = list(pasajes_por_dia)
        
        # Totales del período
        context['total_pasajes'] = sum(v['count'] for v in pasajes_por_dia)
        context['total_ingresos'] = sum(v['total'] for v in pasajes_por_dia)
        
        return context


# =============================================================================
# HTMX PARTIALS
# =============================================================================

class BuscarPersonaView(LoginRequiredMixin, View):
    """Buscar persona por cédula (HTMX)."""
    
    def get(self, request):
        cedula = request.GET.get('cedula')
        if cedula:
            try:
                persona = Persona.objects.get(cedula=cedula)
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
        
        asientos_ocupados = Pasaje.objects.filter(
            viaje=viaje,
            estado__in=['reservado', 'vendido', 'abordado']
        ).values_list('asiento_id', flat=True)
        
        asientos = viaje.bus.asientos.all().order_by('piso', 'numero_asiento')
        
        return render(request, 'operations/partials/mapa_asientos.html', {
            'viaje': viaje,
            'asientos': asientos,
            'asientos_ocupados': list(asientos_ocupados)
        })


class ObtenerPrecioView(LoginRequiredMixin, View):
    """Obtener precio de un tramo (HTMX/AJAX)."""
    
    def get(self, request):
        viaje_pk = request.GET.get('viaje')
        origen_pk = request.GET.get('origen')
        destino_pk = request.GET.get('destino')
        
        if viaje_pk and origen_pk and destino_pk:
            try:
                viaje = Viaje.objects.get(pk=viaje_pk)
                precio = Precio.objects.get(
                    itinerario=viaje.itinerario,
                    origen_id=origen_pk,
                    destino_id=destino_pk
                )
                return JsonResponse({'precio': float(precio.precio)})
            except (Viaje.DoesNotExist, Precio.DoesNotExist):
                return JsonResponse({'precio': 0, 'error': 'No encontrado'})
        
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
        ).order_by('apellido', 'nombre')[:30]
        
        clientes = []
        for persona in personas:
            clientes.append({
                'cedula': str(persona.cedula),
                'nombre': persona.nombre_completo,
                'telefono': persona.telefono or '-',
                'direccion': persona.direccion or '-'
            })
        
        return JsonResponse({'clientes': clientes})

class ObtenerItemsPendientesClienteView(LoginRequiredMixin, View):
    """API para obtener pasajes y encomiendas pendientes de un cliente."""
    
    def get(self, request):
        cedula = request.GET.get('cedula', '').strip()
        
        if not cedula:
            return JsonResponse({'error': 'Cédula requerida'}, status=400)
        
        try:
            persona = Persona.objects.get(cedula=cedula)
        except Persona.DoesNotExist:
            return JsonResponse({'error': 'Cliente no encontrado'}, status=404)
        
        # Obtener pasajes pendientes (vendidos o reservados)
        pasajes = Pasaje.objects.filter(
            Q(pasajero=persona) | Q(cliente=persona),
            estado__in=['vendido', 'reservado']
        ).exclude(
            detalles_factura__factura__estado='emitida'
        ).select_related('viaje__itinerario', 'asiento')
        
        pasajes_data = []
        for p in pasajes:
            pasajes_data.append({
                'pk': p.pk,
                'codigo': p.codigo,
                'viaje': f"{p.viaje.itinerario.nombre} - {p.viaje.fecha_viaje.strftime('%d/%m')}",
                'pasajero': p.pasajero.nombre_completo,
                'asiento': p.asiento.numero_asiento if p.asiento else '-',
                'precio': float(p.precio),
                'empresa_id': p.viaje.empresa_id if p.viaje else None
            })
        
        # Obtener encomiendas pendientes
        encomiendas = Encomienda.objects.filter(
            remitente=persona,
            estado__in=['registrado', 'en_transito', 'en_destino', 'entregado']
        ).exclude(
            detalles_factura__factura__estado='emitida'
        ).select_related('viaje', 'parada_destino')
        
        encomiendas_data = []
        for e in encomiendas:
            encomiendas_data.append({
                'pk': e.pk,
                'codigo': e.codigo,
                'tipo': e.get_tipo_display(),
                'descripcion': e.descripcion[:30] if e.descripcion else '-',
                'destino': e.parada_destino.nombre if e.parada_destino else '-',
                'precio': float(e.precio),
                'empresa_id': e.viaje.empresa_id if e.viaje else None
            })
        
        return JsonResponse({
            'cliente': {
                'cedula': str(persona.cedula),
                'nombre': persona.nombre_completo
            },
            'pasajes': pasajes_data,
            'encomiendas': encomiendas_data
        })


class ViajeParadasView(LoginRequiredMixin, View):
    """API para obtener las paradas de un viaje específico."""
    
    def get(self, request, viaje_pk):
        viaje = get_object_or_404(Viaje, pk=viaje_pk)
        
        # Obtener paradas del itinerario
        paradas_ids = viaje.itinerario.detalles.values_list('parada_id', flat=True)
        paradas = Parada.objects.filter(id__in=list(paradas_ids)).order_by('nombre')
        
        paradas_data = [
            {'id': p.id, 'nombre': p.nombre}
            for p in paradas
        ]
        
        return JsonResponse({
            'viaje': {
                'id': viaje.pk,
                'nombre': viaje.itinerario.nombre,
                'fecha': viaje.fecha_viaje.strftime('%d/%m/%Y'),
                'bus': viaje.bus.placa
            },
            'paradas': paradas_data
        })


class ObtenerHorariosItinerarioView(LoginRequiredMixin, View):
    """Retorna las opciones de horario y buses para un itinerario específico (HTMX)."""
    def get(self, request):
        itinerario_id = request.GET.get('itinerario')
        fecha_str = request.GET.get('fecha')
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
                itinerarios = itinerarios.filter(Q(empresa_id=emp_id) | Q(empresa__isnull=True))
                buses = Bus.objects.filter(empresa_id=emp_id).order_by('placa')
                choferes = Persona.objects.filter(empresa_id=emp_id, es_chofer=True).order_by('apellido', 'nombre')
                ayudantes = Persona.objects.filter(empresa_id=emp_id, es_ayudante=True).order_by('apellido', 'nombre')
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

                # Obtener todos los horarios activos para que estén disponibles globalmente
                todos_horarios = Horario.objects.filter(activo=True).order_by('hora_salida')

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
                    choferes = Persona.objects.filter(empresa=itinerario.empresa, es_chofer=True).order_by('apellido', 'nombre')
                    ayudantes = Persona.objects.filter(empresa=itinerario.empresa, es_ayudante=True).order_by('apellido', 'nombre')
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
        hoy = timezone.now().date()

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
        hoy = timezone.now().date()
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
                ub = UbicacionAyudante.objects.filter(persona=p, activo=True).first()
                if ub:
                    ubicacion = ub
                    break

            pasajes_activos = viaje.pasajes.filter(
                estado__in=['vendido', 'reservado', 'abordado']
            ).values('asiento_id').distinct().count()

            detalles = viaje.itinerario.detalles.select_related('parada', 'parada__localidad').order_by('orden')
            paradas = [{
                'nombre': d.parada.nombre,
                'orden': d.orden,
                'lat': float(d.parada.latitud_gps) if d.parada.latitud_gps else None,
                'lng': float(d.parada.longitud_gps) if d.parada.longitud_gps else None,
            } for d in detalles]

            viaje_data = {
                'id': viaje.pk,
                'itinerario': viaje.itinerario.nombre,
                'empresa': viaje.empresa.nombre if viaje.empresa else '',
                'bus_placa': viaje.bus.placa,
                'bus_marca': f"{viaje.bus.marca or ''} {viaje.bus.modelo or ''}".strip(),
                'chofer': viaje.chofer.nombre_completo,
                'hora_salida': viaje.horario.hora_salida.strftime('%H:%M') if viaje.horario else '--:--',
                'asientos_total': viaje.bus.capacidad_asientos,
                'asientos_ocupados': pasajes_activos,
                'asientos_libres': viaje.bus.capacidad_asientos - pasajes_activos,
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


class RastreoPublicoView(LoginRequiredMixin, TemplateView):

    """Vista del mapa para clientes (público interno)."""
    template_name = 'users/rastreo_publico.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.now().date()
        viajes_en_curso = Viaje.objects.filter(estado='en_curso', fecha_viaje=hoy)
        context['viajes_en_curso'] = viajes_en_curso
        context['total_en_curso'] = viajes_en_curso.count()
        return context


class APIViajesPublicosView(LoginRequiredMixin, View):
    """API JSON para clientes. Oculta datos sensibles y calcula ETAs."""

    def get(self, request):
        import math
        def calcular_km(lat1, lon1, lat2, lon2):
            R = 6371.0
            phi1, phi2 = math.radians(lat1), math.radians(lat2)
            dphi = math.radians(lat2 - lat1)
            dlambda = math.radians(lon2 - lon1)
            a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
            return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        hoy = timezone.now().date()
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
                p_data = {
                    'nombre': d.parada.nombre,
                    'lat': float(d.parada.latitud_gps) if d.parada.latitud_gps else None,
                    'lng': float(d.parada.longitud_gps) if d.parada.longitud_gps else None,
                }
                paradas.append(p_data)
                
                # Calcular proxima parada si tenemos ubicación
                if ubicacion and not proxima_parada and p_data['lat']:
                    dist = calcular_km(float(ubicacion.latitud), float(ubicacion.longitud), p_data['lat'], p_data['lng'])
                    # Si el bus está a más de 0.5km y es una parada futura (simplificado)
                    if dist > 0.5:
                        proxima_parada = d.parada.nombre
                        velocidad = float(ubicacion.velocidad_kmh) if ubicacion.velocidad_kmh and ubicacion.velocidad_kmh > 10 else 40
                        eta_minutos = math.ceil((dist / velocidad) * 60)

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

        if not (persona.es_ayudante or persona.es_chofer or persona.es_empleado):
            return JsonResponse({'error': 'No autorizado para enviar ubicación'}, status=403)

        # Buscar viaje en curso asignado a esta persona
        hoy = timezone.now().date()
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

        # Actualizar o crear ubicación
        ub, created = UbicacionAyudante.objects.update_or_create(
            persona=persona,
            activo=True,
            defaults={
                'latitud': lat,
                'longitud': lng,
                'velocidad_kmh': velocidad,
                'heading': heading,
                'viaje': viaje_actual,
            }
        )

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
        ahora = timezone.now()
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
        )

        # Procesar identificadores virtuales (text_) del autocompletado
        if origen_id and origen_id.startswith('text_'):
            origen_text = origen_id.replace('text_', '')
            origen_id = ''
        
        if destino_id and destino_id.startswith('text_'):
            destino_text = destino_id.replace('text_', '')
            destino_id = ''

        import unicodedata
        def normalize_search(text):
            if not text: return ""
            # Quitar acentos, pasar a minúsculas y quitar palabras comunes
            text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()
            return text.replace('terminal de ', '').replace('terminal ', '').replace('parada ', '').strip()

        # Filtrado por tramo (Origen -> Destino) mejorado
        if origen_id and destino_id:
            from itineraries.models import DetalleItinerario
            from fleet.models import Parada
            
            origen_p = Parada.objects.filter(pk=origen_id).first()
            destino_p = Parada.objects.filter(pk=destino_id).first()
            
            # Buscar IDs de paradas similares (por nombre o localidad normalizados)
            def get_similar_ids(p):
                if not p: return []
                norm = normalize_search(p.nombre)
                loc_norm = normalize_search(p.localidad.nombre if p.localidad else '')
                query = Q(nombre__icontains=norm) | Q(localidad__nombre__icontains=norm)
                if loc_norm:
                    query |= Q(nombre__icontains=loc_norm) | Q(localidad__nombre__icontains=loc_norm)
                return Parada.objects.filter(query).values_list('id', flat=True)

            origen_ids = get_similar_ids(origen_p) if origen_p else [origen_id]
            destino_ids = get_similar_ids(destino_p) if destino_p else [destino_id]
            
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
            
            def get_similar_ids(p):
                if not p: return []
                norm = normalize_search(p.nombre)
                loc_norm = normalize_search(p.localidad.nombre if p.localidad else '')
                query = Q(nombre__icontains=norm) | Q(localidad__nombre__icontains=norm)
                if loc_norm:
                    query |= Q(nombre__icontains=loc_norm) | Q(localidad__nombre__icontains=loc_norm)
                return Parada.objects.filter(query).values_list('id', flat=True)

            origen_ids = get_similar_ids(origen_p) if origen_p else [origen_id]
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
            
            def get_similar_ids(p):
                if not p: return []
                norm = normalize_search(p.nombre)
                loc_norm = normalize_search(p.localidad.nombre if p.localidad else '')
                query = Q(nombre__icontains=norm) | Q(localidad__nombre__icontains=norm)
                if loc_norm:
                    query |= Q(nombre__icontains=loc_norm) | Q(localidad__nombre__icontains=loc_norm)
                return Parada.objects.filter(query).values_list('id', flat=True)

            destino_ids = get_similar_ids(destino_p) if destino_p else [destino_id]
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
            viajes_con_info.append({
                'viaje': viaje,
                'asientos_libres': viaje.bus.capacidad_asientos - pasajes_activos,
                'asientos_total': viaje.bus.capacidad_asientos,
                'porcentaje_ocupacion': viaje.porcentaje_ocupacion,
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
        detalles = viaje.itinerario.detalles.select_related(
            'parada', 'parada__localidad'
        ).order_by('orden')
        context['detalles_itinerario'] = detalles

        # Todos los asientos del bus
        asientos = viaje.bus.asientos.all().order_by('piso', 'numero_asiento')
        context['asientos'] = asientos

        # Origen y destino sugeridos (desde búsqueda)
        context['initial_origen_id'] = self.request.GET.get('origen')
        context['initial_destino_id'] = self.request.GET.get('destino')

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

        # Todos los asientos del bus
        todos = viaje.bus.asientos.all().order_by('piso', 'numero_asiento')

        # Mapa de ocupación
        mapa_ocupacion = obtener_mapa_ocupacion(viaje)

        # Precio
        precio = None
        # 1. Intento exacto: Por paradas e itinerario específico
        precio_obj = Precio.objects.filter(
            itinerario=viaje.itinerario,
            origen=parada_origen,
            destino=parada_destino
        ).first()

        if precio_obj:
            precio = float(precio_obj.precio)
        else:
            # 2. Intento por paradas (independientemente del itinerario)
            precio_alternativo = Precio.objects.filter(
                origen=parada_origen,
                destino=parada_destino
            ).first()
            if precio_alternativo:
                precio = float(precio_alternativo.precio)
            else:
                # 3. Intento por NOMBRES (cuando hay paradas duplicadas para distintas empresas)
                # Buscamos cualquier precio que coincida con los nombres de origen y destino
                precio_por_nombre = Precio.objects.filter(
                    origen__nombre=parada_origen.nombre,
                    destino__nombre=parada_destino.nombre
                ).first()
                if precio_por_nombre:
                    precio = float(precio_por_nombre.precio)
                else:
                    # 4. Intento por NOMBRES DE LOCALIDAD (Exacto)
                    precio_localidad = Precio.objects.filter(
                        origen__localidad__nombre__iexact=parada_origen.localidad.nombre,
                        destino__localidad__nombre__iexact=parada_destino.localidad.nombre
                    ).first()
                    if precio_localidad:
                        precio = float(precio_localidad.precio)
                    else:
                        # 5. Intento SUPER FUZZY (Parcial): ej "Terminal Caaguazu" contiene "Caaguazu"
                        # Limpiamos el nombre para buscar coincidencias parciales
                        o_search = parada_origen.localidad.nombre.replace('Terminal', '').replace('de', '').strip()
                        d_search = parada_destino.localidad.nombre.replace('Terminal', '').replace('de', '').strip()
                        
                        if len(o_search) > 3 and len(d_search) > 3:
                            precio_fuzzy = Precio.objects.filter(
                                Q(origen__localidad__nombre__icontains=o_search) | Q(origen__nombre__icontains=o_search),
                                Q(destino__localidad__nombre__icontains=d_search) | Q(destino__nombre__icontains=d_search)
                            ).first()
                            if precio_fuzzy:
                                precio = float(precio_fuzzy.precio)

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
                    })
            asientos_data.append(info)

        return JsonResponse({
            'asientos': asientos_data,
            'disponibles': len(asientos_disponibles_ids),
            'total': todos.count(),
            'precio': precio,
            'orden_origen': orden_origen,
            'orden_destino': orden_destino,
        })


class CrearReservaClienteView(LoginRequiredMixin, View):
    """Crea una reserva de pasaje para un cliente. Le da 30 min para pagar."""

    def post(self, request, viaje_pk):
        import json
        viaje = get_object_or_404(Viaje, pk=viaje_pk)

        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)

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
        # 1. Intento exacto: Por paradas e itinerario específico
        precio_obj = Precio.objects.filter(
            itinerario=viaje.itinerario,
            origen=parada_origen,
            destino=parada_destino
        ).first()

        if precio_obj:
            precio = precio_obj.precio
        else:
            # 2. Intento por paradas (independientemente del itinerario)
            precio_alternativo = Precio.objects.filter(
                origen=parada_origen,
                destino=parada_destino
            ).first()
            if precio_alternativo:
                precio = precio_alternativo.precio
            else:
                # 3. Intento por NOMBRES
                precio_por_nombre = Precio.objects.filter(
                    origen__nombre=parada_origen.nombre,
                    destino__nombre=parada_destino.nombre
                ).first()
                if precio_por_nombre:
                    precio = precio_por_nombre.precio
                else:
                    # 4. Intento por LOCALIDADES
                    precio_localidad = Precio.objects.filter(
                        origen__localidad__nombre__iexact=parada_origen.localidad.nombre,
                        destino__localidad__nombre__iexact=parada_destino.localidad.nombre
                    ).first()
                    if precio_localidad:
                        precio = precio_localidad.precio
                    else:
                        # 5. Intento Fuzzy
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

        from datetime import datetime
        if viaje.horario:
            fecha_hora_salida = timezone.make_aware(
                datetime.combine(viaje.fecha_viaje, viaje.horario.hora_salida)
            )
            limite_pago = fecha_hora_salida - timedelta(minutes=30)
        else:
            limite_pago = timezone.now() + timedelta(minutes=30)
            
        if timezone.now() >= limite_pago:
            return JsonResponse({
                'error': 'Ya no es posible realizar reservas, el plazo (hasta 30 min antes de la salida) ha concluido.'
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
                f'Tiene hasta 30 minutos antes de la salida para poder abonar en la agencia (Límite: {p_main.fecha_limite_pago.strftime("%d/%m/%Y %H:%M")}), '
                f'de lo contrario su reserva se cancela automáticamente, por lo que dichos asientos quedarán libres. '
            ),
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
            try:
                destinatario = Persona.objects.get(cedula=cedula_destinatario)
            except Persona.DoesNotExist:
                destinatario = Persona.objects.create(
                    cedula=cedula_destinatario,
                    nombre=form.cleaned_data.get('nombre_destinatario'),
                    apellido=form.cleaned_data.get('apellido_destinatario'),
                    telefono=form.cleaned_data.get('telefono_destinatario'),
                    es_cliente=True
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
