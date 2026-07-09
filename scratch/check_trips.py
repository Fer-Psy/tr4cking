import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from operations.models import Viaje
from datetime import date

viajes_hoy = Viaje.objects.filter(fecha_viaje=date.today())
for v in viajes_hoy:
    print(f"Viaje: {v.pk} | Itinerario: {v.itinerario.nombre if v.itinerario else None} | Bus: {v.bus.placa if v.bus else None} | Horario: {v.horario.hora_salida if v.horario else None} | Chofer: {v.chofer.nombre_completo if v.chofer else None}")
