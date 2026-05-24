import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from operations.models import Viaje
from django.utils import timezone

hoy = timezone.now().date()
print(f"Hoy: {hoy}")

v82 = Viaje.objects.get(pk=82)
print(f"Viaje 82: {v82}")
print(f"  - Estado: {v82.estado}")
print(f"  - Itinerario Activo: {v82.itinerario.activo}")
print(f"  - Bus Estado: {v82.bus.estado}")
print(f"  - Empresa: {v82.empresa.nombre if v82.empresa else 'None'}")
print(f"  - Hora Salida: {v82.horario.hora_salida if v82.horario else 'None'}")

ahora = timezone.now().time()
print(f"Hora actual: {ahora}")
print(f"¿Hora salida > Hora actual?: {v82.horario.hora_salida > ahora}")
