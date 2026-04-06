"""
Views for base project.
"""
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from users.models import Persona
from fleet.models import Empresa, Bus
from itineraries.models import Itinerario
from operations.models import Viaje


from django.shortcuts import redirect


class DashboardView(LoginRequiredMixin, TemplateView):
    """Vista principal del dashboard."""
    template_name = 'dashboard.html'
    
    def get(self, request, *args, **kwargs):
        # Redirigir según el rol de la Persona vinculada al usuario
        persona = getattr(request.user, 'persona', None)
        if persona:
            # Si es staff o superuser, ver el panel administrativo (default)
            if request.user.is_staff or request.user.is_superuser:
                return super().get(request, *args, **kwargs)
            
            # Si es Ayudante o Chofer, redirigir a su panel operativo
            if persona.es_ayudante or persona.es_chofer:
                return redirect('operations:dashboard_ayudante')
            
            # Si es Cliente (y no es nada de lo anterior), redirigir a su panel de cliente
            if persona.es_cliente:
                return redirect('users:dashboard_cliente')
        
        return super().get(request, *args, **kwargs)


    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics
        context['stats'] = {
            'personas': Persona.objects.count(),
            'buses': Bus.objects.filter(estado='activo').count(),
            'empresas': Empresa.objects.count(),
            'itinerarios': Itinerario.objects.filter(activo=True).count(),
        }
        
        # Recent items
        context['ultimas_personas'] = Persona.objects.all()[:5]
        context['ultimos_buses'] = Bus.objects.select_related('empresa').order_by('-pk')[:5]
        context['ultimas_empresas'] = Empresa.objects.order_by('-pk')[:5]
        context['ultimos_itinerarios'] = Itinerario.objects.select_related('empresa').order_by('-pk')[:5]
        
        context['ultimos_viajes'] = Viaje.objects.select_related(
            'itinerario', 'bus', 'chofer', 'horario', 'empresa'
        ).order_by('-created_at')[:5]
        
        return context

