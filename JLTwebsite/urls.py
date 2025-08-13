from django.urls import path, include
from rest_framework.routers import DefaultRouter
from JLTsite import views, admin_views
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

router = DefaultRouter()
urlpatterns = [
    path('api/', include(router.urls)),
    path('admin/', admin.site.urls, name ="admin"),
    path('', views.home, name='home'),
    path('repas/', views.repas, name='repas'),
    path('événements/', views.evenement, name='événements'),
    path('contacts/', views.contacts, name='contacts'),
    path('contact/submit/', views.submit_contact_form, name='submit_contact'),
    path('api/contact/submit/', views.submit_contact_api, name='submit_contact_api'),
    path('contact/success/', views.contact_success, name='contact_success'),

    # ========== AUTHENTIFICATION ==========
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # ========== BOUTIQUE ==========
    path('shop-boites-a-lunch/', views.shop_view, name='shop_boites_lunch'),
    path('product/<slug:slug>/', views.product_detail_view, name='product_detail'),
    
    # ========== PANIER ==========
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/', views.remove_from_cart, name='remove_from_cart'),
    
    # ========== COMMANDE ==========
    path('checkout/', views.checkout_view, name='checkout'),
    path('order/confirmation/<str:order_number>/', views.order_confirmation_view, name='order_confirmation'),
    
    # ========== DASHBOARD CLIENT ==========
    path('account/', views.customer_dashboard, name='customer_dashboard'),
    path('account/orders/', views.customer_orders, name='customer_orders'),
    path('account/order/<str:order_number>/', views.customer_order_detail, name='customer_order_detail'),
    path('account/profile/', views.customer_profile, name='customer_profile'),
    
    # ========== DASHBOARD ADMIN ==========
    path('admin-dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/orders/', admin_views.admin_orders_list, name='admin_orders_list'),
    path('admin-dashboard/order/<str:order_number>/', admin_views.admin_order_detail, name='admin_order_detail'),
    path('admin-dashboard/order/<str:order_number>/invoice/', admin_views.admin_order_invoice, name='admin_order_invoice'),
    
    path('admin-dashboard/products/', admin_views.admin_products_list, name='admin_products_list'),
    path('admin-dashboard/products/update-stock/', admin_views.admin_product_update_stock, name='admin_product_update_stock'),
    
    path('admin-dashboard/customers/', admin_views.admin_customers_list, name='admin_customers_list'),
    path('admin-dashboard/customer/<int:user_id>/', admin_views.admin_customer_detail, name='admin_customer_detail'),
    
    path('admin-dashboard/reports/', admin_views.admin_reports, name='admin_reports'),
    path('admin-dashboard/export/', admin_views.admin_export_data, name='admin_export_data'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
