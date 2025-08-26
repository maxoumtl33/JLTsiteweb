# delivery_views.py - Système complet de gestion des livraisons

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, Sum, Prefetch, F
from django.utils import timezone
from django.contrib import messages
from django.core.files.base import ContentFile
from datetime import datetime, timedelta, date
from decimal import Decimal
import json
import base64
import io
from PIL import Image
from django.conf import settings

from .models import (
    Order, Delivery, DeliveryRoute, RouteDelivery, DeliveryPhoto,
    DriverPlanning, DeliveryNotification, DeliverySettings, User
)

# ========================================
# DECORATEURS
# ========================================

def delivery_manager_required(user):
    """Vérifier si l'utilisateur est responsable livraison ou admin"""
    return user.is_authenticated and user.role in ['admin', 'delivery_manager']

def delivery_driver_required(user):
    """Vérifier si l'utilisateur est livreur"""
    return user.is_authenticated and user.role in ['admin', 'delivery_manager', 'delivery_driver']

# ========================================
# VUES RESPONSABLE LIVRAISON
# ========================================


@login_required
@user_passes_test(delivery_manager_required)
def delivery_manager_dashboard(request):
    """Dashboard principal du responsable livraison avec carte et commandes confirmées"""
    
    # Date sélectionnée (par défaut aujourd'hui)
    selected_date = request.GET.get('date')
    if selected_date:
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    else:
        selected_date = timezone.now().date()

    key_google = settings.GOOGLE_API_KEY
    
    # IMPORTANT : Récupérer les commandes confirmées POUR LA DATE SÉLECTIONNÉE
    confirmed_orders = Order.objects.filter(
        status='confirmed',
        delivery_date=selected_date  # Changé : exactement à cette date
    ).exclude(
        # Exclure les commandes qui ont déjà une livraison de type 'delivery'
        id__in=Delivery.objects.filter(
            delivery_type='delivery'
        ).values_list('order_id', flat=True)
    ).select_related(
        'checklist'  # Inclure la checklist si elle existe
    ).prefetch_related(
        'items'
    ).order_by('delivery_time')  # Trier par heure
    
    # Compter les commandes confirmées sans livraison pour cette date
    confirmed_orders_count = confirmed_orders.count()
    
    # Récupérer toutes les livraisons du jour sélectionné
    deliveries = Delivery.objects.filter(
        scheduled_date=selected_date
    ).select_related('order').prefetch_related('route_assignments__route')
    
    # Statistiques pour la date sélectionnée
    stats = {
        'total': deliveries.count(),
        'pending': deliveries.filter(status='pending').count(),
        'assigned': deliveries.filter(status='assigned').count(),
        'in_transit': deliveries.filter(status='in_transit').count(),
        'delivered': deliveries.filter(status='delivered').count(),
        'failed': deliveries.filter(status='failed').count(),
    }
    
    # Routes du jour sélectionné
    routes = DeliveryRoute.objects.filter(
        date=selected_date
    ).select_related('driver').prefetch_related(
        Prefetch('route_deliveries', 
                queryset=RouteDelivery.objects.select_related('delivery').order_by('position'))
    )
    
    # Livraisons non assignées pour cette date
    unassigned_deliveries = Delivery.objects.filter(
        scheduled_date=selected_date,
        status='pending'
    ).exclude(
        id__in=RouteDelivery.objects.filter(
            route__date=selected_date
        ).values_list('delivery_id', flat=True)
    ).order_by('scheduled_time_start')
    
    # CORRECTION : Livreurs disponibles avec le bon related_name
    available_drivers = User.objects.filter(
        role='delivery_driver'
    ).prefetch_related(
        Prefetch(
            'planning',  # ⚠️ CHANGÉ : Utilisez le related_name défini dans DriverPlanning
            queryset=DriverPlanning.objects.filter(date=selected_date),
            to_attr='planning_for_date'
        ),
        Prefetch(
            'delivery_routes',
            queryset=DeliveryRoute.objects.filter(date=selected_date),
            to_attr='routes_for_date'
        )
    )

    # Calculer les statistiques de planning
    planning_stats = get_planning_stats(selected_date, available_drivers)

    
    # Préparer les données pour la carte Google Maps
    map_deliveries = []
    for delivery in deliveries:
        if delivery.latitude and delivery.longitude:
            map_deliveries.append({
                'id': delivery.id,
                'number': delivery.delivery_number,
                'customer': delivery.customer_name,
                'address': delivery.delivery_address,
                'lat': float(delivery.latitude),
                'lng': float(delivery.longitude),
                'status': delivery.status,
                'priority': delivery.priority,
                'type': delivery.delivery_type,
                'time': delivery.scheduled_time_start.strftime('%H:%M') if delivery.scheduled_time_start else '',
                'assigned': bool(delivery.route_assignments.exists()),
            })
    
    # Notifications urgentes
    urgent_notifications = DeliveryNotification.objects.filter(
        recipient=request.user,
        is_read=False,
        is_urgent=True
    ).order_by('-created_at')[:5]
    
    # Paramètres Google Maps
    try:
        settings_obj = DeliverySettings.objects.first()
        google_maps_key = settings_obj.google_maps_api_key if settings_obj else ''
    except:
        google_maps_key = ''
    
    context = {
        'selected_date': selected_date,
        'confirmed_orders': confirmed_orders,
        'confirmed_orders_count': confirmed_orders_count,
        'deliveries': deliveries,
        'unassigned_deliveries': unassigned_deliveries,
        'stats': stats,
        'routes': routes,
        'key_google': key_google,
        'available_drivers': available_drivers,
        'planning_stats': planning_stats,
        'map_deliveries': json.dumps(map_deliveries),
        'urgent_notifications': urgent_notifications,
        'google_maps_key': google_maps_key,
    }
    
    return render(request, 'JLTsite/delivery_manager_dashboard.html', context)

# Ajoutez aussi cette fonction pour gérer la création en masse de livraisons
@login_required
@user_passes_test(delivery_manager_required)
@require_POST
def create_bulk_deliveries(request):
    """Créer des livraisons en masse pour toutes les commandes confirmées d'une date"""
    
    date = request.POST.get('date')
    if date:
        selected_date = datetime.strptime(date, '%Y-%m-%d').date()
    else:
        selected_date = timezone.now().date()
    
    # Récupérer toutes les commandes confirmées sans livraison pour cette date
    orders = Order.objects.filter(
        status='confirmed',
        delivery_date=selected_date
    ).exclude(
        id__in=Delivery.objects.filter(
            delivery_type='delivery'
        ).values_list('order_id', flat=True)
    )
    
    created_count = 0
    
    for order in orders:
        try:
            # Créer la livraison
            delivery = Delivery.objects.create(
                order=order,
                delivery_type='delivery',
                customer_name=f"{order.first_name} {order.last_name}",
                customer_phone=order.phone,
                customer_email=order.email,
                company=order.company or '',
                delivery_address=order.delivery_address,
                delivery_postal_code=order.delivery_postal_code,
                delivery_city=order.delivery_city,
                scheduled_date=order.delivery_date,
                scheduled_time_start=order.delivery_time,
                scheduled_time_end=calculate_end_time(order.delivery_time),
                delivery_instructions=order.delivery_notes,
                items_description=get_order_items_description(order),
                total_packages=1,
                priority='normal',
                has_checklist=hasattr(order, 'checklist'),
                checklist_completed=order.checklist.status == 'completed' if hasattr(order, 'checklist') else False,
                created_by=request.user
            )
            
            # Géocoder l'adresse
            geocode_delivery_address(delivery)
            
            created_count += 1
            
        except Exception as e:
            print(f"Erreur création livraison pour commande {order.order_number}: {str(e)}")
            continue
    
    messages.success(request, f'{created_count} livraison(s) créée(s) avec succès!')
    return redirect('delivery_manager_dashboard')


def calculate_end_time(start_time):
    """Calcule l'heure de fin estimée (30 minutes après le début)"""
    from datetime import datetime, timedelta
    
    # Convertir l'heure en datetime pour le calcul
    dummy_date = datetime(2000, 1, 1)
    start_datetime = datetime.combine(dummy_date, start_time)
    end_datetime = start_datetime + timedelta(minutes=30)
    
    return end_datetime.time()


@login_required
@user_passes_test(delivery_manager_required)
def create_delivery_from_order(request, order_number):
    """Créer une livraison à partir d'une commande confirmée"""
    
    order = get_object_or_404(Order, order_number=order_number, status='confirmed')
    
    # Vérifier si une livraison existe déjà
    existing_delivery = Delivery.objects.filter(order=order, delivery_type='delivery').first()
    if existing_delivery:
        messages.warning(request, 'Une livraison existe déjà pour cette commande.')
        return redirect('delivery_detail', delivery_id=existing_delivery.id)
    
    if request.method == 'POST':
        # Créer la livraison
        delivery = Delivery.objects.create(
            order=order,
            delivery_type='delivery',
            customer_name=f"{order.first_name} {order.last_name}",
            customer_phone=order.phone,
            customer_email=order.email,
            company=order.company,
            delivery_address=order.delivery_address,
            delivery_postal_code=order.delivery_postal_code,
            delivery_city=order.delivery_city,
            scheduled_date=request.POST.get('scheduled_date', order.delivery_date),
            scheduled_time_start=request.POST.get('scheduled_time_start', order.delivery_time),
            scheduled_time_end=request.POST.get('scheduled_time_end', order.delivery_time),
            delivery_instructions=order.delivery_notes,
            items_description=get_order_items_description(order),
            total_packages=int(request.POST.get('total_packages', 1)),
            priority=request.POST.get('priority', 'normal'),
            has_checklist=hasattr(order, 'checklist'),
            checklist_completed=order.checklist.status == 'completed' if hasattr(order, 'checklist') else False,
            created_by=request.user
        )
        
        # Géocoder l'adresse si possible
        geocode_delivery_address(delivery)
        
        messages.success(request, f'Livraison {delivery.delivery_number} créée avec succès!')
        
        # Option pour créer une récupération
        if request.POST.get('create_pickup') == 'on':
            return redirect('create_pickup_delivery', delivery_id=delivery.id)
        
        return redirect('delivery_detail', delivery_id=delivery.id)
    
    context = {
        'order': order,
        'has_checklist': hasattr(order, 'checklist'),
        'checklist_status': order.checklist.get_status_display() if hasattr(order, 'checklist') else None,
    }
    
    return render(request, 'JLTsite/create_delivery.html', context)

@login_required
@user_passes_test(delivery_manager_required)
def create_pickup_delivery(request, delivery_id):
    """Créer une récupération basée sur une livraison"""
    
    parent_delivery = get_object_or_404(Delivery, id=delivery_id)
    
    if request.method == 'POST':
        pickup = Delivery.objects.create(
            order=parent_delivery.order,
            parent_delivery=parent_delivery,
            delivery_type='pickup',
            customer_name=parent_delivery.customer_name,
            customer_phone=parent_delivery.customer_phone,
            customer_email=parent_delivery.customer_email,
            company=parent_delivery.company,
            delivery_address=parent_delivery.delivery_address,
            delivery_postal_code=parent_delivery.delivery_postal_code,
            delivery_city=parent_delivery.delivery_city,
            latitude=parent_delivery.latitude,
            longitude=parent_delivery.longitude,
            scheduled_date=request.POST.get('scheduled_date'),
            scheduled_time_start=request.POST.get('scheduled_time_start'),
            scheduled_time_end=request.POST.get('scheduled_time_end'),
            items_description=request.POST.get('items_description', 'Récupération de matériel'),
            total_packages=int(request.POST.get('total_packages', 1)),
            priority=request.POST.get('priority', 'normal'),
            created_by=request.user
        )
        
        # Copier les photos de livraison pour référence
        for photo in parent_delivery.photos.filter(photo_type='delivery'):
            pickup.photos.create(
                photo_type='pickup',
                photo=photo.photo,
                caption=f"Référence de livraison - {photo.caption}",
                taken_by=request.user
            )
        
        messages.success(request, f'Récupération {pickup.delivery_number} créée avec succès!')
        return redirect('delivery_detail', delivery_id=pickup.id)
    
    context = {
        'parent_delivery': parent_delivery,
        'suggested_date': parent_delivery.scheduled_date + timedelta(days=1),
    }
    
    return render(request, 'JLTsite/create_pickup.html', context)

@login_required
@user_passes_test(delivery_manager_required)
def manage_delivery_routes(request):
    """Interface de gestion des routes avec drag & drop"""
    
    selected_date = request.GET.get('date', timezone.now().date())
    if isinstance(selected_date, str):
        selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    
    # Livraisons non assignées
    unassigned_deliveries = Delivery.objects.filter(
        scheduled_date=selected_date,
        status='pending'
    ).exclude(
        route_assignments__route__date=selected_date
    )
    
    # Routes existantes
    routes = DeliveryRoute.objects.filter(
        date=selected_date
    ).prefetch_related(
        Prefetch('route_deliveries', 
                queryset=RouteDelivery.objects.select_related('delivery').order_by('position'))
    ).select_related('driver')
    
    # CORRECTION : Livreurs disponibles sans filtre is_available
    available_drivers = User.objects.filter(
        role='delivery_driver'
    )
    
    # Planning des livreurs (optionnel, avec gestion d'erreur)
    try:
        driver_plannings = DriverPlanning.objects.filter(
            date=selected_date,
            is_available=True
        ).select_related('driver')
    except:
        driver_plannings = []
    
    context = {
        'selected_date': selected_date,
        'unassigned_deliveries': unassigned_deliveries,
        'routes': routes,
        'available_drivers': available_drivers,
        'driver_plannings': driver_plannings,
    }
    
    return render(request, 'JLTsite/manage_routes.html', context)
@login_required
@user_passes_test(delivery_manager_required)
@require_POST
def create_route(request):
    """Créer une nouvelle route"""
    
    data = json.loads(request.body)
    
    # CORRECTION : Convertir la date string en objet date
    date_str = data['date']
    if isinstance(date_str, str):
        route_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        route_date = date_str
    
    # Créer la route avec la date convertie
    route = DeliveryRoute.objects.create(
        name=data.get('name', f"Route du {route_date}"),
        driver_id=data['driver_id'],
        date=route_date,  # Utiliser l'objet date au lieu de la string
        start_time=data['start_time'],
        vehicle=data.get('vehicle', ''),
        created_by=request.user
    )
    
    # Ajouter les livraisons si fournies
    delivery_ids = data.get('delivery_ids', [])
    for idx, delivery_id in enumerate(delivery_ids):
        delivery = Delivery.objects.get(id=delivery_id)
        RouteDelivery.objects.create(
            route=route,
            delivery=delivery,
            position=idx
        )
        delivery.status = 'assigned'
        delivery.save()
    
    # Calculer les estimations
    calculate_route_estimates(route)
    
    # Notifier le livreur
    DeliveryNotification.objects.create(
        type='route_assigned',
        recipient_type='driver',
        recipient=route.driver,
        route=route,
        title='Nouvelle route assignée',
        message=f'Une nouvelle route vous a été assignée pour le {route.date}',
        is_urgent=True
    )
    
    return JsonResponse({
        'success': True,
        'route_id': route.id,
        'route_number': route.route_number
    })
@login_required
@user_passes_test(delivery_manager_required)
@require_POST
def update_route_deliveries(request):
    """Mettre à jour l'ordre des livraisons dans une route (drag & drop)"""
    
    data = json.loads(request.body)
    route_id = data['route_id']
    delivery_positions = data['positions']  # Liste de {delivery_id, position}
    
    route = get_object_or_404(DeliveryRoute, id=route_id)
    
    for item in delivery_positions:
        RouteDelivery.objects.update_or_create(
            route=route,
            delivery_id=item['delivery_id'],
            defaults={'position': item['position']}
        )
    
    # Recalculer les estimations
    calculate_route_estimates(route)
    
    return JsonResponse({'success': True})

@login_required
@user_passes_test(delivery_manager_required)
@require_POST
def optimize_route(request, route_id):
    """Optimiser automatiquement une route"""
    
    route = get_object_or_404(DeliveryRoute, id=route_id)
    
    # Ici, vous pourriez intégrer l'API Google Maps Directions
    # ou un algorithme d'optimisation comme le TSP
    
    # Pour l'instant, on fait une optimisation simple par zone
    route_deliveries = route.route_deliveries.all().select_related('delivery')
    
    # Trier par code postal puis par adresse
    sorted_deliveries = sorted(
        route_deliveries,
        key=lambda x: (x.delivery.delivery_postal_code, x.delivery.delivery_address)
    )
    
    # Mettre à jour les positions
    for idx, rd in enumerate(sorted_deliveries):
        rd.position = idx
        rd.save()
    
    route.is_optimized = True
    route.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Route optimisée avec succès'
    })

# ========================================
# VUES LIVREUR
# ========================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, Sum, Prefetch, F
from django.utils import timezone
from django.contrib import messages
from datetime import datetime, timedelta, date
from decimal import Decimal
import json

from .models import (
    Order, Delivery, DeliveryRoute, RouteDelivery, DeliveryPhoto,
    DriverPlanning, DeliveryNotification, DeliverySettings, User
)

# ========================================
# VUES DASHBOARD LIVREUR MOBILE
# ========================================

@login_required
@user_passes_test(delivery_driver_required)
def driver_dashboard(request):
    """Dashboard principal du livreur - Version mobile optimisée"""
    
    driver = request.user
    
    # Date sélectionnée (par défaut aujourd'hui)
    selected_date = request.GET.get('date')
    if selected_date:
        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()
    
    # Route du jour sélectionné
    current_route = DeliveryRoute.objects.filter(
        driver=driver,
        date=selected_date
    ).prefetch_related(
        'route_deliveries__delivery'
    ).first()
    
    # Livraisons du jour sélectionné
    deliveries = []
    if current_route:
        route_deliveries = current_route.route_deliveries.all().order_by('position')
        deliveries = [rd.delivery for rd in route_deliveries]
        
        # Mettre à jour les stats de la route
        current_route.total_deliveries = len(deliveries)
        current_route.completed_deliveries = sum(1 for d in deliveries if d.status == 'delivered')
    
    # Statistiques du jour
    stats = {
        'total': len(deliveries),
        'completed': sum(1 for d in deliveries if d.status == 'delivered'),
        'pending': sum(1 for d in deliveries if d.status in ['assigned', 'in_transit']),
        'failed': sum(1 for d in deliveries if d.status == 'failed'),
    }
    
    # Notifications non lues
    notifications_count = DeliveryNotification.objects.filter(
        recipient=driver,
        is_read=False
    ).count()
    
    context = {
        'driver': driver,
        'selected_date': selected_date,
        'current_route': current_route,
        'deliveries': deliveries,
        'stats': stats,
        'notifications_count': notifications_count,
        'today': timezone.now().date(),
    }
    
    return render(request, 'JLTsite/driver_dashboard_mobile.html', context)



@login_required
@user_passes_test(delivery_driver_required)
def validate_delivery(request, delivery_id):
    """Interface de validation d'une livraison"""
    
    delivery = get_object_or_404(Delivery, id=delivery_id)
    
    # Vérifier que le livreur a accès à cette livraison
    route_delivery = RouteDelivery.objects.filter(
        delivery=delivery,
        route__driver=request.user
    ).first()
    
    if not route_delivery and request.user.role != 'admin':
        messages.error(request, 'Vous n\'avez pas accès à cette livraison.')
        return redirect('driver_dashboard')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'validate':
            # Enregistrer la photo de livraison
            if 'delivery_photo' in request.FILES:
                photo = DeliveryPhoto.objects.create(
                    delivery=delivery,
                    photo_type='delivery',
                    photo=request.FILES['delivery_photo'],
                    caption=request.POST.get('photo_caption', ''),
                    taken_by=request.user
                )
                
                # Géolocalisation si disponible
                if request.POST.get('latitude'):
                    photo.latitude = request.POST.get('latitude')
                    photo.longitude = request.POST.get('longitude')
                    photo.save()
            
            # Enregistrer la signature
            if request.POST.get('signature'):
                delivery.signature = request.POST.get('signature')
            
            # Notes de livraison
            delivery.delivery_notes = request.POST.get('delivery_notes', '')
            
            # Marquer comme livrée
            delivery.status = 'delivered'
            delivery.delivered_at = timezone.now()
            delivery.delivered_by = request.user
            delivery.save()
            
            # Mettre à jour la commande originale
            delivery.order.status = 'delivered'
            delivery.order.delivered_at = timezone.now()
            delivery.order.save()
            
            # Mettre à jour la route
            if route_delivery:
                route_delivery.is_completed = True
                route_delivery.completed_at = timezone.now()
                route_delivery.actual_departure = timezone.now().time()
                route_delivery.save()
                
                route_delivery.route.update_stats()
            
            messages.success(request, 'Livraison validée avec succès!')
            
            # Passer à la prochaine livraison
            if route_delivery:
                next_delivery = RouteDelivery.objects.filter(
                    route=route_delivery.route,
                    position__gt=route_delivery.position,
                    is_completed=False
                ).first()
                
                if next_delivery:
                    return redirect('validate_delivery', delivery_id=next_delivery.delivery.id)
            
            return redirect('driver_dashboard')
        
        elif action == 'report_issue':
            # Signaler un problème
            delivery.status = 'failed'
            delivery.delivery_notes = request.POST.get('issue_description', '')
            delivery.save()
            
            # Créer une notification pour le responsable
            DeliveryNotification.objects.create(
                type='issue',
                recipient_type='manager',
                recipient=User.objects.filter(role='delivery_manager').first(),
                delivery=delivery,
                title='Problème de livraison',
                message=f'Problème signalé pour {delivery.delivery_number}: {delivery.delivery_notes}',
                is_urgent=True
            )
            
            messages.warning(request, 'Problème signalé.')
            return redirect('driver_dashboard')
    
    # Photos de référence pour les récupérations
    reference_photos = []
    if delivery.delivery_type == 'pickup' and delivery.parent_delivery:
        reference_photos = delivery.parent_delivery.photos.filter(photo_type='delivery')
    
    context = {
        'delivery': delivery,
        'route_delivery': route_delivery,
        'reference_photos': reference_photos,
        'has_checklist': delivery.has_checklist,
        'checklist_completed': delivery.checklist_completed,
    }
    
    return render(request, 'JLTsite/validate_delivery.html', context)

@login_required
@user_passes_test(delivery_driver_required)
def driver_planning(request):
    """Planning du livreur - Vue mobile"""
    
    driver = request.user
    
    # Mois sélectionné
    month = int(request.GET.get('month', timezone.now().month))
    year = int(request.GET.get('year', timezone.now().year))
    
    # Dates importantes
    today = timezone.now().date()
    first_day = date(year, month, 1)
    
    # Calculer les dates de début et fin pour le mois
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    
    # Planning du mois
    monthly_planning = DriverPlanning.objects.filter(
        driver=driver,
        date__range=[first_day, last_day]
    ).order_by('date')
    
    # Routes du mois
    monthly_routes = DeliveryRoute.objects.filter(
        driver=driver,
        date__range=[first_day, last_day]
    ).select_related().prefetch_related('route_deliveries')
    
    # Construire le calendrier
    import calendar
    cal = calendar.monthcalendar(year, month)
    
    # Créer un dictionnaire pour accès rapide
    planning_by_date = {p.date: p for p in monthly_planning}
    routes_by_date = {r.date: r for r in monthly_routes}
    
    # Données du calendrier
    calendar_data = []
    for week in cal:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
            else:
                current_date = date(year, month, day)
                planning = planning_by_date.get(current_date)
                route = routes_by_date.get(current_date)
                
                day_data = {
                    'day': day,
                    'date': current_date,
                    'is_today': current_date == today,
                    'is_past': current_date < today,
                    'planning': planning,
                    'route': route,
                    'deliveries_count': route.route_deliveries.count() if route else 0,
                    'status': 'available' if planning and planning.is_available else 'unavailable' if planning else 'no-planning'
                }
                week_data.append(day_data)
        calendar_data.append(week_data)
    
    # Navigation mois précédent/suivant
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    context = {
        'driver': driver,
        'calendar_data': calendar_data,
        'current_month': month,
        'current_year': year,
        'month_name': calendar.month_name[month],
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'today': today,
    }
    
    return render(request, 'JLTsite/driver_planning_mobile.html', context)

# ========================================
# FONCTIONS UTILITAIRES
# ========================================

def get_order_items_description(order):
    """Génère une description des items de la commande"""
    items = order.items.all()
    description = []
    for item in items:
        description.append(f"{item.quantity}x {item.product_name}")
    return ', '.join(description)

import requests
from decimal import Decimal
from django.conf import settings

def geocode_delivery_address(delivery):
    """Géocode l'adresse de livraison avec l'API Google Maps"""
    
    # Construire l'adresse complète
    full_address = f"{delivery.delivery_address}, {delivery.delivery_postal_code} {delivery.delivery_city}, Canada"
    
    # Paramètres pour l'API Google Maps Geocoding
    params = {
        'address': full_address,
        'key': settings.GOOGLE_API_KEY,  # Votre clé API
        'region': 'ca',  # Bias vers le Canada
        'components': 'country:CA'
    }
    
    try:
        # Appel à l'API Google Maps Geocoding
        response = requests.get(
            'https://maps.googleapis.com/maps/api/geocode/json',
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data['status'] == 'OK' and data['results']:
                location = data['results'][0]['geometry']['location']
                
                delivery.latitude = Decimal(str(location['lat']))
                delivery.longitude = Decimal(str(location['lng']))
                delivery.save()
                
                print(f"✅ Géocodage réussi pour {delivery.delivery_number}: {location['lat']}, {location['lng']}")
                return True
            else:
                print(f"❌ Géocodage échoué pour {delivery.delivery_number}: {data.get('status', 'Unknown error')}")
                return False
        else:
            print(f"❌ Erreur API pour {delivery.delivery_number}: {response.status_code}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Erreur réseau pour {delivery.delivery_number}: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Erreur générale pour {delivery.delivery_number}: {str(e)}")
        return False

# Fonction pour re-géocoder toutes les livraisons existantes
def regeocoder_toutes_livraisons():
    """Re-géocoder toutes les livraisons qui n'ont pas de coordonnées"""
    from .models import Delivery
    
    livraisons_sans_coordonnees = Delivery.objects.filter(
        Q(latitude__isnull=True) | Q(longitude__isnull=True)
    )
    
    print(f"🔄 Re-géocodage de {livraisons_sans_coordonnees.count()} livraisons...")
    
    succes = 0
    echecs = 0
    
    for delivery in livraisons_sans_coordonnees:
        if geocode_delivery_address(delivery):
            succes += 1
        else:
            echecs += 1
    
    print(f"✅ Géocodage terminé: {succes} succès, {echecs} échecs")
    return succes, echecs

def calculate_route_estimates(route):
    """Calcule les estimations de temps pour une route"""
    route_deliveries = route.route_deliveries.all().order_by('position')
    
    current_time = datetime.combine(route.date, route.start_time)
    total_distance = 0
    
    for rd in route_deliveries:
        # Temps de trajet estimé (simplifié)
        travel_time = timedelta(minutes=15)  # 15 minutes entre chaque livraison
        current_time += travel_time
        
        rd.estimated_arrival = current_time.time()
        
        # Temps sur place
        service_time = timedelta(minutes=rd.delivery.estimated_duration)
        current_time += service_time
        
        rd.estimated_departure = current_time.time()
        rd.save()
        
        # Distance (simplifiée)
        total_distance += 5  # 5km entre chaque point
    
    route.end_time = current_time.time()
    route.total_distance = total_distance
    route.estimated_duration = int((current_time - datetime.combine(route.date, route.start_time)).total_seconds() / 60)
    route.save()

@require_POST
@csrf_exempt
def save_delivery_signature(request):
    """Sauvegarder la signature électronique"""
    
    delivery_id = request.POST.get('delivery_id')
    signature_data = request.POST.get('signature')
    
    delivery = get_object_or_404(Delivery, id=delivery_id)
    delivery.signature = signature_data
    delivery.save()
    
    return JsonResponse({'success': True})

@require_POST
def upload_delivery_photo(request):
    """Upload de photo de livraison via AJAX"""
    
    delivery_id = request.POST.get('delivery_id')
    photo_type = request.POST.get('photo_type', 'delivery')
    
    delivery = get_object_or_404(Delivery, id=delivery_id)
    
    if 'photo' in request.FILES:
        photo = DeliveryPhoto.objects.create(
            delivery=delivery,
            photo_type=photo_type,
            photo=request.FILES['photo'],
            caption=request.POST.get('caption', ''),
            taken_by=request.user
        )
        
        # Géolocalisation
        if request.POST.get('latitude'):
            photo.latitude = request.POST.get('latitude')
            photo.longitude = request.POST.get('longitude')
            photo.save()
        
        return JsonResponse({
            'success': True,
            'photo_id': photo.id,
            'photo_url': photo.photo.url
        })
    
    return JsonResponse({'success': False, 'error': 'Aucune photo fournie'})

def send_delivery_notification(delivery, notification_type='reminder'):
    """Envoie une notification au client"""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    
    if notification_type == 'reminder':
        subject = f'Rappel de livraison - {delivery.delivery_number}'
        template = 'JLTsite/email/delivery_reminder.html'
    elif notification_type == 'completed':
        subject = f'Livraison effectuée - {delivery.delivery_number}'
        template = 'JLTsite/email/delivery_completed.html'
    else:
        return
    
    context = {
        'delivery': delivery,
        'customer_name': delivery.customer_name,
    }
    
    html_message = render_to_string(template, context)
    
    send_mail(
        subject=subject,
        message='',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[delivery.customer_email],
        html_message=html_message,
        fail_silently=False,
    )
    
    if notification_type == 'reminder':
        delivery.reminder_sent = True
        delivery.reminder_sent_at = timezone.now()
        delivery.save()

# ========================================
# VUES MANQUANTES POUR LE SYSTÈME DE LIVRAISON
# Ajouter ces fonctions dans votre delivery_views.py
# ========================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, Sum, Avg, F
from django.utils import timezone
from django.contrib import messages
from datetime import datetime, timedelta, date
from decimal import Decimal
import json
import csv
from django.core.files.base import ContentFile
import base64
from io import BytesIO
from PIL import Image

from .models import (
    Order, Delivery, DeliveryRoute, RouteDelivery, DeliveryPhoto,
    DriverPlanning, DeliveryNotification, DeliverySettings, User
)

# ========================================
# VUES API POUR LIVREUR
# ========================================

@login_required
@user_passes_test(delivery_driver_required)
@require_POST
def start_route(request, route_id):
    """Démarrer une route"""
    try:
        route = get_object_or_404(DeliveryRoute, id=route_id, driver=request.user)
        
        if route.status != 'planned':
            return JsonResponse({
                'success': False,
                'message': 'Cette route ne peut pas être démarrée'
            }, status=400)
        
        route.status = 'in_progress'
        route.started_at = timezone.now()
        route.save()
        
        # Mettre à jour le statut des livraisons
        for rd in route.route_deliveries.all():
            if rd.delivery.status == 'assigned':
                rd.delivery.status = 'in_transit'
                rd.delivery.save()
        
        # Créer une notification
        DeliveryNotification.objects.create(
            type='route_assigned',
            recipient_type='manager',
            recipient=User.objects.filter(role='delivery_manager').first(),
            route=route,
            title='Route démarrée',
            message=f'{request.user.get_full_name()} a démarré la route {route.route_number}'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Route démarrée avec succès'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
@user_passes_test(delivery_driver_required)
@require_POST
def complete_route(request, route_id):
    """Terminer une route"""
    try:
        route = get_object_or_404(DeliveryRoute, id=route_id, driver=request.user)
        
        if route.status != 'in_progress':
            return JsonResponse({
                'success': False,
                'message': 'Cette route n\'est pas en cours'
            }, status=400)
        
        # Vérifier si toutes les livraisons sont complétées
        incomplete_deliveries = route.route_deliveries.filter(
            delivery__status__in=['assigned', 'in_transit']
        ).count()
        
        if incomplete_deliveries > 0:
            return JsonResponse({
                'success': False,
                'message': f'Il reste {incomplete_deliveries} livraison(s) non complétée(s)'
            }, status=400)
        
        route.status = 'completed'
        route.completed_at = timezone.now()
        route.save()
        
        # Mettre à jour les stats
        route.update_stats()
        
        # Notification
        DeliveryNotification.objects.create(
            type='completed',
            recipient_type='manager',
            recipient=User.objects.filter(role='delivery_manager').first(),
            route=route,
            title='Route terminée',
            message=f'La route {route.route_number} a été complétée par {request.user.get_full_name()}',
            is_urgent=False
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Route terminée avec succès!'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
@require_POST
def report_delivery_issue(request):
    """Signaler un problème sur une livraison"""
    try:
        delivery_id = request.POST.get('delivery_id')
        issue_type = request.POST.get('issue_type')
        description = request.POST.get('description')
        
        delivery = get_object_or_404(Delivery, id=delivery_id)
        
        # Mettre à jour le statut
        delivery.status = 'failed'
        delivery.delivery_notes = f"Problème ({issue_type}): {description}"
        delivery.save()
        
        # Créer une photo si fournie
        if 'photo' in request.FILES:
            DeliveryPhoto.objects.create(
                delivery=delivery,
                photo_type='issue',
                photo=request.FILES['photo'],
                caption=f"Problème: {issue_type}",
                taken_by=request.user
            )
        
        # Créer une notification urgente
        DeliveryNotification.objects.create(
            type='issue',
            recipient_type='manager',
            recipient=User.objects.filter(role='delivery_manager').first(),
            delivery=delivery,
            title='Problème de livraison',
            message=f'Problème signalé sur {delivery.delivery_number}: {description}',
            is_urgent=True
        )
        
        # Envoyer un email au responsable
        send_issue_notification_email(delivery, issue_type, description)
        
        return JsonResponse({
            'success': True,
            'message': 'Problème signalé avec succès'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
@require_POST
def mark_delivery_notification_read(request, notification_id):
    """Marquer une notification comme lue"""
    try:
        notification = get_object_or_404(
            DeliveryNotification, 
            id=notification_id,
            recipient=request.user
        )
        notification.mark_as_read()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

# ========================================
# VUES POUR RESPONSABLE LIVRAISON
# ========================================

@login_required
@user_passes_test(delivery_manager_required)
def driver_planning_overview(request):
    """Vue d'ensemble du planning des livreurs"""
    
    # Semaine sélectionnée
    week_start = request.GET.get('week_start')
    if week_start:
        week_start = datetime.strptime(week_start, '%Y-%m-%d').date()
    else:
        week_start = timezone.now().date() - timedelta(days=timezone.now().date().weekday())
    
    week_end = week_start + timedelta(days=6)
    
    # Récupérer tous les livreurs
    drivers = User.objects.filter(role='delivery_driver', is_active=True)
    
    # Créer la grille de planning
    planning_grid = []
    for driver in drivers:
        driver_planning = {
            'driver': driver,
            'days': []
        }
        
        for day_offset in range(7):
            current_date = week_start + timedelta(days=day_offset)
            
            # Planning du jour
            planning = DriverPlanning.objects.filter(
                driver=driver,
                date=current_date
            ).first()
            
            # Routes du jour
            routes = DeliveryRoute.objects.filter(
                driver=driver,
                date=current_date
            )
            
            # Livraisons du jour
            deliveries_count = 0
            for route in routes:
                deliveries_count += route.route_deliveries.count()
            
            driver_planning['days'].append({
                'date': current_date,
                'planning': planning,
                'routes': routes,
                'deliveries_count': deliveries_count,
                'is_available': planning.is_available if planning else True
            })
        
        planning_grid.append(driver_planning)
    
    # Statistiques de la semaine
    week_stats = {
        'total_deliveries': Delivery.objects.filter(
            scheduled_date__range=[week_start, week_end]
        ).count(),
        'assigned_deliveries': Delivery.objects.filter(
            scheduled_date__range=[week_start, week_end],
            status='assigned'
        ).count(),
        'completed_deliveries': Delivery.objects.filter(
            scheduled_date__range=[week_start, week_end],
            status='delivered'
        ).count(),
        'active_drivers': drivers.count(),
    }
    
    context = {
        'planning_grid': planning_grid,
        'week_start': week_start,
        'week_end': week_end,
        'week_stats': week_stats,
        'weekdays': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
    }
    
    return render(request, 'JLTsite/driver_planning_overview.html', context)

@login_required
@user_passes_test(delivery_manager_required)
def delivery_detail(request, delivery_id):
    """Détail d'une livraison pour le responsable"""
    
    delivery = get_object_or_404(Delivery, id=delivery_id)
    
    # Historique de la livraison
    history = []
    
    # Création
    history.append({
        'date': delivery.created_at,
        'event': 'Livraison créée',
        'user': delivery.created_by.get_full_name() if delivery.created_by else 'Système',
        'icon': 'fa-plus-circle',
        'color': 'info'
    })
    
    # Assignation à une route
    route_assignment = delivery.route_assignments.first()
    if route_assignment:
        history.append({
            'date': route_assignment.route.created_at,
            'event': f'Assignée à la route {route_assignment.route.route_number}',
            'user': route_assignment.route.driver.get_full_name(),
            'icon': 'fa-route',
            'color': 'primary'
        })
    
    # Livraison
    if delivery.delivered_at:
        history.append({
            'date': delivery.delivered_at,
            'event': 'Livrée',
            'user': delivery.delivered_by.get_full_name() if delivery.delivered_by else '',
            'icon': 'fa-check-circle',
            'color': 'success'
        })
    
    # Photos
    photos = delivery.photos.all().order_by('-taken_at')
    
    # Notifications
    notifications = delivery.notifications.all().order_by('-created_at')
    key_google = settings.GOOGLE_API_KEY
    context = {
        'delivery': delivery,
        'history': sorted(history, key=lambda x: x['date']),
        'photos': photos,
        'notifications': notifications,
        'route_assignment': route_assignment,
        'key_google': key_google,
    }
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_status':
            new_status = request.POST.get('status')
            delivery.status = new_status
            delivery.save()
            messages.success(request, f'Statut mis à jour: {delivery.get_status_display()}')
            
        elif action == 'assign_driver':
            driver_id = request.POST.get('driver_id')
            # Créer ou mettre à jour la route
            # ... logique d'assignation
            
        return redirect('delivery_detail', delivery_id=delivery.id)
    
    return render(request, 'JLTsite/delivery_detail.html', context)

# ========================================
# RAPPORTS ET EXPORTS
# ========================================

@login_required
@user_passes_test(delivery_manager_required)
def delivery_reports(request):
    """Rapports et analyses des livraisons"""
    
    # Période
    period = request.GET.get('period', 'month')
    if period == 'week':
        start_date = timezone.now() - timedelta(days=7)
    elif period == 'year':
        start_date = timezone.now() - timedelta(days=365)
    else:  # month
        start_date = timezone.now() - timedelta(days=30)
    
    # Statistiques générales
    stats = {
        'total_deliveries': Delivery.objects.filter(
            created_at__gte=start_date
        ).count(),
        
        'completed_deliveries': Delivery.objects.filter(
            created_at__gte=start_date,
            status='delivered'
        ).count(),
        
        'failed_deliveries': Delivery.objects.filter(
            created_at__gte=start_date,
            status='failed'
        ).count(),
        
        'avg_delivery_time': Delivery.objects.filter(
            created_at__gte=start_date,
            status='delivered',
            delivered_at__isnull=False
        ).annotate(
            delivery_duration=F('delivered_at') - F('created_at')
        ).aggregate(
            avg_duration=Avg('delivery_duration')
        )['avg_duration'],
        
        'on_time_rate': calculate_on_time_rate(start_date),
    }
    
    # Performance par livreur
    driver_performance = []
    drivers = User.objects.filter(role='delivery_driver')
    
    for driver in drivers:
        routes = DeliveryRoute.objects.filter(
            driver=driver,
            date__gte=start_date
        )
        
        deliveries = Delivery.objects.filter(
            route_assignments__route__driver=driver,
            created_at__gte=start_date
        )
        
        driver_performance.append({
            'driver': driver,
            'total_routes': routes.count(),
            'total_deliveries': deliveries.count(),
            'completed': deliveries.filter(status='delivered').count(),
            'failed': deliveries.filter(status='failed').count(),
            'success_rate': (deliveries.filter(status='delivered').count() / deliveries.count() * 100) if deliveries.count() > 0 else 0,
        })
    
    # Livraisons par jour
    daily_deliveries = Delivery.objects.filter(
        scheduled_date__gte=start_date
    ).values('scheduled_date').annotate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='delivered')),
        failed=Count('id', filter=Q(status='failed'))
    ).order_by('scheduled_date')
    
    # Problèmes récurrents
    issues = Delivery.objects.filter(
        created_at__gte=start_date,
        status='failed'
    ).values('delivery_notes').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Zones de livraison
    zones_stats = Delivery.objects.filter(
        created_at__gte=start_date
    ).values('delivery_postal_code').annotate(
        count=Count('id'),
        avg_time=Avg('estimated_duration')
    ).order_by('-count')[:20]
    
    context = {
        'period': period,
        'stats': stats,
        'driver_performance': driver_performance,
        'daily_deliveries': list(daily_deliveries),
        'issues': issues,
        'zones_stats': zones_stats,
    }
    
    return render(request, 'JLTsite/delivery_reports.html', context)

@login_required
@user_passes_test(delivery_manager_required)
def export_deliveries(request):
    """Exporter les livraisons en CSV"""
    
    # Paramètres de filtrage
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    status = request.GET.get('status')
    driver_id = request.GET.get('driver_id')
    
    # Requête de base
    deliveries = Delivery.objects.all()
    
    # Appliquer les filtres
    if start_date:
        deliveries = deliveries.filter(scheduled_date__gte=start_date)
    if end_date:
        deliveries = deliveries.filter(scheduled_date__lte=end_date)
    if status:
        deliveries = deliveries.filter(status=status)
    if driver_id:
        deliveries = deliveries.filter(
            route_assignments__route__driver_id=driver_id
        )
    
    # Créer la réponse CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="livraisons_{timezone.now().date()}.csv"'
    response.write('\ufeff'.encode('utf8'))  # BOM pour Excel
    
    writer = csv.writer(response)
    
    # En-têtes
    writer.writerow([
        'Numéro', 'Type', 'Date', 'Heure', 'Client', 'Téléphone', 
        'Adresse', 'Code postal', 'Ville', 'Statut', 'Livreur',
        'Route', 'Livré le', 'Durée (min)', 'Notes'
    ])
    
    # Données
    for delivery in deliveries:
        route = delivery.route_assignments.first()
        driver = route.route.driver if route else None
        
        # Calculer la durée
        duration = None
        if delivery.delivered_at and delivery.created_at:
            duration = (delivery.delivered_at - delivery.created_at).total_seconds() / 60
        
        writer.writerow([
            delivery.delivery_number,
            delivery.get_delivery_type_display(),
            delivery.scheduled_date.strftime('%d/%m/%Y'),
            delivery.scheduled_time_start.strftime('%H:%M'),
            delivery.customer_name,
            delivery.customer_phone,
            delivery.delivery_address,
            delivery.delivery_postal_code,
            delivery.delivery_city,
            delivery.get_status_display(),
            driver.get_full_name() if driver else '',
            route.route.route_number if route else '',
            delivery.delivered_at.strftime('%d/%m/%Y %H:%M') if delivery.delivered_at else '',
            f"{duration:.0f}" if duration else '',
            delivery.delivery_notes
        ])
    
    return response

# ========================================
# FONCTIONS UTILITAIRES
# ========================================

def calculate_on_time_rate(start_date):
    """Calculer le taux de livraison à temps"""
    deliveries = Delivery.objects.filter(
        created_at__gte=start_date,
        status='delivered',
        delivered_at__isnull=False
    )
    
    total = deliveries.count()
    if total == 0:
        return 0
    
    on_time = 0
    for delivery in deliveries:
        # Comparer l'heure de livraison avec l'heure prévue
        scheduled_end = datetime.combine(
            delivery.scheduled_date,
            delivery.scheduled_time_end
        )
        scheduled_end = timezone.make_aware(scheduled_end)
        
        if delivery.delivered_at <= scheduled_end:
            on_time += 1
    
    return (on_time / total) * 100

def send_issue_notification_email(delivery, issue_type, description):
    """Envoyer un email de notification pour un problème"""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    
    subject = f'Problème de livraison - {delivery.delivery_number}'
    
    # Récupérer les emails des responsables
    managers = User.objects.filter(
        role__in=['delivery_manager', 'admin'],
        is_active=True
    ).values_list('email', flat=True)
    
    if not managers:
        return
    
    message = f"""
    Un problème a été signalé sur la livraison {delivery.delivery_number}
    
    Type de problème: {issue_type}
    Description: {description}
    
    Client: {delivery.customer_name}
    Adresse: {delivery.delivery_address}, {delivery.delivery_postal_code} {delivery.delivery_city}
    
    Veuillez prendre les mesures nécessaires.
    """
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=list(managers),
        fail_silently=False,
    )


    # Ajoutez ces fonctions à votre delivery_views.py

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json

@login_required
def get_available_routes(request):
    """API pour obtenir les routes disponibles pour une date"""
    date = request.GET.get('date')
    if not date:
        date = timezone.now().date()
    else:
        date = datetime.strptime(date, '%Y-%m-%d').date()
    
    routes = DeliveryRoute.objects.filter(
        date=date,
        status__in=['planned', 'in_progress']
    ).select_related('driver')
    
    routes_data = []
    for route in routes:
        routes_data.append({
            'id': route.id,
            'route_number': route.route_number,
            'driver_name': route.driver.get_full_name(),
            'driver_id': route.driver.id,
            'start_time': route.start_time.strftime('%H:%M'),
            'deliveries_count': route.route_deliveries.count(),
            'status': route.status,
        })
    
    return JsonResponse({'routes': routes_data})

@login_required
@require_http_methods(["POST"])
def update_delivery_status_api(request, delivery_id):
    """API pour mettre à jour le statut d'une livraison"""
    try:
        delivery = get_object_or_404(Delivery, id=delivery_id)
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if new_status not in ['pending', 'assigned', 'in_transit', 'delivered', 'failed']:
            return JsonResponse({
                'success': False,
                'error': 'Statut invalide'
            }, status=400)
        
        old_status = delivery.status
        delivery.status = new_status
        
        # Gérer les changements spécifiques selon le statut
        if new_status == 'delivered':
            delivery.delivered_at = timezone.now()
            delivery.delivered_by = request.user
            
            # Mettre à jour la commande associée
            if delivery.order:
                delivery.order.status = 'delivered'
                delivery.order.delivered_at = timezone.now()
                delivery.order.save()
                
        elif new_status == 'failed':
            # Créer une notification urgente
            DeliveryNotification.objects.create(
                type='issue',
                recipient_type='manager',
                recipient=User.objects.filter(role='delivery_manager').first(),
                delivery=delivery,
                title='Livraison échouée',
                message=f'La livraison {delivery.delivery_number} a échoué',
                is_urgent=True
            )
        
        delivery.save()
        
        # Ajouter à l'historique
        # Vous pouvez créer un modèle DeliveryHistory si nécessaire
        
        return JsonResponse({
            'success': True,
            'message': f'Statut mis à jour: {old_status} → {new_status}',
            'new_status': new_status,
            'status_display': delivery.get_status_display()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_http_methods(["POST"])
def send_delivery_notification_api(request, delivery_id):
    """API pour envoyer une notification au client"""
    try:
        delivery = get_object_or_404(Delivery, id=delivery_id)
        data = json.loads(request.body)
        
        notification_type = data.get('type', 'reminder')
        custom_message = data.get('message', '')
        
        # Envoyer l'email de notification
        send_delivery_notification(delivery, notification_type)
        
        # Créer un enregistrement de notification
        DeliveryNotification.objects.create(
            type=notification_type,
            recipient_type='customer',
            delivery=delivery,
            title=f'Notification {notification_type}',
            message=custom_message or f'Notification envoyée au client pour la livraison {delivery.delivery_number}',
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Notification envoyée avec succès'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def edit_delivery(request, delivery_id):
    """Éditer une livraison"""
    delivery = get_object_or_404(Delivery, id=delivery_id)
    
    if request.method == 'POST':
        # Mettre à jour les champs
        delivery.customer_name = request.POST.get('customer_name', delivery.customer_name)
        delivery.customer_phone = request.POST.get('customer_phone', delivery.customer_phone)
        delivery.customer_email = request.POST.get('customer_email', delivery.customer_email)
        delivery.company = request.POST.get('company', delivery.company)
        
        delivery.delivery_address = request.POST.get('delivery_address', delivery.delivery_address)
        delivery.delivery_postal_code = request.POST.get('delivery_postal_code', delivery.delivery_postal_code)
        delivery.delivery_city = request.POST.get('delivery_city', delivery.delivery_city)
        
        if request.POST.get('scheduled_date'):
            delivery.scheduled_date = request.POST.get('scheduled_date')
        if request.POST.get('scheduled_time_start'):
            delivery.scheduled_time_start = request.POST.get('scheduled_time_start')
        if request.POST.get('scheduled_time_end'):
            delivery.scheduled_time_end = request.POST.get('scheduled_time_end')
        
        delivery.priority = request.POST.get('priority', delivery.priority)
        delivery.delivery_instructions = request.POST.get('delivery_instructions', delivery.delivery_instructions)
        delivery.items_description = request.POST.get('items_description', delivery.items_description)
        delivery.total_packages = int(request.POST.get('total_packages', delivery.total_packages))
        
        delivery.save()
        
        # Re-géocoder si l'adresse a changé
        if 'delivery_address' in request.POST:
            geocode_delivery_address(delivery)
        
        messages.success(request, 'Livraison mise à jour avec succès!')
        return redirect('delivery_detail', delivery_id=delivery.id)
    
    context = {
        'delivery': delivery,
        'priority_choices': Delivery.PRIORITY_CHOICES,
        'status_choices': Delivery.STATUS_CHOICES,
    }
    
    return render(request, 'JLTsite/edit_delivery.html', context)

# Ajoutez ces vues à votre delivery_views.py

@login_required
@user_passes_test(delivery_manager_required)
@require_POST
def create_driver_planning(request):
    """Créer ou mettre à jour le planning d'un livreur"""
    try:
        data = json.loads(request.body)
        
        driver = get_object_or_404(User, id=data['driver_id'], role='delivery_driver')
        planning_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        
        # Vérifier si un planning existe déjà
        planning, created = DriverPlanning.objects.get_or_create(
            driver=driver,
            date=planning_date,
            defaults={
                'start_time': data.get('start_time', '08:00'),
                'end_time': data.get('end_time', '17:00'),
                'is_available': data.get('is_available', True),
                'unavailability_reason': data.get('unavailability_reason', ''),
                'notes': data.get('notes', ''),
                'created_by': request.user
            }
        )
        
        if not created:
            # Mettre à jour le planning existant
            planning.start_time = data.get('start_time', planning.start_time)
            planning.end_time = data.get('end_time', planning.end_time)
            planning.is_available = data.get('is_available', planning.is_available)
            planning.unavailability_reason = data.get('unavailability_reason', '')
            planning.notes = data.get('notes', planning.notes)
            planning.updated_by = request.user
            planning.save()
        
        # Notifier le livreur par email si demandé
        if data.get('notify_driver', False):
            send_planning_notification(planning)
        
        # Créer une notification système
        DeliveryNotification.objects.create(
            type='planning_updated',
            recipient_type='driver',
            recipient=driver,
            title='Planning mis à jour',
            message=f'Votre planning pour le {planning_date.strftime("%d/%m/%Y")} a été mis à jour',
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Planning créé avec succès' if created else 'Planning mis à jour avec succès',
            'planning_id': planning.id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(delivery_manager_required)
@require_POST
def update_driver_planning(request, planning_id):
    """Mettre à jour un planning existant"""
    try:
        planning = get_object_or_404(DriverPlanning, id=planning_id)
        data = json.loads(request.body)
        
        planning.start_time = data.get('start_time', planning.start_time)
        planning.end_time = data.get('end_time', planning.end_time)
        planning.is_available = data.get('is_available', planning.is_available)
        planning.unavailability_reason = data.get('unavailability_reason', '')
        planning.notes = data.get('notes', planning.notes)
        planning.updated_by = request.user
        planning.save()
        
        # Notifier le livreur si demandé
        if data.get('notify_driver', False):
            send_planning_notification(planning)
        
        return JsonResponse({
            'success': True,
            'message': 'Planning mis à jour avec succès'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(delivery_manager_required)
@require_http_methods(["DELETE"])
def delete_driver_planning(request, planning_id):
    """Supprimer un planning"""
    try:
        planning = get_object_or_404(DriverPlanning, id=planning_id)
        driver_name = planning.driver.get_full_name()
        planning_date = planning.date
        
        planning.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Planning de {driver_name} pour le {planning_date.strftime("%d/%m/%Y")} supprimé'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@user_passes_test(delivery_manager_required)
def get_driver_planning(request, planning_id):
    """Récupérer les détails d'un planning (pour l'édition)"""
    try:
        planning = get_object_or_404(DriverPlanning, id=planning_id)
        
        data = {
            'id': planning.id,
            'driver_id': planning.driver.id,
            'date': planning.date.strftime('%Y-%m-%d'),
            'start_time': planning.start_time.strftime('%H:%M'),
            'end_time': planning.end_time.strftime('%H:%M'),
            'is_available': planning.is_available,
            'unavailability_reason': planning.unavailability_reason,
            'notes': planning.notes,
        }
        
        return JsonResponse({'success': True, 'planning': data})
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def send_planning_notification(planning):
    """Envoyer une notification email au livreur"""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    
    subject = f'Planning mis à jour - {planning.date.strftime("%d/%m/%Y")}'
    
    context = {
        'driver_name': planning.driver.get_full_name(),
        'date': planning.date,
        'start_time': planning.start_time,
        'end_time': planning.end_time,
        'is_available': planning.is_available,
        'unavailability_reason': planning.unavailability_reason,
        'notes': planning.notes,
    }
    
    # Template simple pour l'email
    message = f"""
Bonjour {planning.driver.get_full_name()},

Votre planning pour le {planning.date.strftime("%d/%m/%Y")} a été mis à jour :

Horaires : {planning.start_time.strftime("%H:%M")} - {planning.end_time.strftime("%H:%M")}
Statut : {"Disponible" if planning.is_available else f"Indisponible ({planning.unavailability_reason})"}

{f"Notes : {planning.notes}" if planning.notes else ""}

Cordialement,
L'équipe de livraison
    """
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[planning.driver.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Erreur envoi email planning: {str(e)}")

# Fonction utilitaire pour calculer les statistiques de planning
def get_planning_stats(selected_date, drivers):
    """Calculer les statistiques du planning pour une date donnée"""
    
    # Récupérer tous les plannings pour cette date
    plannings = DriverPlanning.objects.filter(
        date=selected_date,
        driver__in=drivers
    )
    
    # Récupérer toutes les routes pour cette date
    routes = DeliveryRoute.objects.filter(
        date=selected_date,
        driver__in=drivers
    )
    
    # Calculer les statistiques
    available_count = plannings.filter(is_available=True).count()
    unavailable_count = plannings.filter(is_available=False).count()
    total_routes = routes.count()
    
    # Calculer la moyenne de livraisons par livreur
    total_deliveries = 0
    for route in routes:
        total_deliveries += route.route_deliveries.count()
    
    avg_deliveries = total_deliveries / len(drivers) if drivers else 0
    
    return {
        'available': available_count,
        'unavailable': unavailable_count,
        'total_routes': total_routes,
        'avg_deliveries': round(avg_deliveries, 1)
    }

@login_required
@user_passes_test(delivery_driver_required)
def driver_notifications(request):
    """Notifications du livreur - Vue mobile"""
    
    driver = request.user
    
    # Récupérer toutes les notifications
    notifications = DeliveryNotification.objects.filter(
        recipient=driver
    ).order_by('-created_at')
    
    # Marquer comme lues les notifications ouvertes
    unread_notifications = notifications.filter(is_read=False)
    if request.method == 'POST' and request.POST.get('mark_all_read'):
        unread_notifications.update(is_read=True, read_at=timezone.now())
        messages.success(request, 'Toutes les notifications ont été marquées comme lues.')
        return redirect('driver_notifications')
    
    # Grouper par date
    from itertools import groupby
    from operator import attrgetter
    
    notifications_by_date = []
    for date_group, items in groupby(notifications, key=lambda x: x.created_at.date()):
        notifications_by_date.append({
            'date': date_group,
            'notifications': list(items)
        })
    
    context = {
        'driver': driver,
        'notifications_by_date': notifications_by_date,
        'unread_count': unread_notifications.count(),
    }
    
    return render(request, 'JLTsite/driver_notifications_mobile.html', context)

@login_required
@user_passes_test(delivery_driver_required)
def driver_profile(request):
    """Profil du livreur - Vue mobile"""
    
    driver = request.user
    
    if request.method == 'POST':
        # Mise à jour du profil
        driver.first_name = request.POST.get('first_name', driver.first_name)
        driver.last_name = request.POST.get('last_name', driver.last_name)
        driver.email = request.POST.get('email', driver.email)
        driver.phone = request.POST.get('phone', driver.phone)
        driver.driver_license = request.POST.get('driver_license', driver.driver_license)
        driver.vehicle_info = request.POST.get('vehicle_info', driver.vehicle_info)
        
        # Statut de disponibilité
        driver.is_available = request.POST.get('is_available') == 'on'
        
        driver.save()
        messages.success(request, 'Profil mis à jour avec succès!')
        return redirect('driver_profile')
    
    # Statistiques du livreur
    total_deliveries = Delivery.objects.filter(
        route_assignments__route__driver=driver,
        status='delivered'
    ).count()
    
    this_month_deliveries = Delivery.objects.filter(
        route_assignments__route__driver=driver,
        status='delivered',
        delivered_at__month=timezone.now().month,
        delivered_at__year=timezone.now().year
    ).count()
    
    # Routes complétées
    completed_routes = DeliveryRoute.objects.filter(
        driver=driver,
        status='completed'
    ).count()
    
    # Taux de réussite
    total_assigned = Delivery.objects.filter(
        route_assignments__route__driver=driver
    ).count()
    
    success_rate = (total_deliveries / total_assigned * 100) if total_assigned > 0 else 0
    
    context = {
        'driver': driver,
        'stats': {
            'total_deliveries': total_deliveries,
            'this_month_deliveries': this_month_deliveries,
            'completed_routes': completed_routes,
            'success_rate': round(success_rate, 1),
        }
    }
    
    return render(request, 'JLTsite/driver_profile_mobile.html', context)


# ========================================
# API ENDPOINTS POUR MOBILE
# ========================================

@login_required
@user_passes_test(delivery_driver_required)
@require_POST
def retry_delivery_api(request, delivery_id):
    """API pour réessayer une livraison échouée"""
    try:
        delivery = get_object_or_404(Delivery, id=delivery_id)
        
        # Vérifier que le livreur a accès à cette livraison
        if not delivery.route_assignments.filter(route__driver=request.user).exists():
            return JsonResponse({
                'success': False,
                'message': 'Accès non autorisé à cette livraison'
            }, status=403)
        
        if delivery.status != 'failed':
            return JsonResponse({
                'success': False,
                'message': 'Cette livraison n\'est pas en échec'
            }, status=400)
        
        # Remettre en attente
        delivery.status = 'assigned'
        delivery.delivery_notes = ''
        delivery.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Livraison remise en attente'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
@user_passes_test(delivery_driver_required)
@require_POST
def mark_notification_read_api(request, notification_id):
    """API pour marquer une notification comme lue"""
    try:
        notification = get_object_or_404(
            DeliveryNotification,
            id=notification_id,
            recipient=request.user
        )
        
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
@user_passes_test(delivery_driver_required)
def driver_stats_api(request):
    """API pour obtenir les statistiques du livreur"""
    driver = request.user
    selected_date = request.GET.get('date', timezone.now().date())
    
    if isinstance(selected_date, str):
        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.now().date()
    
    # Route du jour
    current_route = DeliveryRoute.objects.filter(
        driver=driver,
        date=selected_date
    ).first()
    
    # Livraisons du jour
    deliveries = []
    if current_route:
        route_deliveries = current_route.route_deliveries.all()
        deliveries = [rd.delivery for rd in route_deliveries]
    
    # Statistiques
    stats = {
        'total': len(deliveries),
        'completed': sum(1 for d in deliveries if d.status == 'delivered'),
        'pending': sum(1 for d in deliveries if d.status in ['assigned', 'in_transit']),
        'failed': sum(1 for d in deliveries if d.status == 'failed'),
        'route_status': current_route.status if current_route else None,
    }
    
    return JsonResponse({
        'success': True,
        'stats': stats,
        'date': selected_date.strftime('%Y-%m-%d')
    })

# ========================================
# VUES ADDITIONNELLES
# ========================================

@login_required
@user_passes_test(delivery_driver_required)
def driver_delivery_history(request):
    """Historique des livraisons du livreur"""
    
    driver = request.user
    
    # Filtres
    status_filter = request.GET.get('status', 'all')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Récupérer toutes les livraisons du livreur
    deliveries = Delivery.objects.filter(
        route_assignments__route__driver=driver
    ).select_related('order').order_by('-scheduled_date', '-scheduled_time_start')
    
    # Appliquer les filtres
    if status_filter != 'all':
        deliveries = deliveries.filter(status=status_filter)
    
    if date_from:
        try:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            deliveries = deliveries.filter(scheduled_date__gte=date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            deliveries = deliveries.filter(scheduled_date__lte=date_to)
        except ValueError:
            pass
    
    # Pagination simple
    from django.core.paginator import Paginator
    paginator = Paginator(deliveries, 20)
    page = request.GET.get('page', 1)
    deliveries_page = paginator.get_page(page)
    
    context = {
        'driver': driver,
        'deliveries': deliveries_page,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': Delivery.STATUS_CHOICES,
    }
    
    return render(request, 'JLTsite/driver_delivery_history_mobile.html', context)

@login_required
@user_passes_test(delivery_driver_required)
def driver_route_detail_mobile(request, route_id):
    """Détail d'une route pour mobile"""
    
    route = get_object_or_404(
        DeliveryRoute,
        id=route_id,
        driver=request.user
    )
    
    # Livraisons de la route
    route_deliveries = route.route_deliveries.select_related(
        'delivery'
    ).order_by('position')
    
    # Statistiques de la route
    total_deliveries = route_deliveries.count()
    completed_deliveries = route_deliveries.filter(
        delivery__status='delivered'
    ).count()
    
    # Temps estimé vs réel
    if route.started_at and route.completed_at:
        actual_duration = route.completed_at - route.started_at
        actual_hours = actual_duration.total_seconds() / 3600
    else:
        actual_hours = None
    
    context = {
        'route': route,
        'route_deliveries': route_deliveries,
        'total_deliveries': total_deliveries,
        'completed_deliveries': completed_deliveries,
        'completion_rate': (completed_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0,
        'actual_hours': round(actual_hours, 1) if actual_hours else None,
    }
    
    return render(request, 'JLTsite/driver_route_detail_mobile.html', context)

@login_required
@user_passes_test(delivery_driver_required)
def driver_realtime_stats_api(request):
    """API pour obtenir les statistiques en temps réel du livreur"""
    driver = request.user
    selected_date = request.GET.get('date', timezone.now().date())
    
    if isinstance(selected_date, str):
        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.now().date()
    
    # Route du jour
    current_route = DeliveryRoute.objects.filter(
        driver=driver,
        date=selected_date
    ).first()
    
    # Livraisons du jour
    deliveries = []
    if current_route:
        route_deliveries = current_route.route_deliveries.all()
        deliveries = [rd.delivery for rd in route_deliveries]
    
    # Statistiques détaillées
    stats = {
        'date': selected_date.strftime('%Y-%m-%d'),
        'total': len(deliveries),
        'completed': sum(1 for d in deliveries if d.status == 'delivered'),
        'pending': sum(1 for d in deliveries if d.status in ['assigned', 'in_transit']),
        'failed': sum(1 for d in deliveries if d.status == 'failed'),
        'route_status': current_route.status if current_route else None,
        'route_id': current_route.id if current_route else None,
        'completion_rate': 0,
        'estimated_completion': None,
    }
    
    # Taux de completion
    if stats['total'] > 0:
        stats['completion_rate'] = round((stats['completed'] / stats['total']) * 100, 1)
    
    # Estimation de fin (logique simple)
    if current_route and stats['pending'] > 0:
        avg_time_per_delivery = 30  # 30 minutes par livraison en moyenne
        estimated_minutes = stats['pending'] * avg_time_per_delivery
        estimated_completion = timezone.now() + timedelta(minutes=estimated_minutes)
        stats['estimated_completion'] = estimated_completion.strftime('%H:%M')
    
    # Notifications non lues
    unread_notifications = DeliveryNotification.objects.filter(
        recipient=driver,
        is_read=False
    ).count()
    
    stats['unread_notifications'] = unread_notifications
    
    return JsonResponse({
        'success': True,
        'stats': stats,
        'timestamp': timezone.now().isoformat()
    })