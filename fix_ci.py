import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from users.models import Persona
from django.db import connection

old_ci = -1780928669039
new_ci = 3232323

try:
    with connection.cursor() as cursor:
        # Disable foreign key constraints temporarily for SQLite
        cursor.execute("PRAGMA foreign_keys = OFF;")
        
        # Update main table
        cursor.execute("UPDATE users_persona SET cedula = %s WHERE cedula = %s", [new_ci, old_ci])
        print(f"Rows affected in users_persona: {cursor.rowcount}")

        # Update related tables
        tables_columns = [
            ('operations_encomienda', 'remitente_id'),
            ('operations_encomienda', 'destinatario_id'),
            ('operations_pasaje', 'cliente_id'),
            ('operations_pasaje', 'pasajero_id'),
        ]

        for table, col in tables_columns:
            cursor.execute(f"UPDATE {table} SET {col} = %s WHERE {col} = %s", [new_ci, old_ci])
            if cursor.rowcount > 0:
                print(f"Updated {cursor.rowcount} rows in {table}.{col}")
                
        cursor.execute("PRAGMA foreign_keys = ON;")
except Exception as e:
    print(f"Error: {e}")

print("Done.")
