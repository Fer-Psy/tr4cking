import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from operations.models import Encomienda

def check_encomienda():
    encs = Encomienda.objects.filter(codigo__icontains='030')
    for enc in encs:
        print(f"ID: {enc.id}, Codigo: {enc.codigo}, Estado: {enc.estado}, Viaje ID: {enc.viaje_id}")
        if enc.viaje:
            print(f"  Viaje estado: {enc.viaje.estado}, Fecha: {enc.viaje.fecha_viaje}")

if __name__ == '__main__':
    check_encomienda()
