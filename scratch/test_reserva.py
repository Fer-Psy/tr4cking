import os
import sys
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "base.settings")
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from fleet.models import Asiento, Parada
from operations.models import Viaje

# We need an active viaje to test
viaje = Viaje.objects.filter(estado__in=['programado', 'en_curso']).first()
if not viaje:
    print("No active viaje found")
    sys.exit()

print(f"Testing with Viaje ID: {viaje.pk}")

# Get some seats
asientos = list(viaje.bus.asientos.all()[:2])
if len(asientos) < 2:
    print("Not enough seats")
    sys.exit()
asiento_ids = [a.pk for a in asientos]

# Get paradas
paradas_itinerario = viaje.itinerario.detalles.all().order_by('orden')
if paradas_itinerario.count() < 2:
    print("Not enough paradas in itinerario")
    sys.exit()

parada_origen = paradas_itinerario.first().parada
parada_destino = paradas_itinerario.last().parada

print(f"Parada Origen ID: {parada_origen.pk}, Parada Destino ID: {parada_destino.pk}")

# Get a user (assuming admin or someone exists)
user = User.objects.first()

c = Client()
c.force_login(user)

payload = {
    'asiento_ids': asiento_ids,
    'parada_origen_id': parada_origen.pk,
    'parada_destino_id': parada_destino.pk,
    'facturacion': {'usar_otros_datos': False},
    'confirmar': True
}

response = c.post(
    f'/operations/api/crear-reserva/{viaje.pk}/',
    data=json.dumps(payload),
    content_type='application/json'
)

print(f"Status Code: {response.status_code}")
try:
    print(response.json())
except Exception:
    print(response.content.decode('utf-8'))
