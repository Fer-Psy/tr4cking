
import os
import django
import sys
from django.utils import timezone
from django.db.models import Q

# Añadir el directorio del proyecto al sys.path
sys.path.append(r'c:\Users\carol\Downloads\tr4cking-app\tr4cking')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from operations.models import Viaje, UbicacionAyudante

hoy = timezone.now().date()
viajes = Viaje.objects.filter(estado='en_curso', fecha_viaje=hoy)

print(f"--- Diagnóstico de Rastreo ({timezone.now()}) ---")
print(f"Viajes 'en_curso' hoy ({hoy}): {viajes.count()}")

for v in viajes:
    print(f"\nViaje ID: {v.pk}")
    print(f"Itinerario: {v.itinerario.nombre}")
    print(f"Bus: {v.bus.placa}")
    print(f"Chofer: {v.chofer.nombre_completo} (CI: {v.chofer.pk})")
    
    # Verificar chofer
    ub_chofer = UbicacionAyudante.objects.filter(persona=v.chofer, activo=True).first()
    print(f" - Tracking Chofer activo: {'SI' if ub_chofer else 'NO'}")
    if ub_chofer:
        print(f"   Coords: {ub_chofer.latitud}, {ub_chofer.longitud}")
    
    # Verificar ayudantes
    for ay in v.ayudantes.all():
        ub_ay = UbicacionAyudante.objects.filter(persona=ay, activo=True).first()
        print(f" - Ayudante: {ay.nombre_completo} (CI: {ay.pk})")
        print(f"   Tracking activo: {'SI' if ub_ay else 'NO'}")
        if ub_ay:
            print(f"   Coords: {ub_ay.latitud}, {ub_ay.longitud}")

print("\n--- Ubicaciones Activas en el Sistema ---")
ubs = UbicacionAyudante.objects.filter(activo=True)
print(f"Total tracking activos: {ubs.count()}")
for u in ubs:
    print(f" - Persona: {u.persona.nombre_completo}, Lat: {u.latitud}, Lng: {u.longitud}, Últ. Act: {u.ultima_actualizacion}")
