import urllib.request
import urllib.parse

url = 'http://127.0.0.1:8000/itineraries/nuevo/'

# We need to get the CSRF token first, but since it's local development, 
# maybe we can disable CSRF or just read the page first to get the cookie and token.
# Let's write a script that does GET first to fetch the CSRF token, then POSTs with it.

import http.cookiejar
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. GET request
response = opener.open(url)
html = response.read().decode('utf-8')

# Extract CSRF token from html
import re
match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
csrf_token = match.group(1) if match else ''

print("CSRF Token found:", csrf_token)

# 2. POST request
# Let's simulate creating a new itinerary
data = {
    'csrfmiddlewaretoken': csrf_token,
    'empresa': '2', # Ybyturuzu (verify ID)
    'nombre': 'Test Itinerary Ybyturuzu',
    'ruta': 'PY02',
    'distancia_total_km': '150.5',
    'duracion_estimada_hs': '3.5',
    'dias_semana_checkboxes': ['0', '1', '2', '3', '4'], # Mon-Fri
    'parada_origen': '3', # Target stop ID
    'activo': 'on'
}

# Encode multiple values for checkboxes correctly
post_data_list = []
for k, v in data.items():
    if isinstance(v, list):
        for item in v:
            post_data_list.append((k, item))
    else:
        post_data_list.append((k, v))

encoded_data = urllib.parse.urlencode(post_data_list).encode('utf-8')

req = urllib.request.Request(url, data=encoded_data, headers={
    'Referer': url,
    'X-Requested-With': 'XMLHttpRequest', # Simulate HTMX/AJAX
})

try:
    post_response = opener.open(req)
    print("Status Code:", post_response.status)
    print("Response Headers:", dict(post_response.headers))
    res_html = post_response.read().decode('utf-8')
    with open('post_out.html', 'w', encoding='utf-8') as f:
        f.write(res_html)
    print("Response written to post_out.html")
except Exception as e:
    print("Error:", e)
    if hasattr(e, 'read'):
        print(e.read().decode('utf-8'))
