"""
Script para cargar coordenadas GPS en las paradas que no las tienen.
Cubre el tramo Coronel Oviedo - Encarnacion y otras ciudades del Paraguay.
"""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tr4cking.settings')
django.setup()

from fleet.models import Parada

# Mapa completo de coordenadas por palabras clave en nombre/localidad
# Se busca la clave como substring en (nombre + localidad).lower()
COORDS_MAP = {
    # --- Asuncion y Gran Asuncion ---
    'asunci':           ('-25.312918', '-57.564998'),
    'san lorenzo':      ('-25.339600', '-57.509700'),
    'capiat':           ('-25.361500', '-57.433900'),
    'itaugu':           ('-25.385400', '-57.341400'),
    'ypacara':          ('-25.399500', '-57.283100'),
    'caacup':           ('-25.387200', '-57.142000'),
    'eusebio':          ('-25.372100', '-56.963400'),
    'san jos':          ('-25.405400', '-56.540100'),   # San Jose de los Arroyos
    'coronel oviedo':   ('-25.444300', '-56.442800'),
    'oviedo':           ('-25.444300', '-56.442800'),
    # --- Tramo Oviedo -> Encarnacion ---
    'caaguaz':          ('-25.452684', '-56.015243'),
    'juan nepomuceno':  ('-26.107800', '-55.941100'),
    'san juan nepomuze':('-26.107800', '-55.941100'),
    'yuty':             ('-26.619400', '-56.250300'),
    'santa rosa del mi':('-26.889200', '-56.854400'),
    'santa rosa misio': ('-26.889200', '-56.854400'),
    'coronel bogado':   ('-27.179800', '-56.258100'),
    'bogado':           ('-27.179800', '-56.258100'),
    'obligado':         ('-27.261700', '-55.841700'),
    'fram':             ('-27.002200', '-55.973900'),
    'encarnaci':        ('-27.335800', '-55.868000'),
    # --- Tramo Este (Ciudad del Este) ---
    'mbocayaty':        ('-25.728900', '-56.411600'),
    'villarrica':       ('-25.779770', '-56.444738'),
    'cde':              ('-25.509700', '-54.611100'),
    'ciudad del este':  ('-25.509700', '-54.611100'),
    # --- Norte / Concepcion ---
    'concepci':         ('-23.412300', '-57.434200'),
    'pedro juan':       ('-22.544700', '-55.729100'),
    # --- Encarnacion area ---
    'natalio':          ('-26.665800', '-55.461400'),
    'bella vista sur':  ('-27.042500', '-55.581900'),
    'bella vista':      ('-27.042500', '-55.581900'),
    'ayolas':           ('-27.372800', '-56.897800'),
    'san cosme':        ('-27.286100', '-56.415300'),
    'pilar':            ('-26.862000', '-58.302800'),
}

paradas_qs = Parada.objects.filter(activo=True)
total = 0
actualizadas = 0
sin_match = []

for parada in paradas_qs:
    total += 1
    if parada.latitud_gps and parada.longitud_gps:
        continue  # ya tiene coordenadas

    # Construir string de busqueda: nombre + localidad
    texto = parada.nombre.lower()
    if parada.localidad:
        texto += ' ' + parada.localidad.nombre.lower()

    matched = False
    for key, (lat, lng) in COORDS_MAP.items():
        if key in texto:
            parada.latitud_gps = lat
            parada.longitud_gps = lng
            parada.save(update_fields=['latitud_gps', 'longitud_gps'])
            print(f"  [OK] '{parada.nombre}' ({parada.localidad}) -> ({lat}, {lng})")
            actualizadas += 1
            matched = True
            break

    if not matched:
        sin_match.append(f"  [--] '{parada.nombre}' ({parada.localidad})")

print(f"\n=== Resultado ===")
print(f"Total paradas activas: {total}")
print(f"Actualizadas: {actualizadas}")
print(f"Sin match ({len(sin_match)}):")
for s in sin_match:
    print(s)
