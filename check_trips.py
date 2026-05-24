import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tr4cking.settings")
django.setup()

from operations.models import Viaje
from django.utils import timezone
hoy = timezone.localtime(timezone.now()).date()

print("Viajes a partir de hoy:")
for v in Viaje.objects.filter(fecha_viaje__gt=hoy).order_by('fecha_viaje', 'horario__hora_salida'):
    print(f"ID: {v.id}, Fecha: {v.fecha_viaje}, Empresa: {v.empresa_id}, Bus_Empresa: {v.bus.empresa_id if v.bus else None}, Estado: {v.estado}, Hora: {v.horario.hora_salida if v.horario else None}")
