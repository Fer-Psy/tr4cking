import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tr4cking.settings')
django.setup()

from operations.models import Viaje
from itineraries.models import DetalleItinerario, Precio

print("====================================")
print("Buscando viajes del 2026-07-16")
viajes = Viaje.objects.filter(fecha_viaje='2026-07-16')
print(f"Total viajes: {viajes.count()}")

for v in viajes:
    print(f"Viaje: {v.id}, Itinerario: {v.itinerario.nombre}, Estado: {v.estado}, Horario: {v.horario.hora_salida}")
    
    detalles = list(DetalleItinerario.objects.filter(itinerario=v.itinerario).order_by('orden'))
    origen_d = next((d for d in detalles if d.parada_id == 3), None)
    destino_d = next((d for d in detalles if d.parada_id == 9), None)
    
    if origen_d and destino_d:
        print(f"  Encontrado en {v.itinerario.nombre} - Origen {origen_d.parada.nombre} (Orden: {origen_d.orden}), Destino {destino_d.parada.nombre} (Orden: {destino_d.orden})")
        if origen_d.orden < destino_d.orden:
            print("  [✓] Orden correcto (origen antes que destino).")
            precio = Precio.objects.filter(origen_id=3, destino_id=9).first()
            print(f"  [✓] Precio registrado: {precio.precio if precio else 'NO HAY PRECIO'}")
        else:
            print("  [x] Orden INCORRECTO: destino antes que origen.")
    else:
        print(f"  [x] Faltan paradas (Origen: {origen_d}, Destino: {destino_d})")

