from django.urls import path, include
from rest_framework.routers import DefaultRouter
from JLTsite import views, admin_views, checklist_views, delivery_views, maitre_hotel_views, kitchen_views
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


    path('admin-dashboard/order/<str:order_number>/checklist/create/', 
         checklist_views.admin_create_checklist, 
         name='admin_create_checklist'),
    
    # Modifier une checklist existante
    path('admin-dashboard/order/<str:order_number>/checklist/edit/', 
         checklist_views.admin_edit_checklist, 
         name='admin_edit_checklist'),
    
    # === DASHBOARD RESPONSABLE CHECKLIST ===
    # Dashboard principal
    path('checklist-dashboard/', 
         checklist_views.checklist_dashboard, 
         name='checklist_dashboard'),
    
    # Vue détaillée d'une checklist (optimisée tablette)
    path('checklist/<int:checklist_id>/', 
         checklist_views.checklist_detail, 
         name='checklist_detail'),
    
    # Compléter une checklist
    path('checklist/<int:checklist_id>/complete/', 
         checklist_views.complete_checklist, 
         name='complete_checklist'),
    
    # === API AJAX ===
    # Valider/dévalider un item
    path('checklist/item/validate/', 
         checklist_views.validate_checklist_item, 
         name='validate_checklist_item'),
    
    # Signaler un problème
    path('checklist/item/report-issue/', 
         checklist_views.report_checklist_issue, 
         name='report_checklist_issue'),
    
    # Marquer une notification comme lue
    path('checklist/notification/<int:notification_id>/read/', 
         checklist_views.mark_notification_read, 
         name='mark_notification_read'),

    # === RESPONSABLE LIVRAISON ===
    # Dashboard principal avec carte
    path('delivery-manager/', 
         delivery_views.delivery_manager_dashboard, 
         name='delivery_manager_dashboard'),
    
    # Créer une livraison depuis une commande
    path('delivery/create/<str:order_number>/', 
         delivery_views.create_delivery_from_order, 
         name='create_delivery_from_order'),
    
    # Créer une récupération
    path('delivery/<int:delivery_id>/create-pickup/', 
         delivery_views.create_pickup_delivery, 
         name='create_pickup_delivery'),
    
    # Gestion des routes
    path('delivery/routes/', 
         delivery_views.manage_delivery_routes, 
         name='manage_delivery_routes'),
    
    # Créer une route
    path('delivery/routes/create/', 
         delivery_views.create_route, 
         name='create_route'),
    
    # Mettre à jour les livraisons d'une route (drag & drop)
    path('delivery/routes/update-deliveries/', 
         delivery_views.update_route_deliveries, 
         name='update_route_deliveries'),
    
    # Optimiser une route
    path('delivery/routes/<int:route_id>/optimize/', 
         delivery_views.optimize_route, 
         name='optimize_route'),
    

     # ========================================
     # URLS DASHBOARD LIVREUR MOBILE
     # ========================================

     # Dashboard principal avec sélection de date
     path('driver/', delivery_views.driver_dashboard, name='driver_dashboard'),

     # Planning du livreur
     path('driver/planning/', delivery_views.driver_planning, name='driver_planning'),

     # Notifications du livreur
     path('driver/notifications/', delivery_views.driver_notifications, name='driver_notifications'),

     # Profil du livreur
     path('driver/profile/', delivery_views.driver_profile, name='driver_profile'),

     # Historique des livraisons
     path('driver/history/', delivery_views.driver_delivery_history, name='driver_delivery_history'),

     # Détail d'une route pour mobile
     path('driver/route/<int:route_id>/', delivery_views.driver_route_detail_mobile, name='driver_route_detail_mobile'),

     # ========================================
     # API ENDPOINTS POUR MOBILE
     # ========================================

     # Réessayer une livraison échouée
     path('delivery/api/<int:delivery_id>/retry/', delivery_views.retry_delivery_api, name='retry_delivery_api'),

     # Marquer une notification comme lue
     path('delivery/notification/<int:notification_id>/read/', delivery_views.mark_notification_read_api, name='mark_notification_read_api'),

     # Statistiques du livreur en temps réel
     path('driver/api/stats/', delivery_views.driver_stats_api, name='driver_stats_api'),
     # Démarrer une route
     path('delivery/route/<int:route_id>/start/', delivery_views.start_route, name='start_route'),

     # Terminer une route  
     path('delivery/route/<int:route_id>/complete/', delivery_views.complete_route, name='complete_route'),

     # Valider une livraison
     path('driver/delivery/<int:delivery_id>/validate/', delivery_views.validate_delivery, name='validate_delivery'),

     path('delivery/bulk-create/', 
          delivery_views.create_bulk_deliveries, 
          name='create_bulk_deliveries'),
     
    # === API ENDPOINTS ===
    # Sauvegarder la signature
    path('delivery/signature/save/', 
         delivery_views.save_delivery_signature, 
         name='save_delivery_signature'),
    
    # Upload photo de livraison
    path('delivery/photo/upload/', 
         delivery_views.upload_delivery_photo, 
         name='upload_delivery_photo'),
    
    # Démarrer une route
    path('delivery/route/<int:route_id>/start/', 
         delivery_views.start_route, 
         name='start_route'),
    
    # Terminer une route
    path('delivery/route/<int:route_id>/complete/', 
         delivery_views.complete_route, 
         name='complete_route'),
    
    # Signaler un problème
    path('delivery/report-issue/', 
         delivery_views.report_delivery_issue, 
         name='report_delivery_issue'),
    
    # Marquer une notification comme lue
    path('delivery/notification/<int:notification_id>/read/', 
         delivery_views.mark_delivery_notification_read, 
         name='mark_delivery_notification_read'),
    
    # Vue planning global des livreurs (pour responsable)
    path('delivery/planning-overview/', 
         delivery_views.driver_planning_overview, 
         name='driver_planning_overview'),
    
    # Détail d'une livraison (pour responsable)
    path('delivery/<int:delivery_id>/', 
         delivery_views.delivery_detail, 
         name='delivery_detail'),
    
    # === RAPPORTS ===
    # Rapport des livraisons
    path('delivery/reports/', 
         delivery_views.delivery_reports, 
         name='delivery_reports'),
    
    # Export des livraisons
    path('delivery/export/', 
         delivery_views.export_deliveries, 
         name='export_deliveries'),

     # === PLANNING DES LIVREURS ===
     # Créer un planning
     path('delivery/planning/create/', 
          delivery_views.create_driver_planning, 
          name='create_driver_planning'),

     # Mettre à jour un planning
     path('delivery/planning/<int:planning_id>/update/', 
          delivery_views.update_driver_planning, 
          name='update_driver_planning'),

     # Supprimer un planning
     path('delivery/planning/<int:planning_id>/delete/', 
          delivery_views.delete_driver_planning, 
          name='delete_driver_planning'),

     # Récupérer un planning (pour édition)
     path('delivery/planning/<int:planning_id>/', 
          delivery_views.get_driver_planning, 
          name='get_driver_planning'),


    # ========================================
    # URLS DASHBOARD MAÎTRE D'HÔTEL MOBILE
    # ========================================

    # Dashboard principal avec sélection de date
    path('maitre-hotel/', maitre_hotel_views.maitre_hotel_dashboard, name='maitre_hotel_dashboard'),
    path('maitre-hotel/reports/', maitre_hotel_views.maitre_hotel_reports, name='maitre_hotel_reports'),

    # Détail d'un événement/contrat
    path('maitre-hotel/event/<int:contract_id>/', maitre_hotel_views.maitre_hotel_event_detail, name='maitre_hotel_event_detail'),

    # Démarrer un événement
    path('maitre-hotel/event/<int:contract_id>/start/', maitre_hotel_views.start_event, name='start_event'),

    # Terminer un événement
    path('maitre-hotel/event/<int:contract_id>/complete/', maitre_hotel_views.complete_event, name='complete_event'),

    # Créer un rapport de fin d'événement
    path('maitre-hotel/event/<int:contract_id>/report/create/', maitre_hotel_views.create_event_report, name='create_event_report'),

    # Planning hebdomadaire
    path('maitre-hotel/planning/', maitre_hotel_views.maitre_hotel_planning, name='maitre_hotel_planning'),

    # Notifications
    path('maitre-hotel/notifications/', maitre_hotel_views.maitre_hotel_notifications, name='maitre_hotel_notifications'),

    # Profil
    path('maitre-hotel/profile/', maitre_hotel_views.maitre_hotel_profile, name='maitre_hotel_profile'),

    # ========================================
    # API ENDPOINTS POUR MOBILE
    # ========================================

    # Upload photo d'événement
    path('maitre-hotel/api/upload-photo/', maitre_hotel_views.upload_event_photo, name='upload_event_photo'),

    # Ajouter événement à la timeline
    path('maitre-hotel/api/add-timeline/', maitre_hotel_views.add_timeline_event, name='add_timeline_event'),

     # ========== GESTION DES ÉVÉNEMENTS ==========
    # Liste des événements pour les ventes
    path('admin-dashboard/events/', admin_views.admin_events_list, name='admin_events_list'),
    path('admin-dashboard/event/<int:contract_id>/', admin_views.admin_event_detail, name='admin_event_detail'),
    path('admin-dashboard/event/<int:contract_id>/remove-staff/<int:assignment_id>/', admin_views.admin_remove_staff_from_event, name='admin_remove_staff_from_event'),
    
    # Créer un événement depuis une commande
    path('admin-dashboard/order/<str:order_number>/create-event/', 
         admin_views.admin_create_event_from_order, 
         name='admin_create_event_from_order'),
        
    
    # ========== API ÉVÉNEMENTS ==========
    # Assignation rapide de maître d'hôtel
    path('admin-dashboard/api/quick-assign-maitre-hotel/', 
         admin_views.admin_quick_assign_maitre_hotel, 
         name='admin_quick_assign_maitre_hotel'),
    
    # Changer le statut d'un événement
    path('admin-dashboard/api/change-event-status/', 
         admin_views.admin_change_event_status, 
         name='admin_change_event_status'),

     
     # ========================================
    # URLS CHEF DE CUISINE (HEAD CHEF)
    # ========================================
    
    # Dashboard principal
    path('head-chef/', kitchen_views.head_chef_dashboard, name='head_chef_dashboard'),
    
    # Gestion des commandes
    path('head-chef/orders/', kitchen_views.head_chef_orders, name='head_chef_orders'),
    path('head-chef/orders/<str:order_number>/', kitchen_views.head_chef_order_detail, name='head_chef_order_detail'),
    
    # Gestion des commandes de produits
    path('head-chef/product-orders/', kitchen_views.head_chef_product_orders, name='head_chef_product_orders'),
    path('head-chef/product-orders/<int:order_id>/', kitchen_views.head_chef_product_order_detail, name='head_chef_product_order_detail'),
    path('head-chef/product-orders/<int:order_id>/approve/', kitchen_views.approve_product_order, name='approve_product_order'),
    path('head-chef/product-orders/<int:order_id>/reject/', kitchen_views.reject_product_order, name='reject_product_order'),
    
    # Dispatch et impression
    path('head-chef/dispatch/', kitchen_views.head_chef_dispatch, name='head_chef_dispatch'),
    path('head-chef/dispatch/<str:date_str>/', kitchen_views.head_chef_dispatch_by_date, name='head_chef_dispatch_by_date'),
    
    # Inventaire et stock
    path('head-chef/inventory/', kitchen_views.head_chef_inventory, name='head_chef_inventory'),
    path('head-chef/inventory/products/', kitchen_views.head_chef_manage_products, name='head_chef_manage_products'),
    path('head-chef/inventory/products/add/', kitchen_views.head_chef_add_product, name='head_chef_add_product'),
    path('head-chef/inventory/products/<int:product_id>/edit/', kitchen_views.head_chef_edit_product, name='head_chef_edit_product'),
    path('head-chef/inventory/suppliers/', kitchen_views.head_chef_manage_suppliers, name='head_chef_manage_suppliers'),
    
    # Rapports
    path('head-chef/reports/', kitchen_views.head_chef_reports, name='head_chef_reports'),
    path('head-chef/reports/production/', kitchen_views.head_chef_production_reports, name='head_chef_production_reports'),
    path('head-chef/reports/export/', kitchen_views.head_chef_export_reports, name='head_chef_export_reports'),
    
    # API endpoints pour le chef de cuisine
    path('head-chef/api/production-stats/', kitchen_views.head_chef_production_stats_api, name='head_chef_production_stats_api'),
    path('head-chef/api/department-progress/', kitchen_views.head_chef_department_progress_api, name='head_chef_department_progress_api'),
    
    # URLs pour la création de production
    path('head-chef/orders/<str:order_number>/get-items/', 
         kitchen_views.get_order_items, 
         name='get_order_items'),
    
    path('head-chef/orders/<str:order_number>/create-production/', 
         kitchen_views.create_production_from_order, 
         name='create_production_from_order'),
    
    path('head-chef/orders/<str:order_number>/check-production/', 
         kitchen_views.check_production_exists, 
         name='check_production_exists'),
    
    path('head-chef/bulk-create-productions/', 
         kitchen_views.bulk_create_productions, 
         name='bulk_create_productions'),
    # ========================================
    # URLS CHEF DE DÉPARTEMENT
    # ========================================
    
    # Dashboard principal
    path('department-chef/', kitchen_views.department_chef_dashboard, name='department_chef_dashboard'),
    
    # Gestion des commandes/production
    path('department-chef/orders/', kitchen_views.department_chef_orders, name='department_chef_orders'),
    #path('department-chef/orders/<str:date_str>/', kitchen_views.department_chef_orders_by_date, name='department_chef_orders_by_date'),
    #path('department-chef/production/<int:production_id>/', kitchen_views.department_chef_production_detail, name='department_chef_production_detail'),
    
    # Commandes de produits
    path('department-chef/product-orders/', kitchen_views.department_product_orders, name='department_product_orders'),
    path('department-chef/product-orders/create/', kitchen_views.create_product_order, name='create_product_order'),
    #path('department-chef/product-orders/<int:order_id>/', kitchen_views.department_product_order_detail, name='department_product_order_detail'),
    #path('department-chef/product-orders/<int:order_id>/edit/', kitchen_views.edit_product_order, name='edit_product_order'),
    #path('department-chef/product-orders/<int:order_id>/cancel/', kitchen_views.cancel_product_order, name='cancel_product_order'),
    
    # Gestion d'équipe
    #path('department-chef/team/', kitchen_views.department_chef_team, name='department_chef_team'),
    #path('department-chef/team/assign/', kitchen_views.assign_cook_to_production, name='assign_cook_to_production'),
    #path('department-chef/team/schedule/', kitchen_views.manage_cook_schedule, name='manage_cook_schedule'),
    
    # Inventaire département
    #path('department-chef/inventory/', kitchen_views.department_chef_inventory, name='department_chef_inventory'),
    #path('department-chef/inventory/request/', kitchen_views.request_stock_transfer, name='request_stock_transfer'),
    
    # API endpoints pour chef de département
    #path('department-chef/api/production-items/', kitchen_views.department_production_items_api, name='department_production_items_api'),
    #path('department-chef/api/assign-cook/', kitchen_views.assign_cook_api, name='assign_cook_api'),
    
    # ========================================
    # URLS CUISINIER
    # ========================================
    
    # Dashboard principal (optimisé tablette)
    path('cook/', kitchen_views.cook_dashboard, name='cook_dashboard'),
    #path('cook/date/<str:date_str>/', kitchen_views.cook_dashboard_by_date, name='cook_dashboard_by_date'),
    
    # Actions sur les items de production
    path('kitchen/cook/start-item/<int:item_id>/', kitchen_views.start_production_item, name='start_production_item'),
    path('kitchen/cook/complete-item/<int:item_id>/', kitchen_views.complete_production_item, name='complete_production_item'),
    path('kitchen/cook/report-issue/<int:item_id>/', kitchen_views.report_production_issue, name='report_production_issue'),
    #path('cook/update-item/<int:item_id>/', kitchen_views.update_production_item, name='update_production_item'),
    
    # Profil cuisinier
    #path('cook/profile/', kitchen_views.cook_profile, name='cook_profile'),
    #path('cook/profile/edit/', kitchen_views.edit_cook_profile, name='edit_cook_profile'),
    #path('cook/stats/', kitchen_views.cook_statistics, name='cook_statistics'),
    
    # Historique de production
    #path('cook/history/', kitchen_views.cook_production_history, name='cook_production_history'),
    #path('cook/history/<str:date_str>/', kitchen_views.cook_production_history_by_date, name='cook_production_history_by_date'),
    
    # API endpoints pour cuisinier
    #path('cook/api/my-progress/', kitchen_views.cook_progress_api, name='cook_progress_api'),
    #path('cook/api/department-status/', kitchen_views.cook_department_status_api, name='cook_department_status_api'),
    
    # ========================================
    # URLS COMMUNES
    # ========================================
    
    # Notifications
    path('notifications/', kitchen_views.kitchen_notifications, name='kitchen_notifications'),
    path('notifications/<int:notification_id>/read/', kitchen_views.mark_notification_read, name='mark_kitchen_notification_read'),
    path('notifications/mark-all-read/', kitchen_views.mark_all_notifications_read, name='mark_all_kitchen_notifications_read'),
    
    # Impression et exports
    path('print/department/<str:department>/', kitchen_views.print_department_dispatch, name='print_department_dispatch'),
    #path('print/department/<str:department>/<str:date_str>/', kitchen_views.print_department_dispatch_by_date, name='print_department_dispatch_by_date'),
    #path('export/production/<str:date_str>/', kitchen_views.export_production_data, name='export_production_data'),
    
    # Recherche et filtres
    #path('search/products/', kitchen_views.search_kitchen_products, name='search_kitchen_products'),
    #path('search/orders/', kitchen_views.search_kitchen_orders, name='search_kitchen_orders'),
    
    # QR Code et scanning (pour tablettes)
    #path('scan/item/<int:item_id>/', kitchen_views.scan_production_item, name='scan_production_item'),
    #path('generate-qr/<int:item_id>/', kitchen_views.generate_item_qr_code, name='generate_item_qr_code'),
    
    # ========================================
    # API ENDPOINTS GÉNÉRAUX
    # ========================================
    
    # Status updates en temps réel
    #path('api/production-status/', kitchen_views.production_status_api, name='production_status_api'),
    #path('api/department-stats/', kitchen_views.department_stats_api, name='department_stats_api'),
    #path('api/kitchen-alerts/', kitchen_views.kitchen_alerts_api, name='kitchen_alerts_api'),
    
    # Gestion automatique des productions
    #path('api/auto-create-productions/', kitchen_views.auto_create_daily_productions, name='auto_create_daily_productions'),
    #path('api/update-production-progress/', kitchen_views.update_production_progress_api, name='update_production_progress_api'),
    
    # Contrôle qualité
    #path('quality/check/<int:item_id>/', kitchen_views.quality_check_item, name='quality_check_item'),
    #path('quality/approve/<int:item_id>/', kitchen_views.approve_quality_check, name='approve_quality_check'),
    #path('quality/reports/', kitchen_views.quality_reports, name='quality_reports'),
    
    # ========================================
    # URLS D'ADMINISTRATION AVANCÉE
    # ========================================
    
    # Configuration système
    #path('admin/kitchen-settings/', kitchen_views.kitchen_settings, name='kitchen_settings'),
    #path('admin/departments/', kitchen_views.manage_departments, name='manage_departments'),
    #path('admin/roles/', kitchen_views.manage_kitchen_roles, name='manage_kitchen_roles'),
    
    # Logs et audit
    #path('admin/logs/', kitchen_views.kitchen_logs, name='kitchen_logs'),
    #path('admin/audit/', kitchen_views.kitchen_audit_trail, name='kitchen_audit_trail'),
    
    # Maintenance
    #path('admin/maintenance/', kitchen_views.kitchen_maintenance, name='kitchen_maintenance'),
    #path('admin/backup/', kitchen_views.backup_kitchen_data, name='backup_kitchen_data'),
    #path('admin/restore/', kitchen_views.restore_kitchen_data, name='restore_kitchen_data'),
    
    # ========================================
    # URLS POUR INTÉGRATIONS EXTERNES
    # ========================================
    
    # Webhooks fournisseurs
    #path('webhooks/supplier/<int:supplier_id>/order/', kitchen_views.supplier_order_webhook, name='supplier_order_webhook'),
    #path('webhooks/supplier/<int:supplier_id>/delivery/', kitchen_views.supplier_delivery_webhook, name='supplier_delivery_webhook'),
    
    # API pour applications mobiles
    #path('mobile/api/login/', kitchen_views.mobile_login_api, name='mobile_login_api'),
    #path('mobile/api/productions/', kitchen_views.mobile_productions_api, name='mobile_productions_api'),
    #path('mobile/api/start-item/', kitchen_views.mobile_start_item_api, name='mobile_start_item_api'),
    #path('mobile/api/complete-item/', kitchen_views.mobile_complete_item_api, name='mobile_complete_item_api'),
    
    # ========================================
    # REDIRECTIONS ET RACCOURCIS
    # ========================================
    
    # Redirection basée sur le rôle
    #path('', kitchen_views.kitchen_role_redirect, name='kitchen_role_redirect'),
    
    # Raccourcis rapides
    #path('today/', kitchen_views.kitchen_today_summary, name='kitchen_today_summary'),
    # path('tomorrow/', kitchen_views.kitchen_tomorrow_preview, name='kitchen_tomorrow_preview'),
    # path('week/', kitchen_views.kitchen_week_overview, name='kitchen_week_overview'),
    
    # Dashboard unifié (pour les admins)
    # path('overview/', kitchen_views.kitchen_global_overview, name='kitchen_global_overview'),

    # Commandes de produits - CRUD
    path('kitchen/product-orders/new/', kitchen_views.create_product_order_view, name='create_product_order'),
    path('product-orders/<int:order_id>/', kitchen_views.view_product_order, name='view_product_order'),
    path('product-orders/<int:order_id>/edit/', kitchen_views.edit_product_order_view, name='edit_product_order'),
    
    # Actions AJAX pour commandes produits
    path('product-orders/<int:order_id>/submit/', kitchen_views.submit_product_order, name='submit_product_order'),
    path('product-orders/<int:order_id>/cancel/', kitchen_views.cancel_product_order, name='cancel_product_order'),
    path('product-orders/<int:order_id>/mark-ordered/', kitchen_views.mark_product_order_ordered, name='mark_product_order_ordered'),
    path('product-orders/<int:order_id>/mark-received/', kitchen_views.mark_product_order_received, name='mark_product_order_received'),

    # Dans votre urls.py, ajouter/corriger ces URLs pour les actions de production:

    
    
    # AJOUTER AUSSI CES ALIASES POUR LES CHEFS DE DÉPARTEMENT
    path('department-chef/start-item/<int:item_id>/', kitchen_views.start_production_item, name='dept_start_production_item'),
    path('department-chef/complete-item/<int:item_id>/', kitchen_views.complete_production_item, name='dept_complete_production_item'),
    path('department-chef/report-issue/<int:item_id>/', kitchen_views.report_production_issue, name='dept_report_production_issue'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
