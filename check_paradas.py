import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from itineraries.models import Itinerario, DetalleItinerario
from fleet.models import Parada

print("=== ITINERARIOS ===")
for itinerario in Itinerario.objects.all():
    print(f"\n{itinerario.nombre} (ID: {itinerario.id}):")
    detalles = itinerario.detalles.all().select_related('parada')
    if detalles.exists():
        for d in detalles:
            print(f"  - {d.orden}. {d.parada.nombre} (Parada ID: {d.parada.id})")
    else:
        print("  (Sin detalles de paradas)")

print("\n=== PARADAS ===")
for parada in Parada.objects.all()[:10]:
    print(f"- {parada.nombre} (ID: {parada.id})")
