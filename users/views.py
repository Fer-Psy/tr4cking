"""
Views for users app.
"""
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth import login
from django.http import HttpResponse, JsonResponse
from .models import Persona, Localidad
from .forms import PersonaForm, LocalidadForm, ClienteRegistroForm, ClientePerfilForm


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
        
        # Filtro de seguridad: Ayudantes y Choferes solo pueden ver clientes
        user_persona = getattr(self.request.user, 'persona', None)
        if user_persona and (user_persona.es_chofer or user_persona.es_ayudante):
            queryset = queryset.filter(es_cliente=True)
        
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
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user_is_admin'] = self.request.user.is_superuser or self.request.user.is_staff
        return kwargs


class PersonaUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Editar una persona existente."""
    model = Persona
    form_class = PersonaForm
    template_name = 'users/persona_form.html'
    success_url = reverse_lazy('users:persona_list')
    success_message = "Persona %(nombre)s %(apellido)s actualizada exitosamente."
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user_is_admin'] = self.request.user.is_superuser or self.request.user.is_staff
        return kwargs
    
    def get_initial(self):
        initial = super().get_initial()
        if self.object.user:
            initial['username'] = self.object.user.username
        return initial



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


class ClienteRegistroView(SuccessMessageMixin, CreateView):
    """Vista pública para que nuevos clientes se registren."""
    model = Persona
    form_class = ClienteRegistroForm
    template_name = 'auth/register.html'
    success_url = reverse_lazy('users:dashboard_cliente')
    success_message = "¡Registro exitoso! Ya puedes utilizar el sistema como cliente."
    
    def get_template_names(self):
        if 'HX-Request' in self.request.headers:
            return ['auth/partials/register_modal.html']
        return [self.template_name]
        
    def form_valid(self, form):
        self.object = form.save()
        # Loguear automáticamente al nuevo usuario
        login(self.request, self.object.user)
        
        if 'HX-Request' in self.request.headers:
            response = HttpResponse()
            response['HX-Redirect'] = self.get_success_url()
            return response
            
        return super().form_valid(form)
    
    def form_invalid(self, form):
        # Si falla en modo HTMX, debe regresar el parcial para mostrar errores en el modal
        if 'HX-Request' in self.request.headers:
            return self.render_to_response(self.get_context_data(form=form))
        return super().form_invalid(form)


class DashboardClienteView(LoginRequiredMixin, TemplateView):
    """Panel de control principal para el cliente final."""
    template_name = 'users/dashboard_cliente.html'
    
    def get_context_data(self, **kwargs):
        from operations.utils import limpiar_reservas_expiradas
        limpiar_reservas_expiradas()
        
        context = super().get_context_data(**kwargs)
        persona = getattr(self.request.user, 'persona', None)
        
        # En caso de que no tenga objeto Persona vinculado (ej: admin nuevo)
        if not persona:
            messages.warning(self.request, "Tu cuenta no tiene un perfil de cliente vinculado.")
            return context
            
        # Estadísticas del cliente
        from operations.models import Pasaje, Encomienda, Viaje
        
        context['pasajes_recientes'] = Pasaje.objects.filter(pasajero=persona).order_by('-fecha_venta')[:5]
        context['encomiendas_recientes'] = Encomienda.objects.filter(remitente=persona).order_by('-fecha_registro')[:5]
        
        ahora = timezone.now()
        hoy = ahora.date()
        hora_actual = ahora.time()
        
        # Viajes sugeridos omitidos para optimizar rendimiento
        # context['proximos_viajes'] = ...
        
        return context

class ClientePerfilUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Vista para que el cliente actualice sus propios datos."""
    model = Persona
    form_class = ClientePerfilForm
    template_name = 'users/perfil_form.html'
    success_url = reverse_lazy('users:dashboard_cliente')
    success_message = "Tu perfil ha sido actualizado correctamente."
    
    def get_object(self, queryset=None):
        return get_object_or_404(Persona, user=self.request.user)
    
    def form_valid(self, form):
        # Si cambió la contraseña, necesitamos re-loguear (opcional pero recomendado en algunos sistemas)
        # para evitar que la sesión expire inmediatamente, pero Django 
        # generalmente mantiene la sesión si usamos UpdateView estándar.
        from django.contrib.auth import update_session_auth_hash
        response = super().form_valid(form)
        if form.cleaned_data.get('password'):
            update_session_auth_hash(self.request, self.request.user)
        return response
