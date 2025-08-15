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

    path('admin-dashboard/orders/update-status/', admin_views.admin_order_update_status, name='admin_order_update_status'),
    path('admin-dashboard/orders/bulk-update/', admin_views.admin_orders_bulk_update, name='admin_orders_bulk_update'),
    path('admin-dashboard/order/<str:order_number>/duplicate/', admin_views.admin_order_duplicate, name='admin_order_duplicate'),
    path('admin-dashboard/order/<str:order_number>/cancel/', admin_views.admin_order_cancel, name='admin_order_cancel'),
    path('admin-dashboard/orders/send-email/', admin_views.admin_order_send_email, name='admin_order_send_email'),
    
    path('admin-dashboard/products/', admin_views.admin_products_list, name='admin_products_list'),
    path('admin-dashboard/products/create/', admin_views.admin_product_create, name='admin_product_create'),
    path('admin-dashboard/products/<int:product_id>/edit/', admin_views.admin_product_edit, name='admin_product_edit'),
    path('admin-dashboard/products/<int:product_id>/delete/', admin_views.admin_product_delete, name='admin_product_delete'),
    path('admin-dashboard/products/update-stock/', admin_views.admin_product_update_stock, name='admin_product_update_stock'),
    
    path('admin-dashboard/customers/', admin_views.admin_customers_list, name='admin_customers_list'),
    path('admin-dashboard/customer/<int:user_id>/', admin_views.admin_customer_detail, name='admin_customer_detail'),
    path('admin-dashboard/customers/send-email/', admin_views.admin_send_customer_email, name='admin_send_customer_email'),
    path('admin-dashboard/customers/send-bulk-email/', admin_views.admin_send_bulk_email, name='admin_send_bulk_email'),
    
    path('admin-dashboard/reports/', admin_views.admin_reports, name='admin_reports'),
    path('admin-dashboard/export/', admin_views.admin_export_data, name='admin_export_data'),


    path('admin-dashboard/orders/create/', admin_views.admin_create_manual_order, name='admin_create_manual_order'),
    path('admin-dashboard/orders/create-for/<int:customer_id>/', admin_views.admin_create_order_for_customer, name='admin_create_order_for_customer'),
    
    # Calendrier des commandes
    path('admin-dashboard/calendar/', admin_views.admin_orders_calendar, name='admin_orders_calendar'),
    path('admin-dashboard/calendar/<str:date_str>/', admin_views.admin_orders_by_date, name='admin_orders_by_date'),
    
    # Dispatch cuisine
    path('admin-dashboard/kitchen/dispatch/', admin_views.admin_kitchen_dispatch, name='admin_kitchen_dispatch'),
    path('admin-dashboard/kitchen/print/<str:department>/', admin_views.admin_print_department_list, name='admin_print_department'),
    
    # API endpoints
    path('admin-dashboard/api/quick-status/', admin_views.admin_quick_order_status, name='admin_quick_order_status'),
    path('admin-dashboard/api/customer-info/', admin_views.admin_get_customer_info, name='admin_get_customer_info'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
