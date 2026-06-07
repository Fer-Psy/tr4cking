import os
import sys
import django

# Direct output to file
out_path = r"c:\Users\carol\Downloads\tr4cking-app\tr4cking\scratch\fields_output.txt"

with open(out_path, "w", encoding="utf-8") as f:
    try:
        f.write("Starting script...\n")
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
        django.setup()
        
        from fleet.models import Bus
        f.write("Bus model imported successfully.\n")
        
        f.write("Fields on Bus model:\n")
        for field in Bus._meta.get_fields():
            f.write(f"{field.name}: {type(field)}\n")
            
    except Exception as e:
        import traceback
        f.write(f"ERROR: {str(e)}\n")
        f.write(traceback.format_exc())
