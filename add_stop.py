import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from itineraries.models import DetalleItinerario, Itinerario
from fleet.models import Parada

itinerario = Itinerario.objects.filter(nombre__icontains='Coronel Oviedo-Caaguazu').first()
print(f"Itinerario: {itinerario.nombre}")

for d in itinerario.detalles.all().order_by('orden'):
    print(f"  {d.orden} - {d.parada.nombre} (ID: {d.parada.pk})")

parada = Parada.objects.filter(nombre__icontains='Terminal').filter(nombre__icontains='Oviedo').first()
print(f"\nParada encontrada: {parada.nombre if parada else 'No encontrada'}")

if parada:
    # Agregarla como orden 0 u orden 1 y empujar las demas
    print("Agregando al inicio...")
    for d in itinerario.detalles.all():
        d.orden += 1
        d.save()
        
    DetalleItinerario.objects.create(
        itinerario=itinerario,
        parada=parada,
        orden=1,
        minutos_desde_origen=0
    )
    print("Guardado.")
