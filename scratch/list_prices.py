import os
import sys
import django

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from itineraries.models import Precio

print("LISTADO EXHAUSTIVO DE PRECIOS (ASUNCION / CDE):")
for p in Precio.objects.all():
    def clean(t):
        return t.lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')

    on = clean(p.origen.nombre)
    dn = clean(p.destino.nombre)
    ol = clean(p.origen.localidad.nombre) if p.origen.localidad else ""
    dl = clean(p.destino.localidad.nombre) if p.destino.localidad else ""
    
    if 'asuncion' in on or 'asuncion' in ol or 'ciudad del este' in dn or 'ciudad del este' in dl or 'cde' in dn or 'cde' in dl:
        print(f"ID: {p.id} | {p.origen.nombre} ({ol}) -> {p.destino.nombre} ({dl}) = {p.precio}")
