import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from operations.models import Viaje
from fleet.models import Empresa, Parada
from django.utils import timezone

hoy = timezone.now().date()
print(f"Hoy: {hoy}")

viajes = Viaje.objects.filter(fecha_viaje=hoy)
print(f"Total viajes hoy: {viajes.count()}")

for v in viajes:
    print(f"ID: {v.id}, Empresa: {v.empresa.nombre if v.empresa else 'None'}, Itinerario: {v.itinerario.nombre}, Hora: {v.horario.hora_salida if v.horario else 'None'}, Estado: {v.estado}")
    for d in v.itinerario.detalles.all().order_by('orden'):
        print(f"  - Parada: {d.parada.nombre} (ID: {d.parada.id}), Orden: {d.orden}")

print("\nEmpresas:")
for e in Empresa.objects.all():
    print(f"ID: {e.id}, Nombre: {e.nombre}")

print("\nParadas similares a ID 3 (Oviedo):")
p3 = Parada.objects.get(pk=3)
print(f"P3: {p3.nombre} ({p3.localidad})")
for p in Parada.objects.all():
    if p.id != 3:
        if p3.nombre.lower() in p.nombre.lower() or p.nombre.lower() in p3.nombre.lower():
             print(f"ID: {p.id}, Nombre: {p.nombre}, Empresa: {p.empresa.nombre if p.empresa else 'None'}")
