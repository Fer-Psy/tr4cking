import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tr4cking.settings")
django.setup()

from operations.models import Pasaje

pasajes = Pasaje.objects.filter(codigo__icontains='082')
print(f"Total pasajes con '082': {pasajes.count()}")

for p in pasajes:
    print(f"Codigo: {p.codigo}, Estado: {p.estado}, Pagador: {p.cliente}, Pasajero: {p.pasajero}")

print("All pasajes:", [p.codigo for p in Pasaje.objects.all()[:5]])
