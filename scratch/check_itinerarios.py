import os
import django
import sys

# Setup django
sys.path.append('c:\\Users\\carol\\Downloads\\tr4cking-app\\tr4cking')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from itineraries.models import DetalleItinerario, Parada
from operations.models import Viaje
from django.utils import timezone

# IDs from the form (I'll try to find them or use names)
# Origen: San Lorenzo
# Destino: Terminal Coronel Oviedo

p_origen = Parada.objects.filter(nombre__icontains='San Lorenzo').first()
p_destino = Parada.objects.filter(nombre__icontains='Coronel Oviedo').first()

print(f"Origen: {p_origen} (ID: {p_origen.id if p_origen else 'None'})")
print(f"Destino: {p_destino} (ID: {p_destino.id if p_destino else 'None'})")

if p_origen and p_destino:
    detalles_origen = DetalleItinerario.objects.filter(parada=p_origen)
    detalles_destino = DetalleItinerario.objects.filter(parada=p_destino)
    
    itinerarios_compatibles_ids = []
    origen_map = {d.itinerario_id: d.orden for d in detalles_origen}
    
    for d_dest in detalles_destino:
        it_id = d_dest.itinerario_id
        if it_id in origen_map:
            if origen_map[it_id] < d_dest.orden:
                itinerarios_compatibles_ids.append(it_id)
                
    print(f"Itinerarios compatibles: {itinerarios_compatibles_ids}")
    
    ahora_local = timezone.localtime(timezone.now())
    hoy = ahora_local.date()
    hora_actual = ahora_local.time()
    
    print(f"Hoy local: {hoy}, Hora local: {hora_actual}")
    
    viajes = Viaje.objects.filter(
        itinerario_id__in=itinerarios_compatibles_ids,
        fecha_viaje__gte=hoy,
        estado__in=['programado', 'en_curso']
    ).select_related('itinerario', 'bus', 'horario').order_by('fecha_viaje', 'horario__hora_salida')
    
    print(f"Total viajes encontrados: {viajes.count()}")
    for v in viajes:
        skip = False
        if v.fecha_viaje == hoy and v.horario:
            if v.horario.hora_salida < hora_actual:
                skip = True
        
        print(f"- {v.fecha_viaje} {v.horario.hora_salida if v.horario else 'N/A'} {'[SKIP]' if skip else '[OK]'}")
