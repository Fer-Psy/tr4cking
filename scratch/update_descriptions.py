import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "base.settings")
django.setup()

from operations.models import Pasaje

pasajes = Pasaje.objects.all()
count = 0
for p in pasajes:
    if p.descripcion and 'As. ' in p.descripcion:
        p.descripcion = p.descripcion.replace('As. ', 'Asiento ')
        p.save(update_fields=['descripcion'])
        count += 1
print(f'Actualizados: {count}')
