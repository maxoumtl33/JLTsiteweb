from django.urls import path, include
from rest_framework.routers import DefaultRouter
from JLTsite import api_views, views
from django.contrib import admin


router = DefaultRouter()
router.register(r'lunch-boxes', api_views.LunchBoxViewSet)
router.register(r'cart', api_views.CartViewSet, basename='cart')
router.register(r'orders', api_views.OrderViewSet, basename='order')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/payment/create-intent/', api_views.create_payment_intent),
    path('api/dashboard/stats/', api_views.dashboard_stats),
    path('api/webhook/stripe/', api_views.webhook_stripe),
    path('admin/', admin.site.urls, name ="admin"),
    path('', views.home, name='home'),
    path('repas/', views.repas, name='repas'),
    path('événements/', views.evenement, name='événements'),
    path('contacts/', views.contacts, name='contacts'),

]
