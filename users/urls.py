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
    path('personas/<int:pk>/', views.PersonaDetailView.as_view(), name='persona_detail'),
    path('personas/<int:pk>/editar/', views.PersonaUpdateView.as_view(), name='persona_update'),
    path('personas/<int:pk>/eliminar/', views.PersonaDeleteView.as_view(), name='persona_delete'),
    
    # Localidades
    path('localidades/', views.LocalidadListView.as_view(), name='localidad_list'),
    path('localidades/nuevo/', views.LocalidadCreateView.as_view(), name='localidad_create'),
    path('localidades/<int:pk>/', views.LocalidadDetailView.as_view(), name='localidad_detail'),
    path('localidades/<int:pk>/editar/', views.LocalidadUpdateView.as_view(), name='localidad_update'),
    path('localidades/<int:pk>/eliminar/', views.LocalidadDeleteView.as_view(), name='localidad_delete'),
]
