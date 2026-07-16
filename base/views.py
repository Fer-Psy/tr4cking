"""
Views for base project.
"""
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from users.models import Persona
from fleet.models import Empresa, Bus
from itineraries.models import Itinerario
from operations.models import Viaje, Factura, Pasaje, Encomienda, SesionCaja
from django.utils import timezone


from django.shortcuts import redirect
from django.http import HttpResponse

def debug_view_2(request):
    from operations.models import Encomienda
    encs = Encomienda.objects.filter(codigo__icontains='030')
    out = []
    for enc in encs:
        s = f"ID: {enc.id}, Codigo: {enc.codigo}, Estado: {enc.estado}, Viaje ID: {enc.viaje_id}"
        if enc.viaje:
            s += f" | Viaje: {enc.viaje.estado}, Fecha: {enc.viaje.fecha_viaje}"
        out.append(s)
    
    if not out:
        out = ["No found 030"]
    return HttpResponse('<br>'.join(out))

def debug_view(request):
    from operations.models import Viaje
    from itineraries.models import DetalleItinerario, Precio
    out = []
    viaje = Viaje.objects.filter(id=197).first()
    if viaje:
        out.append(f"Viaje: 197, Itinerario: {viaje.itinerario.nombre}")
        detalles = list(DetalleItinerario.objects.filter(itinerario=viaje.itinerario).order_by('orden'))
        for d in detalles:
            out.append(f"Orden: {d.orden}, ID: {d.parada_id}, Nombre: {d.parada.nombre}")
    return HttpResponse('<br>'.join(out))


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
                
            # Si es agente, usar un dashboard personalizado
            if persona.es_agente:
                self.template_name = 'dashboard_agente.html'
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
        
        persona = getattr(self.request.user, 'persona', None)
        
        # Contexto específico para el Agente Comercial
        if persona and persona.es_agente and not (self.request.user.is_staff or self.request.user.is_superuser):
            hoy = timezone.now().date()
            ahora = timezone.localtime(timezone.now())
            
            context['stats'] = {
                'facturas_hoy': Factura.objects.filter(fecha_emision__date=hoy).count(),
                'pasajes_hoy': Pasaje.objects.filter(fecha_venta__date=hoy).count(),
                'encomiendas_hoy': Encomienda.objects.filter(fecha_registro__date=hoy).count(),
                'caja_abierta': SesionCaja.objects.filter(cajero=self.request.user, estado='abierta').exists(),
            }
            
            # Alerta de cierre de caja próximo (después de las 20:00)
            sesion_abierta = SesionCaja.objects.filter(
                cajero=self.request.user, estado='abierta'
            ).first()
            if sesion_abierta and ahora.hour >= 20:
                context['alerta_cierre_caja'] = True
                context['hora_limite_caja'] = 23
            
            context['ultimas_facturas'] = Factura.objects.order_by('-fecha_emision')[:5]
            context['ultimos_pasajes'] = Pasaje.objects.select_related('viaje', 'pasajero').order_by('-fecha_venta')[:5]
            context['ultimas_encomiendas'] = Encomienda.objects.select_related('viaje', 'remitente', 'destinatario').order_by('-fecha_registro')[:5]
            
            context['viajes_hoy'] = Viaje.objects.filter(fecha_viaje=hoy, estado='programado').select_related(
                'itinerario', 'bus', 'horario', 'empresa'
            ).order_by('horario__hora_salida')
            
            return context
        
        # Statistics (General para Admin)
        context['stats'] = {
            'personas': Persona.objects.count(),
            'buses': Bus.objects.filter(estado='activo').count(),
            'empresas': Empresa.objects.count(),
            'itinerarios': Itinerario.objects.filter(activo=True).count(),
        }
        
        from django.db.models import Q
        context['ultimas_personas'] = Persona.objects.filter(
            activo=True
        ).filter(
            Q(es_chofer=True) | Q(es_ayudante=True) | Q(es_agente=True) | Q(es_empleado=True)
        )[:5]
        context['ultimos_buses'] = Bus.objects.select_related('empresa').order_by('-pk')[:5]
        context['ultimas_empresas'] = Empresa.objects.order_by('-pk')[:5]
        context['ultimos_itinerarios'] = Itinerario.objects.select_related('empresa').order_by('-pk')[:5]
        
        context['ultimos_viajes'] = Viaje.objects.select_related(
            'itinerario', 'bus', 'chofer', 'horario', 'empresa'
        ).order_by('-created_at')[:5]
        
        return context

