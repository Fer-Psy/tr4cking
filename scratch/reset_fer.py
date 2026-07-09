import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
import django
django.setup()

from django.contrib.auth.models import User
from users.models import Persona

output_path = r"c:\Users\carol\Downloads\tr4cking-app\tr4cking\scratch\reset_fer_output.txt"

with open(output_path, 'w') as f:
    try:
        f.write("Starting reset...\n")
        u, created = User.objects.get_or_create(username='fer')
        u.set_password('Gabriel10.')
        u.is_active = True
        u.is_staff = True
        u.is_superuser = True
        u.save()
        
        # Ensure persona exists too
        p, p_created = Persona.objects.get_or_create(
            user=u,
            defaults={
                'nombre': 'Fer',
                'apellido': 'Admin',
                'cedula': 1234567,
                'telefono': '123456',
                'email': 'fer@example.com'
            }
        )
        f.write(f"SUCCESS: User 'fer' exists. Created={created}. Password set to 'Gabriel10.'. Persona Created={p_created}\n")
    except Exception as e:
        f.write(f"ERROR: {str(e)}\n")
