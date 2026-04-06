import sys, os, django
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tr4cking.settings')
django.setup()

from itineraries.models import DetalleItinerario, Itinerario
from fleet.models import Parada

lines = []
for it in Itinerario.objects.all():
    lines.append(f"IT {it.pk}: {it.nombre}")
    for d in it.detalles.select_related('parada').order_by('orden'):
        lines.append(f"  ord={d.orden} pid={d.parada_id} name={d.parada.nombre}")

lines.append("")
lines.append("PARADAS 12 y 3:")
for p in Parada.objects.filter(pk__in=[3, 12]):
    lines.append(f"  id={p.pk} name={p.nombre}")

with open('_data.md', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print("Done")
