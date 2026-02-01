# SGBE - Sistema de Gestión de Buses y Encomiendas

## Descripción del Proyecto
SGBE (tr4cking-app) es un sistema web integral diseñado para la gestión de flota de buses de larga distancia, reservas de pasajes y logística de encomiendas. Este proyecto se desarrolla como Trabajo Final de Grado Universitario, con un enfoque pragmático y orientado a la estabilidad.

## Características Principales
- **Gestión de Flota:** Control de buses, empresas, paradas e itinerarios.
- **Logística de Encomiendas:** Recepción, rastreo y entrega de paquetes.
- **Sistema de Reservas:** Gestión de pasajes y disponibilidad de asientos en tiempo real.
- **Gestión Financiera:** Control de cajas, facturación y arqueos.
- **Tracking en Tiempo Real:** Seguimiento de la ubicación de los buses y cálculo de ETA por parada.

## Stack Tecnológico
- **Backend:** Django 6.0.1 (Patrón MVT)
- **Frontend:** HTML5, Bootstrap 5, Django Crispy Forms
- **Interactividad:** HTMX y Alpine.js
- **Base de Datos:** SQLite (Desarrollo) / PostgreSQL (Producción)

## Estructura del Proyecto
- `base/`: Configuraciones principales de Django.
- `fleet/`: Gestión de buses, empresas y asientos.
- `itineraries/`: Itinerarios, paradas y matriz de precios.
- `users/`: Perfiles de usuarios y gestión de roles.
- `operations/`: (Próximamente) Gestión de viajes y reservas.
- `parcels/`: (Próximamente) Logística de encomiendas.
- `finance/`: (Próximamente) Facturación y cajas.

## Instalación y Configuración Local

### Requisitos Previos
- Python 3.10+
- Git

### Pasos para el despliegue local
1. **Clonar el repositorio:**
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd tr4cking-app
   ```

2. **Crear y activar un entorno virtual:**
   ```bash
   python -m venv venv
   # En Windows:
   .\venv\Scripts\activate
   # En Linux/macOS:
   source venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Realizar migraciones:**
   ```bash
   python manage.py migrate
   ```

5. **Crear un superusuario:**
   ```bash
   python manage.py createsuperuser
   ```

6. **Ejecutar el servidor de desarrollo:**
   ```bash
   python manage.py runserver
   ```

## Autores
- Proyecto impulsado por el equipo de desarrollo de tr4cking-app.
