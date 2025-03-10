"""
URL configuration for JLTwebsite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from JLTsite import views
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include



urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),  # Définit la route pour la page d'accueil
    path('dashboard', views.dashboard, name='dashboard'),
    path('create-boitelunch/', views.create_boite, name='create_boite'),
    path('edit-boitelunch/<int:pk>/', views.edit_boite, name='edit_boite'),
    path('accounts/', include('django.contrib.auth.urls')),  # Include the auth URLs
    path('get_boites/<int:category_id>/', views.get_boites, name='get_boites'),  # Add the new URL pattern
    path('boite/<int:boite_id>/', views.boite_detail, name='boite_detail'),
    path('contact/', views.contact_view, name='contact'),
    path('events/', views.home_events, name='home_events'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)