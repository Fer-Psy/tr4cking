import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from operations.models import Viaje

viaje = Viaje.objects.get(id=91)
print(f"Viaje: {viaje}")
print(f"Itinerario: {viaje.itinerario}")
print("Paradas in order:")
for det in viaje.itinerario.detalles.all().order_by('orden'):
    print(f"  ID: {det.parada.id} - Orden: {det.orden} - Parada: {det.parada.nombre}")
