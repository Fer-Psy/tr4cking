import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
django.setup()

from fleet.models import Bus
print("FIELDS_FOUND_START")
for field in Bus._meta.get_fields():
    print("FIELD:", field.name, type(field))
print("FIELDS_FOUND_END")
