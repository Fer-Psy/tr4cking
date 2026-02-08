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
    Factura, DetalleFactura, SesionCaja, MovimientoCaja, Incidencia
)
from .forms import (
    ViajeForm, ViajeEstadoForm, PasajeVentaForm, PasajeCancelacionForm,
    EncomiendaForm, EncomiendaEntregaForm, TimbradoForm, FacturaAnulacionForm,
    AperturaCajaForm, CierreCajaForm, MovimientoCajaForm,
    IncidenciaForm, IncidenciaResolucionForm, BusquedaViajeForm
)
from users.models import Persona
from fleet.models import Bus, Parada, Empresa
from itineraries.models import Itinerario, Precio


# =============================================================================
# DASHBOARD OPERATIVO
# =============================================================================

class OperationsDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard principal de operaciones."""
    template_name = 'operations/dashboard.html'
    
    def get_context_data(self, **kwargs):
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
        ).select_related('itinerario', 'bus', 'chofer').order_by('itinerario__detalles__hora_salida')[:5]
        
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
        context['alertas'] = alertas
        
        return context


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
        queryset = super().get_queryset().select_related(
            'itinerario', 'bus', 'chofer'
        ).annotate(
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
        
        # Mapa de asientos
        context['asientos_bus'] = viaje.bus.asientos.all().order_by('piso', 'numero_asiento')
        context['asientos_ocupados'] = list(viaje.pasajes.filter(
            estado__in=['reservado', 'vendido', 'abordado']
        ).values_list('asiento_id', flat=True))
        
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
        
        return context


class ViajeCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Crear un nuevo viaje."""
    model = Viaje
    form_class = ViajeForm
    template_name = 'operations/viaje_form.html'
    success_url = reverse_lazy('operations:viaje_list')
    success_message = "Viaje programado exitosamente."


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
        cedula = form.cleaned_data.get('cedula_pasajero')
        try:
            pasajero = Persona.objects.get(cedula=cedula)
        except Persona.DoesNotExist:
            pasajero = Persona.objects.create(
                cedula=cedula,
                nombre=form.cleaned_data.get('nombre_pasajero', 'Sin nombre'),
                apellido=form.cleaned_data.get('apellido_pasajero', ''),
                telefono=form.cleaned_data.get('telefono_pasajero', ''),
                es_pasajero=True
            )
        
        pasaje.pasajero = pasajero
        pasaje.vendedor = self.request.user
        pasaje.estado = 'vendido'
        
        # Obtener precio del itinerario
        try:
            precio_obj = Precio.objects.get(
                itinerario=pasaje.viaje.itinerario,
                origen=pasaje.parada_origen,
                destino=pasaje.parada_destino
            )
            pasaje.precio = precio_obj.precio
        except Precio.DoesNotExist:
            messages.warning(self.request, "No se encontró precio para este tramo. Configure precios.")
            pasaje.precio = Decimal('0.00')
        
        pasaje.save()
        
        # Registrar movimiento de caja si hay sesión abierta
        try:
            sesion_caja = SesionCaja.objects.get(
                cajero=self.request.user,
                estado='abierta'
            )
            MovimientoCaja.objects.create(
                sesion=sesion_caja,
                tipo='ingreso',
                concepto='venta_pasaje',
                monto=pasaje.precio,
                descripcion=f"Venta pasaje {pasaje.codigo}"
            )
        except SesionCaja.DoesNotExist:
            messages.warning(self.request, "No hay caja abierta. El movimiento no fue registrado.")
        
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
        
        # Obtener remitente
        cedula_remitente = form.cleaned_data.get('cedula_remitente')
        try:
            remitente = Persona.objects.get(cedula=cedula_remitente)
        except Persona.DoesNotExist:
            messages.error(self.request, f"No se encontró persona con cédula {cedula_remitente}")
            return self.form_invalid(form)
        
        # Obtener destinatario
        cedula_destinatario = form.cleaned_data.get('cedula_destinatario')
        try:
            destinatario = Persona.objects.get(cedula=cedula_destinatario)
        except Persona.DoesNotExist:
            messages.error(self.request, f"No se encontró persona con cédula {cedula_destinatario}")
            return self.form_invalid(form)
        
        encomienda.remitente = remitente
        encomienda.destinatario = destinatario
        encomienda.registrador = self.request.user
        encomienda.save()
        
        # Registrar ingreso en caja
        try:
            sesion_caja = SesionCaja.objects.get(
                cajero=self.request.user,
                estado='abierta'
            )
            MovimientoCaja.objects.create(
                sesion=sesion_caja,
                tipo='ingreso',
                concepto='venta_encomienda',
                monto=encomienda.precio,
                descripcion=f"Encomienda {encomienda.codigo}"
            )
        except SesionCaja.DoesNotExist:
            messages.warning(self.request, "No hay caja abierta. El movimiento no fue registrado.")
        
        messages.success(self.request, f"Encomienda {encomienda.codigo} registrada exitosamente.")
        return redirect('operations:encomienda_detail', pk=encomienda.pk)


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
            context['movimientos'] = sesion.movimientos.order_by('-fecha')[:20]
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
                Q(cliente__nombre__icontains=search)
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
        
        # Obtener pasajes vendidos no facturados
        pasajes_sin_factura = Pasaje.objects.filter(
            estado='vendido'
        ).exclude(
            detalles_factura__factura__estado='emitida'
        ).select_related('pasajero', 'viaje__itinerario', 'asiento')
        
        # Obtener encomiendas no facturadas
        encomiendas_sin_factura = Encomienda.objects.filter(
            estado__in=['registrado', 'en_transito', 'en_destino', 'entregado']
        ).exclude(
            detalles_factura__factura__estado='emitida'
        ).select_related('remitente', 'parada_destino')
        
        # Agrupar por cliente
        clientes_dict = {}
        
        for pasaje in pasajes_sin_factura:
            cliente = pasaje.pasajero
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
        
        form = FacturaForm(cliente=cliente_cedula, pasaje=pasaje, encomienda=encomienda)
        
        return render(request, 'operations/factura_form.html', {
            'form': form,
            'cliente_cedula': cliente_cedula
        })
    
    def post(self, request):
        from .forms import FacturaForm
        from .services import FacturacionService
        
        form = FacturaForm(request.POST)
        
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
