import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from fleet.models import Parada
from itineraries.models import DetalleItinerario, Precio
from operations.models import Pasaje, Encomienda

def merge_paradas(keep_id, delete_id):
    print(f"=== INICIANDO MERGE DE PARADAS ===")
    print(f"Mantener ID: {keep_id}")
    print(f"Eliminar ID: {delete_id}")
    
    try:
        p_keep = Parada.objects.get(id=keep_id)
        p_delete = Parada.objects.get(id=delete_id)
    except Parada.DoesNotExist as e:
        print(f"Error: {e}")
        return

    print(f"Parada a mantener: {p_keep.nombre}")
    print(f"Parada a eliminar: {p_delete.nombre}")

    # Actualizar DetalleItinerario
    detalles = DetalleItinerario.objects.filter(parada=p_delete)
    count = detalles.count()
    detalles.update(parada=p_keep)
    print(f"DetalleItinerario actualizados: {count}")

    # Actualizar Precios (origen)
    precios_origen = Precio.objects.filter(origen=p_delete)
    count = precios_origen.count()
    precios_origen.update(origen=p_keep)
    print(f"Precios (origen) actualizados: {count}")

    # Actualizar Precios (destino)
    precios_destino = Precio.objects.filter(destino=p_delete)
    count = precios_destino.count()
    precios_destino.update(destino=p_keep)
    print(f"Precios (destino) actualizados: {count}")

    # Actualizar Pasajes (origen)
    pasajes_origen = Pasaje.objects.filter(parada_origen=p_delete)
    count = pasajes_origen.count()
    pasajes_origen.update(parada_origen=p_keep)
    print(f"Pasajes (origen) actualizados: {count}")

    # Actualizar Pasajes (destino)
    pasajes_destino = Pasaje.objects.filter(parada_destino=p_delete)
    count = pasajes_destino.count()
    pasajes_destino.update(parada_destino=p_keep)
    print(f"Pasajes (destino) actualizados: {count}")

    # Actualizar Encomiendas (origen)
    encomiendas_origen = Encomienda.objects.filter(parada_origen=p_delete)
    count = encomiendas_origen.count()
    encomiendas_origen.update(parada_origen=p_keep)
    print(f"Encomiendas (origen) actualizadas: {count}")

    # Actualizar Encomiendas (destino)
    encomiendas_destino = Encomienda.objects.filter(parada_destino=p_delete)
    count = encomiendas_destino.count()
    encomiendas_destino.update(parada_destino=p_keep)
    print(f"Encomiendas (destino) actualizadas: {count}")

    # Eliminar la parada duplicada
    p_delete.delete()
    print("=======================================")
    print("La parada duplicada ha sido eliminada exitosamente.")

if __name__ == '__main__':
    # Mantener ID 9 (Terminal de Caaguazu)
    # Eliminar ID 13 (Terminal Caaguazu (Terminal))
    merge_paradas(9, 13)
