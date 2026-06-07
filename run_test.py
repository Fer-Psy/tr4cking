import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from itineraries.models import Itinerario
from django.db.models import Count

lines = []
lines.append("=== ITINERARIOS ===")
for i in Itinerario.objects.all():
    lines.append(f"Itinerario: {i.id} - {i.nombre}")
    lines.append(f"  Detalles count (ORM count): {i.detalles.count()}")
    lines.append(f"  Horarios count: {i.horarios.count()}")
    
    # Let's count via annotate
    annotated = Itinerario.objects.annotate(num_paradas=Count('detalles')).get(id=i.id)
    lines.append(f"  Annotated Count: {annotated.num_paradas}")
    
    # Let's count via annotate with distinct=True
    annotated_distinct = Itinerario.objects.annotate(num_paradas=Count('detalles', distinct=True)).get(id=i.id)
    lines.append(f"  Annotated Distinct Count: {annotated_distinct.num_paradas}")

with open('_out_utf8.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print("Done writing test results.")
