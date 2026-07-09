"""
URL configuration for users app.
"""
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Personas
    path('personas/', views.PersonaListView.as_view(), name='persona_list'),
    path('personas/nuevo/', views.PersonaCreateView.as_view(), name='persona_create'),
    path('personas/<str:pk>/', views.PersonaDetailView.as_view(), name='persona_detail'),
    path('personas/<str:pk>/editar/', views.PersonaUpdateView.as_view(), name='persona_update'),
    path('personas/<str:pk>/eliminar/', views.PersonaDeleteView.as_view(), name='persona_delete'),
    path('personas/<str:pk>/dar-de-baja/', views.PersonaDarDeBajaView.as_view(), name='persona_dar_de_baja'),
    path('personas/<str:pk>/activar/', views.PersonaActivarView.as_view(), name='persona_activar'),
    
    # Localidades
    path('localidades/', views.LocalidadListView.as_view(), name='localidad_list'),
    path('localidades/nuevo/', views.LocalidadCreateView.as_view(), name='localidad_create'),
    path('localidades/nuevo-ajax/', views.LocalidadCreateAjaxView.as_view(), name='localidad_create_ajax'),
    path('localidades/<int:pk>/coords/', views.get_localidad_coords_ajax, name='localidad_coords_ajax'),
    path('localidades/<int:pk>/', views.LocalidadDetailView.as_view(), name='localidad_detail'),
    path('localidades/<int:pk>/editar/', views.LocalidadUpdateView.as_view(), name='localidad_update'),
    path('localidades/<int:pk>/eliminar/', views.LocalidadDeleteView.as_view(), name='localidad_delete'),
    
    # Registro y Dashboard público
    path('registro/', views.ClienteRegistroView.as_view(), name='cliente_registro'),
    path('perfil/', views.ClientePerfilUpdateView.as_view(), name='perfil'),
    path('dashboard/', views.DashboardClienteView.as_view(), name='dashboard_cliente'),
]
