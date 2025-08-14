
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
            'link': '/admin/orders/?status=pending'
        })
    
    # Stock faible
    if low_stock_products > 0:
        alerts.append({
            'type': 'danger',
            'message': f'{low_stock_products} produit(s) avec stock faible',
            'link': '/admin/products/low-stock/'
        })
    
    # Commandes du jour
    if orders_today > 5:
        alerts.append({
            'type': 'info',
            'message': f'{orders_today} commandes aujourd\'hui!',
            'link': '/admin/orders/?date=today'
        })
    
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