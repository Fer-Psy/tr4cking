"""
URL configuration for base project.
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

from django.views.generic.base import RedirectView

from . import views
from .views import DashboardView

urlpatterns = [
    path('debug-view/', views.debug_view),
    path('debug-view-2/', views.debug_view_2),
    path('favicon.ico', RedirectView.as_view(url='/static/img/favicon.svg')),

    # Admin
    path('admin/', admin.site.urls),
    
    path('login/', auth_views.LoginView.as_view(
        template_name='auth/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Password Reset
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='auth/password_reset_form.html',
        email_template_name='auth/password_reset_email.html',
        subject_template_name='auth/password_reset_subject.txt',
        success_url='/password_reset/done/'
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='auth/password_reset_done.html'
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='auth/password_reset_confirm.html',
        success_url='/reset/done/'
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='auth/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Dashboard
    path('', DashboardView.as_view(), name='dashboard'),
    
    # Apps
    path('users/', include('users.urls', namespace='users')),
    path('fleet/', include('fleet.urls', namespace='fleet')),
    path('itineraries/', include('itineraries.urls', namespace='itineraries')),
    path('operations/', include('operations.urls', namespace='operations')),
]
