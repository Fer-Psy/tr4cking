"""
Views for users app.
"""
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.contrib import messages

from .models import Persona, Localidad
from .forms import PersonaForm, LocalidadForm


# =============================================================================
# PERSONA VIEWS
# =============================================================================

class PersonaListView(LoginRequiredMixin, ListView):
    """Lista de personas."""
    model = Persona
    template_name = 'users/persona_list.html'
    context_object_name = 'personas'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search filter
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                models.Q(cedula__icontains=search) |
                models.Q(nombre__icontains=search) |
                models.Q(apellido__icontains=search) |
                models.Q(telefono__icontains=search)
            )
        
        # Role filter
        rol = self.request.GET.get('rol', '')
        if rol == 'empleado':
            queryset = queryset.filter(es_empleado=True)
        elif rol == 'cliente':
            queryset = queryset.filter(es_cliente=True)
        elif rol == 'pasajero':
            queryset = queryset.filter(es_pasajero=True)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['rol'] = self.request.GET.get('rol', '')
        return context


class PersonaDetailView(LoginRequiredMixin, DetailView):
    """Detalle de una persona."""
    model = Persona
    template_name = 'users/persona_detail.html'
    context_object_name = 'persona'


class PersonaCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Crear una nueva persona."""
    model = Persona
    form_class = PersonaForm
    template_name = 'users/persona_form.html'
    success_url = reverse_lazy('users:persona_list')
    success_message = "Persona %(nombre)s %(apellido)s creada exitosamente."


class PersonaUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar una persona existente."""
    model = Persona
    form_class = PersonaForm
    template_name = 'users/persona_form.html'
    success_url = reverse_lazy('users:persona_list')
    success_message = "Persona %(nombre)s %(apellido)s actualizada exitosamente."


class PersonaDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar una persona."""
    model = Persona
    template_name = 'users/persona_confirm_delete.html'
    success_url = reverse_lazy('users:persona_list')
    
    def form_valid(self, form):
        messages.success(self.request, f"Persona {self.object.nombre_completo} eliminada exitosamente.")
        return super().form_valid(form)


# =============================================================================
# LOCALIDAD VIEWS
# =============================================================================

class LocalidadListView(LoginRequiredMixin, ListView):
    """Lista de localidades."""
    model = Localidad
    template_name = 'users/localidad_list.html'
    context_object_name = 'localidades'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Search filter
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(nombre__icontains=search)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        return context


class LocalidadDetailView(LoginRequiredMixin, DetailView):
    """Detalle de una localidad."""
    model = Localidad
    template_name = 'users/localidad_detail.html'
    context_object_name = 'localidad'


class LocalidadCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Crear una nueva localidad."""
    model = Localidad
    form_class = LocalidadForm
    template_name = 'users/localidad_form.html'
    success_url = reverse_lazy('users:localidad_list')
    success_message = "Localidad %(nombre)s creada exitosamente."


class LocalidadUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar una localidad existente."""
    model = Localidad
    form_class = LocalidadForm
    template_name = 'users/localidad_form.html'
    success_url = reverse_lazy('users:localidad_list')
    success_message = "Localidad %(nombre)s actualizada exitosamente."


class LocalidadDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar una localidad."""
    model = Localidad
    template_name = 'users/localidad_confirm_delete.html'
    success_url = reverse_lazy('users:localidad_list')
    
    def form_valid(self, form):
        messages.success(self.request, f"Localidad {self.object.nombre} eliminada exitosamente.")
        return super().form_valid(form)
