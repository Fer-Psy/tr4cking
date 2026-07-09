import random
from django.core.management.base import BaseCommand
from users.models import Persona
from django.db import connection

class Command(BaseCommand):
    help = 'Corrige registros de persona con cédula vacía o negativa asignando números aleatorios positivos'

    def handle(self, *args, **options):
        self.stdout.write("Iniciando corrección de cédulas...")
        
        # Obtenemos todos los registros con cedula vacia o negativa usando raw SQL
        # porque el ORM con PKs vacías a veces puede fallar al cargar el objeto
        with connection.cursor() as cursor:
            cursor.execute("SELECT cedula, nombre, apellido FROM users_persona WHERE cedula = '' OR cedula LIKE '-%'")
            rows = cursor.fetchall()
            
            if rows:
                cursor.execute("PRAGMA foreign_keys = OFF;")
                
            for row in rows:
                old_cedula = row[0]
                nombre = f"{row[1]} {row[2]}"
                
                # Si el nombre contiene fernando y se quería la 5333090
                if 'fernando' in nombre.lower():
                    new_cedula = '5333090'
                else:
                    new_cedula = str(random.randint(9000000, 9999999))
                
                # Asegurarse de que no exista
                while Persona.objects.filter(cedula=new_cedula).exists():
                    new_cedula = str(random.randint(9000000, 9999999))
                
                self.stdout.write(f"Actualizando '{nombre}' (vieja CI: '{old_cedula}') -> nueva CI: {new_cedula}")
                
                # Update users_persona
                cursor.execute("UPDATE users_persona SET cedula = %s WHERE cedula = %s", [new_cedula, old_cedula])
                
                # Update related tables gracefully
                queries = [
                    "UPDATE operations_encomienda SET remitente_id = %s WHERE remitente_id = %s",
                    "UPDATE operations_encomienda SET destinatario_id = %s WHERE destinatario_id = %s",
                    "UPDATE operations_viaje SET chofer_id = %s WHERE chofer_id = %s",
                    "UPDATE operations_viaje_ayudantes SET persona_id = %s WHERE persona_id = %s",
                    "UPDATE itineraries_itinerario SET chofer_predeterminado_id = %s WHERE chofer_predeterminado_id = %s",
                    "UPDATE itineraries_itinerario SET ayudante_predeterminado_id = %s WHERE ayudante_predeterminado_id = %s"
                ]
                
                for query in queries:
                    try:
                        cursor.execute(query, [new_cedula, old_cedula])
                    except Exception as e:
                        pass # Ignore if table or column doesn't exist
                
            if rows:
                cursor.execute("PRAGMA foreign_keys = ON;")
                
        self.stdout.write(self.style.SUCCESS("Corrección finalizada exitosamente."))
