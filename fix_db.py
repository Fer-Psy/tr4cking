import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from itineraries.models import Itinerario, Horario

# First make sure we have some active horarios
horarios = Horario.objects.all()
if not horarios.exists():
    from datetime import time
    Horario.objects.create(hora_salida=time(6, 0), activo=True)
    Horario.objects.create(hora_salida=time(12, 0), activo=True)
    Horario.objects.create(hora_salida=time(18, 0), activo=True)
    horarios = Horario.objects.all()
else:
    horarios.update(activo=True)

it = Itinerario.objects.filter(nombre__icontains='Ciudad del Este', empresa__nombre__icontains='Guaireña').first()
if not it:
    it = Itinerario.objects.filter(nombre__icontains='Ciudad del Este').first()

if it:
    # Add all active horarios to it
    active_horarios = Horario.objects.filter(activo=True)
    it.horarios.add(*active_horarios)
    it.save()
