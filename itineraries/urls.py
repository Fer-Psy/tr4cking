"""
URL configuration for itineraries app.
"""
from django.urls import path
from . import views

app_name = 'itineraries'

urlpatterns = [
    # Itinerarios
    path('', views.ItinerarioListView.as_view(), name='itinerario_list'),
    path('nuevo/', views.ItinerarioCreateView.as_view(), name='itinerario_create'),
    path('<int:pk>/', views.ItinerarioDetailView.as_view(), name='itinerario_detail'),
    path('<int:pk>/editar/', views.ItinerarioUpdateView.as_view(), name='itinerario_update'),
    path('<int:pk>/eliminar/', views.ItinerarioDeleteView.as_view(), name='itinerario_delete'),
    
    # Detalles de Itinerario (paradas)
    path('<int:itinerario_pk>/paradas/nuevo/', views.DetalleItinerarioCreateView.as_view(), name='detalle_create'),
    path('paradas/<int:pk>/editar/', views.DetalleItinerarioUpdateView.as_view(), name='detalle_update'),
    path('paradas/<int:pk>/eliminar/', views.DetalleItinerarioDeleteView.as_view(), name='detalle_delete'),
    
    # Precios
    path('precios/', views.PrecioListView.as_view(), name='precio_list'),
    path('precios/nuevo/', views.PrecioCreateView.as_view(), name='precio_create'),
    path('precios/<int:pk>/editar/', views.PrecioUpdateView.as_view(), name='precio_update'),
    path('precios/<int:pk>/eliminar/', views.PrecioDeleteView.as_view(), name='precio_delete'),
    
    # Horarios
    path('horarios/', views.HorarioListView.as_view(), name='horario_list'),
    path('horarios/nuevo/', views.HorarioCreateView.as_view(), name='horario_create_generic'),
    path('<int:itinerario_pk>/horarios/nuevo/', views.HorarioCreateView.as_view(), name='horario_create'),
    path('horarios/<int:pk>/eliminar/', views.HorarioDeleteView.as_view(), name='horario_delete'),
]
