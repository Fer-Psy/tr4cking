import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from users.models import Persona
from django.contrib.auth.models import User

user = User.objects.filter(username='Juan').first()
if user:
    print(f"User: {user.username} | Superuser: {user.is_superuser}")
    p = getattr(user, 'persona', None)
    if p:
        print(f"Persona: {p.nombre_completo} | Es ayudante: {p.es_ayudante} | Es chofer: {p.es_chofer}")
    else:
        print("No Persona linked to this user.")
else:
    print("User Juan not found.")
