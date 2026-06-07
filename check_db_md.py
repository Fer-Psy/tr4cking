import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from itineraries.models import Itinerario

it = Itinerario.objects.filter(nombre__icontains='Ciudad del Este', empresa__nombre__icontains='Guaireña').first()

with open('_db_out.md', 'w', encoding='utf-8') as f:
    f.write('# Itinerario Info\n')
    if it:
        f.write(f'- Nombre: {it.nombre}\n')
        f.write(f'- ID: {it.id}\n')
        f.write(f'- Horarios Totales: {[str(h.hora_salida) for h in it.horarios.all()]}\n')
        f.write(f'- Horarios Activos: {[str(h.hora_salida) for h in it.horarios.filter(activo=True)]}\n')
        f.write(f'- Empresa: {it.empresa.nombre if it.empresa else "None"}\n')
    else:
        f.write('Not found\n')

print("Done")
