import os
import sys

# Setup Django
sys.path.append(r"c:\Users\carol\Downloads\tr4cking-app\tr4cking")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tr4cking.settings")

import django
django.setup()

from operations.models import Viaje
from fleet.models import Empresa
from django.utils import timezone

hoy = timezone.localtime(timezone.now()).date()

with open("trips_output.txt", "w", encoding="utf-8") as f:
    f.write(f"Hoy: {hoy}\n\n")
    
    empresas = Empresa.objects.all()
    for e in empresas:
        f.write(f"Empresa: {e.id} - {e.nombre}\n")
        
    viajes = Viaje.objects.all().order_by('fecha_viaje')
    f.write(f"\nTotal viajes: {viajes.count()}\n")
    for v in viajes:
        hora = v.horario.hora_salida if v.horario else 'N/A'
        emp_id = v.empresa_id or (v.bus.empresa_id if v.bus else None)
        f.write(f"Viaje {v.id}: Fecha {v.fecha_viaje}, Hora {hora}, Estado {v.estado}, Empresa {emp_id}, Itinerario {v.itinerario.nombre}\n")
