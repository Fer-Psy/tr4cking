import os
import sys
import django

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from fleet.models import Parada

p17 = Parada.objects.get(pk=17)
p18 = Parada.objects.get(pk=18)

print(f"P17: {p17.nombre} ({p17.localidad})")
print(f"P18: {p18.nombre} ({p18.localidad})")

import unicodedata
def normalize_search(text):
    if not text: return ""
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()
    return text.replace('terminal de ', '').replace('terminal ', '').replace('parada ', '').strip()

n17 = normalize_search(p17.nombre)
n18 = normalize_search(p18.nombre)
print(f"Normalized 17: '{n17}'")
print(f"Normalized 18: '{n18}'")

if n17 in n18 or n18 in n17:
    print("MATCH!")
else:
    print("NO MATCH!")
