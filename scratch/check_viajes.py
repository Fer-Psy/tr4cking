import os
import sys

# Setup Django
sys.path.append(r"c:\Users\carol\Downloads\tr4cking-app\tr4cking")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "base.settings")

import django
django.setup()

from django.contrib.auth.models import User
from users.models import Persona

try:
    ivan_user = User.objects.get(username__icontains="Ivan")
    print("User Ivan:", ivan_user)
    try:
        persona = ivan_user.persona
        print("Persona linked:", persona)
        print("  - es_cliente:", persona.es_cliente)
        print("  - es_chofer:", persona.es_chofer)
    except Persona.DoesNotExist:
        print("No persona linked to user Ivan!")
except User.DoesNotExist:
    print("No user named Ivan in database!")
