import os
import sys
import django

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from django.db import models
from fleet.models import Parada

print("TODAS LAS PARADAS:")
for p in Parada.objects.all():
    n = p.nombre.lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
    if 'asuncion' in n or 'ciudad del este' in n or 'cde' in n:
        print(f"ID: {p.id} | Nombre: {p.nombre} | Localidad: {p.localidad.nombre if p.localidad else 'N/A'}")
