
from .models import *
from .forms import *
from .views import *


# ========================================
# admin_views.py - Dashboard administrateur avec statistiques
# ========================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from django.db.models import Sum, Count, Avg, Q, F, Max
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from django.contrib import messages
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import (
    User, Product, Order, OrderItem, Category, Review
)

# ========================================
# 1. DECORATEURS
# ========================================

def admin_required(user):
    """Vérifier si l'utilisateur est admin"""
    return user.is_authenticated and user.role in ['admin', 'staff']

# ========================================
# 2. DASHBOARD PRINCIPAL
# ========================================
@user_passes_test(admin_required)
def admin_product_create(request):
    """Créer un nouveau produit"""
    categories = Category.objects.filter(is_active=True).order_by('order', 'name')
    
    if request.method == 'POST':
        try:
            # Créer le produit
            product = Product(
                name=request.POST.get('name'),
                slug=request.POST.get('slug', '').lower().replace(' ', '-'),
                category_id=request.POST.get('category'),
                description=request.POST.get('description'),
                ingredients=request.POST.get('ingredients', ''),
                allergens=request.POST.get('allergens', ''),
                price=Decimal(request.POST.get('price', 0)),
                stock=int(request.POST.get('stock', 0)),
                min_order=int(request.POST.get('min_order', 1)),
                is_vegetarian='is_vegetarian' in request.POST,
                is_vegan='is_vegan' in request.POST,
                is_gluten_free='is_gluten_free' in request.POST,
                is_featured='is_featured' in request.POST,
                is_active='is_active' in request.POST,
                calories=int(request.POST.get('calories', 0)) if request.POST.get('calories') else None,
                preparation_time=int(request.POST.get('preparation_time', 0)) if request.POST.get('preparation_time') else None,
            )
            
            # Gérer le prix promo
            promo_price = request.POST.get('promo_price')
            if promo_price:
                product.promo_price = Decimal(promo_price)
            
            # Gérer l'image
            if 'image' in request.FILES:
                product.image = request.FILES['image']
            
            # Gérer le statut
            if product.stock == 0:
                product.status = 'rupture'
            elif product.stock < 10:
                product.status = 'disponible'
            else:
                product.status = 'disponible'
            
            product.save()
            
            messages.success(request, f'Produit "{product.name}" créé avec succès!')
            return redirect('admin_product_edit', product_id=product.id)
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la création: {str(e)}')
    
    return render(request, 'JLTsite/product_form.html', {
        'categories': categories,
        'is_create': True
    })

@user_passes_test(admin_required)
def admin_product_edit(request, product_id):
    """Modifier un produit existant"""
    product = get_object_or_404(Product, id=product_id)
    categories = Category.objects.filter(is_active=True).order_by('order', 'name')
    
    if request.method == 'POST':
        try:
            # Mettre à jour le produit
            product.name = request.POST.get('name')
            product.slug = request.POST.get('slug', '').lower().replace(' ', '-')
            product.category_id = request.POST.get('category')
            product.description = request.POST.get('description')
            product.ingredients = request.POST.get('ingredients', '')
            product.allergens = request.POST.get('allergens', '')
            product.price = Decimal(request.POST.get('price', 0))
            product.stock = int(request.POST.get('stock', 0))
            product.min_order = int(request.POST.get('min_order', 1))
            product.is_vegetarian = 'is_vegetarian' in request.POST
            product.is_vegan = 'is_vegan' in request.POST
            product.is_gluten_free = 'is_gluten_free' in request.POST
            product.is_featured = 'is_featured' in request.POST
            product.is_active = 'is_active' in request.POST
            
            # Gérer les champs optionnels
            calories = request.POST.get('calories')
            product.calories = int(calories) if calories else None
            
            prep_time = request.POST.get('preparation_time')
            product.preparation_time = int(prep_time) if prep_time else None
            
            # Gérer le prix promo
            promo_price = request.POST.get('promo_price')
            product.promo_price = Decimal(promo_price) if promo_price else None
            
            # Gérer l'image
            if 'image' in request.FILES:
                # Supprimer l'ancienne image si elle existe
                if product.image:
                    product.image.delete(save=False)
                product.image = request.FILES['image']
            
            # Gérer le statut
            if product.stock == 0:
                product.status = 'rupture'
            elif product.stock < 10:
                product.status = 'disponible'
            else:
                product.status = 'disponible'
            
            product.save()
            
            messages.success(request, f'Produit "{product.name}" mis à jour avec succès!')
            return redirect('admin_product_edit', product_id=product.id)
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la mise à jour: {str(e)}')
    
    return render(request, 'JLTsite/product_form.html', {
        'product': product,
        'categories': categories,
        'is_create': False
    })

# ========================================
# VUE POUR SUPPRIMER UN PRODUIT
# ========================================

@user_passes_test(admin_required)
@require_POST
def admin_product_delete(request, product_id):
    """Supprimer un produit (désactiver)"""
    try:
        product = get_object_or_404(Product, id=product_id)
        
        # On ne supprime pas vraiment, on désactive
        product.is_active = False
        product.save()
        
        # Ou si vous voulez vraiment supprimer :
        # product.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Produit "{product.name}" supprimé avec succès'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@user_passes_test(admin_required)
def admin_dashboard(request):
    """Dashboard principal avec statistiques"""
    
    # Période sélectionnée
    period = request.GET.get('period', '30')  # 7, 30, 90 jours
    if period == '7':
        start_date = timezone.now() - timedelta(days=7)
    elif period == '90':
        start_date = timezone.now() - timedelta(days=90)
    else:
        start_date = timezone.now() - timedelta(days=30)
    
    # ========== STATISTIQUES GÉNÉRALES ==========
    
    # Commandes
    total_orders = Order.objects.filter(created_at__gte=start_date).count()
    pending_orders = Order.objects.filter(status='pending').count()
    orders_today = Order.objects.filter(
        created_at__date=timezone.now().date()
    ).count()
    
    # Revenus
    revenue_data = Order.objects.filter(
        created_at__gte=start_date,
        status__in=['confirmed', 'preparing', 'ready', 'delivered']
    ).aggregate(
        total=Sum('total'),
        count=Count('id')
    )
    total_revenue = revenue_data['total'] or Decimal('0')
    avg_order_value = total_revenue / revenue_data['count'] if revenue_data['count'] else Decimal('0')
    
    # Clients
    new_customers = User.objects.filter(
        created_at__gte=start_date,
        role='customer'
    ).count()
    
    total_customers = User.objects.filter(role='customer').count()
    
    # Produits
    low_stock_products = Product.objects.filter(
        stock__lt=10,
        is_active=True
    ).count()
    
    # ========== GRAPHIQUES ==========
    
    # Évolution des ventes (30 derniers jours)
    sales_chart_data = Order.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=30),
        status__in=['confirmed', 'preparing', 'ready', 'delivered']
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        total=Sum('total'),
        count=Count('id')
    ).order_by('date')
    
    sales_labels = []
    sales_revenue = []
    sales_count = []
    
    for item in sales_chart_data:
        sales_labels.append(item['date'].strftime('%d/%m'))
        sales_revenue.append(float(item['total'] or 0))
        sales_count.append(item['count'])
    
    # Top produits vendus
    top_products = OrderItem.objects.filter(
        order__created_at__gte=start_date,
        order__status__in=['confirmed', 'preparing', 'ready', 'delivered']
    ).values(
        'product__name'
    ).annotate(
        quantity_sold=Sum('quantity'),
        revenue=Sum('subtotal')
    ).order_by('-quantity_sold')[:10]
    
    top_products_names = []
    top_products_quantities = []
    
    for product in top_products:
        top_products_names.append(product['product__name'][:20])
        top_products_quantities.append(product['quantity_sold'])
    
    # Répartition par catégorie
    category_stats = OrderItem.objects.filter(
        order__created_at__gte=start_date,
        order__status__in=['confirmed', 'preparing', 'ready', 'delivered']
    ).values(
        'product__category__name'
    ).annotate(
        total=Sum('subtotal')
    ).order_by('-total')
    
    category_names = []
    category_values = []
    
    for cat in category_stats:
        category_names.append(cat['product__category__name'])
        category_values.append(float(cat['total'] or 0))
    
    # Commandes par statut
    status_stats = Order.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    status_labels = []
    status_counts = []
    
    for stat in status_stats:
        status_labels.append(Order.STATUS_CHOICES[
            next(i for i, choice in enumerate(Order.STATUS_CHOICES) if choice[0] == stat['status'])
        ][1])
        status_counts.append(stat['count'])
    
    # ========== COMMANDES RÉCENTES ==========
    recent_orders = Order.objects.all().order_by('-created_at')[:10]
    
    # ========== ALERTES ==========
    alerts = []
    
    # Commandes en attente
    if pending_orders > 0:
        alerts.append({
            'type': 'warning',
            'message': f'{pending_orders} commande(s) en attente de confirmation',
            'link': '/admin-dashboard/orders/?status=pending'
        })
    
    # Stock faible
    if low_stock_products > 0:
        alerts.append({
            'type': 'danger',
            'message': f'{low_stock_products} produit(s) avec stock faible',
            'link': '/admin-dashboard/products/low-stock/'
        })
    
    # Commandes du jour
    if orders_today > 5:
        alerts.append({
            'type': 'info',
            'message': f'{orders_today} commandes aujourd\'hui!',
            'link': '/admin-dashboard/orders/?date=today'
        })
    
    # AJOUTER: Statistiques des événements
    total_events = EventContract.objects.count()
    pending_events = EventContract.objects.filter(
        status__in=['draft', 'confirmed'],
        maitre_hotel__isnull=True
    ).count()
    
    events_today = EventContract.objects.filter(
        event_start_time__date=timezone.now().date()
    ).count()
    
    context = {
        'period': period,
        'stats': {
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'orders_today': orders_today,
            'total_revenue': total_revenue,
            'avg_order_value': avg_order_value,
            'new_customers': new_customers,
            'total_customers': total_customers,
            'low_stock_products': low_stock_products,
            'total_events': total_events,
            'pending_events_count': pending_events,
            'events_today': events_today,
        },
        'charts': {
            'sales': {
                'labels': json.dumps(sales_labels),
                'revenue': json.dumps(sales_revenue),
                'count': json.dumps(sales_count),
            },
            'top_products': {
                'names': json.dumps(top_products_names),
                'quantities': json.dumps(top_products_quantities),
            },
            'categories': {
                'names': json.dumps(category_names),
                'values': json.dumps(category_values),
            },
            'status': {
                'labels': json.dumps(status_labels),
                'counts': json.dumps(status_counts),
            }
        },
        'recent_orders': recent_orders,
        'alerts': alerts,
    }
    
    return render(request, 'JLTsite/dashboard_admin.html', context)

# ========================================
# 3. GESTION DES COMMANDES
# ========================================

@user_passes_test(admin_required)
def admin_orders_list(request):
    """Liste des commandes avec filtres - VERSION AMÉLIORÉE"""
    
    # Récupérer toutes les commandes
    orders = Order.objects.all().select_related('user').prefetch_related('items')
    
    # Appliquer les filtres
    status = request.GET.get('status')
    date_filter = request.GET.get('date')
    search = request.GET.get('search')
    
    if status:
        orders = orders.filter(status=status)
    
    if date_filter == 'today':
        orders = orders.filter(created_at__date=timezone.now().date())
    elif date_filter == 'week':
        orders = orders.filter(created_at__gte=timezone.now() - timedelta(days=7))
    elif date_filter == 'month':
        orders = orders.filter(created_at__gte=timezone.now() - timedelta(days=30))
    
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Ordonner par date de création (plus récent en premier)
    orders = orders.order_by('-created_at')
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(orders, 20)  # 20 commandes par page
    page = request.GET.get('page')
    orders_page = paginator.get_page(page)
    
    # Calculer les statistiques
    all_orders = Order.objects.all()
    stats = {
        'total': all_orders.count(),
        'pending': all_orders.filter(status='pending').count(),
        'confirmed': all_orders.filter(status='confirmed').count(),
        'preparing': all_orders.filter(status='preparing').count(),
        'ready': all_orders.filter(status='ready').count(),
        'delivered': all_orders.filter(status='delivered').count(),
        'cancelled': all_orders.filter(status='cancelled').count(),
    }
    
    context = {
        'orders': orders_page,
        'stats': stats,
        'current_status': status,
        'current_date': date_filter,
        'search_query': search,
    }
    
    return render(request, 'JLTsite/orders_list.html', context)
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
import json
import uuid

# ========================================
# AMÉLIORATION DE LA VUE EXISTANTE admin_order_detail
# ========================================

@user_passes_test(admin_required)
def admin_order_detail(request, order_number):
    """Détail et gestion d'une commande - VERSION COMPLÈTE"""
    order = get_object_or_404(Order, order_number=order_number)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_status':
            new_status = request.POST.get('status')
            old_status = order.status
            order.status = new_status
            
            # Mettre à jour les timestamps selon le statut
            if new_status == 'confirmed' and not order.confirmed_at:
                order.confirmed_at = timezone.now()
            elif new_status == 'delivered' and not order.delivered_at:
                order.delivered_at = timezone.now()
            
            # Ajouter à l'historique dans les notes
            log_entry = f"\n{timezone.now().strftime('%d/%m/%Y %H:%M')} - Statut changé de {old_status} à {new_status} par {request.user.username}"
            if order.admin_notes:
                order.admin_notes += log_entry
            else:
                order.admin_notes = log_entry.strip()
            
            order.save()
            
            # Envoyer un email au client
            try:
                send_order_status_email(order)
                messages.success(request, f'Statut mis à jour: {order.get_status_display()}. Email envoyé au client.')
            except:
                messages.success(request, f'Statut mis à jour: {order.get_status_display()}')
            
            return redirect('admin_order_detail', order_number=order.order_number)
            
        elif action == 'add_note':
            note = request.POST.get('admin_notes', '')
            order.admin_notes = note
            order.save()
            messages.success(request, 'Notes administrateur mises à jour')
            return redirect('admin_order_detail', order_number=order.order_number)
    
    # Récupérer les items de la commande
    order_items = order.items.all().select_related('product', 'product__category')
    
    context = {
        'order': order,
        'order_items': order_items,
    }
    
    return render(request, 'JLTsite/order_detail.html', context)


@user_passes_test(admin_required)
def admin_order_invoice(request, order_number):
    """Générer une facture PDF"""
    order = get_object_or_404(Order, order_number=order_number)
    
    # Ici vous pouvez utiliser une bibliothèque comme ReportLab ou WeasyPrint
    # Pour générer un PDF
    
    return render(request, 'JLTsite/invoice.html', {'order': order})

# ========================================
# 4. GESTION DES PRODUITS
# ========================================

@user_passes_test(admin_required)
def admin_products_list(request):
    """Liste des produits avec gestion du stock - VERSION COMPLÈTE"""
    
    products = Product.objects.all().select_related('category').order_by('-created_at')
    
    # Filtres
    category = request.GET.get('category')
    stock_filter = request.GET.get('stock')
    search = request.GET.get('search')
    
    if category:
        products = products.filter(category__slug=category)
    
    if stock_filter == 'low':
        products = products.filter(stock__lt=10, stock__gt=0)
    elif stock_filter == 'out':
        products = products.filter(stock=0)
    
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(ingredients__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(products, 12)  # 12 produits par page
    page = request.GET.get('page')
    products_page = paginator.get_page(page)
    
    # Statistiques
    all_products = Product.objects.all()
    stock_in_good = all_products.filter(stock__gte=10).count()
    stock_low = all_products.filter(stock__lt=10, stock__gt=0).count()
    stock_out = all_products.filter(stock=0).count()
    
    # Catégories pour le filtre
    categories = Category.objects.filter(is_active=True).order_by('order', 'name')
    
    context = {
        'products': products_page,
        'categories': categories,
        'current_category': category,
        'stock_filter': stock_filter,
        'search_query': search,
        'stock_in_good': stock_in_good,
        'stock_low': stock_low,
        'stock_out': stock_out,
    }
    
    return render(request, 'JLTsite/products_list.html', context)
@user_passes_test(admin_required)
@require_POST
def admin_product_update_stock(request):
    """Mise à jour rapide du stock via AJAX - VERSION AMÉLIORÉE"""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        new_stock = int(data.get('stock', 0))
        
        # Validation
        if new_stock < 0:
            return JsonResponse({
                'success': False,
                'message': 'Le stock ne peut pas être négatif'
            }, status=400)
        
        product = Product.objects.get(id=product_id)
        old_stock = product.stock
        product.stock = new_stock
        
        # Mettre à jour le statut automatiquement
        if new_stock == 0:
            product.status = 'rupture'
            status_display = 'Rupture'
        elif new_stock < 10:
            product.status = 'disponible'
            status_display = 'Stock faible'
        else:
            product.status = 'disponible'
            status_display = 'Disponible'
        
        product.save()
        
        # Log l'action
        log_message = f"Stock mis à jour de {old_stock} à {new_stock} par {request.user.username}"
        # Vous pouvez ajouter un système de logs si nécessaire
        
        return JsonResponse({
            'success': True,
            'message': f'Stock mis à jour: {new_stock} unités',
            'status': product.status,
            'status_display': status_display,
            'stock': new_stock
        })
        
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Produit introuvable'
        }, status=404)
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Valeur de stock invalide'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
# ========================================
# 5. RAPPORTS ET ANALYSES
# ========================================

from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count, Avg
from django.db.models.functions import Extract, ExtractWeekDay
from .models import Order, User, Cart, Category, OrderItem  # Import your models

@user_passes_test(admin_required)
def admin_reports(request):
    """Page des rapports et analyses"""

    # Période
    period = request.GET.get('period', 'month')

    if period == 'week':
        start_date = timezone.now() - timedelta(days=7)
    elif period == 'year':
        start_date = timezone.now() - timedelta(days=365)
    else:  # month
        start_date = timezone.now() - timedelta(days=30)

    # ========== ANALYSES DES VENTES ==========

    # Ventes par mois
    monthly_sales = Order.objects.filter(
        created_at__gte=start_date,
        status__in=['confirmed', 'preparing', 'ready', 'delivered']
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        revenue=Sum('total'),
        orders=Count('id'),
        items=Sum('items__quantity')
    ).order_by('month')

    # Top clients
    top_customers = User.objects.filter(
        role='customer',
        orders__created_at__gte=start_date
    ).annotate(
        total_spent=Sum('orders__total'),
        orders_count=Count('orders'),
        avg_order=Avg('orders__total')
    ).order_by('-total_spent')[:10]

    # Produits les plus rentables
    profitable_products = OrderItem.objects.filter(
        order__created_at__gte=start_date,
        order__status__in=['confirmed', 'preparing', 'ready', 'delivered']
    ).values(
        'product__id',
        'product__name',
        'product__category__name'
    ).annotate(
        quantity_sold=Sum('quantity'),
        revenue=Sum('subtotal'),
        orders_count=Count('order', distinct=True)
    ).order_by('-revenue')[:20]

    # Analyse des heures de commande
    orders_by_hour = Order.objects.filter(
        created_at__gte=start_date
    ).annotate(
        hour=Extract('created_at', 'hour')
    ).values('hour').annotate(
        count=Count('id')
    ).order_by('hour')

    # Analyse des jours de la semaine
    orders_by_weekday = Order.objects.filter(
        created_at__gte=start_date
    ).annotate(
        weekday=ExtractWeekDay('created_at')
    ).values('weekday').annotate(
        count=Count('id'),
        revenue=Sum('total')
    ).order_by('weekday')

    # Taux de conversion
    total_carts = Cart.objects.filter(created_at__gte=start_date).count()
    converted_carts = Order.objects.filter(created_at__gte=start_date).count()
    conversion_rate = (converted_carts / total_carts * 100) if total_carts > 0 else 0

    # Performance des catégories
    category_performance = Category.objects.filter(
        products__orderitem__order__created_at__gte=start_date
    ).annotate(
        revenue=Sum('products__orderitem__subtotal'),
        items_sold=Sum('products__orderitem__quantity'),
        orders=Count('products__orderitem__order', distinct=True)
    ).order_by('-revenue')

    context = {
        'period': period,
        'monthly_sales': monthly_sales,
        'top_customers': top_customers,
        'profitable_products': profitable_products,
        'orders_by_hour': orders_by_hour,
        'orders_by_weekday': orders_by_weekday,
        'conversion_rate': conversion_rate,
        'category_performance': category_performance,
    }

    return render(request, 'JLTsite/reports.html', context)

@user_passes_test(admin_required)
def admin_export_data(request):
    """Exporter les données en CSV/Excel - VERSION AMÉLIORÉE"""
    
    export_type = request.GET.get('type', 'orders')
    format_type = request.GET.get('format', 'csv')
    ids = request.GET.get('ids', '').split(',') if request.GET.get('ids') else None
    
    # Export des clients
    if export_type == 'customers':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="clients_{timezone.now().date()}.csv"'
        response.write('\ufeff'.encode('utf8'))  # BOM pour Excel
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Nom d\'utilisateur', 'Prénom', 'Nom', 'Email', 
            'Téléphone', 'Entreprise', 'Ville', 'Code postal',
            'Date d\'inscription', 'Nombre de commandes', 'Total dépensé',
            'Dernière commande', 'Newsletter'
        ])
        
        customers = User.objects.filter(role='customer').annotate(
            orders_count=Count('orders'),
            total_spent=Sum('orders__total'),
            last_order=Max('orders__created_at')
        )
        
        # Filtrer par IDs si spécifiés
        if ids and ids[0]:
            customers = customers.filter(id__in=ids)
        
        for customer in customers:
            writer.writerow([
                customer.id,
                customer.username,
                customer.first_name,
                customer.last_name,
                customer.email,
                customer.phone or '',
                customer.company or '',
                customer.city or '',
                customer.postal_code or '',
                customer.created_at.strftime('%d/%m/%Y'),
                customer.orders_count or 0,
                f"{customer.total_spent or 0:.2f}",
                customer.last_order.strftime('%d/%m/%Y') if customer.last_order else '',
                'Oui' if customer.newsletter else 'Non'
            ])
        
        return response
    
    # Export des commandes (déjà existant, à améliorer si nécessaire)
    elif export_type == 'orders':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="commandes_{timezone.now().date()}.csv"'
        response.write('\ufeff'.encode('utf8'))  # BOM pour Excel
        
        writer = csv.writer(response)
        writer.writerow([
            'Numéro', 'Date', 'Client', 'Email', 'Téléphone',
            'Entreprise', 'Statut', 'Type livraison', 'Date livraison',
            'Sous-total', 'Taxes', 'Livraison', 'Total'
        ])
        
        orders = Order.objects.all().select_related('user')
        
        # Filtrer par IDs si spécifiés
        if ids and ids[0]:
            orders = orders.filter(id__in=ids)
        
        # Filtrer par dates si spécifiées
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        if start_date:
            orders = orders.filter(created_at__gte=start_date)
        if end_date:
            orders = orders.filter(created_at__lte=end_date)
        
        for order in orders:
            writer.writerow([
                order.order_number,
                order.created_at.strftime('%d/%m/%Y %H:%M'),
                f"{order.first_name} {order.last_name}",
                order.email,
                order.phone,
                order.company or '',
                order.get_status_display(),
                order.get_delivery_type_display() if hasattr(order, 'get_delivery_type_display') else '',
                order.delivery_date.strftime('%d/%m/%Y') if order.delivery_date else '',
                f"{order.subtotal:.2f}",
                f"{order.tax_amount:.2f}",
                f"{order.delivery_fee:.2f}",
                f"{order.total:.2f}"
            ])
        
        return response
    
    # Export des produits
    elif export_type == 'products':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="produits_{timezone.now().date()}.csv"'
        response.write('\ufeff'.encode('utf8'))  # BOM pour Excel
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Nom', 'Catégorie', 'Prix', 'Prix promo', 
            'Stock', 'Statut', 'Ventes', 'Végétarien', 
            'Végane', 'Sans gluten', 'Actif'
        ])
        
        products = Product.objects.all().select_related('category')
        
        if ids and ids[0]:
            products = products.filter(id__in=ids)
        
        for product in products:
            writer.writerow([
                product.id,
                product.name,
                product.category.name if product.category else '',
                f"{product.price:.2f}",
                f"{product.promo_price:.2f}" if product.promo_price else '',
                product.stock,
                product.get_status_display() if hasattr(product, 'get_status_display') else product.status,
                product.sales_count,
                'Oui' if product.is_vegetarian else 'Non',
                'Oui' if product.is_vegan else 'Non',
                'Oui' if product.is_gluten_free else 'Non',
                'Oui' if product.is_active else 'Non'
            ])
        
        return response
    
    return JsonResponse({'error': 'Type d\'export non valide'}, status=400)
# ========================================
# 6. GESTION DES CLIENTS
# ========================================

from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Sum, Max, Q, Avg
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse, JsonResponse
import csv

# ========================================
# VUE AMÉLIORÉE POUR LA LISTE DES CLIENTS
# ========================================

@user_passes_test(admin_required)
def admin_customers_list(request):
    """Liste des clients avec statistiques complètes"""
    
    # Récupérer tous les clients avec leurs statistiques
    customers = User.objects.filter(role='customer').annotate(
        orders_count=Count('orders'),
        total_spent=Sum('orders__total'),
        last_order=Max('orders__created_at')
    ).order_by('-created_at')
    
    # Filtre de recherche
    search = request.GET.get('search')
    if search:
        customers = customers.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(company__icontains=search)
        )
    
    # Calculer les statistiques globales
    all_customers = User.objects.filter(role='customer')
    total_customers = all_customers.count()
    
    # Clients du mois dernier
    today = timezone.now()
    first_day_of_this_month = today.replace(day=1)
    customers_last_month = all_customers.filter(
        created_at__gte=first_day_of_this_month
    ).count()
    
    # Clients VIP (10+ commandes)
    customers_with_10_or_more_orders = all_customers.annotate(
        orders_count=Count('orders')
    ).filter(orders_count__gte=10).count()
    
    # Dépense moyenne par client
    average_spent_data = all_customers.annotate(
        total_spent=Sum('orders__total')
    ).aggregate(
        avg_spent=Avg('total_spent')
    )
    average_spent = average_spent_data['avg_spent'] or 0
    
    # Pagination
    paginator = Paginator(customers, 20)  # 20 clients par page
    page = request.GET.get('page')
    customers_page = paginator.get_page(page)
    
    context = {
        'customers': customers_page,
        'search_query': search,
        'total_customers': total_customers,
        'customers_last_month': customers_last_month,
        'customers_with_10_or_more_orders': customers_with_10_or_more_orders,
        'average_spent': average_spent,
    }
    
    return render(request, 'JLTsite/customers_list.html', context)
@user_passes_test(admin_required)
def admin_customer_detail(request, user_id):
    """Détail d'un client avec historique complet"""
    customer = get_object_or_404(User, id=user_id, role='customer')
    
    # Commandes du client
    orders = Order.objects.filter(user=customer).order_by('-created_at')
    
    # Statistiques détaillées
    stats = {
        'total_orders': orders.count(),
        'total_spent': orders.aggregate(Sum('total'))['total__sum'] or 0,
        'avg_order': orders.aggregate(Avg('total'))['total__avg'] or 0,
        'pending_orders': orders.filter(status='pending').count(),
        'delivered_orders': orders.filter(status='delivered').count(),
    }
    
    # Produits favoris (les plus commandés)
    favorite_products = OrderItem.objects.filter(
        order__user=customer
    ).values(
        'product__id',
        'product__name',
        'product__image'
    ).annotate(
        times_ordered=Count('id'),
        total_quantity=Sum('quantity')
    ).order_by('-times_ordered')[:5]
    
    # Historique des commandes par mois
    monthly_orders = orders.annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id'),
        total=Sum('total')
    ).order_by('-month')[:12]
    
    # Notes sur le client (si vous avez un champ notes)
    # customer_notes = CustomerNote.objects.filter(customer=customer).order_by('-created_at')
    
    context = {
        'customer': customer,
        'orders': orders[:10],  # 10 dernières commandes
        'stats': stats,
        'favorite_products': favorite_products,
        'monthly_orders': monthly_orders,
        # 'customer_notes': customer_notes,
    }
    
    return render(request, 'JLTsite/customer_detail.html', context)
# ========================================
# 7. NOTIFICATIONS ET EMAILS
# ========================================

def send_order_status_email(order):
    """Envoyer un email de mise à jour du statut"""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    
    subject = f'Mise à jour de votre commande {order.order_number}'
    
    context = {
        'order': order,
        'status_message': get_status_message(order.status)
    }
    
    html_message = render_to_string('JLTsite/order_status_update.html', context)
    
    send_mail(
        subject=subject,
        message=f'Votre commande {order.order_number} est maintenant: {order.get_status_display()}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.email],
        html_message=html_message,
        fail_silently=False,
    )

def get_status_message(status):
    """Messages personnalisés selon le statut"""
    messages = {
        'confirmed': 'Votre commande a été confirmée et sera préparée bientôt.',
        'preparing': 'Votre commande est en cours de préparation par notre équipe.',
        'ready': 'Votre commande est prête! Vous pouvez venir la récupérer.',
        'delivered': 'Votre commande a été livrée. Bon appétit!',
        'cancelled': 'Votre commande a été annulée. Si vous avez des questions, contactez-nous.'
    }
    return messages.get(status, '')
        

# Ajouter ces vues dans votre admin_views.py

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

# ========================================
# AJAX VIEWS FOR ORDER MANAGEMENT
# ========================================

@user_passes_test(admin_required)
@require_POST
def admin_order_update_status(request):
    """Mise à jour du statut d'une commande via AJAX"""
    try:
        data = json.loads(request.body)
        order_number = data.get('order_number')
        new_status = data.get('status')
        
        # Valider le statut
        valid_statuses = ['pending', 'confirmed', 'preparing', 'ready', 'delivered', 'cancelled']
        if new_status not in valid_statuses:
            return JsonResponse({
                'success': False,
                'message': 'Statut invalide'
            }, status=400)
        
        # Récupérer et mettre à jour la commande
        order = Order.objects.get(order_number=order_number)
        old_status = order.status
        order.status = new_status
        
        # Mettre à jour les timestamps selon le statut
        if new_status == 'confirmed' and old_status != 'confirmed':
            order.confirmed_at = timezone.now()
        elif new_status == 'delivered' and old_status != 'delivered':
            order.delivered_at = timezone.now()
        
        order.save()
        
        # Envoyer un email de notification au client
        try:
            send_order_status_email(order)
        except Exception as e:
            print(f"Erreur envoi email: {e}")
        
        # Log l'action
        log_message = f"Statut changé de {old_status} à {new_status} par {request.user.username}"
        if order.admin_notes:
            order.admin_notes += f"\n{timezone.now().strftime('%d/%m/%Y %H:%M')} - {log_message}"
        else:
            order.admin_notes = f"{timezone.now().strftime('%d/%m/%Y %H:%M')} - {log_message}"
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Statut mis à jour: {order.get_status_display()}',
            'new_status': new_status,
            'status_display': order.get_status_display()
        })
        
    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Commande introuvable'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@user_passes_test(admin_required)
@require_POST
def admin_orders_bulk_update(request):
    """Mise à jour groupée des commandes"""
    try:
        data = json.loads(request.body)
        action = data.get('action')
        order_ids = data.get('order_ids', [])
        
        if not order_ids:
            return JsonResponse({
                'success': False,
                'message': 'Aucune commande sélectionnée'
            }, status=400)
        
        # Mapping des actions vers les statuts
        action_to_status = {
            'confirm': 'confirmed',
            'prepare': 'preparing',
            'ready': 'ready',
            'deliver': 'delivered',
            'cancel': 'cancelled'
        }
        
        if action not in action_to_status:
            return JsonResponse({
                'success': False,
                'message': 'Action invalide'
            }, status=400)
        
        new_status = action_to_status[action]
        
        # Récupérer les commandes
        orders = Order.objects.filter(id__in=order_ids)
        updated_count = 0
        
        for order in orders:
            old_status = order.status
            order.status = new_status
            
            # Mettre à jour les timestamps
            if new_status == 'confirmed' and old_status != 'confirmed':
                order.confirmed_at = timezone.now()
            elif new_status == 'delivered' and old_status != 'delivered':
                order.delivered_at = timezone.now()
            
            # Ajouter une note admin
            log_message = f"Mise à jour groupée: {old_status} → {new_status} par {request.user.username}"
            if order.admin_notes:
                order.admin_notes += f"\n{timezone.now().strftime('%d/%m/%Y %H:%M')} - {log_message}"
            else:
                order.admin_notes = f"{timezone.now().strftime('%d/%m/%Y %H:%M')} - {log_message}"
            
            order.save()
            updated_count += 1
            
            # Optionnel: envoyer email pour certains statuts
            if new_status in ['confirmed', 'ready', 'delivered']:
                try:
                    send_order_status_email(order)
                except Exception as e:
                    print(f"Erreur envoi email pour commande {order.order_number}: {e}")
        
        return JsonResponse({
            'success': True,
            'message': f'{updated_count} commande(s) mise(s) à jour',
            'updated_count': updated_count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@user_passes_test(admin_required)
@require_POST
def admin_order_send_email(request):
    """Envoyer un email de mise à jour pour une commande"""
    try:
        data = json.loads(request.body)
        order_number = data.get('order_number')
        email_type = data.get('email_type', 'status_update')
        
        order = Order.objects.get(order_number=order_number)
        
        # Envoyer l'email approprié
        if email_type == 'status_update':
            send_order_status_email(order)
        elif email_type == 'invoice':
            send_order_invoice_email(order)
        else:
            send_order_status_email(order)
        
        # Log l'action
        log_message = f"Email ({email_type}) envoyé par {request.user.username}"
        if order.admin_notes:
            order.admin_notes += f"\n{timezone.now().strftime('%d/%m/%Y %H:%M')} - {log_message}"
        else:
            order.admin_notes = f"{timezone.now().strftime('%d/%m/%Y %H:%M')} - {log_message}"
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Email envoyé à {order.email}'
        })
        
    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Commande introuvable'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

def send_order_invoice_email(order):
    """Envoyer la facture par email"""
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    
    subject = f'Facture - Commande {order.order_number}'
    
    context = {
        'order': order,
        'items': order.items.all(),
        'company_info': {
            'name': 'Julien-Leblanc Traiteur',
            'address': 'Votre adresse',
            'phone': 'Votre téléphone',
            'email': settings.DEFAULT_FROM_EMAIL
        }
    }
    
    html_content = render_to_string('JLTsite/invoice.html', context)
    text_content = render_to_string('JLTsite/invoice.txt', context)
    
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()


@user_passes_test(admin_required)
@require_POST
def admin_order_duplicate(request, order_number):
    """Dupliquer une commande"""
    try:
        # Récupérer la commande originale
        original_order = get_object_or_404(Order, order_number=order_number)
        
        # Créer une nouvelle commande avec les mêmes informations
        new_order = Order.objects.create(
            user=original_order.user,
            status='pending',  # Nouvelle commande en attente
            first_name=original_order.first_name,
            last_name=original_order.last_name,
            email=original_order.email,
            phone=original_order.phone,
            company=original_order.company,
            delivery_type=original_order.delivery_type,
            delivery_address=original_order.delivery_address,
            delivery_postal_code=original_order.delivery_postal_code,
            delivery_city=original_order.delivery_city,
            delivery_date=timezone.now().date() + timedelta(days=1),  # Demain par défaut
            delivery_time=original_order.delivery_time,
            delivery_notes=original_order.delivery_notes,
            subtotal=original_order.subtotal,
            tax_rate=original_order.tax_rate,
            tax_amount=original_order.tax_amount,
            delivery_fee=original_order.delivery_fee,
            discount_amount=Decimal('0.00'),
            total=original_order.total,
            payment_method=original_order.payment_method,
            payment_status='pending',
            admin_notes=f"Dupliquée depuis la commande #{original_order.order_number}"
        )
        
        # Copier tous les items
        for item in original_order.items.all():
            OrderItem.objects.create(
                order=new_order,
                product=item.product,
                product_name=item.product_name,
                product_price=item.product_price,
                quantity=item.quantity,
                notes=item.notes,
                subtotal=item.subtotal
            )
        
        # Recalculer les totaux
        new_order.calculate_totals()
        new_order.save()
        
        # Log l'action sur la commande originale
        log_entry = f"\n{timezone.now().strftime('%d/%m/%Y %H:%M')} - Commande dupliquée vers #{new_order.order_number} par {request.user.username}"
        if original_order.admin_notes:
            original_order.admin_notes += log_entry
        else:
            original_order.admin_notes = log_entry.strip()
        original_order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Commande dupliquée avec succès: #{new_order.order_number}',
            'new_order_number': new_order.order_number,
            'new_order_url': f'/admin-dashboard/order/{new_order.order_number}/'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors de la duplication: {str(e)}'
        }, status=500)

@user_passes_test(admin_required)
@require_POST
def admin_order_cancel(request, order_number):
    """Annuler une commande"""
    try:
        order = get_object_or_404(Order, order_number=order_number)
        
        # Vérifier si la commande peut être annulée
        if order.status == 'cancelled':
            return JsonResponse({
                'success': False,
                'message': 'Cette commande est déjà annulée'
            }, status=400)
        
        if order.status == 'delivered':
            return JsonResponse({
                'success': False,
                'message': 'Impossible d\'annuler une commande déjà livrée'
            }, status=400)
        
        # Sauvegarder l'ancien statut
        old_status = order.status
        
        # Annuler la commande
        order.status = 'cancelled'
        order.payment_status = 'cancelled' if order.payment_status != 'refunded' else order.payment_status
        
        # Restaurer le stock si nécessaire
        for item in order.items.all():
            if item.product:
                item.product.stock += item.quantity
                item.product.sales_count -= item.quantity
                item.product.save()
        
        # Ajouter une note
        log_entry = f"\n{timezone.now().strftime('%d/%m/%Y %H:%M')} - Commande annulée (était: {old_status}) par {request.user.username}"
        if order.admin_notes:
            order.admin_notes += log_entry
        else:
            order.admin_notes = log_entry.strip()
        
        order.save()
        
        # Envoyer un email au client
        try:
            send_order_cancellation_email(order)
            email_sent = True
        except:
            email_sent = False
        
        return JsonResponse({
            'success': True,
            'message': 'Commande annulée avec succès' + (' et email envoyé' if email_sent else ''),
            'new_status': 'cancelled'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors de l\'annulation: {str(e)}'
        }, status=500)

def send_order_cancellation_email(order):
    """Envoyer un email d'annulation au client"""
    from django.core.mail import EmailMultiAlternatives
    from django.template.loader import render_to_string
    
    subject = f'Annulation de votre commande #{order.order_number}'
    
    context = {
        'order': order,
        'first_name': order.first_name,
    }
    
    # Template HTML
    html_template = '''
    <h2>Bonjour {{ first_name }},</h2>
    <p>Nous vous confirmons que votre commande <strong>#{{ order.order_number }}</strong> a été annulée.</p>
    
    <h3>Détails de la commande annulée:</h3>
    <ul>
        <li>Numéro: #{{ order.order_number }}</li>
        <li>Date: {{ order.created_at|date:"d/m/Y" }}</li>
        <li>Montant: ${{ order.total|floatformat:2 }}</li>
    </ul>
    
    {% if order.payment_status == 'paid' %}
    <p><strong>Remboursement:</strong> Votre paiement sera remboursé dans les 5-7 jours ouvrables.</p>
    {% endif %}
    
    <p>Si vous avez des questions, n'hésitez pas à nous contacter.</p>
    
    <p>Cordialement,<br>
    L'équipe Julien-Leblanc Traiteur</p>
    '''
    
    from django.template import Template, Context
    template = Template(html_template)
    html_content = template.render(Context(context))
    
    # Version texte
    text_content = f'''
    Bonjour {order.first_name},
    
    Votre commande #{order.order_number} a été annulée.
    
    Si vous avez des questions, contactez-nous.
    
    Cordialement,
    L'équipe Julien-Leblanc Traiteur
    '''
    
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send()


@user_passes_test(admin_required)
@require_POST
def admin_send_customer_email(request):
    """Envoyer un email à un client"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        email_type = data.get('type', 'promotional')
        
        # Créer le contenu de l'email selon le type
        if email_type == 'promotional':
            subject = 'Offres spéciales chez Julien-Leblanc Traiteur'
            message = 'Découvrez nos nouvelles offres...'
        elif email_type == 'newsletter':
            subject = 'Newsletter - Julien-Leblanc Traiteur'
            message = 'Les dernières nouvelles...'
        else:
            subject = 'Message de Julien-Leblanc Traiteur'
            message = data.get('message', '')
        
        # Envoyer l'email
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        
        return JsonResponse({'success': True, 'message': 'Email envoyé avec succès'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@user_passes_test(admin_required)
@require_POST
def admin_send_bulk_email(request):
    """Envoyer un email groupé aux clients"""
    try:
        data = json.loads(request.body)
        emails = data.get('emails', [])
        email_type = data.get('type', 'newsletter')
        
        if not emails:
            return JsonResponse({'success': False, 'message': 'Aucun destinataire'}, status=400)
        
        # Créer le contenu
        subject = 'Newsletter - Julien-Leblanc Traiteur'
        message = 'Découvrez nos dernières nouveautés...'
        
        # Envoyer en BCC pour respecter la confidentialité
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.DEFAULT_FROM_EMAIL],  # To: nous-mêmes
            bcc=emails,  # BCC: les clients
            fail_silently=False,
        )
        
        return JsonResponse({
            'success': True, 
            'message': f'Email envoyé à {len(emails)} destinataires'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Count, Prefetch
from django.utils import timezone
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta, date
from decimal import Decimal
import json
import calendar

from .models import (
    User, Product, Order, OrderItem, Category, Cart, CartItem
)
from .forms import CheckoutForm

def admin_required(user):
    """Vérifier si l'utilisateur est admin ou staff"""
    return user.is_authenticated and user.role in ['admin', 'staff']

# ========================================
# 1. CRÉATION DE COMMANDE MANUELLE
# ========================================

@user_passes_test(admin_required)
def admin_create_manual_order(request):
    """Créer une commande manuellement (téléphone/sur place)"""
    
    # Récupérer tous les produits actifs organisés par catégorie
    categories = Category.objects.filter(is_active=True).prefetch_related(
        Prefetch('products', queryset=Product.objects.filter(is_active=True, stock__gt=0))
    ).order_by('order', 'name')
    
    # Récupérer les clients existants pour l'autocomplétion
    customers = User.objects.filter(role='customer').order_by('last_name', 'first_name')
    
    if request.method == 'POST':
        try:
            # Déterminer si c'est pour un client existant ou nouveau
            customer_type = request.POST.get('customer_type')
            
            if customer_type == 'existing':
                # Client existant
                customer_id = request.POST.get('customer_id')
                customer = get_object_or_404(User, id=customer_id, role='customer')
                
                # Utiliser les infos du client
                first_name = customer.first_name
                last_name = customer.last_name
                email = customer.email
                phone = customer.phone or request.POST.get('phone')
                company = customer.company or request.POST.get('company', '')
                
            else:
                # Nouveau client ou commande anonyme
                first_name = request.POST.get('first_name')
                last_name = request.POST.get('last_name')
                email = request.POST.get('email')
                phone = request.POST.get('phone')
                company = request.POST.get('company', '')
                
                # Créer un compte client si demandé
                create_account = request.POST.get('create_account') == 'on'
                if create_account and email:
                    # Vérifier si le client existe déjà
                    existing_customer = User.objects.filter(email=email).first()
                    if existing_customer:
                        customer = existing_customer
                    else:
                        # Créer un nouveau client
                        username = email.split('@')[0] + '_' + str(timezone.now().timestamp())[:5]
                        customer = User.objects.create(
                            username=username,
                            email=email,
                            first_name=first_name,
                            last_name=last_name,
                            phone=phone,
                            company=company,
                            role='customer',
                            # Mot de passe temporaire - envoyer par email
                            password='temp_' + str(timezone.now().timestamp())[:8]
                        )
                else:
                    customer = None
            
            # Créer la commande
            order = Order.objects.create(
                user=customer,
                status='confirmed',  # Commandes manuelles sont automatiquement confirmées
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                company=company,
                delivery_type=request.POST.get('delivery_type', 'pickup'),
                delivery_address=request.POST.get('delivery_address', ''),
                delivery_postal_code=request.POST.get('delivery_postal_code', ''),
                delivery_city=request.POST.get('delivery_city', 'Montréal'),
                delivery_date=request.POST.get('delivery_date'),
                delivery_time=request.POST.get('delivery_time'),
                delivery_notes=request.POST.get('delivery_notes', ''),
                subtotal=Decimal('0.00'),
                tax_rate=Decimal('14.975'),
                tax_amount=Decimal('0.00'),
                delivery_fee=Decimal('0.00'),
                total=Decimal('0.00'),
                payment_method=request.POST.get('payment_method', 'cash'),
                payment_status='pending',
                admin_notes=f"Commande créée manuellement par {request.user.username} le {timezone.now().strftime('%d/%m/%Y %H:%M')}",
                # Nouveau champ pour identifier la source
                order_source='manual'  # À ajouter dans le modèle
            )
            
            # Traiter les produits sélectionnés
            products_data = json.loads(request.POST.get('products_data', '[]'))
            subtotal = Decimal('0.00')
            
            for item_data in products_data:
                product = Product.objects.get(id=item_data['product_id'])
                quantity = int(item_data['quantity'])
                notes = item_data.get('notes', '')
                
                # Créer l'article de commande
                order_item = OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    product_price=product.get_price(),
                    quantity=quantity,
                    notes=notes,
                    subtotal=product.get_price() * quantity,
                    # Nouveau champ pour le département
                    department=get_product_department(product)  # Fonction à créer
                )
                
                subtotal += order_item.subtotal
                
                # Mettre à jour le stock
                product.stock -= quantity
                product.sales_count += quantity
                product.save()
            
            # Calculer les totaux
            order.subtotal = subtotal
            order.tax_amount = subtotal * (order.tax_rate / 100)
            
            # Frais de livraison
            if order.delivery_type == 'delivery':
                order.delivery_fee = Decimal('5.00') if subtotal < 50 else Decimal('0.00')
            
            order.total = order.subtotal + order.tax_amount + order.delivery_fee
            order.save()
            
            # Marquer comme payée si paiement immédiat
            if request.POST.get('mark_as_paid') == 'on':
                order.payment_status = 'paid'
                order.save()
            
            messages.success(request, f'Commande #{order.order_number} créée avec succès!')
            
            # Rediriger selon l'action
            if request.POST.get('action') == 'save_and_new':
                return redirect('admin_create_manual_order')
            else:
                return redirect('admin_order_detail', order_number=order.order_number)
                
        except Exception as e:
            messages.error(request, f'Erreur lors de la création: {str(e)}')
    
    context = {
        'categories': categories,
        'customers': customers,
        'delivery_dates': get_available_delivery_dates(),  # Fonction helper
        'delivery_times': get_delivery_time_slots(),  # Fonction helper
    }
    
    return render(request, 'JLTsite/admin_manual_order.html', context)

@user_passes_test(admin_required)
def admin_create_order_for_customer(request, customer_id):
    """Créer une commande en se faisant passer pour un client"""
    customer = get_object_or_404(User, id=customer_id, role='customer')
    
    # Récupérer ou créer le panier du client
    cart, created = Cart.objects.get_or_create(user=customer)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_to_cart':
            # Ajouter des produits au panier du client
            product_id = request.POST.get('product_id')
            quantity = int(request.POST.get('quantity', 1))
            
            product = get_object_or_404(Product, id=product_id)
            
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            
            messages.success(request, f'{product.name} ajouté au panier de {customer.get_full_name()}')
            
        elif action == 'checkout':
            # Procéder à la commande
            return redirect('admin_checkout_for_customer', customer_id=customer.id)
    
    # Récupérer les produits
    categories = Category.objects.filter(is_active=True).prefetch_related(
        Prefetch('products', queryset=Product.objects.filter(is_active=True))
    )
    
    context = {
        'customer': customer,
        'cart': cart,
        'categories': categories,
        'cart_total': cart.get_total() if cart else 0,
    }
    
    return render(request, 'JLTsite/admin_order_for_customer.html', context)

# ========================================
# 2. CALENDRIER DES COMMANDES
# ========================================

@user_passes_test(admin_required)
def admin_orders_calendar(request):
    """Vue calendrier des commandes"""
    
    # Récupérer le mois et l'année depuis les paramètres
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    
    # Créer le calendrier
    cal = calendar.monthcalendar(year, month)
    
    # Récupérer toutes les commandes du mois
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    
    orders = Order.objects.filter(
        delivery_date__gte=start_date,
        delivery_date__lte=end_date
    ).values('delivery_date').annotate(
        total_orders=Count('id'),
        confirmed_orders=Count('id', filter=Q(status='confirmed')),
        pending_orders=Count('id', filter=Q(status='pending')),
        total_revenue=Sum('total', filter=Q(status__in=['confirmed', 'delivered']))
    )
    
    # Créer un dictionnaire pour accès rapide
    orders_by_date = {
        order['delivery_date']: order for order in orders
    }
    
    # Construire les données du calendrier
    calendar_data = []
    for week in cal:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
            else:
                current_date = date(year, month, day)
                day_data = {
                    'day': day,
                    'date': current_date,
                    'is_today': current_date == timezone.now().date(),
                    'is_past': current_date < timezone.now().date(),
                    'orders': orders_by_date.get(current_date, {
                        'total_orders': 0,
                        'confirmed_orders': 0,
                        'pending_orders': 0,
                        'total_revenue': 0
                    })
                }
                week_data.append(day_data)
        calendar_data.append(week_data)
    
    # Navigation
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    context = {
        'calendar_data': calendar_data,
        'current_month': month,
        'current_year': year,
        'month_name': calendar.month_name[month],
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'weekdays': ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'],
    }
    
    return render(request, 'JLTsite/admin_orders_calendar.html', context)

@user_passes_test(admin_required)
def admin_orders_by_date(request, date_str):
    """Afficher les commandes d'une date spécifique"""
    
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, 'Date invalide')
        return redirect('admin_orders_calendar')
    
    # Récupérer les commandes de cette date
    orders = Order.objects.filter(delivery_date=selected_date).select_related('user').prefetch_related('items__product')
    
    # Séparer par source et statut
    online_orders = orders.filter(order_source='online')
    manual_orders = orders.filter(order_source='manual')
    
    # Statistiques du jour
    stats = {
        'total_orders': orders.count(),
        'online_orders': online_orders.count(),
        'manual_orders': manual_orders.count(),
        'pending': orders.filter(status='pending').count(),
        'confirmed': orders.filter(status='confirmed').count(),
        'total_revenue': orders.filter(
            status__in=['confirmed', 'preparing', 'ready', 'delivered']
        ).aggregate(Sum('total'))['total__sum'] or 0,
        'pickup_orders': orders.filter(delivery_type='pickup').count(),
        'delivery_orders': orders.filter(delivery_type='delivery').count(),
    }
    
    context = {
        'selected_date': selected_date,
        'orders': orders,
        'online_orders': online_orders,
        'manual_orders': manual_orders,
        'stats': stats,
    }
    
    return render(request, 'JLTsite/admin_orders_by_date.html', context)

# ========================================
# 3. DISPATCH CUISINE (IMPRESSION)
# ========================================

@user_passes_test(admin_required)
def admin_kitchen_dispatch(request):
    """Vue pour le dispatch en cuisine"""
    
    # Date pour le dispatch (par défaut demain)
    dispatch_date = request.GET.get('date')
    if dispatch_date:
        dispatch_date = datetime.strptime(dispatch_date, '%Y-%m-%d').date()
    else:
        dispatch_date = timezone.now().date() + timedelta(days=1)
    
    # Récupérer toutes les commandes confirmées pour cette date
    orders = Order.objects.filter(
        delivery_date=dispatch_date,
        status__in=['confirmed', 'preparing']
    ).prefetch_related('items__product__category')
    
    # Définir les départements
    DEPARTMENTS = {
        'patisserie': {'name': 'Pâtisserie', 'categories': ['desserts', 'patisseries'], 'items': []},
        'chaud': {'name': 'Cuisine Chaude', 'categories': ['plats-chauds', 'soupes'], 'items': []},
        'sandwichs': {'name': 'Sandwichs', 'categories': ['sandwichs', 'wraps'], 'items': []},
        'boites': {'name': 'Boîtes à lunch', 'categories': ['boites-lunch'], 'items': []},
        'salades': {'name': 'Salades', 'categories': ['salades'], 'items': []},
        'dejeuners': {'name': 'Déjeuners', 'categories': ['dejeuners', 'brunchs'], 'items': []},
        'bouchees': {'name': 'Bouchées', 'categories': ['bouchees', 'canapes'], 'items': []},
    }
    
    # Organiser les items par département
    for order in orders:
        for item in order.items.all():
            dept = get_item_department(item)
            if dept in DEPARTMENTS:
                DEPARTMENTS[dept]['items'].append({
                    'order_number': order.order_number,
                    'customer': f"{order.first_name} {order.last_name}",
                    'delivery_time': order.delivery_time,
                    'product': item.product_name,
                    'quantity': item.quantity,
                    'notes': item.notes,
                    'allergens': item.product.allergens if item.product else '',
                })
    
    # Trier les items par heure de livraison
    for dept in DEPARTMENTS.values():
        dept['items'].sort(key=lambda x: x['delivery_time'])
        
        # Calculer les totaux par produit
        product_totals = {}
        for item in dept['items']:
            key = item['product']
            if key not in product_totals:
                product_totals[key] = 0
            product_totals[key] += item['quantity']
        dept['product_totals'] = product_totals
    
    context = {
        'dispatch_date': dispatch_date,
        'departments': DEPARTMENTS,
        'total_orders': orders.count(),
        'print_time': timezone.now(),
    }
    
    # Si demande d'impression
    if request.GET.get('print') == '1':
        return render(request, 'JLTsite/admin_kitchen_dispatch_print.html', context)
    
    return render(request, 'JLTsite/admin_kitchen_dispatch.html', context)

@user_passes_test(admin_required)
def admin_print_department_list(request, department):
    """Imprimer la liste pour un département spécifique"""
    
    dispatch_date = request.GET.get('date', timezone.now().date() + timedelta(days=1))
    if isinstance(dispatch_date, str):
        dispatch_date = datetime.strptime(dispatch_date, '%Y-%m-%d').date()
    
    # Récupérer les commandes
    orders = Order.objects.filter(
        delivery_date=dispatch_date,
        status__in=['confirmed', 'preparing']
    ).prefetch_related('items__product__category')
    
    # Filtrer par département
    department_items = []
    department_name = ''
    
    # Mapping des départements
    dept_mapping = {
        'patisserie': {'name': 'Pâtisserie', 'categories': ['desserts', 'patisseries']},
        'chaud': {'name': 'Cuisine Chaude', 'categories': ['plats-chauds', 'soupes']},
        'sandwichs': {'name': 'Sandwichs', 'categories': ['sandwichs', 'wraps']},
        'boites': {'name': 'Boîtes à lunch', 'categories': ['boites-lunch']},
        'salades': {'name': 'Salades', 'categories': ['salades']},
        'dejeuners': {'name': 'Déjeuners', 'categories': ['dejeuners', 'brunchs']},
        'bouchees': {'name': 'Bouchées', 'categories': ['bouchees', 'canapes']},
    }
    
    if department in dept_mapping:
        department_name = dept_mapping[department]['name']
        categories = dept_mapping[department]['categories']
        
        for order in orders:
            for item in order.items.all():
                if item.product and item.product.category.slug in categories:
                    department_items.append({
                        'order_number': order.order_number,
                        'customer': f"{order.first_name} {order.last_name}",
                        'delivery_time': order.delivery_time,
                        'delivery_type': order.get_delivery_type_display(),
                        'product': item.product_name,
                        'quantity': item.quantity,
                        'notes': item.notes,
                        'ingredients': item.product.ingredients if item.product else '',
                    })
    
    # Trier par heure
    department_items.sort(key=lambda x: x['delivery_time'])
    
    # Calculer les totaux
    product_totals = {}
    for item in department_items:
        if item['product'] not in product_totals:
            product_totals[item['product']] = {'quantity': 0, 'orders': []}
        product_totals[item['product']]['quantity'] += item['quantity']
        product_totals[item['product']]['orders'].append(item['order_number'])
    
    context = {
        'department': department,
        'department_name': department_name,
        'dispatch_date': dispatch_date,
        'items': department_items,
        'product_totals': product_totals,
        'print_time': timezone.now(),
    }
    
    response = render(request, 'JLTsite/admin_department_print.html', context)
    response['Content-Type'] = 'text/html; charset=utf-8'
    
    return response

# ========================================
# 4. FONCTIONS HELPERS
# ========================================

def get_product_department(product):
    """Déterminer le département d'un produit selon sa catégorie"""
    if not product.category:
        return 'autres'
    
    category_slug = product.category.slug.lower()
    
    # Mapping des catégories vers les départements
    dept_mapping = {
        'patisserie': ['desserts', 'patisseries', 'gateaux'],
        'chaud': ['plats-chauds', 'soupes', 'plats-principaux'],
        'sandwichs': ['sandwichs', 'wraps', 'paninis'],
        'boites': ['boites-lunch', 'lunch-box'],
        'salades': ['salades', 'salades-repas'],
        'dejeuners': ['dejeuners', 'brunchs', 'petits-dejeuners'],
        'bouchees': ['bouchees', 'canapes', 'hors-doeuvres'],
    }
    
    for dept, categories in dept_mapping.items():
        if category_slug in categories:
            return dept
    
    return 'autres'

def get_item_department(order_item):
    """Déterminer le département d'un article de commande"""
    if order_item.product:
        return get_product_department(order_item.product)
    return 'autres'

def get_available_delivery_dates():
    """Retourner les dates de livraison disponibles (7 prochains jours)"""
    dates = []
    start = timezone.now().date() + timedelta(days=1)  # Commencer demain
    
    for i in range(7):
        current_date = start + timedelta(days=i)
        # Exclure les dimanches
        if current_date.weekday() != 6:
            dates.append({
                'date': current_date,
                'display': current_date.strftime('%A %d %B'),
                'value': current_date.strftime('%Y-%m-%d')
            })
    
    return dates

def get_delivery_time_slots():
    """Retourner les créneaux horaires disponibles"""
    slots = []
    start_hour = 8
    end_hour = 18
    
    for hour in range(start_hour, end_hour):
        slots.append({
            'value': f"{hour:02d}:00",
            'display': f"{hour:02d}h00 - {hour+1:02d}h00"
        })
        slots.append({
            'value': f"{hour:02d}:30",
            'display': f"{hour:02d}h30 - {hour+1:02d}h30"
        })
    
    return slots

# ========================================
# 5. API ENDPOINTS AJAX
# ========================================

@user_passes_test(admin_required)
@require_POST
def admin_quick_order_status(request):
    """Changement rapide du statut depuis le calendrier"""
    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
        new_status = data.get('status')
        
        order = Order.objects.get(id=order_id)
        order.status = new_status
        
        if new_status == 'confirmed':
            order.confirmed_at = timezone.now()
        
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Commande {order.order_number} mise à jour'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@user_passes_test(admin_required)
def admin_get_customer_info(request):
    """Récupérer les infos d'un client pour pré-remplir le formulaire"""
    customer_id = request.GET.get('customer_id')
    
    try:
        customer = User.objects.get(id=customer_id, role='customer')
        
        return JsonResponse({
            'success': True,
            'data': {
                'first_name': customer.first_name,
                'last_name': customer.last_name,
                'email': customer.email,
                'phone': customer.phone,
                'company': customer.company,
                'address': customer.address,
                'postal_code': customer.postal_code,
                'city': customer.city,
            }
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Client introuvable'
        }, status=404)
    
# Ajouter dans admin_views.py

@user_passes_test(admin_required)
def admin_create_event_from_order(request, order_number):
    """Créer un événement à partir d'une commande"""
    order = get_object_or_404(Order, order_number=order_number)
    
    # Vérifier qu'il n'y a pas déjà un événement pour cette commande
    if hasattr(order, 'event_contract'):
        messages.warning(request, 'Un événement existe déjà pour cette commande')
        return redirect('admin_order_detail', order_number=order.order_number)
    
    # Récupérer tous les maîtres d'hôtel disponibles
    maitre_hotels = User.objects.filter(role='maitre_hotel', is_active=True).order_by('first_name', 'last_name')
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            event_name = request.POST.get('event_name')
            event_description = request.POST.get('event_description', '')
            maitre_hotel_id = request.POST.get('maitre_hotel')
            priority = request.POST.get('priority', 'normal')
            
            # Dates et heures
            setup_start = request.POST.get('setup_start_time')
            event_start = request.POST.get('event_start_time')
            event_end = request.POST.get('event_end_time')
            cleanup_end = request.POST.get('cleanup_end_time')
            
            # Lieu
            venue_name = request.POST.get('venue_name', '')
            venue_contact = request.POST.get('venue_contact', '')
            venue_phone = request.POST.get('venue_phone', '')
            venue_instructions = request.POST.get('venue_instructions', '')
            
            # Équipements et exigences
            equipment_needed = request.POST.get('equipment_needed', '')
            special_requirements = request.POST.get('special_requirements', '')
            
            # Valider que le maître d'hôtel existe
            maitre_hotel = None
            if maitre_hotel_id:
                maitre_hotel = get_object_or_404(User, id=maitre_hotel_id, role='maitre_hotel')
            
            # Créer l'événement
            event_contract = EventContract.objects.create(
                order=order,
                maitre_hotel=maitre_hotel,
                event_name=event_name,
                event_description=event_description,
                priority=priority,
                status='confirmed',  # Les événements créés depuis les ventes sont confirmés
                
                # Dates (parser les strings en datetime)
                setup_start_time=datetime.strptime(setup_start, '%Y-%m-%dT%H:%M'),
                event_start_time=datetime.strptime(event_start, '%Y-%m-%dT%H:%M'),
                event_end_time=datetime.strptime(event_end, '%Y-%m-%dT%H:%M'),
                cleanup_end_time=datetime.strptime(cleanup_end, '%Y-%m-%dT%H:%M'),
                
                # Lieu
                venue_name=venue_name,
                venue_contact=venue_contact,
                venue_phone=venue_phone,
                venue_instructions=venue_instructions,
                
                # Équipements
                equipment_needed=equipment_needed,
                special_requirements=special_requirements,
                
                # Métadonnées
                created_by=request.user,
                is_validated=True  # Validé automatiquement par les ventes
            )
            
            # Ajouter une entrée initiale à la timeline
            EventTimeline.objects.create(
                event=event_contract,
                timestamp=timezone.now(),
                action_type='other',
                description=f'Événement créé par {request.user.get_full_name()} depuis la commande #{order.order_number}',
                created_by=request.user
            )
            
            # Assigner le personnel si spécifié
            staff_members = request.POST.getlist('staff_members')
            for staff_id in staff_members:
                if staff_id:
                    staff_member = User.objects.get(id=staff_id, role='staff')
                    EventStaffAssignment.objects.create(
                        event=event_contract,
                        staff_member=staff_member,
                        role=request.POST.get(f'staff_role_{staff_id}', 'assistant'),
                        arrival_time=event_contract.setup_start_time,
                        departure_time=event_contract.cleanup_end_time,
                        hourly_rate=Decimal(request.POST.get(f'staff_rate_{staff_id}', '20.00'))
                    )
            
            # Créer une notification pour le maître d'hôtel assigné
            if maitre_hotel:
                EventNotifications.objects.create(
                    recipient=maitre_hotel,
                    event=event_contract,
                    type='new_event',
                    title='Nouvel événement assigné',
                    message=f'L\'événement "{event_name}" vous a été assigné pour le {event_contract.event_start_time.strftime("%d/%m/%Y à %H:%M")}',
                    is_urgent=priority == 'urgent'
                )
            
            # Créer une notification pour l'admin
            admin_users = User.objects.filter(role='admin')
            for admin_user in admin_users:
                EventNotifications.objects.create(
                    recipient=admin_user,
                    event=event_contract,
                    type='new_event',
                    title='Nouvel événement créé',
                    message=f'Événement "{event_name}" créé par {request.user.get_full_name()}' + 
                           (f' et assigné à {maitre_hotel.get_full_name()}' if maitre_hotel else ''),
                    is_urgent=False
                )
            
            messages.success(request, f'Événement "{event_name}" créé avec succès!' + 
                           (f' Assigné à {maitre_hotel.get_full_name()}.' if maitre_hotel else ''))
            
            return redirect('admin_order_detail', order_number=order.order_number)
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la création: {str(e)}')
    
    # Récupérer le personnel disponible
    staff_members = User.objects.filter(role='staff', is_active=True).order_by('first_name', 'last_name')
    
    # Données par défaut basées sur la commande
    default_data = {
        'event_name': f'Événement pour {order.first_name} {order.last_name}',
        'event_start_time': order.delivery_date.strftime('%Y-%m-%d') + 'T' + order.delivery_time.strftime('%H:%M'),
        'venue_address': order.delivery_address + ', ' + order.delivery_postal_code + ' ' + order.delivery_city,
    }
    
    context = {
        'order': order,
        'maitre_hotels': maitre_hotels,
        'staff_members': staff_members,
        'default_data': default_data,
    }
    
    return render(request, 'JLTsite/admin_create_event.html', context)

@user_passes_test(admin_required)
def admin_events_list(request):
    """Liste des événements pour les ventes/admin"""
    
    # Filtres
    status = request.GET.get('status')
    maitre_hotel_id = request.GET.get('maitre_hotel')
    date_filter = request.GET.get('date')
    search = request.GET.get('search')
    
    # Base queryset
    events = EventContract.objects.all().select_related(
        'order', 'maitre_hotel', 'created_by'
    ).prefetch_related('staff_assignments')
    
    # Appliquer les filtres
    if status:
        events = events.filter(status=status)
    
    if maitre_hotel_id:
        events = events.filter(maitre_hotel_id=maitre_hotel_id)
    
    if date_filter == 'today':
        events = events.filter(event_start_time__date=timezone.now().date())
    elif date_filter == 'week':
        events = events.filter(
            event_start_time__date__gte=timezone.now().date(),
            event_start_time__date__lte=timezone.now().date() + timedelta(days=7)
        )
    elif date_filter == 'month':
        events = events.filter(
            event_start_time__date__gte=timezone.now().date(),
            event_start_time__date__lte=timezone.now().date() + timedelta(days=30)
        )
    
    if search:
        events = events.filter(
            Q(event_name__icontains=search) |
            Q(contract_number__icontains=search) |
            Q(order__order_number__icontains=search) |
            Q(order__first_name__icontains=search) |
            Q(order__last_name__icontains=search)
        )
    
    # Ordonner par date d'événement
    events = events.order_by('event_start_time')
    
    # Pagination
    paginator = Paginator(events, 20)
    page = request.GET.get('page')
    events_page = paginator.get_page(page)
    
    # Statistiques
    all_events = EventContract.objects.all()
    stats = {
        'total': all_events.count(),
        'draft': all_events.filter(status='draft').count(),
        'confirmed': all_events.filter(status='confirmed').count(),
        'in_progress': all_events.filter(status='in_progress').count(),
        'completed': all_events.filter(status='completed').count(),
        'today': all_events.filter(event_start_time__date=timezone.now().date()).count(),
    }
    
    # Maîtres d'hôtel pour le filtre
    maitre_hotels = User.objects.filter(role='maitre_hotel', is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'events': events_page,
        'stats': stats,
        'maitre_hotels': maitre_hotels,
        'current_status': status,
        'current_maitre_hotel': maitre_hotel_id,
        'current_date': date_filter,
        'search_query': search,
    }
    
    return render(request, 'JLTsite/admin_events_list.html', context)

@user_passes_test(admin_required)
def admin_event_detail(request, contract_id):
    """Détail d'un événement pour les ventes/admin"""
    event = get_object_or_404(EventContract, id=contract_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'assign_maitre_hotel':
            maitre_hotel_id = request.POST.get('maitre_hotel_id')
            if maitre_hotel_id:
                maitre_hotel = get_object_or_404(User, id=maitre_hotel_id, role='maitre_hotel')
                old_maitre_hotel = event.maitre_hotel
                event.maitre_hotel = maitre_hotel
                event.save()
                
                # Créer notification pour le nouveau maître d'hôtel
                EventNotifications.objects.create(
                    recipient=maitre_hotel,
                    event=event,
                    type='event_updated',
                    title='Événement assigné',
                    message=f'L\'événement "{event.event_name}" vous a été assigné',
                    is_urgent=event.priority == 'urgent'
                )
                
                # Timeline
                EventTimeline.objects.create(
                    event=event,
                    timestamp=timezone.now(),
                    action_type='other',
                    description=f'Maître d\'hôtel changé: {old_maitre_hotel.get_full_name() if old_maitre_hotel else "Aucun"} → {maitre_hotel.get_full_name()}',
                    created_by=request.user
                )
                
                messages.success(request, f'Événement assigné à {maitre_hotel.get_full_name()}')
            
        elif action == 'update_priority':
            new_priority = request.POST.get('priority')
            old_priority = event.priority
            event.priority = new_priority
            event.save()
            
            # Timeline
            EventTimeline.objects.create(
                event=event,
                timestamp=timezone.now(),
                action_type='other',
                description=f'Priorité changée: {old_priority} → {new_priority}',
                created_by=request.user
            )
            
            messages.success(request, 'Priorité mise à jour')
        
        elif action == 'add_staff':
            staff_id = request.POST.get('staff_id')
            role = request.POST.get('role', 'assistant')
            hourly_rate = request.POST.get('hourly_rate', '20.00')
            
            if staff_id:
                staff_member = get_object_or_404(User, id=staff_id, role='staff')
                
                # Vérifier que cette personne n'est pas déjà assignée
                if not event.staff_assignments.filter(staff_member=staff_member).exists():
                    EventStaffAssignment.objects.create(
                        event=event,
                        staff_member=staff_member,
                        role=role,
                        arrival_time=event.setup_start_time,
                        departure_time=event.cleanup_end_time,
                        hourly_rate=Decimal(hourly_rate)
                    )
                    
                    messages.success(request, f'{staff_member.get_full_name()} ajouté à l\'équipe')
                else:
                    messages.warning(request, 'Cette personne est déjà assignée à l\'événement')
        
        return redirect('admin_event_detail', contract_id=event.id)
    
    # Récupérer les données pour l'affichage
    timeline = event.timeline.all().order_by('-timestamp')[:20]
    photos = event.photos.all().order_by('-taken_at')[:10]
    staff_assignments = event.staff_assignments.all().select_related('staff_member')
    
    # Maîtres d'hôtel disponibles
    maitre_hotels = User.objects.filter(role='maitre_hotel', is_active=True).order_by('first_name', 'last_name')
    
    # Personnel disponible (non déjà assigné)
    assigned_staff_ids = staff_assignments.values_list('staff_member_id', flat=True)
    available_staff = User.objects.filter(
        role='staff', 
        is_active=True
    ).exclude(id__in=assigned_staff_ids).order_by('first_name', 'last_name')
    
    context = {
        'event': event,
        'timeline': timeline,
        'photos': photos,
        'staff_assignments': staff_assignments,
        'maitre_hotels': maitre_hotels,
        'available_staff': available_staff,
        'can_edit': True,  # Les ventes peuvent toujours éditer
    }
    
    return render(request, 'JLTsite/admin_event_detail.html', context)

@user_passes_test(admin_required)
@require_POST
def admin_change_event_status(request):
    """Changer le statut d'un événement via AJAX"""
    try:
        data = json.loads(request.body)
        event_id = data.get('event_id')
        new_status = data.get('status')
        
        # Valider le statut
        valid_statuses = ['draft', 'confirmed', 'in_progress', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            return JsonResponse({
                'success': False,
                'message': 'Statut invalide'
            }, status=400)
        
        # Import dynamique pour éviter les erreurs circulaires
        from .models import EventContract, EventTimeline, EventNotifications
        
        event = get_object_or_404(EventContract, id=event_id)
        old_status = event.status
        event.status = new_status
        event.save()
        
        # Ajouter à la timeline
        EventTimeline.objects.create(
            event=event,
            timestamp=timezone.now(),
            action_type='other',
            description=f'Statut changé de {old_status} à {new_status} par {request.user.get_full_name()}',
            created_by=request.user
        )
        
        # Notifier le maître d'hôtel si assigné
        if event.maitre_hotel and new_status in ['in_progress', 'completed']:
            EventNotifications.objects.create(
                recipient=event.maitre_hotel,
                event=event,
                type='event_updated',
                title=f'Événement {new_status}',
                message=f'L\'événement "{event.event_name}" est maintenant: {dict(event.STATUS_CHOICES).get(new_status, new_status)}',
                is_urgent=False
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Statut mis à jour: {dict(event.STATUS_CHOICES).get(new_status, new_status)}',
            'new_status': new_status
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

# Aussi ajouter la vue pour l'assignation rapide
@user_passes_test(admin_required)
@require_POST
def admin_quick_assign_maitre_hotel(request):
    """Assignation rapide d'un maître d'hôtel via AJAX"""
    try:
        data = json.loads(request.body)
        event_id = data.get('event_id')
        maitre_hotel_id = data.get('maitre_hotel_id')
        
        # Import dynamique
        from .models import EventContract, EventTimeline, EventNotifications
        
        event = get_object_or_404(EventContract, id=event_id)
        
        if maitre_hotel_id:
            maitre_hotel = get_object_or_404(User, id=maitre_hotel_id, role='maitre_hotel')
            old_maitre_hotel = event.maitre_hotel
            event.maitre_hotel = maitre_hotel
            event.save()
            
            # Notification
            EventNotifications.objects.create(
                recipient=maitre_hotel,
                event=event,
                type='new_event' if not old_maitre_hotel else 'event_updated',
                title='Événement assigné',
                message=f'L\'événement "{event.event_name}" vous a été assigné pour le {event.event_start_time.strftime("%d/%m/%Y à %H:%M")}',
                is_urgent=event.priority in ['high', 'urgent']
            )
            
            # Timeline
            EventTimeline.objects.create(
                event=event,
                timestamp=timezone.now(),
                action_type='other',
                description=f'Assigné à {maitre_hotel.get_full_name()} par {request.user.get_full_name()}',
                created_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Événement assigné à {maitre_hotel.get_full_name()}',
                'maitre_hotel_name': maitre_hotel.get_full_name()
            })
        else:
            # Désassigner
            old_maitre_hotel = event.maitre_hotel
            event.maitre_hotel = None
            event.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Maître d\'hôtel désassigné',
                'maitre_hotel_name': None
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
    
@user_passes_test(admin_required)
@require_POST
def admin_remove_staff_from_event(request, contract_id, assignment_id):
    """Retirer un membre du personnel d'un événement"""
    try:
        event = get_object_or_404(EventContract, id=contract_id)
        assignment = get_object_or_404(EventStaffAssignment, id=assignment_id, event=event)
        
        staff_name = assignment.staff_member.get_full_name()
        assignment.delete()
        
        # Timeline
        EventTimeline.objects.create(
            event=event,
            timestamp=timezone.now(),
            action_type='other',
            description=f'{staff_name} retiré de l\'équipe par {request.user.get_full_name()}',
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': f'{staff_name} retiré de l\'équipe'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)
        
    try:
        data = json.loads(request.body)
        event_id = data.get('event_id')
        maitre_hotel_id = data.get('maitre_hotel_id')
        
        event = get_object_or_404(EventContract, id=event_id)
        
        if maitre_hotel_id:
            maitre_hotel = get_object_or_404(User, id=maitre_hotel_id, role='maitre_hotel')
            old_maitre_hotel = event.maitre_hotel
            event.maitre_hotel = maitre_hotel
            event.save()
            
            # Notification
            EventNotifications.objects.create(
                recipient=maitre_hotel,
                event=event,
                type='new_event' if not old_maitre_hotel else 'event_updated',
                title='Événement assigné',
                message=f'L\'événement "{event.event_name}" vous a été assigné pour le {event.event_start_time.strftime("%d/%m/%Y à %H:%M")}',
                is_urgent=event.priority in ['high', 'urgent']
            )
            
            # Timeline
            EventTimeline.objects.create(
                event=event,
                timestamp=timezone.now(),
                action_type='other',
                description=f'Assigné à {maitre_hotel.get_full_name()} par {request.user.get_full_name()}',
                created_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Événement assigné à {maitre_hotel.get_full_name()}',
                'maitre_hotel_name': maitre_hotel.get_full_name()
            })
        else:
            # Désassigner
            old_maitre_hotel = event.maitre_hotel
            event.maitre_hotel = None
            event.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Maître d\'hôtel désassigné',
                'maitre_hotel_name': None
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)