
import os
import django
import sys

# Añadir el directorio del proyecto al sys.path
sys.path.append(r'c:\Users\carol\Downloads\tr4cking-app\tr4cking')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from operations.models import Viaje
from fleet.models import Empresa
from django.utils import timezone

hoy = timezone.now().date()
viajes = Viaje.objects.filter(empresa__nombre__icontains='Ybyturuzu', fecha_viaje__gte=hoy)

print(f"Buscando viajes de Ybyturuzu desde {hoy}...")
if not viajes.exists():
    print("No se encontraron viajes de Ybyturuzu.")
    # Buscar empresa
    empresa = Empresa.objects.filter(nombre__icontains='Ybyturuzu').first()
    if empresa:
        print(f"Empresa encontrada: {empresa.nombre} (ID: {empresa.id})")
        # Buscar viajes de esta empresa sin filtro de fecha
        v_total = Viaje.objects.filter(empresa=empresa)
        print(f"Total viajes de esta empresa en DB: {v_total.count()}")
        for v in v_total[:5]:
            print(f" - ID: {v.id}, Fecha: {v.fecha_viaje}, Estado: {v.estado}, Itinerario: {v.itinerario.nombre}")
    else:
        print("Empresa 'Ybyturuzu' no encontrada en la base de datos.")
else:
    for v in viajes:
        hora = v.horario.hora_salida if v.horario else 'N/A'
        print(f"ID: {v.id}, Fecha: {v.fecha_viaje}, Hora: {hora}, Estado: {v.estado}, Itinerario: {v.itinerario.nombre}")

# Verificar si el itinerario 'Asunción-Ciudad del Este' existe y quién lo tiene
from itineraries.models import Itinerario
its = Itinerario.objects.filter(nombre__icontains='Asunción')
print("\nItinerarios con 'Asunción' en el nombre:")
for it in its:
    print(f" - ID: {it.id}, Nombre: {it.nombre}, Empresa: {it.empresa.nombre if it.empresa else 'Global'}")
