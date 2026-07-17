import sys

with open('operations/views.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
for i, line in enumerate(lines):
    if 'class CrearReservaClienteView' in line:
        start_idx = i
        break

if start_idx != -1:
    atomic_idx = -1
    for i in range(start_idx, len(lines)):
        if 'with transaction.atomic():' in lines[i]:
            atomic_idx = i
            break
            
    end_idx = -1
    for i in range(atomic_idx + 10, len(lines)):
        if lines[i].startswith('    def ') or lines[i].startswith('class '):
            end_idx = i
            break
            
    target_start = -1
    for i in range(atomic_idx, end_idx):
        if 'if viaje.reservas_bloqueadas:' in lines[i]:
            target_start = i
            break
            
    for i in range(target_start, end_idx):
        if lines[i].strip() == '':
            continue
        if lines[i].startswith('        '):
            lines[i] = '    ' + lines[i]

    with open('operations/views.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Fixed!")
