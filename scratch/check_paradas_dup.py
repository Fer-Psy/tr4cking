
import os
import django
import sys

sys.path.append(r'c:\Users\carol\Downloads\tr4cking-app\tr4cking')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from itineraries.models import Parada, DetalleItinerario

paradas = Parada.objects.filter(nombre__icontains='Terminal Asunción')
print("Paradas con 'Terminal Asunción':")
for p in paradas:
    print(f" - ID: {p.id}, Nombre: {p.nombre}")

paradas_oviedo = Parada.objects.filter(nombre__icontains='Terminal Coronel Oviedo')
print("\nParadas con 'Terminal Coronel Oviedo':")
for p in paradas_oviedo:
    print(f" - ID: {p.id}, Nombre: {p.nombre}")

# Ver qué paradas usa el itinerario 16
it_id = 16
detalles = DetalleItinerario.objects.filter(itinerario_id=it_id).select_related('parada')
print(f"\nParadas del Itinerario 16 (Ybyturuzu):")
for d in detalles:
    print(f" - {d.parada.nombre} (ID: {d.parada.id})")

# Ver qué paradas usa el itinerario 15
it_id = 15
detalles = DetalleItinerario.objects.filter(itinerario_id=it_id).select_related('parada')
print(f"\nParadas del Itinerario 15 (Guaireña):")
for d in detalles:
    print(f" - {d.parada.nombre} (ID: {d.parada.id})")
