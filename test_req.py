import os
import django
import json
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from django.test import Client
from users.models import CustomUser

c = Client()
user = CustomUser.objects.filter(is_superuser=True).first()
c.force_login(user)

try:
    r = c.post('/operations/api/crear-reserva/116/', data=json.dumps({'asiento_ids': [1], 'parada_origen_id': 17, 'parada_destino_id': 27, 'confirmar': True}), content_type='application/json')
    print('HTTP_STATUS:', r.status_code)
    print('CONTENT:', r.content.decode('utf-8', errors='ignore'))
except Exception as e:
    traceback.print_exc()
