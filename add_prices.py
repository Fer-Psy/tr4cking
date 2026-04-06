import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from itineraries.models import Itinerario, Precio
from fleet.models import Parada

itinerario = Itinerario.objects.filter(nombre__icontains='Coronel Oviedo-Caaguazu').first()
terminal = Parada.objects.filter(nombre__icontains='Terminal').filter(nombre__icontains='Oviedo').first()
blas_garay = Parada.objects.filter(nombre__icontains='Blas Garay').first()

# Copiar precios de Blas Garay como si fueran desde Terminal
precios = Precio.objects.filter(itinerario=itinerario, origen=blas_garay)
print(f"Precios desde Blas Garay: {precios.count()}")

for p in precios:
    # Crear precio equivalente desde Terminal
    Precio.objects.get_or_create(
        itinerario=itinerario,
        origen=terminal,
        destino=p.destino,
        defaults={'precio': p.precio}
    )
print("Precios desde Terminal agregados/verificados.")
