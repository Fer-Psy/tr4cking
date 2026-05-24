import os
import docx

def update_manual():
    doc_path = "manual.docx"
    if not os.path.exists(doc_path):
        print(f"Error: {doc_path} not found.")
        return

    doc = docx.Document(doc_path)
    shapes = list(doc.inline_shapes)
    
    print(f"Loaded manual.docx. Total inline shapes: {len(shapes)}")
    
    screenshots_ordered = [
        "01_login.png",                    # Shape 0, Figura 1
        "02_dashboard_admin.png",          # Shape 1, Figura 2
        "02b_dashboard_admin_scroll.png",  # Shape 2, Figura 3
        "03_persona_list.png",             # Shape 3, Figura 4
        "04_persona_form.png",             # Shape 4, Figura 5
        "05_persona_detail.png",           # Shape 5, Figura 6
        "06_localidad_list.png",           # Shape 6, Figura 7
        "07_localidad_form.png",           # Shape 7, Figura 8
        "08_empresa_list.png",             # Shape 8, Figura 9
        "09_empresa_detail.png",           # Shape 9, Figura 10
        "10_parada_list.png",              # Shape 10, Figura 11
        "11_parada_form.png",              # Shape 11, Figura 12
        "12_bus_list.png",                 # Shape 12, Figura 13
        "13_bus_detail.png",               # Shape 13, Figura 14
        "14_itinerario_list.png",          # Shape 14, Figura 15
        "15_itinerario_form.png",          # Shape 15, Figura 16
        "16_itinerario_detail.png",        # Shape 16, Figura 17
        "16b_itinerario_detail_scroll.png",# Shape 17, Figura 18
        "17_precio_list.png",              # Shape 18, Figura 19
        "18_horario_list.png",             # Shape 19, Figura 20
        "19_operations_dashboard.png",     # Shape 20, Figura 21
        "20_viaje_list.png",               # Shape 21, Figura 22
        "21_viaje_form.png",               # Shape 22, Figura 23
        "22_viaje_detail.png",             # Shape 23, Figura 24
        "22b_viaje_detail_scroll.png",     # Shape 24, Figura 25
        "23_pasaje_venta.png",             # Shape 25, Figura 26
        "23b_pasaje_venta_asientos.png",   # Shape 26, Figura 27
        "24_pasaje_list.png",              # Shape 27, Figura 28
        "25_pasaje_detail.png",            # Shape 28, Figura 29
        "26_encomienda_list.png",          # Shape 29, Figura 30
        "27_encomienda_detail.png",        # Shape 30, Figura 31
        "28_rastreo_publico.png",          # Shape 31, Figura 32
        "30_factura_form.png",             # Shape 32, Figura 33
        "36_pendientes_factura.png",       # Shape 33, Figura 34
        "29_factura_list.png",             # Shape 34, Figura 35
        "31_timbrado_list.png",            # Shape 35, Figura 36
        "32_caja_dashboard.png",           # Shape 36, Figura 37
        "33_reporte_diario.png",           # Shape 37, Figura 38
        "34_reporte_ventas.png",           # Shape 38, Figura 39
        "41_dashboard_agente.png",         # Shape 39, Figura 40
        "37_dashboard_ayudante.png",       # Shape 40, Figura 41
        "35_rastreo_mapa.png",             # Shape 41, Figura 42
        "38_dashboard_cliente.png",        # Shape 42, Figura 43
        "39_buscar_viajes.png",            # Shape 43, Figura 44
        "40_rastreo_publico_mapa.png"      # Shape 44, Figura 45
    ]
    
    if len(shapes) != len(screenshots_ordered):
        print(f"Warning: Shapes count ({len(shapes)}) does not match screenshots count ({len(screenshots_ordered)})")
    
    for idx, shape in enumerate(shapes):
        if idx >= len(screenshots_ordered):
            print(f"Skipping shape {idx} (no screenshot mapped)")
            continue
            
        screenshot_name = screenshots_ordered[idx]
        screenshot_path = os.path.join("screenshots", screenshot_name)
        
        if not os.path.exists(screenshot_path):
            print(f"Error: Screenshot file {screenshot_path} not found!")
            continue
            
        # Get or create the image relationship in the document part
        # get_or_add_image returns a tuple: (new_rId, image_instance)
        new_rId, _ = doc.part.get_or_add_image(screenshot_path)
        
        # Modify the XML to point to our new rId
        blips = shape._inline.xpath('.//a:blip')
        if blips:
            blip = blips[0]
            # Update the r:embed attribute
            blip.set('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed', new_rId)
            print(f"Shape {idx:2d} -> Mapped to {screenshot_name:32s} (new rId: {new_rId})")
        else:
            print(f"Error: Shape {idx} has no blip element!")
            
    # Save the modified document
    doc.save("manual.docx")
    print("manual.docx successfully updated and saved!")

if __name__ == "__main__":
    update_manual()
