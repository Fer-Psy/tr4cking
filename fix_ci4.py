from users.models import Persona
from django.db import connection

old_ci = -1780928669039
new_ci = 3232323

try:
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA foreign_keys = OFF;")
        cursor.execute("UPDATE users_persona SET cedula = %s WHERE cedula = %s", [new_ci, old_ci])
        
        tables_columns = [
            ('operations_encomienda', 'remitente_id'),
            ('operations_encomienda', 'destinatario_id'),
            ('operations_pasaje', 'cliente_id'),
            ('operations_pasaje', 'pasajero_id'),
        ]

        for table, col in tables_columns:
            try:
                cursor.execute(f"UPDATE {table} SET {col} = %s WHERE {col} = %s", [new_ci, old_ci])
            except Exception:
                pass
                
        cursor.execute("PRAGMA foreign_keys = ON;")
except Exception as e:
    pass

p = Persona.objects.filter(cedula=new_ci).first()
if p:
    with open('success.txt', 'w') as f:
        f.write('updated')
else:
    with open('success.txt', 'w') as f:
        f.write('not_found')
