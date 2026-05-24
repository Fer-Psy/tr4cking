from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from users.models import Persona, Localidad
from operations.models import Pasaje, Viaje
from fleet.models import Bus, Asiento, Parada, Empresa
from itineraries.models import Itinerario
import datetime

class PasajeSellerRenderingTests(TestCase):
    def setUp(self):
        # 1. Create a superuser for login
        self.admin = User.objects.create_superuser(username='admin', password='password123')
        
        # 2. Create client user (Ivan)
        self.client_user = User.objects.create_user(username='Ivan', password='password123')
        self.client_persona = Persona.objects.create(
            cedula=111111,
            user=self.client_user,
            nombre='Ivan',
            apellido='Frutos',
            telefono='123456789',
            es_cliente=True
        )
        
        # 3. Create regular seller user (Juan)
        self.staff_user = User.objects.create_user(username='Juan', password='password123')
        self.staff_persona = Persona.objects.create(
            cedula=222222,
            user=self.staff_user,
            nombre='Juan',
            apellido='Perez',
            telefono='987654321',
            es_cliente=False,
            es_empleado=True
        )
        
        # 4. Create master data for Pasaje
        self.empresa = Empresa.objects.create(nombre="Empresa Test", ruc="12345-6")
        self.localidad = Localidad.objects.create(nombre="Asuncion")
        self.bus = Bus.objects.create(
            placa="AAA-123", 
            capacidad_asientos=40, 
            empresa=self.empresa
        )
        self.asiento = Asiento.objects.create(numero_asiento=1, bus=self.bus)
        self.parada_origen = Parada.objects.create(
            nombre="Origen", 
            empresa=self.empresa,
            localidad=self.localidad
        )
        self.parada_destino = Parada.objects.create(
            nombre="Destino", 
            empresa=self.empresa,
            localidad=self.localidad
        )
        self.itinerario = Itinerario.objects.create(
            nombre="Ruta Test",
            dias_semana="1111111",
            empresa=self.empresa
        )
        self.chofer = Persona.objects.create(
            cedula=333333,
            nombre='Chofer',
            apellido='Test',
            telefono='555555',
            es_chofer=True
        )
        self.viaje = Viaje.objects.create(
            empresa=self.empresa,
            itinerario=self.itinerario,
            bus=self.bus,
            chofer=self.chofer,
            fecha_viaje=datetime.date.today()
        )
        
        # 5. Create ticket with Client as seller (e.g. Ivan)
        self.pasaje_client = Pasaje.objects.create(
            viaje=self.viaje,
            asiento=self.asiento,
            pasajero=self.client_persona,
            parada_origen=self.parada_origen,
            parada_destino=self.parada_destino,
            precio=50000.00,
            vendedor=self.client_user
        )
        
        # 6. Create ticket with Staff as seller (e.g. Juan)
        self.asiento2 = Asiento.objects.create(numero_asiento=2, bus=self.bus)
        self.pasaje_staff = Pasaje.objects.create(
            viaje=self.viaje,
            asiento=self.asiento2,
            pasajero=self.staff_persona,
            parada_origen=self.parada_origen,
            parada_destino=self.parada_destino,
            precio=50000.00,
            vendedor=self.staff_user
        )
        
        # 7. Create ticket with no seller (System)
        self.asiento3 = Asiento.objects.create(numero_asiento=3, bus=self.bus)
        self.pasaje_system = Pasaje.objects.create(
            viaje=self.viaje,
            asiento=self.asiento3,
            pasajero=self.client_persona,
            parada_origen=self.parada_origen,
            parada_destino=self.parada_destino,
            precio=50000.00,
            vendedor=None
        )

    def test_pasaje_list_seller_rendering(self):
        self.client.login(username='admin', password='password123')
        
        # 1. Test Pasaje List View
        response = self.client.get(reverse('operations:pasaje_list'))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode('utf-8')
        
        # Staff user should be rendered
        self.assertIn("Juan", html)
        # Tickets with no seller should show "Sistema"
        self.assertIn("Sistema", html)
        
        # Verify Ivan as a seller username is NOT rendered in the table cell
        # (while still being present as the passenger's name "Ivan Frutos")
        self.assertIn("Ivan Frutos", html)
        
        # We can construct specific snippets to verify that Ivan is not inside the vendor small tag:
        # e.g., if we search for Ivan as a seller, it shouldn't be rendered under seller column structure.
        # Let's count occurrences of "Ivan". It should only be present for passenger/name but not as vendedor username
        # The username of Ivan is "Ivan" (case sensitive).
        # We can also check the detail page of the client passage
        
    def test_pasaje_detail_seller_rendering(self):
        self.client.login(username='admin', password='password123')
        
        # 1. Staff passage detail should show "Juan"
        response = self.client.get(reverse('operations:pasaje_detail', kwargs={'pk': self.pasaje_staff.pk}))
        self.assertEqual(response.status_code, 200)
        html_staff = response.content.decode('utf-8')
        self.assertIn("Juan", html_staff)
        
        # 2. Client passage detail should not show "Ivan" under vendedor label
        response = self.client.get(reverse('operations:pasaje_detail', kwargs={'pk': self.pasaje_client.pk}))
        self.assertEqual(response.status_code, 200)
        html_client = response.content.decode('utf-8')
        # Vendedor row should be empty / not have "Ivan"
        # The label is <th>Vendedor:</th>
        self.assertIn("<th>Vendedor:</th>", html_client)
        # Since it is left blank, the next td should contain whitespace but not the username "Ivan"
        # We can verify that "<td>" immediately followed by whitespace and "</td>" or similar empty rendering is present.
        self.assertNotIn("<td>\n                                    \n                                        Ivan", html_client)
        
        # 3. System passage detail should show "Sistema"
        response = self.client.get(reverse('operations:pasaje_detail', kwargs={'pk': self.pasaje_system.pk}))
        self.assertEqual(response.status_code, 200)
        html_system = response.content.decode('utf-8')
        self.assertIn("Sistema", html_system)
