"""
URL configuration for fleet app.
"""
from django.urls import path
from . import views

app_name = 'fleet'

urlpatterns = [
    # Empresas
    path('empresas/', views.EmpresaListView.as_view(), name='empresa_list'),
    path('empresas/nuevo/', views.EmpresaCreateView.as_view(), name='empresa_create'),
    path('empresas/<int:pk>/', views.EmpresaDetailView.as_view(), name='empresa_detail'),
    path('empresas/<int:pk>/editar/', views.EmpresaUpdateView.as_view(), name='empresa_update'),
    path('empresas/<int:pk>/eliminar/', views.EmpresaDeleteView.as_view(), name='empresa_delete'),
    
    # Paradas
    path('paradas/', views.ParadaListView.as_view(), name='parada_list'),
    path('paradas/nuevo/', views.ParadaCreateView.as_view(), name='parada_create'),
    path('paradas/<int:pk>/', views.ParadaDetailView.as_view(), name='parada_detail'),
    path('paradas/<int:pk>/editar/', views.ParadaUpdateView.as_view(), name='parada_update'),
    path('paradas/<int:pk>/eliminar/', views.ParadaDeleteView.as_view(), name='parada_delete'),
    
    # Buses
    path('buses/', views.BusListView.as_view(), name='bus_list'),
    path('buses/nuevo/', views.BusCreateView.as_view(), name='bus_create'),
    path('buses/<int:pk>/', views.BusDetailView.as_view(), name='bus_detail'),
    path('buses/<int:pk>/editar/', views.BusUpdateView.as_view(), name='bus_update'),
    path('buses/<int:pk>/eliminar/', views.BusDeleteView.as_view(), name='bus_delete'),
    
    # Asientos
    path('buses/<int:bus_pk>/asientos/', views.AsientoListView.as_view(), name='asiento_list'),
    path('buses/<int:bus_pk>/asientos/nuevo/', views.AsientoCreateView.as_view(), name='asiento_create'),
    path('asientos/<int:pk>/editar/', views.AsientoUpdateView.as_view(), name='asiento_update'),
    path('asientos/<int:pk>/eliminar/', views.AsientoDeleteView.as_view(), name='asiento_delete'),
]
