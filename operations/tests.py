from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from users.models import Persona, Localidad
from operations.models import Pasaje, Viaje
from fleet.models import Bus, Asiento, Parada, Empresa
from itineraries.models import Itinerario, DetalleItinerario
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


class AyudanteOverbookingTests(TestCase):
    def setUp(self):
        # 1. Create users and personas
        self.ayudante_user = User.objects.create_user(username='ayudante', password='password123')
        self.ayudante_persona = Persona.objects.create(
            cedula=444444,
            user=self.ayudante_user,
            nombre='Ayudante',
            apellido='Test',
            telefono='444444',
            es_ayudante=True,
            es_cliente=False
        )

        self.otro_user = User.objects.create_user(username='otro', password='password123')
        self.otro_persona = Persona.objects.create(
            cedula=555555,
            user=self.otro_user,
            nombre='Otro',
            apellido='Vendedor',
            telefono='555555',
            es_agente=True,
            es_cliente=False
        )

        # 2. Master data
        self.empresa = Empresa.objects.create(nombre="Empresa Test", ruc="12345-6")
        self.localidad = Localidad.objects.create(nombre="Asuncion")
        self.bus = Bus.objects.create(placa="AAA-123", capacidad_asientos=40, empresa=self.empresa)
        self.asiento = Asiento.objects.create(numero_asiento=1, bus=self.bus)
        self.parada_origen = Parada.objects.create(nombre="Origen", empresa=self.empresa, localidad=self.localidad)
        self.parada_destino = Parada.objects.create(nombre="Destino", empresa=self.empresa, localidad=self.localidad)
        
        self.itinerario = Itinerario.objects.create(nombre="Ruta Test", dias_semana="1111111", empresa=self.empresa)
        
        # Setup stops order
        self.detalle_origen = DetalleItinerario.objects.create(
            itinerario=self.itinerario,
            parada=self.parada_origen,
            orden=1
        )
        self.detalle_destino = DetalleItinerario.objects.create(
            itinerario=self.itinerario,
            parada=self.parada_destino,
            orden=2
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

    def test_obtener_mapa_ocupacion_returns_vendedor_id(self):
        # Create a ticket sold by ayudante
        pasaje = Pasaje.objects.create(
            viaje=self.viaje,
            asiento=self.asiento,
            pasajero=self.ayudante_persona,
            parada_origen=self.parada_origen,
            parada_destino=self.parada_destino,
            precio=50000.00,
            vendedor=self.ayudante_user,
            estado='vendido',
            orden_origen=1,
            orden_destino=2
        )

        from operations.utils import obtener_mapa_ocupacion
        mapa = obtener_mapa_ocupacion(self.viaje)
        
        self.assertIn(self.asiento.id, mapa)
        self.assertEqual(mapa[self.asiento.id][0]['vendedor_id'], self.ayudante_user.id)

    def test_api_asientos_segmento_returns_expected_fields(self):
        # Create a ticket sold by ayudante
        Pasaje.objects.create(
            viaje=self.viaje,
            asiento=self.asiento,
            pasajero=self.ayudante_persona,
            parada_origen=self.parada_origen,
            parada_destino=self.parada_destino,
            precio=50000.00,
            vendedor=self.ayudante_user,
            estado='vendido',
            orden_origen=1,
            orden_destino=2
        )

        self.client.login(username='ayudante', password='password123')
        
        # Call the endpoint
        response = self.client.get(
            reverse('operations:api_asientos_segmento', kwargs={'viaje_pk': self.viaje.pk}),
            {'origen': self.parada_origen.id, 'destino': self.parada_destino.id}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['es_ayudante'])
        self.assertEqual(data['usuario_actual_id'], self.ayudante_user.id)
        
        # Find our seat in response
        seat_info = next(s for s in data['asientos'] if s['id'] == self.asiento.id)
        self.assertFalse(seat_info['disponible'])
        self.assertEqual(seat_info['ocupaciones'][0]['vendedor_id'], self.ayudante_user.id)

    def test_pasaje_venta_form_validation_for_ayudante(self):
        from operations.forms import PasajeVentaForm
        from django.core.exceptions import ValidationError

        # CASE 1: Seat is sold by the ayudante themselves -> Should be ALLOWED
        pasaje_mio = Pasaje.objects.create(
            viaje=self.viaje,
            asiento=self.asiento,
            pasajero=self.ayudante_persona,
            parada_origen=self.parada_origen,
            parada_destino=self.parada_destino,
            precio=50000.00,
            vendedor=self.ayudante_user,
            estado='vendido',
            orden_origen=1,
            orden_destino=2
        )

        # Form with same seat and overlapping segment
        form_data = {
            'viaje': self.viaje.id,
            'asiento': self.asiento.id,
            'parada_origen': self.parada_origen.id,
            'parada_destino': self.parada_destino.id,
            'precio': 50000.00,
            'cedula_pasajero': 999999,
            'nombre_pasajero': 'Nuevo',
            'apellido_pasajero': 'Pasajero',
        }

        form = PasajeVentaForm(data=form_data, viaje=self.viaje, user=self.ayudante_user)
        self.assertTrue(form.is_valid())

        # CASE 2: Seat is sold by another seller -> Should NOT be allowed
        pasaje_mio.delete()
        Pasaje.objects.create(
            viaje=self.viaje,
            asiento=self.asiento,
            pasajero=self.otro_persona,
            parada_origen=self.parada_origen,
            parada_destino=self.parada_destino,
            precio=50000.00,
            vendedor=self.otro_user,
            estado='vendido',
            orden_origen=1,
            orden_destino=2
        )

        form = PasajeVentaForm(data=form_data, viaje=self.viaje, user=self.ayudante_user)
        self.assertFalse(form.is_valid())
        self.assertIn('ya está vendido en este tramo por otro vendedor', form.errors['__all__'][0])

        # CASE 3: Seat is reserved (even if by the ayudante) -> Should NOT be allowed
        Pasaje.objects.filter(asiento=self.asiento).delete()
        Pasaje.objects.create(
            viaje=self.viaje,
            asiento=self.asiento,
            pasajero=self.ayudante_persona,
            parada_origen=self.parada_origen,
            parada_destino=self.parada_destino,
            precio=50000.00,
            vendedor=self.ayudante_user,
            estado='reservado',
            orden_origen=1,
            orden_destino=2
        )

        form = PasajeVentaForm(data=form_data, viaje=self.viaje, user=self.ayudante_user)
        self.assertFalse(form.is_valid())
        self.assertIn('tiene una RESERVA ACTIVA', form.errors['__all__'][0])


class EncomiendaCrewSecurityTests(TestCase):
    def setUp(self):
        # 1. Create crew member (ayudante felipe)
        self.felipe_user = User.objects.create_user(username='felipe', password='password123')
        self.felipe_persona = Persona.objects.create(
            cedula=5333333,
            user=self.felipe_user,
            nombre='Felipe',
            apellido='Saucedo',
            telefono='555-555',
            es_ayudante=True
        )

        # 2. Create another user (Ivan - passenger/remitente)
        self.ivan_user = User.objects.create_user(username='Ivan', password='password123')
        self.ivan_persona = Persona.objects.create(
            cedula=111111,
            user=self.ivan_user,
            nombre='Ivan',
            apellido='Frutos',
            telefono='123456789',
            es_cliente=True
        )

        # 3. Create regular/admin user
        self.admin = User.objects.create_superuser(username='admin', password='password123')

        # 4. Master data
        self.empresa = Empresa.objects.create(nombre="Empresa Test", ruc="12345-6")
        self.localidad = Localidad.objects.create(nombre="Asuncion")
        self.bus = Bus.objects.create(placa="AAA-123", capacidad_asientos=40, empresa=self.empresa)
        self.parada_origen = Parada.objects.create(nombre="Origen", empresa=self.empresa, localidad=self.localidad)
        self.parada_destino = Parada.objects.create(nombre="Destino", empresa=self.empresa, localidad=self.localidad)
        self.itinerario = Itinerario.objects.create(nombre="Asuncion-Natalio", dias_semana="1111111", empresa=self.empresa)
        
        self.viaje_felipe = Viaje.objects.create(
            empresa=self.empresa,
            itinerario=self.itinerario,
            bus=self.bus,
            chofer=self.felipe_persona,  # assigned to felipe
            fecha_viaje=datetime.date.today()
        )
        self.viaje_felipe.ayudantes.add(self.felipe_persona)

        # Create another viaje felipe is NOT assigned to
        self.itinerario_cde = Itinerario.objects.create(nombre="Asuncion-Ciudad del Este", dias_semana="1111111", empresa=self.empresa)
        self.chofer_otro = Persona.objects.create(cedula=99999, nombre="Chofer", apellido="Otro", es_chofer=True)
        self.viaje_otro = Viaje.objects.create(
            empresa=self.empresa,
            itinerario=self.itinerario_cde,
            bus=self.bus,
            chofer=self.chofer_otro,
            fecha_viaje=datetime.date.today()
        )

        # Create a past trip felipe is assigned to, but it's not active
        self.viaje_past = Viaje.objects.create(
            empresa=self.empresa,
            itinerario=self.itinerario,
            bus=self.bus,
            chofer=self.felipe_persona,
            fecha_viaje=datetime.date.today() - datetime.timedelta(days=5),
            estado='programado'
        )
        self.viaje_past.ayudantes.add(self.felipe_persona)

        # 5. Create encomiendas
        from operations.models import Encomienda
        self.enc_felipe = Encomienda.objects.create(
            viaje=self.viaje_felipe,
            remitente=self.ivan_persona,
            destinatario=self.felipe_persona,
            parada_origen=self.parada_origen,
            parada_destino=self.parada_destino,
            precio=30000.00,
            registrador=self.admin
        )
        self.enc_otro = Encomienda.objects.create(
            viaje=self.viaje_otro,
            remitente=self.ivan_persona,
            destinatario=self.ivan_persona,
            parada_origen=self.parada_origen,
            parada_destino=self.parada_destino,
            precio=40000.00,
            registrador=self.admin
        )
        self.enc_past = Encomienda.objects.create(
            viaje=self.viaje_past,
            remitente=self.ivan_persona,
            destinatario=self.felipe_persona,
            parada_origen=self.parada_origen,
            parada_destino=self.parada_destino,
            precio=35000.00,
            registrador=self.admin
        )

    def test_encomienda_list_filters_for_crew(self):
        # Admin should see all 3
        self.client.login(username='admin', password='password123')
        response = self.client.get(reverse('operations:encomienda_list'))
        self.assertEqual(len(response.context['encomiendas']), 3)

        # Felipe (ayudante) should only see his active/future trip's encomienda, NOT the past one or the other one
        self.client.login(username='felipe', password='password123')
        response = self.client.get(reverse('operations:encomienda_list'))
        self.assertEqual(len(response.context['encomiendas']), 1)
        self.assertEqual(response.context['encomiendas'][0].pk, self.enc_felipe.pk)

    def test_encomienda_detail_forbidden_for_crew(self):
        self.client.login(username='felipe', password='password123')
        # Accessing own active encomienda should succeed
        response = self.client.get(reverse('operations:encomienda_detail', kwargs={'pk': self.enc_felipe.pk}))
        self.assertEqual(response.status_code, 200)

        # Accessing other encomienda should give 404
        response = self.client.get(reverse('operations:encomienda_detail', kwargs={'pk': self.enc_otro.pk}))
        self.assertEqual(response.status_code, 404)

        # Accessing past inactive encomienda should also give 404
        response = self.client.get(reverse('operations:encomienda_detail', kwargs={'pk': self.enc_past.pk}))
        self.assertEqual(response.status_code, 404)

    def test_encomienda_actions_forbidden_for_crew(self):
        self.client.login(username='felipe', password='password123')
        
        # 1. GET delivery for own active encomienda should succeed (200 OK)
        response = self.client.get(reverse('operations:encomienda_entregar', kwargs={'pk': self.enc_felipe.pk}))
        self.assertEqual(response.status_code, 200)

        # 2. GET delivery for other encomienda should redirect with error (302)
        response = self.client.get(reverse('operations:encomienda_entregar', kwargs={'pk': self.enc_otro.pk}))
        self.assertEqual(response.status_code, 302)

        # 3. POST delivery for own active encomienda (valid data) should succeed and redirect (302)
        delivery_data = {
            'receptor_nombre': 'Juan Perez',
            'receptor_cedula': '123456'
        }
        response = self.client.post(
            reverse('operations:encomienda_entregar', kwargs={'pk': self.enc_felipe.pk}),
            data=delivery_data
        )
        self.assertEqual(response.status_code, 302)
        self.enc_felipe.refresh_from_db()
        self.assertEqual(self.enc_felipe.estado, 'entregado')

        # Reset state to test boarding
        self.enc_felipe.estado = 'registrado'
        self.enc_felipe.save()

        # 4. POST boarding for own active encomienda should succeed (200 OK)
        response = self.client.post(reverse('operations:encomienda_abordar', kwargs={'pk': self.enc_felipe.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['ok'], True)

        # 5. POST boarding for other encomienda should be forbidden (403)
        response = self.client.post(reverse('operations:encomienda_abordar', kwargs={'pk': self.enc_otro.pk}))
        self.assertEqual(response.status_code, 403)


