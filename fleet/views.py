"""
Views for fleet app.
"""
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse

from .models import Empresa, Parada, Bus, Asiento
from .forms import EmpresaForm, ParadaForm, BusForm, AsientoForm


# =============================================================================
# EMPRESA VIEWS
# =============================================================================

class EmpresaListView(LoginRequiredMixin, ListView):
    """Lista de empresas."""
    model = Empresa
    template_name = 'fleet/empresa_list.html'
    context_object_name = 'empresas'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = super().get_queryset().annotate(
            num_buses=Count('buses'),
            num_paradas=Count('paradas')
        )
        
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(ruc__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        return context


class EmpresaDetailView(LoginRequiredMixin, DetailView):
    """Detalle de una empresa."""
    model = Empresa
    template_name = 'fleet/empresa_detail.html'
    context_object_name = 'empresa'


class EmpresaCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Crear una nueva empresa."""
    model = Empresa
    form_class = EmpresaForm
    template_name = 'fleet/empresa_form.html'
    success_url = reverse_lazy('fleet:empresa_list')
    success_message = "Empresa %(nombre)s creada exitosamente."


class EmpresaUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar una empresa."""
    model = Empresa
    form_class = EmpresaForm
    template_name = 'fleet/empresa_form.html'
    success_url = reverse_lazy('fleet:empresa_list')
    success_message = "Empresa %(nombre)s actualizada exitosamente."


class EmpresaDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar una empresa."""
    model = Empresa
    template_name = 'fleet/empresa_confirm_delete.html'
    success_url = reverse_lazy('fleet:empresa_list')
    
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request, 
                f"No se puede eliminar la empresa '{self.get_object().nombre}' porque está referenciada "
                "en otras partes del sistema."
            )
            return self.get(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f"Empresa {self.object.nombre} eliminada exitosamente.")
        return super().form_valid(form)


# =============================================================================
# PARADA VIEWS
# =============================================================================

class ParadaListView(LoginRequiredMixin, ListView):
    """Lista de paradas."""
    model = Parada
    template_name = 'fleet/parada_list.html'
    context_object_name = 'paradas'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('empresa', 'localidad')
        
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(localidad__nombre__icontains=search)
            )
        
        empresa = self.request.GET.get('empresa', '')
        if empresa:
            queryset = queryset.filter(empresa_id=empresa)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['empresa_filter'] = self.request.GET.get('empresa', '')
        context['empresas'] = Empresa.objects.all()
        
        # Datos para el mapa del dashboard
        import json
        paradas_data = []
        for p in context['paradas']:
            lat = p.latitud_gps or (p.localidad.latitud if p.localidad else None)
            lng = p.longitud_gps or (p.localidad.longitud if p.localidad else None)
            
            if lat and lng:
                paradas_data.append({
                    'id': p.id,
                    'nombre': p.nombre,
                    'lat': float(lat),
                    'lng': float(lng),
                    'empresa': p.empresa.nombre,
                    'localidad': p.localidad.nombre,
                    'is_agencia': p.es_agencia,
                    'url': reverse('fleet:parada_detail', args=[p.id])
                })
        context['paradas_json'] = json.dumps(paradas_data)
        return context


class ParadaDetailView(LoginRequiredMixin, DetailView):
    """Detalle de una parada."""
    model = Parada
    template_name = 'fleet/parada_detail.html'
    context_object_name = 'parada'


class ParadaCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Crear una nueva parada."""
    model = Parada
    form_class = ParadaForm
    template_name = 'fleet/parada_form.html'
    success_url = reverse_lazy('fleet:parada_list')
    success_message = "Parada %(nombre)s creada exitosamente."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from users.forms import LocalidadForm
        context['localidad_form'] = LocalidadForm()
        return context


class ParadaUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar una parada."""
    model = Parada
    form_class = ParadaForm
    template_name = 'fleet/parada_form.html'
    success_url = reverse_lazy('fleet:parada_list')
    success_message = "Parada %(nombre)s actualizada exitosamente."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from users.forms import LocalidadForm
        context['localidad_form'] = LocalidadForm()
        return context


class ParadaDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar una parada."""
    model = Parada
    template_name = 'fleet/parada_confirm_delete.html'
    success_url = reverse_lazy('fleet:parada_list')
    
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request, 
                f"No se puede eliminar la parada '{self.get_object().nombre}' porque está siendo utilizada "
                "en otras partes del sistema (ej. precios o itinerarios)."
            )
            return self.get(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f"Parada {self.object.nombre} eliminada exitosamente.")
        return super().form_valid(form)


# =============================================================================
# BUS VIEWS
# =============================================================================

class BusListView(LoginRequiredMixin, ListView):
    """Lista de buses."""
    model = Bus
    template_name = 'fleet/bus_list.html'
    context_object_name = 'buses'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('empresa').annotate(
            num_asientos=Count('asientos')
        )
        
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(placa__icontains=search) |
                Q(marca__icontains=search) |
                Q(modelo__icontains=search)
            )
        
        empresa = self.request.GET.get('empresa', '')
        if empresa:
            queryset = queryset.filter(empresa_id=empresa)
        
        estado = self.request.GET.get('estado', '')
        if estado:
            queryset = queryset.filter(estado=estado)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['empresa_filter'] = self.request.GET.get('empresa', '')
        context['estado_filter'] = self.request.GET.get('estado', '')
        context['empresas'] = Empresa.objects.all()
        context['estados'] = Bus.ESTADO_CHOICES
        return context


class BusDetailView(LoginRequiredMixin, DetailView):
    """Detalle de un bus."""
    model = Bus
    template_name = 'fleet/bus_detail.html'
    context_object_name = 'bus'


class BusCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Crear un nuevo bus con generación automática de asientos."""
    model = Bus
    form_class = BusForm
    template_name = 'fleet/bus_form.html'
    success_url = reverse_lazy('fleet:bus_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Obtener el tipo de asiento seleccionado
        tipo_asiento = form.cleaned_data.get('tipo_asiento', 'convencional')
        bus = self.object
        capacidad = bus.capacidad_asientos
        pisos = bus.capacidad_pisos
        
        # Generar los asientos automáticamente
        asientos = []
        for i in range(1, capacidad + 1):
            # Distribuir asientos entre pisos
            if pisos == 2:
                piso = 1 if i <= capacidad // 2 else 2
            else:
                piso = 1
            
            asientos.append(Asiento(
                bus=bus,
                numero_asiento=i,
                piso=piso,
                tipo_asiento=tipo_asiento,
            ))
        
        Asiento.objects.bulk_create(asientos)
        
        messages.success(
            self.request, 
            f"Bus {bus.placa} creado exitosamente con {capacidad} asientos de tipo "
            f"'{dict(Asiento.TIPO_ASIENTO_CHOICES).get(tipo_asiento, tipo_asiento)}'."
        )
        return response


class BusUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar un bus con opción de regenerar asientos."""
    model = Bus
    form_class = BusForm
    template_name = 'fleet/bus_form.html'
    success_url = reverse_lazy('fleet:bus_list')
    
    def get_initial(self):
        initial = super().get_initial()
        # Pre-seleccionar el tipo de asiento más común del bus actual
        bus = self.get_object()
        asiento_mas_comun = (
            bus.asientos
            .values('tipo_asiento')
            .annotate(total=Count('tipo_asiento'))
            .order_by('-total')
            .first()
        )
        if asiento_mas_comun:
            initial['tipo_asiento'] = asiento_mas_comun['tipo_asiento']
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['asientos_actuales'] = self.object.asientos.count()
        return context
    
    def form_valid(self, form):
        bus = self.object
        capacidad_anterior = Bus.objects.get(pk=bus.pk).capacidad_asientos
        nueva_capacidad = form.cleaned_data['capacidad_asientos']
        tipo_asiento = form.cleaned_data.get('tipo_asiento', 'convencional')
        pisos = form.cleaned_data['capacidad_pisos']
        regenerar = form.cleaned_data.get('regenerar_asientos')
        
        response = super().form_valid(form)
        
        if regenerar:
            # Eliminar asientos existentes y regenerar
            bus.asientos.all().delete()
            
            asientos = []
            for i in range(1, nueva_capacidad + 1):
                if pisos == 2:
                    piso = 1 if i <= nueva_capacidad // 2 else 2
                else:
                    piso = 1
                
                asientos.append(Asiento(
                    bus=bus,
                    numero_asiento=i,
                    piso=piso,
                    tipo_asiento=tipo_asiento,
                ))
            
            Asiento.objects.bulk_create(asientos)
            
            messages.success(
                self.request, 
                f"Bus {bus.placa} actualizado y {nueva_capacidad} asientos regenerados con tipo "
                f"'{dict(Asiento.TIPO_ASIENTO_CHOICES).get(tipo_asiento, tipo_asiento)}'."
            )
        else:
            messages.success(
                self.request, 
                f"Bus {bus.placa} actualizado exitosamente. Los asientos no fueron modificados."
            )
        
        return response


class BusDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar un bus."""
    model = Bus
    template_name = 'fleet/bus_confirm_delete.html'
    success_url = reverse_lazy('fleet:bus_list')
    
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request, 
                f"No se puede eliminar el bus '{self.get_object().placa}' porque tiene registros relacionados "
                "que están protegidos (ej. viajes realizados)."
            )
            return self.get(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f"Bus {self.object.placa} eliminado exitosamente.")
        return super().form_valid(form)


# =============================================================================
# ASIENTO VIEWS
# =============================================================================

class AsientoListView(LoginRequiredMixin, ListView):
    """Lista de asientos de un bus."""
    model = Asiento
    template_name = 'fleet/asiento_list.html'
    context_object_name = 'asientos'
    
    def get_queryset(self):
        self.bus = get_object_or_404(Bus, pk=self.kwargs['bus_pk'])
        return Asiento.objects.filter(bus=self.bus).order_by('piso', 'numero_asiento')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bus'] = self.bus
        return context


class AsientoCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Crear un nuevo asiento."""
    model = Asiento
    form_class = AsientoForm
    template_name = 'fleet/asiento_form.html'
    success_message = "Asiento %(numero_asiento)s creado exitosamente."
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.bus = get_object_or_404(Bus, pk=self.kwargs['bus_pk'])
        kwargs['bus'] = self.bus
        return kwargs
    
    def form_valid(self, form):
        form.instance.bus = self.bus
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('fleet:asiento_list', kwargs={'bus_pk': self.kwargs['bus_pk']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bus'] = self.bus
        return context


class AsientoUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar un asiento."""
    model = Asiento
    form_class = AsientoForm
    template_name = 'fleet/asiento_form.html'
    success_message = "Asiento %(numero_asiento)s actualizado exitosamente."
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['bus'] = self.object.bus
        return kwargs
    
    def get_success_url(self):
        return reverse('fleet:asiento_list', kwargs={'bus_pk': self.object.bus.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bus'] = self.object.bus
        return context


class AsientoDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar un asiento."""
    model = Asiento
    template_name = 'fleet/asiento_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('fleet:asiento_list', kwargs={'bus_pk': self.object.bus.pk})
    
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request, 
                f"No se puede eliminar el asiento {self.get_object().numero_asiento} porque está relacionado "
                "con registros de ventas o reservas."
            )
            return self.get(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f"Asiento {self.object.numero_asiento} eliminado exitosamente.")
        return super().form_valid(form)


class ParadaCreateAjaxView(LoginRequiredMixin, CreateView):
    """Crear una nueva parada vía AJAX."""
    model = Parada
    form_class = ParadaForm
    
    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({
            'success': True,
            'id': self.object.id,
            'nombre': f"{self.object.nombre} ({self.object.localidad.nombre})",
            'empresa': self.object.empresa.nombre,
            'localidad': self.object.localidad.nombre,
        })
    
    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'errors': form.errors.as_json()
        })
