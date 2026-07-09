import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base.settings')
import django
django.setup()

from django.contrib.auth.models import User

results = []

# List all users
results.append("=== ALL USERS ===")
for u in User.objects.all():
    results.append(f"  username={u.username}, active={u.is_active}, staff={u.is_staff}, super={u.is_superuser}, pass_check_123={u.check_password('123')}")

# Fix or create user fer
results.append("\n=== FIXING USER FER ===")
try:
    u = User.objects.get(username='fer')
    results.append(f"  Found existing user: {u.username}")
except User.DoesNotExist:
    u = User(username='fer')
    results.append("  Created new user fer")

u.set_password('123')
u.is_staff = True
u.is_superuser = True
u.is_active = True
u.save()

# Verify
u.refresh_from_db()
results.append(f"  After fix: active={u.is_active}, staff={u.is_staff}, super={u.is_superuser}, check_password('123')={u.check_password('123')}")
results.append("DONE")

# Write to file
with open('scratch/fix_fer_output.txt', 'w') as f:
    f.write('\n'.join(results))
