import os
import django
from datetime import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from itineraries.models import Itinerario, DetalleItinerario
from fleet.models import Parada

# Obtener el itinerario y las paradas
itinerario = Itinerario.objects.get(id=1)  # Asunción - Natalio
terminal_asuncion = Parada.objects.get(id=2)
terminal_oviedo = Parada.objects.get(id=3)
terminal_santa_rita = Parada.objects.get(id=1)

print(f"Configurando detalles para itinerario: {itinerario.nombre}")

# Crear los detalles del itinerario (paradas en orden)
detalles_data = [
    {'parada': terminal_asuncion, 'orden': 1, 'hora_salida': time(6, 0), 'minutos_desde_origen': 0},
    {'parada': terminal_oviedo, 'orden': 2, 'hora_salida': time(8, 30), 'minutos_desde_origen': 150},
    {'parada': terminal_santa_rita, 'orden': 3, 'hora_salida': time(11, 0), 'minutos_desde_origen': 300},
]

for data in detalles_data:
    detalle, created = DetalleItinerario.objects.get_or_create(
        itinerario=itinerario,
        parada=data['parada'],
        defaults={
            'orden': data['orden'],
            'hora_salida': data['hora_salida'],
            'minutos_desde_origen': data['minutos_desde_origen']
        }
    )
    if created:
        print(f"  ✓ Creado: {detalle}")
    else:
        print(f"  - Ya existe: {detalle}")

print("\n¡Detalles del itinerario configurados exitosamente!")
print("Ahora los selectores de Parada Origen y Parada Destino mostrarán las paradas.")
