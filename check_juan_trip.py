from django.utils import timezone
from operations.models import Viaje
from users.models import Persona
import django
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

def check_juan_trip():
    p = Persona.objects.filter(nombre='Juan', apellido='Perez').first()
    if not p:
        print("Juan Perez not found")
        return
    
    hoy = timezone.now().date()
    v = Viaje.objects.filter(ayudantes=p).order_by('-fecha_viaje').first()
    if v:
        print(f"Viaje: {v.itinerario.nombre}, Fecha: {v.fecha_viaje}, Estado: {v.estado}")
        if v.estado == 'programado' and v.fecha_viaje == hoy:
            print("Action: Updating trip state to 'en_curso' so it's visible on the map.")
            v.estado = 'en_curso'
            v.save()
    else:
        print("No trip assigned to Juan Perez")

if __name__ == "__main__":
    check_juan_trip()
