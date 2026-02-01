"""
Views for base project.
"""
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from users.models import Persona
from fleet.models import Empresa, Bus
from itineraries.models import Itinerario


class DashboardView(LoginRequiredMixin, TemplateView):
    """Vista principal del dashboard."""
    template_name = 'dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistics
        context['stats'] = {
            'personas': Persona.objects.count(),
            'buses': Bus.objects.filter(estado='activo').count(),
            'empresas': Empresa.objects.count(),
            'itinerarios': Itinerario.objects.filter(activo=True).count(),
        }
        
        # Last 5 registered personas
        context['ultimas_personas'] = Persona.objects.all()[:5]
        
        return context
