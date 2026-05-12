
import os
import django
import sys

sys.path.append(r'c:\Users\carol\Downloads\tr4cking-app\tr4cking')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from itineraries.models import DetalleItinerario, Parada

id_duplicado = 4
id_principal = 3

# Ver quién usa el ID 4
detalles = DetalleItinerario.objects.filter(parada_id=id_duplicado)
print(f"Itinerarios que usan la parada ID {id_duplicado}:")
for d in detalles:
    print(f" - Itinerario: {d.itinerario.nombre} (ID: {d.itinerario.id}), Empresa: {d.itinerario.empresa.nombre if d.itinerario.empresa else 'Global'}")

# Actualizar Itinerario 16 para usar ID 3
print(f"\nActualizando DetalleItinerario del Itinerario 16...")
DetalleItinerario.objects.filter(itinerario_id=16, parada_id=id_duplicado).update(parada_id=id_principal)
print("Actualización completada.")

# Verificar si hay otros que usan ID 4
detalles_restantes = DetalleItinerario.objects.filter(parada_id=id_duplicado)
if detalles_restantes.exists():
    print(f"\nAún quedan itinerarios usando el ID {id_duplicado}. Merging those too...")
    detalles_restantes.update(parada_id=id_principal)
else:
    print("\nNo quedan itinerarios usando el ID 4.")

# Finalmente, borrar la parada duplicada si ya no se usa
# Pero antes verificar si se usa en Encomiendas o Pasajes
from operations.models import Encomienda, Pasaje
if not Encomienda.objects.filter(parada_origen_id=id_duplicado).exists() and \
   not Encomienda.objects.filter(parada_destino_id=id_duplicado).exists() and \
   not Pasaje.objects.filter(parada_origen_id=id_duplicado).exists() and \
   not Pasaje.objects.filter(parada_destino_id=id_duplicado).exists():
    print(f"\nBorrando parada duplicada ID {id_duplicado}...")
    Parada.objects.filter(id=id_duplicado).delete()
    print("Borrado exitoso.")
else:
    print(f"\nLa parada ID {id_duplicado} se usa en operaciones (encomiendas/pasajes). Actualizando esas referencias...")
    Encomienda.objects.filter(parada_origen_id=id_duplicado).update(parada_origen_id=id_principal)
    Encomienda.objects.filter(parada_destino_id=id_duplicado).update(parada_destino_id=id_principal)
    Pasaje.objects.filter(parada_origen_id=id_duplicado).update(parada_origen_id=id_principal)
    Pasaje.objects.filter(parada_destino_id=id_duplicado).update(parada_destino_id=id_principal)
    # También Precio
    from fleet.models import Precio
    Precio.objects.filter(origen_id=id_duplicado).update(origen_id=id_principal)
    Precio.objects.filter(destino_id=id_duplicado).update(destino_id=id_principal)
    
    Parada.objects.filter(id=id_duplicado).delete()
    print("Referencias actualizadas y parada borrada.")
