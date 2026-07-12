import sys

lines = open('operations/views.py', 'r', encoding='utf-8').readlines()
for i, line in enumerate(lines):
    if 'class PasajeVentaView' in line:
        print(f'{i+1}: {line.strip()}')
        
for i, line in enumerate(lines):
    if 'facturacion' in line.lower() and 'redirect' in line.lower():
        print(f'{i+1}: {line.strip()}')
