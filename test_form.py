import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from itineraries.forms import ItinerarioForm
from fleet.models import Empresa, Parada

# Get a real company and stop to test
empresa = Empresa.objects.first()
parada = Parada.objects.filter(empresa=empresa).first()

output = []
output.append(f"Testing with Empresa ID: {empresa.id if empresa else 'None'}")
output.append(f"Testing with Parada ID: {parada.id if parada else 'None'}")

# Simulate POST data
data = {
    'empresa': str(empresa.id) if empresa else '',
    'nombre': 'Test Itinerary',
    'ruta': 'PY02',
    'distancia_total_km': '100',
    'duracion_estimada_hs': '2',
    'dias_semana_checkboxes': ['0', '1', '2', '3', '4'],
    'parada_origen': str(parada.id) if parada else '',
    'activo': 'on'
}

form = ItinerarioForm(data=data)
output.append(f"Form is bound: {form.is_bound}")
output.append(f"Form is valid: {form.is_valid()}")
if not form.is_valid():
    output.append(f"Form errors: {form.errors.as_json()}")

with open('form_out.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))
print("Done")
