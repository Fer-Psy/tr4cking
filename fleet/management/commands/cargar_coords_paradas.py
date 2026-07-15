"""
Management command para cargar/actualizar coordenadas GPS de paradas sin coordenadas.
Uso: python manage.py cargar_coords_paradas
"""
from django.core.management.base import BaseCommand
from fleet.models import Parada


COORDS_MAP = {
    # --- Asuncion y Gran Asuncion ---
    'asunci':               (-25.312918, -57.564998),
    'san lorenzo':          (-25.339600, -57.509700),
    'capiat':               (-25.361500, -57.433900),
    'itaugu':               (-25.385400, -57.341400),
    'ypacara':              (-25.399500, -57.283100),
    'caacup':               (-25.387200, -57.142000),
    'eusebio ayala':        (-25.372100, -56.963400),
    'eusebio':              (-25.372100, -56.963400),
    'san jos':              (-25.405400, -56.540100),   # San Jose de los Arroyos
    # --- Coronel Oviedo ---
    'coronel oviedo':       (-25.444300, -56.442800),
    'oviedo':               (-25.444300, -56.442800),
    # --- Tramo Oviedo -> Encarnacion (sur) ---
    'caaguaz':              (-25.452684, -56.015243),
    'juan nepomuceno':      (-26.107800, -55.941100),
    'san juan nepomu':      (-26.107800, -55.941100),
    'nepomuceno':           (-26.107800, -55.941100),
    'yuty':                 (-26.619400, -56.250300),
    'santa rosa del mi':    (-26.889200, -56.854400),
    'santa rosa':           (-26.889200, -56.854400),
    'coronel bogado':       (-27.179800, -56.258100),
    'bogado':               (-27.179800, -56.258100),
    'obligado':             (-27.261700, -55.841700),
    'fram':                 (-27.002200, -55.973900),
    'encarnaci':            (-27.335800, -55.868000),
    # --- Tramo Este (Ciudad del Este / Alto Parana) ---
    'mbocayaty':            (-25.728900, -56.411600),
    'villarrica':           (-25.779770, -56.444738),
    'coronel martinez':     (-25.694800, -56.060400),
    'cde':                  (-25.509700, -54.611100),
    'ciudad del este':      (-25.509700, -54.611100),
    'hernandarias':         (-25.397700, -54.619500),
    'minga guazu':          (-25.480000, -54.730000),
    # --- Norte / Concepcion ---
    'concepci':             (-23.412300, -57.434200),
    'pedro juan':           (-22.544700, -55.729100),
    'pedro juan caballero': (-22.544700, -55.729100),
    'horqueta':             (-23.344900, -57.055600),
    'antonio':              (-23.153600, -56.996300),   # San Antonio
    # --- Itapua / Sur ---
    'natalio':              (-26.665800, -55.461400),
    'bella vista sur':      (-27.042500, -55.581900),
    'bella vista norte':    (-22.135200, -56.527200),
    'bella vista':          (-27.042500, -55.581900),
    'ayolas':               (-27.372800, -56.897800),
    'san cosme':            (-27.286100, -56.415300),
    'pilar':                (-26.862000, -58.302800),
    'ita':                  (-25.490000, -57.363900),   # Ita
    # --- Misiones ---
    'san miguel':           (-26.475800, -57.098100),
    'san juan bautista':    (-26.683000, -57.143000),
    'san ignacio':          (-26.882900, -57.024700),
    'santiago':             (-26.772700, -56.762800),
    # --- Canindeyu ---
    'salto del guaira':     (-24.063700, -54.318000),
    'curuguaty':            (-24.510200, -55.710300),
}


class Command(BaseCommand):
    help = 'Carga coordenadas GPS en paradas que no las tienen registradas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--forzar',
            action='store_true',
            help='Sobrescribir coordenadas existentes (por defecto solo actualiza las que no tienen)',
        )

    def handle(self, *args, **options):
        forzar = options['forzar']
        qs = Parada.objects.filter(activo=True)
        if not forzar:
            qs = qs.filter(latitud_gps__isnull=True)

        total = qs.count()
        actualizadas = 0
        sin_match = []

        self.stdout.write(f"Procesando {total} paradas sin coordenadas...")

        for parada in qs:
            texto = parada.nombre.lower()
            if parada.localidad:
                texto += ' ' + parada.localidad.nombre.lower()

            matched = False
            for key, (lat, lng) in COORDS_MAP.items():
                if key in texto:
                    parada.latitud_gps = lat
                    parada.longitud_gps = lng
                    parada.save(update_fields=['latitud_gps', 'longitud_gps'])
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  [OK] '{parada.nombre}' ({parada.localidad}) -> ({lat}, {lng})"
                        )
                    )
                    actualizadas += 1
                    matched = True
                    break

            if not matched:
                sin_match.append(f"'{parada.nombre}' ({parada.localidad})")

        self.stdout.write(f"\n=== Resultado ===")
        self.stdout.write(self.style.SUCCESS(f"Actualizadas: {actualizadas}/{total}"))

        if sin_match:
            self.stdout.write(self.style.WARNING(f"\nSin coordenadas encontradas ({len(sin_match)}):"))
            for s in sin_match:
                self.stdout.write(f"  - {s}")
            self.stdout.write(
                self.style.WARNING(
                    "\nPara estas paradas, cargalas manualmente en Admin > Fleet > Paradas"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("Todas las paradas tienen coordenadas."))
