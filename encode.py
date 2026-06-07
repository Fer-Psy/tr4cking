import base64
with open('_out.txt', 'rb') as f:
    data = f.read()
with open('_out_b64.txt', 'w') as f:
    f.write(base64.b64encode(data).decode('ascii'))
