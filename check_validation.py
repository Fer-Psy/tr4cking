import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from itineraries.models import Itinerario
from fleet.models import Empresa, Parada
from itineraries.forms import ItinerarioForm

lines = []

# List all companies
lines.append("=== EMPRESAS ===")
for e in Empresa.objects.all():
    lines.append(f"ID={e.id}: {e.nombre}")

# List all paradas
lines.append("\n=== PARADAS ===")
for p in Parada.objects.all():
    lines.append(f"ID={p.id}: {p.nombre} (Empresa ID={p.empresa_id})")

# List all itineraries
lines.append("\n=== ITINERARIOS ===")
for i in Itinerario.objects.all():
    lines.append(f"ID={i.id}: {i.nombre} (Empresa ID={i.empresa_id if i.empresa else 'None'})")

# Let's test form validation with a different company but same name
# Find an existing itinerary name
existing_it = Itinerario.objects.first()
if existing_it:
    name = existing_it.nombre
    current_company_id = existing_it.empresa_id
    
    # Find a different company
    different_company = Empresa.objects.exclude(id=current_company_id).first()
    if different_company:
        # Find a parada for the different company
        parada = Parada.objects.filter(empresa=different_company).first()
        
        lines.append(f"\n=== TESTING VALIDATION ===")
        lines.append(f"Trying to create itinerary '{name}' for different company '{different_company.nombre}' (ID={different_company.id})")
        
        data = {
            'empresa': str(different_company.id),
            'nombre': name,
            'ruta': 'PY02',
            'distancia_total_km': '100',
            'duracion_estimada_hs': '2',
            'dias_semana_checkboxes': ['0', '1', '2', '3', '4'],
            'parada_origen': str(parada.id) if parada else '',
            'activo': 'on'
        }
        
        form = ItinerarioForm(data=data)
        lines.append(f"Form is valid: {form.is_valid()}")
        if not form.is_valid():
            lines.append(f"Errors: {form.errors.as_json()}")
        else:
            lines.append("Form validated successfully!")

with open('validation_errors.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print("Done")
