"""
Views for itineraries app.
"""
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from base.mixins import AdminOnlyMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy, reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q, Count
from django.db.models.deletion import ProtectedError

from django.http import HttpResponse, JsonResponse
from .models import Itinerario, DetalleItinerario, Precio, Horario
from .forms import ItinerarioForm, DetalleItinerarioForm, PrecioForm, HorarioForm, ItinerarioAddHorarioForm


# =============================================================================
# ITINERARIO VIEWS
# =============================================================================

class ItinerarioListView(AdminOnlyMixin, ListView):
    """Lista de itinerarios."""
    model = Itinerario
    template_name = 'itineraries/itinerario_list.html'
    context_object_name = 'itinerarios'
    paginate_by = 15
    
    def get_queryset(self):
        queryset = super().get_queryset().annotate(
            num_paradas=Count('detalles', distinct=True)
        ).distinct()
        
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(ruta__icontains=search)
            )
        
        estado = self.request.GET.get('estado', 'activos')
        if estado == 'inactivos':
            queryset = queryset.filter(activo=False)
        elif estado == 'todos':
            pass
        else:
            queryset = queryset.filter(activo=True)
        
        empresa_id = self.request.GET.get('empresa', '')
        if empresa_id:
            queryset = queryset.filter(empresa_id=empresa_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['estado'] = self.request.GET.get('estado', 'activos')
        context['empresa_filter'] = self.request.GET.get('empresa', '')
        
        from fleet.models import Empresa
        context['empresas'] = Empresa.objects.all()
        
        # Para los modales de creación rápida
        from fleet.forms import ParadaForm
        from users.forms import LocalidadForm
        context['parada_form'] = ParadaForm()
        context['localidad_form'] = LocalidadForm()
        
        return context


class ItinerarioDetailView(AdminOnlyMixin, DetailView):
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



class ItinerarioCreateView(AdminOnlyMixin, SuccessMessageMixin, CreateView):
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from fleet.forms import ParadaForm
        from users.forms import LocalidadForm
        context['parada_form'] = ParadaForm()
        context['localidad_form'] = LocalidadForm()
        return context

    def form_valid(self, form):
        self.object = form.save()
        
        # Crear paradas iniciales si se proporcionaron en el formulario
        parada_origen = form.cleaned_data.get('parada_origen')
        
        if parada_origen:
            DetalleItinerario.objects.get_or_create(
                itinerario=self.object,
                parada=parada_origen,
                defaults={'orden': 1, 'minutos_desde_origen': 0}
            )

        if self.request.headers.get('HX-Request'):
            import json
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

    def form_invalid(self, form):
        with open('last_validation_errors.txt', 'w', encoding='utf-8') as f:
            f.write(f"Errors: {form.errors.as_json()}\n")
            f.write(f"Data: {form.data}\n")
        return super().form_invalid(form)


class ItinerarioUpdateView(AdminOnlyMixin, SuccessMessageMixin, UpdateView):
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from fleet.forms import ParadaForm
        from users.forms import LocalidadForm
        context['parada_form'] = ParadaForm()
        context['localidad_form'] = LocalidadForm()
        return context

    def form_valid(self, form):
        self.object = form.save()
        
        # Guardar/Actualizar parada de origen si se proporcionó o modificó
        parada_origen = form.cleaned_data.get('parada_origen')
        primera = self.object.primera_parada
        
        if parada_origen:
            if primera:
                if primera.parada != parada_origen:
                    primera.parada = parada_origen
                    primera.save()
            else:
                DetalleItinerario.objects.create(
                    itinerario=self.object,
                    parada=parada_origen,
                    orden=1,
                    minutos_desde_origen=0
                )
        elif primera:
            primera.delete()

        if self.request.headers.get('HX-Request'):
            import json
            messages.success(self.request, self.get_success_message(form.cleaned_data))
            response = HttpResponse(status=204)
            
            # Send the updated data for potential selection/updating
            data = {'id': self.object.id, 'nombre': self.object.nombre}
            response['HX-Trigger'] = json.dumps({'itinerarioUpdated': data})
            
            # Check for explicit refresh or default to refresh for list view consistency
            if self.request.GET.get('refresh') == 'true' or not self.request.GET.get('refresh'):
                response['HX-Refresh'] = 'true'
            return response
            
        from django.http import HttpResponseRedirect
        messages.success(self.request, self.get_success_message(form.cleaned_data))
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        with open('last_validation_errors.txt', 'w', encoding='utf-8') as f:
            f.write(f"Errors: {form.errors.as_json()}\n")
            f.write(f"Data: {form.data}\n")
        return super().form_invalid(form)


class ItinerarioDeleteView(AdminOnlyMixin, DeleteView):
    """Eliminar un itinerario."""
    model = Itinerario
    template_name = 'itineraries/itinerario_confirm_delete.html'
    success_url = reverse_lazy('itineraries:itinerario_list')
    
    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except ProtectedError:
            self.object = self.get_object()
            if request.user.is_superuser or request.user.is_staff:
                messages.error(
                    request, 
                    f"No se puede eliminar el itinerario '{self.object.nombre}' porque tiene registros "
                    "relacionados protegidos (ej. viajes o ventas). "
                    "Como administrador, puedes dar de baja este itinerario para inactivarlo del sistema."
                )
                context = self.get_context_data(object=self.object, show_deactivate=True)
                return self.render_to_response(context)
            else:
                messages.error(
                    request, 
                    f"No se puede eliminar el itinerario '{self.object.nombre}' porque tiene registros "
                    "relacionados protegidos (ej. viajes o ventas)."
                )
                return self.get(request, *args, **kwargs)

    def form_valid(self, form):
        nombre = self.object.nombre
        response = super().form_valid(form)
        messages.success(self.request, f"Itinerario {nombre} eliminado exitosamente.")
        return response


class ItinerarioDarDeBajaView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Dar de baja a un itinerario."""
    
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff
        
    def post(self, request, pk, *args, **kwargs):
        itinerario = get_object_or_404(Itinerario, pk=pk)
        itinerario.activo = False
        itinerario.save()
            
        messages.success(request, f"Itinerario '{itinerario.nombre}' ha sido dado de baja exitosamente.")
        return redirect('itineraries:itinerario_list')


class ItinerarioActivarView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Reactivar a un itinerario dado de baja."""
    
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff
        
    def post(self, request, pk, *args, **kwargs):
        itinerario = get_object_or_404(Itinerario, pk=pk)
        itinerario.activo = True
        itinerario.save()
            
        messages.success(request, f"Itinerario '{itinerario.nombre}' ha sido reactivado exitosamente.")
        return redirect('itineraries:itinerario_list')


# =============================================================================
# DETALLE ITINERARIO VIEWS
# =============================================================================

class DetalleItinerarioCreateView(AdminOnlyMixin, SuccessMessageMixin, CreateView):
    """Agregar una parada a un itinerario."""
    model = DetalleItinerario
    form_class = DetalleItinerarioForm
    template_name = 'itineraries/detalle_form.html'
    success_message = "Parada agregada exitosamente."
    
    def get_initial(self):
        initial = super().get_initial()
        itinerario = get_object_or_404(Itinerario, pk=self.kwargs['itinerario_pk'])
        ultimo_detalle = itinerario.detalles.order_by('-orden').first()
        initial['orden'] = (ultimo_detalle.orden + 1) if ultimo_detalle else 1
        return initial

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
        from users.models import Localidad
        from users.forms import LocalidadForm
        context['parada_form'] = ParadaForm(initial={'empresa': self.itinerario.empresa})
        context['localidad_form'] = LocalidadForm()
        
        # Para el selector rápido de localidades (filtrado por empresa)
        from users.models import Localidad
        from fleet.models import Parada
        from django.db.models import Prefetch
        
        pref_paradas = Prefetch(
            'paradas', 
            queryset=Parada.objects.filter(empresa=self.itinerario.empresa).order_by('nombre')
        )
        context['localidades'] = Localidad.objects.prefetch_related(pref_paradas).order_by('nombre')
        
        return context


class DetalleItinerarioUpdateView(AdminOnlyMixin, SuccessMessageMixin, UpdateView):
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
        from users.models import Localidad
        from users.forms import LocalidadForm
        context['parada_form'] = ParadaForm(initial={'empresa': self.object.itinerario.empresa})
        context['localidad_form'] = LocalidadForm()
        
        # Para el selector rápido de localidades (filtrado por empresa)
        from users.models import Localidad
        from fleet.models import Parada
        from django.db.models import Prefetch
        
        pref_paradas = Prefetch(
            'paradas', 
            queryset=Parada.objects.filter(empresa=self.object.itinerario.empresa).order_by('nombre')
        )
        context['localidades'] = Localidad.objects.prefetch_related(pref_paradas).order_by('nombre')
        
        return context


class DetalleItinerarioDeleteView(AdminOnlyMixin, DeleteView):
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
        response = super().form_valid(form)
        messages.success(self.request, "Parada eliminada del itinerario.")
        return response


# =============================================================================
# PRECIO VIEWS
# =============================================================================

class PrecioListView(AdminOnlyMixin, ListView):
    """Lista de precios."""
    model = Precio
    template_name = 'itineraries/precio_list.html'
    context_object_name = 'precios'
    paginate_by = 20
    
    def get_queryset(self):
        qs = super().get_queryset().select_related('origen', 'destino', 'origen__localidad', 'destino__localidad')
        q = self.request.GET.get('q')
        if q:
            from django.db.models import Q
            qs = qs.filter(
                Q(origen__nombre__icontains=q) | 
                Q(destino__nombre__icontains=q) |
                Q(origen__localidad__nombre__icontains=q) |
                Q(destino__localidad__nombre__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '')
        return context


class PrecioCreateView(AdminOnlyMixin, SuccessMessageMixin, CreateView):
    """Crear un nuevo precio."""
    model = Precio
    form_class = PrecioForm
    template_name = 'itineraries/precio_form.html'
    success_url = reverse_lazy('itineraries:precio_list')
    success_message = "Precio creado exitosamente."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from fleet.models import Parada
        context['paradas'] = Parada.objects.all().select_related('localidad', 'empresa').order_by('localidad__nombre', 'nombre')
        return context


class PrecioUpdateView(AdminOnlyMixin, SuccessMessageMixin, UpdateView):
    """Editar un precio."""
    model = Precio
    form_class = PrecioForm
    template_name = 'itineraries/precio_form.html'
    success_url = reverse_lazy('itineraries:precio_list')
    success_message = "Precio actualizado exitosamente."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from fleet.models import Parada
        context['paradas'] = Parada.objects.all().select_related('localidad', 'empresa').order_by('localidad__nombre', 'nombre')
        return context


class PrecioDeleteView(AdminOnlyMixin, DeleteView):
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
        response = super().form_valid(form)
        messages.success(self.request, "Precio eliminado exitosamente.")
        return response


# =============================================================================
# HORARIO VIEWS
# =============================================================================

class HorarioListView(AdminOnlyMixin, ListView):
    """Lista de todos los horarios agrupados/filtrables por itinerario."""
    model = Horario
    template_name = 'itineraries/horario_list.html'
    context_object_name = 'horarios'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtro por estado
        estado = self.request.GET.get('estado')
        if estado == 'activo':
            queryset = queryset.filter(activo=True)
        elif estado == 'inactivo':
            queryset = queryset.filter(activo=False)
        
        return queryset.order_by('hora_salida')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['estado_filter'] = self.request.GET.get('estado', '')
        return context

class ItinerarioAddHorarioView(AdminOnlyMixin, SuccessMessageMixin, FormView):
    """Vista para agregar horarios existentes a un itinerario."""
    template_name = 'itineraries/itinerario_add_horario.html'
    form_class = ItinerarioAddHorarioForm
    success_message = "Horarios agregados exitosamente al itinerario."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        self.itinerario = get_object_or_404(Itinerario, pk=self.kwargs['itinerario_pk'])
        kwargs['itinerario'] = self.itinerario
        return kwargs

    def form_valid(self, form):
        horarios = form.cleaned_data['horarios']
        self.itinerario.horarios.add(*horarios)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('itineraries:itinerario_detail', kwargs={'pk': self.itinerario.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['itinerario'] = self.itinerario
        return context

class HorarioCreateView(AdminOnlyMixin, SuccessMessageMixin, CreateView):
    """Crear un nuevo horario general."""
    model = Horario
    form_class = HorarioForm
    template_name = 'itineraries/horario_form.html'
    success_message = "Horario agregado exitosamente."
    
    def get_success_url(self):
        return reverse('itineraries:horario_list')


class HorarioUpdateView(AdminOnlyMixin, SuccessMessageMixin, UpdateView):
    """Editar un horario existente."""
    model = Horario
    form_class = HorarioForm
    template_name = 'itineraries/horario_form.html'
    success_message = "Horario actualizado exitosamente."
    
    def get_success_url(self):
        return reverse('itineraries:horario_list')


class HorarioDeleteView(AdminOnlyMixin, DeleteView):
    """Eliminar un horario de un itinerario."""
    model = Horario
    template_name = 'itineraries/horario_confirm_delete.html'
    
    def get_success_url(self):
        return reverse('itineraries:horario_list')
    
    def form_valid(self, form):
        try:
            self.object = self.get_object()
            response = super().form_valid(form)
            messages.success(self.request, "Horario eliminado del itinerario.")
            return response
        except ProtectedError:
            messages.error(
                self.request, 
                "No se puede eliminar este horario porque hay viajes programados con él."
            )
            return redirect(self.get_success_url())
        except Exception as e:
            messages.error(
                self.request,
                f"Ocurrió un error al intentar eliminar: {str(e)}"
            )
            return redirect(self.get_success_url())


class HorarioCreateAjaxView(AdminOnlyMixin, CreateView):
    """Crear un nuevo horario vía AJAX."""
    model = Horario
    form_class = HorarioForm
    
    def form_valid(self, form):
        self.object = form.save()
        return JsonResponse({
            'success': True,
            'id': self.object.id,
            'hora': self.object.hora_salida.strftime('%H:%M'),
        })
    
    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'errors': form.errors.as_text()
        })


from fleet.models import Parada

def obtener_paradas_empresa(request):
    empresa_id = request.GET.get('empresa')
    if empresa_id:
        try:
            paradas = Parada.objects.filter(empresa_id=int(empresa_id)).select_related('localidad').order_by('localidad__nombre', 'nombre')
        except (ValueError, TypeError):
            paradas = Parada.objects.none()
    else:
        paradas = Parada.objects.all().select_related('localidad', 'empresa').order_by('localidad__nombre', 'nombre')
        
    options = ['<option value="">---------</option>']
    for p in paradas:
        if empresa_id:
            label = f"{p.localidad.nombre}: {p.nombre}"
        else:
            label = f"{p.localidad.nombre}: {p.nombre} ({p.empresa.nombre})"
        options.append(f'<option value="{p.id}">{label}</option>')
        
    return HttpResponse('\n'.join(options))


def verificar_itinerario_duplicado(request):
    """Endpoint AJAX para verificar si ya existe un itinerario con el mismo nombre y empresa."""
    empresa_id = request.GET.get('empresa', '').strip()
    nombre = request.GET.get('nombre', '').strip()
    exclude_pk = request.GET.get('exclude_pk', '').strip()
    
    if not empresa_id or not nombre:
        return JsonResponse({'exists': False})
    
    try:
        qs = Itinerario.objects.filter(
            empresa_id=int(empresa_id),
            nombre__iexact=nombre
        )
        if exclude_pk:
            qs = qs.exclude(pk=int(exclude_pk))
        
        if qs.exists():
            itinerario = qs.first()
            return JsonResponse({
                'exists': True,
                'message': f"Ya existe el itinerario '{itinerario.nombre}' para esta empresa."
            })
    except (ValueError, TypeError):
        pass
    
    return JsonResponse({'exists': False})

