import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from itineraries.models import Itinerario

it = Itinerario.objects.filter(nombre__icontains='Ciudad del Este', empresa__nombre__icontains='Guaireña').first()

with open('_out.txt', 'w', encoding='utf-8') as f:
    if it:
        f.write(f'Itinerario: {it.nombre} - Horarios: {[h.hora_salida for h in it.horarios.all()]}\n')
        f.write(f'Dias de operacion: {it.dias_semana}\n')
        f.write(f'Activo: {it.activo}\n')
        f.write(f'Horarios activos: {[h.hora_salida for h in it.horarios.filter(activo=True)]}\n')
    else:
        f.write('Not found\n')
