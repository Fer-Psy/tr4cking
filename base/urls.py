"""
URL configuration for base project.
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

from .views import DashboardView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(
        template_name='auth/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Dashboard
    path('', DashboardView.as_view(), name='dashboard'),
    
    # Apps
    path('users/', include('users.urls', namespace='users')),
    path('fleet/', include('fleet.urls', namespace='fleet')),
    path('itineraries/', include('itineraries.urls', namespace='itineraries')),
]
