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
from django.db.models.deletion import ProtectedError

from django.http import HttpResponse
from .models import Itinerario, DetalleItinerario, Precio, Horario
from .forms import ItinerarioForm, DetalleItinerarioForm, PrecioForm, HorarioForm


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from operations.models import Viaje
        from django.utils import timezone
        
        hoy = timezone.now().date()
        context['proximos_viajes'] = Viaje.objects.filter(
            itinerario=self.object,
            fecha_viaje__gte=hoy
        ).select_related('bus', 'chofer', 'horario').prefetch_related('ayudantes').order_by('fecha_viaje', 'horario__hora_salida')[:10]
        return context



class ItinerarioCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Crear un nuevo itinerario."""
    model = Itinerario
    form_class = ItinerarioForm
    template_name = 'itineraries/itinerario_form.html'
    success_url = reverse_lazy('itineraries:itinerario_list')
    success_message = "Itinerario %(nombre)s creado exitosamente."

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['itineraries/partials/itinerario_form_modal.html']
        return [self.template_name]

    def form_valid(self, form):
        if self.request.headers.get('HX-Request'):
            import json
            self.object = form.save()
            messages.success(self.request, self.get_success_message(form.cleaned_data))
            response = HttpResponse(status=204)
            
            # Send the new data for potential selection
            data = {'id': self.object.id, 'nombre': self.object.nombre}
            response['HX-Trigger'] = json.dumps({'itinerarioCreated': data})
            
            # Check for explicit refresh
            if self.request.GET.get('refresh') == 'true':
                response['HX-Refresh'] = 'true'
            return response
        return super().form_valid(form)


class ItinerarioUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar un itinerario."""
    model = Itinerario
    form_class = ItinerarioForm
    template_name = 'itineraries/itinerario_form.html'
    success_url = reverse_lazy('itineraries:itinerario_list')
    success_message = "Itinerario %(nombre)s actualizado exitosamente."

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['itineraries/partials/itinerario_form_modal.html']
        return [self.template_name]

    def form_valid(self, form):
        if self.request.headers.get('HX-Request'):
            self.object = form.save()
            messages.success(self.request, self.get_success_message(form.cleaned_data))
            response = HttpResponse(status=204)
            response['HX-Refresh'] = 'true'
            return response
        return super().form_valid(form)


class ItinerarioDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar un itinerario."""
    model = Itinerario
    template_name = 'itineraries/itinerario_confirm_delete.html'
    success_url = reverse_lazy('itineraries:itinerario_list')
    
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request, 
                f"No se puede eliminar el itinerario '{self.get_object().nombre}' porque tiene registros "
                "relacionados protegidos (ej. viajes o ventas)."
            )
            return self.get(request, *args, **kwargs)

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
        
        # Para el modal de nueva parada
        from fleet.forms import ParadaForm
        from users.forms import LocalidadForm
        context['parada_form'] = ParadaForm()
        context['localidad_form'] = LocalidadForm()
        
        # Para el selector rápido de localidades
        from users.models import Localidad
        context['localidades'] = Localidad.objects.all().order_by('nombre').prefetch_related('paradas')
        
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
        
        # Para el modal de nueva parada
        from fleet.forms import ParadaForm
        from users.forms import LocalidadForm
        context['parada_form'] = ParadaForm()
        context['localidad_form'] = LocalidadForm()
        
        # Para el selector rápido de localidades
        from users.models import Localidad
        context['localidades'] = Localidad.objects.all().order_by('nombre').prefetch_related('paradas')
        
        return context


class DetalleItinerarioDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar una parada de un itinerario."""
    model = DetalleItinerario
    template_name = 'itineraries/detalle_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('itineraries:itinerario_detail', kwargs={'pk': self.object.itinerario.pk})
    
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request, 
                "No se puede eliminar esta parada del itinerario porque tiene registros relacionados protegidos."
            )
            return self.get(request, *args, **kwargs)

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
    
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request, 
                "No se puede eliminar este precio porque está siendo utilizado por ventas existentes."
            )
            return self.get(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, "Precio eliminado exitosamente.")
        return super().form_valid(form)


# =============================================================================
# HORARIO VIEWS
# =============================================================================

class HorarioListView(LoginRequiredMixin, ListView):
    """Lista de todos los horarios agrupados/filtrables por itinerario."""
    model = Horario
    template_name = 'itineraries/horario_list.html'
    context_object_name = 'horarios'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('itinerario')
        
        # Filtro por itinerario
        itinerario_id = self.request.GET.get('itinerario')
        if itinerario_id:
            queryset = queryset.filter(itinerario_id=itinerario_id)
        
        # Filtro por estado
        estado = self.request.GET.get('estado')
        if estado == 'activo':
            queryset = queryset.filter(activo=True)
        elif estado == 'inactivo':
            queryset = queryset.filter(activo=False)
        
        # Búsqueda
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(itinerario__nombre__icontains=search)
            )
        
        return queryset.order_by('itinerario__nombre', 'hora_salida')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['itinerarios'] = Itinerario.objects.filter(activo=True).order_by('nombre')
        context['itinerario_filter'] = self.request.GET.get('itinerario', '')
        context['estado_filter'] = self.request.GET.get('estado', '')
        context['search'] = self.request.GET.get('search', '')
        return context

class HorarioCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Agregar un horario a un itinerario."""
    model = Horario
    form_class = HorarioForm
    template_name = 'itineraries/horario_form.html'
    success_message = "Horario agregado exitosamente."
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if 'itinerario_pk' in self.kwargs:
            self.itinerario = get_object_or_404(Itinerario, pk=self.kwargs['itinerario_pk'])
            kwargs['itinerario'] = self.itinerario
        else:
            self.itinerario = None
        return kwargs
    
    def get_success_url(self):
        if self.itinerario:
            return reverse('itineraries:itinerario_detail', kwargs={'pk': self.itinerario.pk})
        return reverse('itineraries:horario_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['itinerario'] = self.itinerario
        return context


class HorarioDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar un horario de un itinerario."""
    model = Horario
    template_name = 'itineraries/horario_confirm_delete.html'
    
    def get_success_url(self):
        # Si venimos del detalle iterario volvemos ahi, si no a la lista
        referer = self.request.META.get('HTTP_REFERER', '')
        if 'horarios' in referer and 'nuevo' not in referer:
            return reverse('itineraries:horario_list')
        return reverse('itineraries:itinerario_detail', kwargs={'pk': self.object.itinerario.pk})
    
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request, 
                "No se puede eliminar este horario porque hay viajes programados con él."
            )
            return self.get(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, "Horario eliminado del itinerario.")
        return super().form_valid(form)
