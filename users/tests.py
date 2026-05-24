from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from users.models import Persona

class PersonaDeactivationTests(TestCase):
    def setUp(self):
        # Create an admin user
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password123'
        )
        # Create a non-admin user
        self.regular_user = User.objects.create_user(
            username='regular',
            email='regular@example.com',
            password='password123'
        )
        
        # Create a persona linked to a standard user (active)
        self.user_persona_1 = User.objects.create_user(
            username='persona1',
            email='p1@example.com',
            password='password123'
        )
        self.persona_active = Persona.objects.create(
            cedula=1234567,
            user=self.user_persona_1,
            nombre="Juan",
            apellido="Pérez",
            telefono="0981111222",
            activo=True
        )
        
        # Create another persona linked to a user (inactive)
        self.user_persona_2 = User.objects.create_user(
            username='persona2',
            email='p2@example.com',
            password='password123',
            is_active=False
        )
        self.persona_inactive = Persona.objects.create(
            cedula=7654321,
            user=self.user_persona_2,
            nombre="María",
            apellido="Gómez",
            telefono="0982222333",
            activo=False
        )

    def test_list_view_default_only_active(self):
        """By default, the list view only shows active personas."""
        self.client.login(username='admin', password='password123')
        response = self.client.get(reverse('users:persona_list'))
        self.assertEqual(response.status_code, 200)
        personas = list(response.context['personas'])
        self.assertIn(self.persona_active, personas)
        self.assertNotIn(self.persona_inactive, personas)

    def test_list_view_filter_inactive(self):
        """When filtering by 'inactivos', only inactive personas are shown."""
        self.client.login(username='admin', password='password123')
        response = self.client.get(reverse('users:persona_list'), {'estado': 'inactivos'})
        self.assertEqual(response.status_code, 200)
        personas = list(response.context['personas'])
        self.assertNotIn(self.persona_active, personas)
        self.assertIn(self.persona_inactive, personas)

    def test_list_view_filter_todos(self):
        """When filtering by 'todos', both active and inactive personas are shown."""
        self.client.login(username='admin', password='password123')
        response = self.client.get(reverse('users:persona_list'), {'estado': 'todos'})
        self.assertEqual(response.status_code, 200)
        personas = list(response.context['personas'])
        self.assertIn(self.persona_active, personas)
        self.assertIn(self.persona_inactive, personas)

    def test_dar_de_baja_admin(self):
        """Admin can deactivate a persona, which also deactivates the linked User."""
        self.client.login(username='admin', password='password123')
        
        # Verify initial status
        self.assertTrue(self.persona_active.activo)
        self.assertTrue(self.persona_active.user.is_active)
        
        url = reverse('users:persona_dar_de_baja', kwargs={'pk': self.persona_active.pk})
        response = self.client.post(url)
        
        # Redirects to list
        self.assertRedirects(response, reverse('users:persona_list'))
        
        # Refresh from db
        self.persona_active.refresh_from_db()
        self.persona_active.user.refresh_from_db()
        
        self.assertFalse(self.persona_active.activo)
        self.assertFalse(self.persona_active.user.is_active)

    def test_dar_de_baja_non_admin_denied(self):
        """A non-admin user cannot deactivate a persona."""
        self.client.login(username='regular', password='password123')
        
        url = reverse('users:persona_dar_de_baja', kwargs={'pk': self.persona_active.pk})
        response = self.client.post(url)
        
        # Denied (due to UserPassesTestMixin)
        self.assertEqual(response.status_code, 403)
        
        # Status remains unchanged
        self.persona_active.refresh_from_db()
        self.assertTrue(self.persona_active.activo)

    def test_activar_admin(self):
        """Admin can reactivate a persona, which also reactivates the linked User."""
        self.client.login(username='admin', password='password123')
        
        # Verify initial status
        self.assertFalse(self.persona_inactive.activo)
        self.assertFalse(self.persona_inactive.user.is_active)
        
        url = reverse('users:persona_activar', kwargs={'pk': self.persona_inactive.pk})
        response = self.client.post(url)
        
        # Redirects to list
        self.assertRedirects(response, reverse('users:persona_list'))
        
        # Refresh from db
        self.persona_inactive.refresh_from_db()
        self.persona_inactive.user.refresh_from_db()
        
        self.assertTrue(self.persona_inactive.activo)
        self.assertTrue(self.persona_inactive.user.is_active)

    def test_activar_non_admin_denied(self):
        """A non-admin user cannot reactivate a persona."""
        self.client.login(username='regular', password='password123')
        
        url = reverse('users:persona_activar', kwargs={'pk': self.persona_inactive.pk})
        response = self.client.post(url)
        
        # Denied
        self.assertEqual(response.status_code, 403)
        
        # Status remains unchanged
        self.persona_inactive.refresh_from_db()
        self.assertFalse(self.persona_inactive.activo)
