"""
Views for itineraries app.
"""
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count

from .models import Itinerario, DetalleItinerario, Precio
from .forms import ItinerarioForm, DetalleItinerarioForm, PrecioForm


# =============================================================================
# ITINERARIO VIEWS
# =============================================================================

class ItinerarioListView(LoginRequiredMixin, ListView):
    """Lista de itinerarios."""
    model = Itinerario
    template_name = 'itineraries/itinerario_list.html'
    context_object_name = 'itinerarios'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = super().get_queryset().annotate(
            num_paradas=Count('detalles')
        )
        
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(ruta__icontains=search)
            )
        
        activo = self.request.GET.get('activo', '')
        if activo == '1':
            queryset = queryset.filter(activo=True)
        elif activo == '0':
            queryset = queryset.filter(activo=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['activo_filter'] = self.request.GET.get('activo', '')
        return context


class ItinerarioDetailView(LoginRequiredMixin, DetailView):
    """Detalle de un itinerario."""
    model = Itinerario
    template_name = 'itineraries/itinerario_detail.html'
    context_object_name = 'itinerario'


class ItinerarioCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Crear un nuevo itinerario."""
    model = Itinerario
    form_class = ItinerarioForm
    template_name = 'itineraries/itinerario_form.html'
    success_url = reverse_lazy('itineraries:itinerario_list')
    success_message = "Itinerario %(nombre)s creado exitosamente."


class ItinerarioUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar un itinerario."""
    model = Itinerario
    form_class = ItinerarioForm
    template_name = 'itineraries/itinerario_form.html'
    success_url = reverse_lazy('itineraries:itinerario_list')
    success_message = "Itinerario %(nombre)s actualizado exitosamente."


class ItinerarioDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar un itinerario."""
    model = Itinerario
    template_name = 'itineraries/itinerario_confirm_delete.html'
    success_url = reverse_lazy('itineraries:itinerario_list')
    
    def form_valid(self, form):
        messages.success(self.request, f"Itinerario {self.object.nombre} eliminado exitosamente.")
        return super().form_valid(form)


# =============================================================================
# DETALLE ITINERARIO VIEWS
# =============================================================================

class DetalleItinerarioCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Agregar una parada a un itinerario."""
    model = DetalleItinerario
    form_class = DetalleItinerarioForm
    template_name = 'itineraries/detalle_form.html'
    success_message = "Parada agregada exitosamente."
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.itinerario = get_object_or_404(Itinerario, pk=self.kwargs['itinerario_pk'])
        kwargs['itinerario'] = self.itinerario
        return kwargs
    
    def form_valid(self, form):
        form.instance.itinerario = self.itinerario
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('itineraries:itinerario_detail', kwargs={'pk': self.kwargs['itinerario_pk']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['itinerario'] = self.itinerario
        return context


class DetalleItinerarioUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar una parada de un itinerario."""
    model = DetalleItinerario
    form_class = DetalleItinerarioForm
    template_name = 'itineraries/detalle_form.html'
    success_message = "Parada actualizada exitosamente."
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['itinerario'] = self.object.itinerario
        return kwargs
    
    def get_success_url(self):
        return reverse('itineraries:itinerario_detail', kwargs={'pk': self.object.itinerario.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['itinerario'] = self.object.itinerario
        return context


class DetalleItinerarioDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar una parada de un itinerario."""
    model = DetalleItinerario
    template_name = 'itineraries/detalle_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('itineraries:itinerario_detail', kwargs={'pk': self.object.itinerario.pk})
    
    def form_valid(self, form):
        messages.success(self.request, "Parada eliminada del itinerario.")
        return super().form_valid(form)


# =============================================================================
# PRECIO VIEWS
# =============================================================================

class PrecioListView(LoginRequiredMixin, ListView):
    """Lista de precios."""
    model = Precio
    template_name = 'itineraries/precio_list.html'
    context_object_name = 'precios'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('itinerario', 'origen', 'destino')
        
        itinerario = self.request.GET.get('itinerario', '')
        if itinerario:
            queryset = queryset.filter(itinerario_id=itinerario)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['itinerario_filter'] = self.request.GET.get('itinerario', '')
        context['itinerarios'] = Itinerario.objects.all()
        return context


class PrecioCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Crear un nuevo precio."""
    model = Precio
    form_class = PrecioForm
    template_name = 'itineraries/precio_form.html'
    success_url = reverse_lazy('itineraries:precio_list')
    success_message = "Precio creado exitosamente."


class PrecioUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar un precio."""
    model = Precio
    form_class = PrecioForm
    template_name = 'itineraries/precio_form.html'
    success_url = reverse_lazy('itineraries:precio_list')
    success_message = "Precio actualizado exitosamente."


class PrecioDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar un precio."""
    model = Precio
    template_name = 'itineraries/precio_confirm_delete.html'
    success_url = reverse_lazy('itineraries:precio_list')
    
    def form_valid(self, form):
        messages.success(self.request, "Precio eliminado exitosamente.")
        return super().form_valid(form)
