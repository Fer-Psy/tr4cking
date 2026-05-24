import os
import sys
import django

# Add current directory to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from django.contrib.auth import get_user_model
from users.models import Persona, Localidad
from fleet.models import Empresa, Parada, Bus
from itineraries.models import Itinerario
from operations.models import Viaje, Pasaje, Encomienda

def get_first_id(model):
    obj = model.objects.first()
    return obj.pk if obj else None

print("Valid DB IDs:")
print("Persona:", get_first_id(Persona))
print("Localidad:", get_first_id(Localidad))
print("Empresa:", get_first_id(Empresa))
print("Parada:", get_first_id(Parada))
print("Bus:", get_first_id(Bus))
print("Itinerario:", get_first_id(Itinerario))
print("Viaje:", get_first_id(Viaje))
print("Pasaje:", get_first_id(Pasaje))
print("Encomienda:", get_first_id(Encomienda))
