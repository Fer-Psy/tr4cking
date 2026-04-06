from django.contrib.auth.models import User
from users.models import Persona
import sys

def setup_juan():
    try:
        # 1. Crear el usuario 'Juan' si no existe
        user, created = User.objects.get_or_create(username='Juan')
        user.set_password('Juan')
        user.save()
        print(f"Usuario 'Juan' {'creado' if created else 'actualizado'}.")

        # 2. Buscar o crear la Persona 'Juan Perez'
        persona = Persona.objects.filter(nombre='Juan', apellido='Perez').first()
        if not persona:
            persona = Persona.objects.create(
                user=user,
                nombre='Juan',
                apellido='Perez',
                cedula=123456, # Dummy
                es_ayudante=True,
                es_empleado=True
            )
            print("Persona 'Juan Perez' creada.")
        else:
            persona.user = user
            persona.es_ayudante = True
            persona.save()
            print("Persona 'Juan Perez' actualizada.")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    import os
    import django
    import sys
    
    # Agregar el directorio actual al path
    sys.path.append(os.getcwd())
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
    try:
        django.setup()
        setup_juan()
    except Exception as e:
        print(f"Setup Error: {str(e)}")

