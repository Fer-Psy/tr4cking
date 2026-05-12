import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "base.settings")
django.setup()

from operations.models import Viaje
from fleet.models import Parada
from itineraries.models import DetalleItinerario
from django.db.models import Q, F, Subquery, OuterRef
from django.utils import timezone
from datetime import datetime
import unicodedata

def normalize_search(text):
    if not text: return ""
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()
    return text.replace('terminal de ', '').replace('terminal ', '').replace('parada ', '').strip()

def get_similar_ids(p):
    if not p: return []
    norm = normalize_search(p.nombre)
    loc_norm = normalize_search(p.localidad.nombre if p.localidad else '')
    query = Q(nombre__icontains=norm) | Q(localidad__nombre__icontains=norm)
    if loc_norm:
        query |= Q(nombre__icontains=loc_norm) | Q(localidad__nombre__icontains=loc_norm)
    return list(Parada.objects.filter(query).values_list('id', flat=True))

origen_p = Parada.objects.filter(nombre__icontains='Capiat').first()
destino_p = Parada.objects.filter(nombre__icontains='Coronel Oviedo').first()

print(f"Origen: {origen_p}")
print(f"Destino: {destino_p}")

origen_ids = get_similar_ids(origen_p)
destino_ids = get_similar_ids(destino_p)

print(f"origen_ids: {origen_ids}")
print(f"destino_ids: {destino_ids}")

sub_origen = DetalleItinerario.objects.filter(
    itinerario_id=OuterRef('itinerario_id'),
    parada_id__in=origen_ids
).values('orden')[:1]

sub_destino = DetalleItinerario.objects.filter(
    itinerario_id=OuterRef('itinerario_id'),
    parada_id__in=destino_ids
).values('orden')[:1]

fecha = datetime.strptime('2026-05-09', '%Y-%m-%d').date()

viajes = Viaje.objects.filter(fecha_viaje=fecha)
print(f"Total viajes en esa fecha: {viajes.count()}")

for v in viajes:
    print(f"Viaje: {v.pk} - {v.itinerario.nombre}")
    
    detalles = v.itinerario.detalles.all()
    print("  Paradas:")
    for d in detalles:
        print(f"    - {d.orden}: {d.parada.nombre} (ID: {d.parada_id})")

viajes_filtrados = viajes.annotate(
    orden_o=Subquery(sub_origen),
    orden_d=Subquery(sub_destino)
).filter(
    (Q(orden_o__isnull=False) & Q(orden_d__isnull=False) & Q(orden_o__lt=F('orden_d')))
)

print(f"\nViajes filtrados: {viajes_filtrados.count()}")
for v in viajes_filtrados:
    print(f"Match: {v.pk} - {v.itinerario.nombre} (O: {v.orden_o}, D: {v.orden_d})")

