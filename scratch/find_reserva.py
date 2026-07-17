import sys
with open('operations/views.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'class ReservarPasajeView' in line:
            print(f'Line {i+1}: {line.strip()}')
