import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from users.models import Persona
from django.db import connection

old_ci = -1780928669039
new_ci = 3232323

output = []

try:
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA foreign_keys = OFF;")
        
        cursor.execute("UPDATE users_persona SET cedula = %s WHERE cedula = %s", [new_ci, old_ci])
        output.append(f"Rows affected in users_persona: {cursor.rowcount}")

        tables_columns = [
            ('operations_encomienda', 'remitente_id'),
            ('operations_encomienda', 'destinatario_id'),
            ('operations_pasaje', 'cliente_id'),
            ('operations_pasaje', 'pasajero_id'),
        ]

        for table, col in tables_columns:
            try:
                cursor.execute(f"UPDATE {table} SET {col} = %s WHERE {col} = %s", [new_ci, old_ci])
                if cursor.rowcount > 0:
                    output.append(f"Updated {cursor.rowcount} rows in {table}.{col}")
            except Exception:
                pass
                
        cursor.execute("PRAGMA foreign_keys = ON;")
except Exception as e:
    output.append(f"Error: {e}")

p = Persona.objects.filter(cedula=new_ci).first()
if p:
    output.append(f"Persona with {new_ci} successfully updated/exists.")
else:
    output.append(f"Persona with {new_ci} NOT FOUND. Checking if negative exists...")
    old = Persona.objects.filter(cedula=old_ci).first()
    if old:
        output.append("Negative record still exists!")
    else:
        output.append("Negative record was already deleted!")

output.append("Done.")

with open('fix_output.txt', 'w') as f:
    f.write('\n'.join(output))
