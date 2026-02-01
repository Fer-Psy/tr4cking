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


class ParadaUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar una parada."""
    model = Parada
    form_class = ParadaForm
    template_name = 'fleet/parada_form.html'
    success_url = reverse_lazy('fleet:parada_list')
    success_message = "Parada %(nombre)s actualizada exitosamente."


class ParadaDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar una parada."""
    model = Parada
    template_name = 'fleet/parada_confirm_delete.html'
    success_url = reverse_lazy('fleet:parada_list')
    
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
    """Crear un nuevo bus."""
    model = Bus
    form_class = BusForm
    template_name = 'fleet/bus_form.html'
    success_url = reverse_lazy('fleet:bus_list')
    success_message = "Bus %(placa)s creado exitosamente."


class BusUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar un bus."""
    model = Bus
    form_class = BusForm
    template_name = 'fleet/bus_form.html'
    success_url = reverse_lazy('fleet:bus_list')
    success_message = "Bus %(placa)s actualizado exitosamente."


class BusDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar un bus."""
    model = Bus
    template_name = 'fleet/bus_confirm_delete.html'
    success_url = reverse_lazy('fleet:bus_list')
    
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
    
    def form_valid(self, form):
        messages.success(self.request, f"Asiento {self.object.numero_asiento} eliminado exitosamente.")
        return super().form_valid(form)
