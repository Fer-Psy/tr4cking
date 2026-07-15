"""Script para verificar paradas del itinerario Coronel Oviedo - Encarnacion."""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tr4cking.settings')
django.setup()

from itineraries.models import Itinerario

# Buscar itinerarios con 'oviedo' o 'encarnacion'
its = Itinerario.objects.filter(nombre__icontains='oviedo') | Itinerario.objects.filter(nombre__icontains='encarnaci')
its = its.distinct()

for it in its:
    print(f"\n=== Itinerario ID={it.id}: {it.nombre} ===")
    detalles = it.detalles.select_related('parada', 'parada__localidad').order_by('orden')
    sin_coords = 0
    for d in detalles:
        p = d.parada
        tiene = bool(p.latitud_gps and p.longitud_gps)
        estado = "✓" if tiene else "✗ SIN COORDS"
        localidad = p.localidad.nombre if p.localidad else ''
        print(f"  [{d.orden:02d}] {p.nombre} ({localidad}) | {estado}")
        if not tiene:
            sin_coords += 1
    print(f"  -> Total sin coordenadas: {sin_coords}/{detalles.count()}")
