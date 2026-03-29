import os

def run():
    with open(r'c:\Users\carol\Downloads\tr4cking-app\tr4cking\templates\users\localidad_form.html', 'r', encoding='utf-8') as f:
        loc = f.read()

    # Extract extra_css block
    css_start = loc.find('{% block extra_css %}')
    css_end = loc.find('{% endblock %}', css_start) + len('{% endblock %}')
    css_block = loc[css_start:css_end]

    # Extract extra_js block
    js_start = loc.find('{% block extra_js %}')
    js_end = loc.find('{% endblock %}', js_start) + len('{% endblock %}')
    js_block = loc[js_start:js_end]
    js_block = js_block.replace("'id_latitud'", "'id_latitud_gps'")
    js_block = js_block.replace("'id_longitud'", "'id_longitud_gps'")

    with open(r'c:\Users\carol\Downloads\tr4cking-app\tr4cking\templates\fleet\parada_form.html', 'r', encoding='utf-8') as f:
        parada = f.read()

    # Create new file content
    parada = parada.replace('<div class="col-12 col-lg-8">', '<div class="col-12 col-lg-5">')
    
    old_col4_start = parada.find('<div class="col-12 col-lg-4">')
    old_col4_end = parada.find('</div>', old_col4_start)
    # the </div> is closed twice for card body and card, then col
    # let's just find the end block
    col4_content_end = parada.find('</div>\n</div>\n{% endblock %}') + len('</div>\n</div>\n')
    
    map_html = """<div class="col-12 col-lg-7">
        <div class="card">
            <div class="card-header">
                <h3 class="card-title">
                    <i class="bi bi-map me-2 text-primary"></i>
                    Seleccionar Ubicación en el Mapa
                </h3>
            </div>
            <div class="card-body p-0">
                <div id="map-container">
                    <div class="map-instructions" id="map-instructions">
                        <i class="bi bi-cursor me-1"></i> Haz clic en el mapa para seleccionar la ubicación
                    </div>
                    <div class="map-coords-badge" id="map-coords-badge" style="display:none;">
                        <span id="coords-display">--</span>
                    </div>
                    <div class="map-search-container">
                        <div class="position-relative">
                            <i class="bi bi-search search-icon"></i>
                            <input type="text" class="form-control" id="map-search" 
                                   placeholder="Buscar lugar..." autocomplete="off">
                            <div class="search-results" id="search-results"></div>
                        </div>
                    </div>
                    <div class="map-action-btns">
                        <button type="button" class="btn" id="btn-my-location" title="Mi Ubicación">
                            <i class="bi bi-crosshair"></i>
                        </button>
                        <button type="button" class="btn" id="btn-clear-coords" title="Limpiar coordenadas">
                            <i class="bi bi-x-circle"></i>
                        </button>
                        <button type="button" class="btn" id="btn-center-py" title="Centrar en Paraguay">
                            <i class="bi bi-geo"></i>
                        </button>
                        <button type="button" class="btn" id="btn-fullscreen" title="Pantalla completa">
                            <i class="bi bi-arrows-fullscreen"></i>
                        </button>
                    </div>
                    <div id="map"></div>
                </div>
                <div class="p-3 bg-light border-top">
                    <h6 class="fw-semibold mb-2">Opciones adicionales</h6>
                    <p class="text-secondary small mb-0">
                        Marca la opción "Es sucursal" en el formulario izquierdo si en esta parada se pueden realizar operaciones físicas (venta de boletos, encomiendas).
                    </p>
                </div>
            </div>
        </div>
    </div>\n"""

    parada = parada[:old_col4_start] + map_html + parada[col4_content_end:]

    title_end = parada.find('{% endblock %}\n', parada.find('{% block title %}')) + len('{% endblock %}\n')
    parada = parada[:title_end] + '\n' + css_block + '\n' + parada[title_end:]

    parada = parada + '\n' + js_block + '\n'

    with open(r'c:\Users\carol\Downloads\tr4cking-app\tr4cking\templates\fleet\parada_form.html', 'w', encoding='utf-8') as f:
        f.write(parada)
    print("DONE YAY")

if __name__ == '__main__':
    run()
