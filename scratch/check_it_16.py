
import os
import django
import sys

sys.path.append(r'c:\Users\carol\Downloads\tr4cking-app\tr4cking')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from itineraries.models import Itinerario, DetalleItinerario

it_id = 16
detalles = DetalleItinerario.objects.filter(itinerario_id=it_id).select_related('parada').order_by('orden')

print(f"Detalles para Itinerario {it_id}:")
for d in detalles:
    print(f" - Orden {d.orden}: {d.parada.nombre} (ID: {d.parada.id})")
