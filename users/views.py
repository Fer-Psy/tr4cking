"""
Views for users app.
"""
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
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
                Q(cedula__icontains=search) |
                Q(nombre__icontains=search) |
                Q(apellido__icontains=search) |
                Q(telefono__icontains=search)
            )
        
        # Role filter
        rol = self.request.GET.get('rol', '')
        if rol == 'empleado':
            queryset = queryset.filter(es_empleado=True)
        elif rol == 'cliente':
            queryset = queryset.filter(es_cliente=True)
        elif rol == 'pasajero':
            queryset = queryset.filter(es_pasajero=True)
        elif rol == 'chofer':
            queryset = queryset.filter(es_chofer=True)
        elif rol == 'ayudante':
            queryset = queryset.filter(es_ayudante=True)
        
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
    
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request, 
                f"No se puede eliminar a '{self.get_object().nombre_completo}' porque tiene registros "
                "relacionados que están protegidos (ej. ventas o asignaciones)."
            )
            return self.get(request, *args, **kwargs)

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
    
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            messages.error(
                request, 
                f"No se puede eliminar la localidad '{self.get_object().nombre}' porque está siendo utilizada "
                "por paradas u otros registros protegidos."
            )
            return self.get(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f"Localidad {self.object.nombre} eliminada exitosamente.")
        return super().form_valid(form)


class LocalidadCreateAjaxView(LoginRequiredMixin, CreateView):
    """Crear una nueva localidad vía AJAX."""
    model = Localidad
    form_class = LocalidadForm
    
    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({
            'success': True,
            'id': self.object.id,
            'nombre': self.object.nombre
        }, status=201)
        
    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)


def get_localidad_coords_ajax(request, pk):
    """Retorna las coordenadas de una localidad en formato JSON."""
    try:
        localidad = Localidad.objects.get(pk=pk)
        return JsonResponse({
            'success': True,
            'latitud': float(localidad.latitud) if localidad.latitud else None,
            'longitud': float(localidad.longitud) if localidad.longitud else None,
            'nombre': localidad.nombre
        })
    except Localidad.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Localidad no encontrada'}, status=404)
