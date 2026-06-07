import os
import django
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tr4cking.settings")
django.setup()

from operations.models import Pasaje, Encomienda

pasajes = Pasaje.objects.filter(codigo__icontains='082')

with open(r"c:\Users\carol\Downloads\tr4cking-app\tr4cking\scratch\out.txt", "w", encoding="utf-8") as f:
    f.write(f"Encontrados {pasajes.count()} pasajes con '082'\n")
    for p in pasajes:
        has_factura = p.detalles_factura.filter(factura__estado='emitida').exists()
        f.write(f"ID: {p.id}\n")
        f.write(f"Codigo: {p.codigo}\n")
        f.write(f"Estado: {p.estado}\n")
        f.write(f"Fecha viaje: {p.viaje.fecha_viaje if p.viaje else 'None'}\n")
        f.write(f"Vendedor: {p.vendedor}\n")
        f.write(f"Tiene factura emitida: {has_factura}\n")
        f.write("---\n")
