import os
import sys
import time
from playwright.sync_api import sync_playwright

def take_screenshots():
    # Ensure screenshots folder exists
    os.makedirs("screenshots", exist_ok=True)
    
    base_url = "http://127.0.0.1:8000"
    
    # Valid DB IDs discovered:
    persona_id = 700002
    localidad_id = 6
    empresa_id = 1
    parada_id = 2
    bus_id = 1
    itinerario_id = 1
    viaje_id = 91
    pasaje_id = 70
    encomienda_id = 16

    with sync_playwright() as p:
        # Launch Chromium (headless for speed and reliability)
        browser = p.chromium.launch(headless=True)
        print("Playwright Chromium browser launched successfully.")

        # ----------------------------------------------------
        # SESSION 1: ADMIN (fer / fer)
        # ----------------------------------------------------
        print("Starting Session 1: Admin (fer)")
        context_admin = browser.new_context(viewport={"width": 1280, "height": 800})
        page_admin = context_admin.new_page()

        # Handle dialogs automatically to prevent alerts from hanging the script
        page_admin.on("dialog", lambda dialog: (print(f"Dialog encountered and dismissed: {dialog.message}"), dialog.dismiss()))

        # FIGURA 1: Pantalla de Inicio de Sesion
        print("Capturing FIGURA 1: Login Page...")
        page_admin.goto(f"{base_url}/login/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/01_login.png")

        # Perform Login
        page_admin.fill("input[name='username']", "fer")
        page_admin.fill("input[name='password']", "fer")
        page_admin.press("input[name='password']", "Enter")
        page_admin.wait_for_load_state("networkidle")
        print("Logged in as Admin successfully.")

        # FIGURA 2: Dashboard del Administrador
        print("Capturing FIGURA 2: Admin Dashboard...")
        page_admin.goto(f"{base_url}/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/02_dashboard_admin.png")

        # FIGURA 3: Dashboard del Administrador - Tablas de ultimos registros
        print("Capturing FIGURA 3: Admin Dashboard Scroll...")
        page_admin.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(0.5)
        page_admin.screenshot(path="screenshots/02b_dashboard_admin_scroll.png")
        page_admin.evaluate("window.scrollTo(0, 0)")

        # FIGURA 4: Listado de Personas
        print("Capturing FIGURA 4: Persona List...")
        page_admin.goto(f"{base_url}/users/personas/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/03_persona_list.png")

        # FIGURA 5: Formulario de Registro de Persona
        print("Capturing FIGURA 5: Persona Form...")
        page_admin.goto(f"{base_url}/users/personas/nuevo/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/04_persona_form.png")

        # FIGURA 6: Detalle de una Persona
        print("Capturing FIGURA 6: Persona Detail...")
        page_admin.goto(f"{base_url}/users/personas/{persona_id}/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/05_persona_detail.png")

        # FIGURA 7: Listado de Localidades con mapa
        print("Capturing FIGURA 7: Localidad List...")
        page_admin.goto(f"{base_url}/users/localidades/")
        time.sleep(1.5) # Allow map to render
        page_admin.screenshot(path="screenshots/06_localidad_list.png")

        # FIGURA 8: Formulario de Registro de Localidad
        print("Capturing FIGURA 8: Localidad Form...")
        page_admin.goto(f"{base_url}/users/localidades/nuevo/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/07_localidad_form.png")

        # FIGURA 9: Listado de Empresas
        print("Capturing FIGURA 9: Empresa List...")
        page_admin.goto(f"{base_url}/fleet/empresas/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/08_empresa_list.png")

        # FIGURA 10: Detalle de una Empresa
        print("Capturing FIGURA 10: Empresa Detail...")
        page_admin.goto(f"{base_url}/fleet/empresas/{empresa_id}/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/09_empresa_detail.png")

        # FIGURA 11: Listado de Paradas con mapa
        print("Capturing FIGURA 11: Parada List...")
        page_admin.goto(f"{base_url}/fleet/paradas/")
        time.sleep(1.5) # Allow map to render
        page_admin.screenshot(path="screenshots/10_parada_list.png")

        # FIGURA 12: Formulario de Registro de Parada
        print("Capturing FIGURA 12: Parada Form...")
        page_admin.goto(f"{base_url}/fleet/paradas/nuevo/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/11_parada_form.png")

        # FIGURA 13: Listado de Buses
        print("Capturing FIGURA 13: Bus List...")
        page_admin.goto(f"{base_url}/fleet/buses/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/12_bus_list.png")

        # FIGURA 14: Detalle de un Bus
        print("Capturing FIGURA 14: Bus Detail...")
        page_admin.goto(f"{base_url}/fleet/buses/{bus_id}/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/13_bus_detail.png")

        # FIGURA 15: Listado de Itinerarios
        print("Capturing FIGURA 15: Itinerario List...")
        page_admin.goto(f"{base_url}/itineraries/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/14_itinerario_list.png")

        # FIGURA 16: Formulario de Creacion de Itinerario
        print("Capturing FIGURA 16: Itinerario Form...")
        page_admin.goto(f"{base_url}/itineraries/nuevo/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/15_itinerario_form.png")

        # FIGURA 17: Detalle de un Itinerario
        print("Capturing FIGURA 17: Itinerario Detail...")
        page_admin.goto(f"{base_url}/itineraries/{itinerario_id}/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/16_itinerario_detail.png")

        # FIGURA 18: Detalle - Secuencia de paradas
        print("Capturing FIGURA 18: Itinerario Stops Scroll...")
        page_admin.evaluate("window.scrollTo(0, 450)")
        time.sleep(0.5)
        page_admin.screenshot(path="screenshots/16b_itinerario_detail_scroll.png")
        page_admin.evaluate("window.scrollTo(0, 0)")

        # FIGURA 19: Listado de Precios
        print("Capturing FIGURA 19: Price List...")
        page_admin.goto(f"{base_url}/itineraries/precios/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/17_precio_list.png")

        # FIGURA 20: Listado de Horarios
        print("Capturing FIGURA 20: Horario List...")
        page_admin.goto(f"{base_url}/itineraries/horarios/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/18_horario_list.png")

        # FIGURA 21: Dashboard de Operaciones
        print("Capturing FIGURA 21: Operations Dashboard...")
        page_admin.goto(f"{base_url}/operations/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/19_operations_dashboard.png")

        # FIGURA 22: Listado de Viajes
        print("Capturing FIGURA 22: Viaje List...")
        page_admin.goto(f"{base_url}/operations/viajes/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/20_viaje_list.png")

        # FIGURA 23: Formulario de Creacion de Viaje
        print("Capturing FIGURA 23: Viaje Form...")
        page_admin.goto(f"{base_url}/operations/viajes/nuevo/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/21_viaje_form.png")

        # FIGURA 24: Detalle de un Viaje
        print("Capturing FIGURA 24: Viaje Detail...")
        page_admin.goto(f"{base_url}/operations/viajes/{viaje_id}/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/22_viaje_detail.png")

        # FIGURA 25: Detalle de Viaje - Pasajeros y Encomiendas
        print("Capturing FIGURA 25: Viaje Detail Scroll...")
        page_admin.evaluate("window.scrollTo(0, 550)")
        time.sleep(0.5)
        page_admin.screenshot(path="screenshots/22b_viaje_detail_scroll.png")
        page_admin.evaluate("window.scrollTo(0, 0)")

        # FIGURA 26: Formulario de Venta de Pasaje
        print("Capturing FIGURA 26: Pasaje Venta Form...")
        page_admin.goto(f"{base_url}/operations/viajes/{viaje_id}/vender-pasaje/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/23_pasaje_venta.png")

        # FIGURA 27: Seleccion de asientos (Interactive Modal)
        print("Capturing FIGURA 27: Seat Selection Modal...")
        # Select valid origin (2 = Terminal Asunción) and destination (17 = Terminal Ciudad del Este)
        page_admin.locator("#id_parada_origen").select_option(value="2")
        time.sleep(0.5)
        page_admin.locator("#id_parada_destino").select_option(value="17")
        time.sleep(0.5)
            
        page_admin.click("#btn-trigger-mapa")
        page_admin.wait_for_selector("#modal-mapa-asientos", state="visible")
        time.sleep(1.5) # Wait for Ajax to fetch seat layout
        page_admin.screenshot(path="screenshots/23b_pasaje_venta_asientos.png")
        # Close the modal
        page_admin.click("#modal-mapa-asientos .btn-close")
        page_admin.wait_for_selector("#modal-mapa-asientos", state="hidden")

        # FIGURA 28: Listado de Pasajes
        print("Capturing FIGURA 28: Pasaje List...")
        page_admin.goto(f"{base_url}/operations/pasajes/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/24_pasaje_list.png")

        # FIGURA 29: Detalle de un Pasaje
        print("Capturing FIGURA 29: Pasaje Detail...")
        page_admin.goto(f"{base_url}/operations/pasajes/{pasaje_id}/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/25_pasaje_detail.png")

        # FIGURA 30: Listado de Encomiendas
        print("Capturing FIGURA 30: Encomienda List...")
        page_admin.goto(f"{base_url}/operations/encomiendas/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/26_encomienda_list.png")

        # FIGURA 31: Detalle de una Encomienda
        print("Capturing FIGURA 31: Encomienda Detail...")
        page_admin.goto(f"{base_url}/operations/encomiendas/{encomienda_id}/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/27_encomienda_detail.png")

        # FIGURA 33: Formulario de Creacion de Factura
        print("Capturing FIGURA 33: Factura Form...")
        page_admin.goto(f"{base_url}/operations/facturas/nueva/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/30_factura_form.png")

        # FIGURA 34: Clientes Pendientes de Facturar
        print("Capturing FIGURA 34: Clientes Pendientes Facturar...")
        page_admin.goto(f"{base_url}/operations/facturacion/pendientes/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/36_pendientes_factura.png")

        # FIGURA 35: Listado de Facturas
        print("Capturing FIGURA 35: Factura List...")
        page_admin.goto(f"{base_url}/operations/facturas/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/29_factura_list.png")

        # FIGURA 36: Listado de Timbrados
        print("Capturing FIGURA 36: Timbrado List...")
        page_admin.goto(f"{base_url}/operations/timbrados/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/31_timbrado_list.png")

        # FIGURA 37: Dashboard de Caja
        print("Capturing FIGURA 37: Caja Dashboard...")
        page_admin.goto(f"{base_url}/operations/caja/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/32_caja_dashboard.png")

        # FIGURA 38: Reporte Diario de Operaciones
        print("Capturing FIGURA 38: Reporte Diario...")
        page_admin.goto(f"{base_url}/operations/reportes/diario/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/33_reporte_diario.png")

        # FIGURA 39: Reporte de Ventas
        print("Capturing FIGURA 39: Reporte Ventas...")
        page_admin.goto(f"{base_url}/operations/reportes/ventas/")
        page_admin.wait_for_load_state("networkidle")
        page_admin.screenshot(path="screenshots/34_reporte_ventas.png")

        # FIGURA 42: Mapa de Rastreo en Tiempo Real (Admin)
        print("Capturing FIGURA 42: Admin GPS Tracking Map...")
        page_admin.goto(f"{base_url}/operations/rastreo-mapa/")
        time.sleep(2.0) # Wait for map scripts to execute and load leaflet/openstreetmaps
        page_admin.screenshot(path="screenshots/35_rastreo_mapa.png")

        # Close Admin context
        context_admin.close()
        print("Admin context closed.")

        # ----------------------------------------------------
        # SESSION 2: AYUDANTE (Juan / 123)
        # ----------------------------------------------------
        print("\nStarting Session 2: Ayudante (Juan)")
        context_juan = browser.new_context(viewport={"width": 1280, "height": 800})
        page_juan = context_juan.new_page()
        page_juan.goto(f"{base_url}/login/")
        page_juan.fill("input[name='username']", "Juan")
        page_juan.fill("input[name='password']", "123")
        page_juan.press("input[name='password']", "Enter")
        page_juan.wait_for_load_state("networkidle")
        time.sleep(1.0)
        print("Logged in as Ayudante successfully.")

        # FIGURA 41: Dashboard del Ayudante/Chofer
        print("Capturing FIGURA 41: Ayudante Dashboard...")
        page_juan.goto(f"{base_url}/operations/ayudante/")
        page_juan.wait_for_load_state("networkidle")
        time.sleep(1.0)
        page_juan.screenshot(path="screenshots/37_dashboard_ayudante.png")
        
        context_juan.close()

        # ----------------------------------------------------
        # SESSION 3: AGENTE (Gabriel / 123)
        # ----------------------------------------------------
        print("\nStarting Session 3: Agente (Gabriel)")
        context_gabriel = browser.new_context(viewport={"width": 1280, "height": 800})
        page_gabriel = context_gabriel.new_page()
        page_gabriel.goto(f"{base_url}/login/")
        page_gabriel.fill("input[name='username']", "Gabriel")
        page_gabriel.fill("input[name='password']", "123")
        page_gabriel.press("input[name='password']", "Enter")
        page_gabriel.wait_for_load_state("networkidle")
        time.sleep(1.0)
        print("Logged in as Agente successfully.")

        # FIGURA 40: Dashboard del Agente Comercial
        print("Capturing FIGURA 40: Agente Dashboard...")
        page_gabriel.goto(f"{base_url}/operations/")
        page_gabriel.wait_for_load_state("networkidle")
        page_gabriel.screenshot(path="screenshots/41_dashboard_agente.png")
        
        context_gabriel.close()

        # ----------------------------------------------------
        # SESSION 4: CLIENTE (Ivan / 123)
        # ----------------------------------------------------
        print("\nStarting Session 4: Cliente (Ivan)")
        context_ivan = browser.new_context(viewport={"width": 1280, "height": 800})
        page_ivan = context_ivan.new_page()
        page_ivan.goto(f"{base_url}/login/")
        page_ivan.fill("input[name='username']", "Ivan")
        page_ivan.fill("input[name='password']", "123")
        page_ivan.press("input[name='password']", "Enter")
        page_ivan.wait_for_load_state("networkidle")
        time.sleep(1.0)
        print("Logged in as Cliente successfully.")

        # FIGURA 43: Dashboard del Cliente
        print("Capturing FIGURA 43: Cliente Dashboard...")
        page_ivan.goto(f"{base_url}/users/dashboard/")
        page_ivan.wait_for_load_state("networkidle")
        page_ivan.screenshot(path="screenshots/38_dashboard_cliente.png")

        # FIGURA 44: Busqueda de Viajes
        print("Capturing FIGURA 44: Cliente Search Trips...")
        page_ivan.goto(f"{base_url}/operations/buscar-viajes/")
        page_ivan.wait_for_load_state("networkidle")
        page_ivan.screenshot(path="screenshots/39_buscar_viajes.png")
        
        context_ivan.close()

        # ----------------------------------------------------
        # SESSION 5: ANONYMOUS/PUBLIC PAGES
        # ----------------------------------------------------
        print("\nStarting Session 5: Anonymous/Public Views")
        context_public = browser.new_context(viewport={"width": 1280, "height": 800})
        page_public = context_public.new_page()

        # FIGURA 32: Rastreo Publico de Encomiendas
        print("Capturing FIGURA 32: Public Parcel Tracking...")
        page_public.goto(f"{base_url}/operations/rastreo/")
        page_public.wait_for_load_state("networkidle")
        page_public.screenshot(path="screenshots/28_rastreo_publico.png")

        # FIGURA 45: Mapa Publico de Rastreo de Buses
        print("Capturing FIGURA 45: Public GPS Bus Tracking Map...")
        page_public.goto(f"{base_url}/operations/rastreo-publico/")
        time.sleep(2.0) # Allow map to load
        page_public.screenshot(path="screenshots/40_rastreo_publico_mapa.png")

        context_public.close()

        # Close Browser
        browser.close()
        print("\nAll sessions closed successfully.")

if __name__ == "__main__":
    take_screenshots()
    print("FINISHED taking all screenshots successfully.")
