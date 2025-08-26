# kitchen/views.py - Vues pour la gestion de cuisine

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta, date
import json
from django.urls import reverse
from .models import *
from JLTsite.models import Order, OrderItem

# ========================================
# VUES CHEF DE CUISINE (HEAD CHEF)
# ========================================

@login_required
def head_chef_dashboard(request):
    """Dashboard principal du chef de cuisine"""
    if request.user.role not in ['head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    # Période sélectionnée
    period = request.GET.get('period', '7')
    today = timezone.now().date()
    
    if period == '7':
        start_date = today - timedelta(days=7)
    elif period == '30':
        start_date = today - timedelta(days=30)
    else:
        start_date = today - timedelta(days=90)
    
    # Statistiques générales
    orders = Order.objects.filter(
        delivery_date__gte=start_date,
        delivery_date__lte=today + timedelta(days=7)
    )
    
    stats = {
        'total_orders': orders.count(),
        'pending_orders': orders.filter(status='pending').count(),
        'total_revenue': orders.aggregate(Sum('total'))['total__sum'] or 0,
        'avg_order_value': orders.aggregate(Avg('total'))['total__avg'] or 0,
    }
    
    # Productions du jour
    today_productions = KitchenProduction.objects.filter(date=today)
    production_stats = {
        'total_departments': today_productions.count(),
        'completed_departments': today_productions.filter(status='completed').count(),
        'in_progress_departments': today_productions.filter(status='in_progress').count(),
        'avg_progress': today_productions.aggregate(Avg('progress_percentage'))['progress_percentage__avg'] or 0,
    }
    
    # Commandes de produits en attente
    pending_product_orders = ProductOrder.objects.filter(status='pending').count()
    
    # Stock faible
    low_stock_products = KitchenProduct.objects.filter(
        current_stock__lte=models.F('min_stock')
    ).count()
    
    # Alertes
    alerts = []
    if pending_product_orders > 0:
        alerts.append({
            'type': 'warning',
            'message': f'{pending_product_orders} commande(s) de produits en attente d\'approbation',
            'link': '/kitchen/head-chef/product-orders/'
        })
    
    if low_stock_products > 0:
        alerts.append({
            'type': 'danger',
            'message': f'{low_stock_products} produit(s) en stock faible',
            'link': '/kitchen/head-chef/inventory/'
        })
    
    # Notifications récentes
    notifications = KitchenNotification.objects.filter(
        recipient=request.user,
        is_read=False
    )[:5]
    
    # Données pour les graphiques
    # Production par département (7 derniers jours)
    dept_data = {}
    for i in range(7):
        check_date = today - timedelta(days=i)
        productions = KitchenProduction.objects.filter(date=check_date)
        for prod in productions:
            if prod.department not in dept_data:
                dept_data[prod.department] = []
            dept_data[prod.department].append(prod.progress_percentage)
    
    context = {
        'period': period,
        'stats': stats,
        'production_stats': production_stats,
        'alerts': alerts,
        'notifications': notifications,
        'today_productions': today_productions,
        'dept_data': dept_data,
    }
    
    return render(request, 'JLTsite/head_chef_dashboard.html', context)

@login_required
def head_chef_orders(request):
    """Gestion des commandes par le chef de cuisine"""
    if request.user.role not in ['head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    # Filtres
    date_filter = request.GET.get('date', '')
    status_filter = request.GET.get('status', '')
    department_filter = request.GET.get('department', '')
    
    # Base queryset
    orders = Order.objects.all().select_related().prefetch_related('items')
    
    # Application des filtres
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            orders = orders.filter(delivery_date=filter_date)
        except ValueError:
            pass
    else:
        # Par défaut, afficher les commandes d'aujourd'hui et des 7 prochains jours
        today = timezone.now().date()
        orders = orders.filter(
            delivery_date__gte=today,
            delivery_date__lte=today + timedelta(days=7)
        )
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    if department_filter:
        orders = orders.filter(items__department=department_filter).distinct()
    
    # Pagination
    paginator = Paginator(orders.order_by('delivery_date', 'delivery_time'), 20)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    
    # Statistiques rapides
    today = timezone.now().date()
    quick_stats = {
        'today_orders': Order.objects.filter(delivery_date=today).count(),
        'tomorrow_orders': Order.objects.filter(delivery_date=today + timedelta(days=1)).count(),
        'week_orders': Order.objects.filter(
            delivery_date__gte=today,
            delivery_date__lte=today + timedelta(days=7)
        ).count(),
    }
    
    context = {
        'orders': orders,
        'date_filter': date_filter,
        'status_filter': status_filter,
        'department_filter': department_filter,
        'quick_stats': quick_stats,
        'departments': OrderItem.DEPARTMENT_CHOICES,
        'statuses': Order.STATUS_CHOICES,
    }
    
    return render(request, 'JLTsite/head_chef_orders.html', context)

@login_required
def head_chef_product_orders(request):
    """Gestion des commandes de produits"""
    if request.user.role not in ['head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    status_filter = request.GET.get('status', 'pending')
    department_filter = request.GET.get('department', '')
    
    # Base queryset
    product_orders = ProductOrder.objects.all().select_related('supplier', 'requested_by')
    
    if status_filter:
        product_orders = product_orders.filter(status=status_filter)
    
    if department_filter:
        product_orders = product_orders.filter(department=department_filter)
    
    # Pagination
    paginator = Paginator(product_orders.order_by('-created_at'), 20)
    page = request.GET.get('page')
    product_orders = paginator.get_page(page)
    
    context = {
        'product_orders': product_orders,
        'status_filter': status_filter,
        'department_filter': department_filter,
        'departments': ProductOrder._meta.get_field('department').choices,
        'statuses': ProductOrder.STATUS_CHOICES,
    }
    
    return render(request, 'JLTsite/head_chef_product_orders.html', context)

@login_required
@require_http_methods(["POST"])
def approve_product_order(request, order_id):
    """Approuver une commande de produits"""
    if request.user.role not in ['head_chef', 'admin']:
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'})
    
    try:
        product_order = get_object_or_404(ProductOrder, id=order_id)
        product_order.status = 'approved'
        product_order.approved_by = request.user
        product_order.approved_at = timezone.now()
        product_order.save()
        
        # Créer une notification pour le demandeur
        KitchenNotification.objects.create(
            type='general',
            recipient_type='department_chef',
            recipient=product_order.requested_by,
            title='Commande approuvée',
            message=f'Votre commande {product_order.order_number} a été approuvée.',
            product_order=product_order
        )
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def head_chef_dispatch(request):
    """Impression des dispatch par département"""
    if request.user.role not in ['head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    date_str = request.GET.get('date', timezone.now().date().strftime('%Y-%m-%d'))
    try:
        dispatch_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        dispatch_date = timezone.now().date()
    
    # Récupérer toutes les productions du jour par département
    departments_data = {}
    
    for dept_code, dept_name in OrderItem.DEPARTMENT_CHOICES:
        # Récupérer ou créer la production pour ce département
        production, created = KitchenProduction.objects.get_or_create(
            date=dispatch_date,
            department=dept_code,
            defaults={'department_chef': None}
        )
        
        # Récupérer tous les items à produire pour ce département
        order_items = OrderItem.objects.filter(
            order__delivery_date=dispatch_date,
            department=dept_code,
            order__status__in=['confirmed', 'preparing']
        ).select_related('order', 'product')
        
        # Créer les items de production si nécessaire
        for item in order_items:
            ProductionItem.objects.get_or_create(
                production=production,
                order_item=item,
                defaults={
                    'quantity_to_produce': item.quantity,
                    'is_priority': item.order.delivery_time.hour < 12
                }
            )
        
        # Récupérer les items de production
        production_items = production.production_items.all().select_related(
            'order_item__order', 'order_item__product'
        ).order_by('is_priority', 'order_item__order__delivery_time')
        
        departments_data[dept_code] = {
            'name': dept_name,
            'production': production,
            'items': production_items,
            'total_items': production_items.count(),
            'completed_items': production_items.filter(is_completed=True).count(),
        }
    
    context = {
        'dispatch_date': dispatch_date,
        'departments_data': departments_data,
    }
    
    return render(request, 'JLTsite/head_chef_dispatch.html', context)

# Ajouter ces imports en haut de votre fichier kitchen_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Avg, Count, Q, F
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json
import csv
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

from .models import (
    Order, OrderItem, KitchenProduction, ProductionItem,
    ProductOrder, ProductOrderItem, KitchenProduct, Supplier,
    KitchenNotification, QualityCheck, User
)
from .forms import (
    ProductForm, SupplierForm, ProductOrderForm,
    ProductionReportForm
)

# ========================================
# VUES DÉTAILS DES COMMANDES
# ========================================

@login_required
def head_chef_order_detail(request, order_number):
    """Détail d'une commande pour le chef de cuisine"""
    if request.user.role not in ['head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    order = get_object_or_404(Order, order_number=order_number)
    
    # Regrouper les items par département
    items_by_department = {}
    for item in order.items.all():
        dept = item.department or 'autres'
        if dept not in items_by_department:
            items_by_department[dept] = []
        items_by_department[dept].append(item)
    
    # Vérifier si une production existe pour cette commande
    productions = KitchenProduction.objects.filter(
        date=order.delivery_date,
        production_items__order_item__order=order
    ).distinct()
    
    context = {
        'order': order,
        'items_by_department': items_by_department,
        'productions': productions,
    }
    
    return render(request, 'JLTsite/head_chef_order_detail.html', context)

# ========================================
# VUES COMMANDES DE PRODUITS
# ========================================

@login_required
def head_chef_product_order_detail(request, order_id):
    """Détail d'une commande de produits"""
    if request.user.role not in ['head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    product_order = get_object_or_404(ProductOrder, id=order_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            product_order.status = 'approved'
            product_order.approved_by = request.user
            product_order.approved_at = timezone.now()
            product_order.save()
            messages.success(request, f"Commande {product_order.order_number} approuvée")
            
        elif action == 'reject':
            product_order.status = 'cancelled'
            product_order.internal_notes = request.POST.get('rejection_reason', '')
            product_order.save()
            messages.warning(request, f"Commande {product_order.order_number} rejetée")
            
        elif action == 'mark_received':
            product_order.status = 'received'
            product_order.save()
            
            # Mettre à jour le stock
            for item in product_order.items.all():
                item.product.current_stock += item.received_quantity
                item.product.save()
                
            messages.success(request, "Commande marquée comme reçue et stock mis à jour")
        
        return redirect('head_chef_product_orders')
    
    context = {
        'product_order': product_order,
        'can_approve': product_order.status == 'pending',
        'can_receive': product_order.status == 'ordered',
    }
    
    return render(request, 'JLTsite/head_chef_product_order_detail.html', context)

@login_required
@require_http_methods(["POST"])
def reject_product_order(request, order_id):
    """Rejeter une commande de produits"""
    if request.user.role not in ['head_chef', 'admin']:
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'})
    
    try:
        product_order = get_object_or_404(ProductOrder, id=order_id)
        product_order.status = 'cancelled'
        product_order.internal_notes = request.POST.get('reason', 'Rejetée par le chef')
        product_order.save()
        
        # Notification
        KitchenNotification.objects.create(
            type='general',
            recipient_type='department_chef',
            recipient=product_order.requested_by,
            title='Commande rejetée',
            message=f'Votre commande {product_order.order_number} a été rejetée.',
            product_order=product_order
        )
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ========================================
# VUES DISPATCH
# ========================================

@login_required
def head_chef_dispatch_by_date(request, date_str):
    """Dispatch pour une date spécifique"""
    if request.user.role not in ['head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    try:
        dispatch_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, "Date invalide")
        return redirect('head_chef_dispatch')
    
    # Même logique que head_chef_dispatch mais avec date spécifique
    return redirect(f"{reverse('head_chef_dispatch')}?date={date_str}")

# ========================================
# VUES INVENTAIRE ET STOCK
# ========================================

@login_required
def head_chef_inventory(request):
    """Gestion de l'inventaire"""
    if request.user.role not in ['head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    # Filtres
    category_filter = request.GET.get('category', '')
    low_stock_only = request.GET.get('low_stock', '') == '1'
    search_query = request.GET.get('search', '')
    
    # Base queryset
    products = KitchenProduct.objects.filter(is_active=True)
    
    # Application des filtres
    if category_filter:
        products = products.filter(category=category_filter)
    
    if low_stock_only:
        products = products.filter(current_stock__lte=F('min_stock'))
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(category__icontains=search_query)
        )
    
    # Statistiques
    stats = {
        'total_products': products.count(),
        'low_stock_count': products.filter(current_stock__lte=F('min_stock')).count(),
        'out_of_stock': products.filter(current_stock=0).count(),
        'total_value': products.aggregate(
            total=Sum(F('current_stock') * F('unit_price'))
        )['total'] or 0,
    }
    
    # Pagination
    paginator = Paginator(products.order_by('category', 'name'), 25)
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    context = {
        'products': products,
        'stats': stats,
        'category_filter': category_filter,
        'low_stock_only': low_stock_only,
        'search_query': search_query,
        'categories': KitchenProduct.CATEGORY_CHOICES,
    }
    
    return render(request, 'JLTsite/head_chef_inventory.html', context)

@login_required
def head_chef_manage_products(request):
    """Gestion des produits cuisine"""
    if request.user.role not in ['head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    products = KitchenProduct.objects.all().order_by('category', 'name')
    
    context = {
        'products': products,
        'categories': KitchenProduct.CATEGORY_CHOICES,
    }
    
    return render(request, 'JLTsite/head_chef_manage_products.html', context)

@login_required
def head_chef_add_product(request):
    """Ajouter un nouveau produit"""
    if request.user.role not in ['head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    if request.method == 'POST':
        # Création manuelle du produit depuis le POST
        product = KitchenProduct(
            name=request.POST.get('name'),
            category=request.POST.get('category'),
            unit=request.POST.get('unit'),
            current_stock=request.POST.get('current_stock', 0),
            min_stock=request.POST.get('min_stock', 0),
            max_stock=request.POST.get('max_stock', 0),
            unit_price=request.POST.get('unit_price', 0),
            shelf_life_days=request.POST.get('shelf_life_days', 7),
        )
        
        supplier_id = request.POST.get('supplier')
        if supplier_id:
            product.supplier = get_object_or_404(Supplier, id=supplier_id)
        
        # Départements
        departments = request.POST.getlist('departments')
        product.departments = departments
        
        product.save()
        messages.success(request, f"Produit {product.name} ajouté avec succès")
        return redirect('head_chef_manage_products')
    
    suppliers = Supplier.objects.filter(is_active=True)
    context = {
        'suppliers': suppliers,
        'categories': KitchenProduct.CATEGORY_CHOICES,
        'units': KitchenProduct.UNIT_CHOICES,
        'departments': OrderItem.DEPARTMENT_CHOICES,
    }
    
    return render(request, 'JLTsite/head_chef_add_product.html', context)

@login_required
def head_chef_edit_product(request, product_id):
    """Modifier un produit"""
    if request.user.role not in ['head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    product = get_object_or_404(KitchenProduct, id=product_id)
    
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.category = request.POST.get('category')
        product.unit = request.POST.get('unit')
        product.current_stock = request.POST.get('current_stock', 0)
        product.min_stock = request.POST.get('min_stock', 0)
        product.max_stock = request.POST.get('max_stock', 0)
        product.unit_price = request.POST.get('unit_price', 0)
        product.shelf_life_days = request.POST.get('shelf_life_days', 7)
        
        supplier_id = request.POST.get('supplier')
        if supplier_id:
            product.supplier = get_object_or_404(Supplier, id=supplier_id)
        
        departments = request.POST.getlist('departments')
        product.departments = departments
        
        product.save()
        messages.success(request, f"Produit {product.name} modifié avec succès")
        return redirect('head_chef_manage_products')
    
    suppliers = Supplier.objects.filter(is_active=True)
    context = {
        'product': product,
        'suppliers': suppliers,
        'categories': KitchenProduct.CATEGORY_CHOICES,
        'units': KitchenProduct.UNIT_CHOICES,
        'departments': OrderItem.DEPARTMENT_CHOICES,
    }
    
    return render(request, 'JLTsite/head_chef_edit_product.html', context)

@login_required
def head_chef_manage_suppliers(request):
    """Gestion des fournisseurs"""
    if request.user.role not in ['head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            supplier = Supplier(
                name=request.POST.get('name'),
                contact_name=request.POST.get('contact_name', ''),
                email=request.POST.get('email', ''),
                phone=request.POST.get('phone', ''),
                address=request.POST.get('address', ''),
                min_order_amount=request.POST.get('min_order_amount', 0),
                delivery_days=request.POST.get('delivery_days', ''),
            )
            supplier.save()
            messages.success(request, f"Fournisseur {supplier.name} ajouté")
            
        elif action == 'edit':
            supplier_id = request.POST.get('supplier_id')
            supplier = get_object_or_404(Supplier, id=supplier_id)
            supplier.name = request.POST.get('name')
            supplier.contact_name = request.POST.get('contact_name', '')
            supplier.email = request.POST.get('email', '')
            supplier.phone = request.POST.get('phone', '')
            supplier.address = request.POST.get('address', '')
            supplier.min_order_amount = request.POST.get('min_order_amount', 0)
            supplier.delivery_days = request.POST.get('delivery_days', '')
            supplier.save()
            messages.success(request, f"Fournisseur {supplier.name} modifié")
            
        elif action == 'delete':
            supplier_id = request.POST.get('supplier_id')
            supplier = get_object_or_404(Supplier, id=supplier_id)
            supplier.is_active = False
            supplier.save()
            messages.success(request, f"Fournisseur {supplier.name} désactivé")
    
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    
    context = {
        'suppliers': suppliers,
    }
    
    return render(request, 'JLTsite/head_chef_manage_suppliers.html', context)

# ========================================
# VUES RAPPORTS
# ========================================

@login_required
def head_chef_reports(request):
    """Page principale des rapports"""
    if request.user.role not in ['head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    # Période par défaut : dernier mois
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=30)
    
    if request.GET.get('start_date'):
        start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
    if request.GET.get('end_date'):
        end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
    
    # Statistiques générales
    orders = Order.objects.filter(
        delivery_date__gte=start_date,
        delivery_date__lte=end_date
    )
    
    stats = {
        'total_orders': orders.count(),
        'total_revenue': orders.aggregate(Sum('total'))['total__sum'] or 0,
        'avg_order_value': orders.aggregate(Avg('total'))['total__avg'] or 0,
        'total_items': OrderItem.objects.filter(
            order__in=orders
        ).aggregate(Sum('quantity'))['quantity__sum'] or 0,
    }
    
    # Production par département
    dept_stats = []
    for dept_code, dept_name in OrderItem.DEPARTMENT_CHOICES:
        productions = KitchenProduction.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            department=dept_code
        )
        dept_stats.append({
            'name': dept_name,
            'total_productions': productions.count(),
            'avg_progress': productions.aggregate(
                Avg('progress_percentage')
            )['progress_percentage__avg'] or 0,
            'completed': productions.filter(status='completed').count(),
        })
    
    # Top produits
    top_products = OrderItem.objects.filter(
        order__delivery_date__gte=start_date,
        order__delivery_date__lte=end_date
    ).values('product_name').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('subtotal')
    ).order_by('-total_quantity')[:10]
    
    context = {
        'start_date': start_date,
        'end_date': end_date,
        'stats': stats,
        'dept_stats': dept_stats,
        'top_products': top_products,
    }
    
    return render(request, 'JLTsite/head_chef_reports.html', context)

@login_required
def head_chef_production_reports(request):
    """Rapports détaillés de production"""
    if request.user.role not in ['head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    # Filtres
    department = request.GET.get('department', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Base queryset
    productions = KitchenProduction.objects.all()
    
    if department:
        productions = productions.filter(department=department)
    
    if start_date:
        productions = productions.filter(date__gte=start_date)
    
    if end_date:
        productions = productions.filter(date__lte=end_date)
    
    # Statistiques par département
    dept_performance = []
    for dept_code, dept_name in OrderItem.DEPARTMENT_CHOICES:
        dept_prods = productions.filter(department=dept_code)
        if dept_prods.exists():
            dept_performance.append({
                'department': dept_name,
                'total_productions': dept_prods.count(),
                'completed': dept_prods.filter(status='completed').count(),
                'on_time_rate': (dept_prods.filter(status='completed').count() / 
                                dept_prods.count() * 100) if dept_prods.count() > 0 else 0,
                'avg_progress': dept_prods.aggregate(
                    Avg('progress_percentage')
                )['progress_percentage__avg'] or 0,
            })
    
    # Qualité moyenne
    quality_checks = QualityCheck.objects.filter(
        production_item__production__in=productions
    )
    
    quality_stats = {
        'total_checks': quality_checks.count(),
        'avg_rating': quality_checks.aggregate(
            Avg('overall_rating')
        )['overall_rating__avg'] or 0,
        'approved_rate': (quality_checks.filter(
            approved_for_service=True
        ).count() / quality_checks.count() * 100) if quality_checks.count() > 0 else 0,
    }
    
    context = {
        'productions': productions.order_by('-date')[:50],
        'dept_performance': dept_performance,
        'quality_stats': quality_stats,
        'departments': OrderItem.DEPARTMENT_CHOICES,
        'filters': {
            'department': department,
            'start_date': start_date,
            'end_date': end_date,
        }
    }
    
    return render(request, 'JLTsite/head_chef_production_reports.html', context)

@login_required
def head_chef_export_reports(request):
    """Exporter les rapports en PDF ou CSV"""
    if request.user.role not in ['head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    export_type = request.GET.get('type', 'csv')
    report_type = request.GET.get('report', 'orders')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    if not start_date:
        start_date = (timezone.now().date() - timedelta(days=30)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = timezone.now().date().strftime('%Y-%m-%d')
    
    if export_type == 'csv':
        return export_csv_report(request, report_type, start_date, end_date)
    elif export_type == 'pdf':
        return export_pdf_report(request, report_type, start_date, end_date)
    
    return redirect('head_chef_reports')

def export_csv_report(request, report_type, start_date, end_date):
    """Exporter en CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="rapport_{report_type}_{start_date}_{end_date}.csv"'
    
    writer = csv.writer(response)
    
    if report_type == 'orders':
        # En-tête
        writer.writerow(['Numéro', 'Date livraison', 'Client', 'Montant', 'Statut'])
        
        # Données
        orders = Order.objects.filter(
            delivery_date__gte=start_date,
            delivery_date__lte=end_date
        )
        for order in orders:
            writer.writerow([
                order.order_number,
                order.delivery_date,
                f"{order.first_name} {order.last_name}",
                order.total,
                order.get_status_display()
            ])
    
    elif report_type == 'production':
        # En-tête
        writer.writerow(['Date', 'Département', 'Statut', 'Progression', 'Items complétés'])
        
        # Données
        productions = KitchenProduction.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        )
        for prod in productions:
            writer.writerow([
                prod.date,
                prod.get_department_display(),
                prod.get_status_display(),
                f"{prod.progress_percentage}%",
                f"{prod.completed_items}/{prod.total_items}"
            ])
    
    elif report_type == 'inventory':
        # En-tête
        writer.writerow(['Produit', 'Catégorie', 'Stock actuel', 'Stock min', 'Prix unitaire', 'Valeur totale'])
        
        # Données
        products = KitchenProduct.objects.filter(is_active=True)
        for product in products:
            writer.writerow([
                product.name,
                product.get_category_display(),
                product.current_stock,
                product.min_stock,
                product.unit_price,
                product.current_stock * product.unit_price
            ])
    
    return response

def export_pdf_report(request, report_type, start_date, end_date):
    """Exporter en PDF"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    # Titre
    title = Paragraph(f"Rapport {report_type} - {start_date} à {end_date}", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    if report_type == 'orders':
        # Données des commandes
        data = [['Numéro', 'Date', 'Client', 'Montant', 'Statut']]
        
        orders = Order.objects.filter(
            delivery_date__gte=start_date,
            delivery_date__lte=end_date
        )
        
        for order in orders:
            data.append([
                order.order_number,
                order.delivery_date.strftime('%Y-%m-%d'),
                f"{order.first_name} {order.last_name}"[:25],
                f"${order.total}",
                order.get_status_display()
            ])
        
        # Créer le tableau
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(table)
    
    doc.build(elements)
    
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="rapport_{report_type}_{start_date}_{end_date}.pdf"'
    response.write(pdf)
    
    return response

# ========================================
# API ENDPOINTS
# ========================================

@login_required
def head_chef_production_stats_api(request):
    """API pour les statistiques de production"""
    if request.user.role not in ['head_chef', 'admin']:
        return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    
    # Période (derniers 7 jours par défaut)
    days = int(request.GET.get('days', 7))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Données par jour
    daily_stats = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        productions = KitchenProduction.objects.filter(date=date)
        
        daily_stats.append({
            'date': date.strftime('%Y-%m-%d'),
            'total_productions': productions.count(),
            'completed': productions.filter(status='completed').count(),
            'avg_progress': productions.aggregate(
                Avg('progress_percentage')
            )['progress_percentage__avg'] or 0,
        })
    
    # Données par département
    dept_stats = {}
    for dept_code, dept_name in OrderItem.DEPARTMENT_CHOICES:
        productions = KitchenProduction.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            department=dept_code
        )
        dept_stats[dept_name] = {
            'total': productions.count(),
            'completed': productions.filter(status='completed').count(),
            'in_progress': productions.filter(status='in_progress').count(),
        }
    
    return JsonResponse({
        'daily_stats': daily_stats,
        'dept_stats': dept_stats,
    })

@login_required
def head_chef_department_progress_api(request):
    """API pour le progrès des départements en temps réel"""
    if request.user.role not in ['head_chef', 'admin']:
        return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    
    date = request.GET.get('date', timezone.now().date().strftime('%Y-%m-%d'))
    try:
        date = datetime.strptime(date, '%Y-%m-%d').date()
    except ValueError:
        date = timezone.now().date()
    
    departments = []
    for dept_code, dept_name in OrderItem.DEPARTMENT_CHOICES:
        try:
            production = KitchenProduction.objects.get(
                date=date,
                department=dept_code
            )
            departments.append({
                'name': dept_name,
                'code': dept_code,
                'progress': production.progress_percentage,
                'status': production.status,
                'total_items': production.total_items,
                'completed_items': production.completed_items,
            })
        except KitchenProduction.DoesNotExist:
            departments.append({
                'name': dept_name,
                'code': dept_code,
                'progress': 0,
                'status': 'not_started',
                'total_items': 0,
                'completed_items': 0,
            })
    
    return JsonResponse({
        'date': date.strftime('%Y-%m-%d'),
        'departments': departments,
    })

# ========================================
# VUES NOTIFICATIONS
# ========================================


# ========================================
# VUES CHEF DE DÉPARTEMENT
# ========================================

@login_required
def department_chef_dashboard(request):
    """Dashboard du chef de département"""
    if request.user.role not in ['department_chef', 'head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    # Récupérer le département du chef
    try:
        cook_profile = request.user.cook_profile
        department = cook_profile.primary_department
    except:
        # Si pas de profil, utiliser le premier département par défaut
        department = 'chaud'
    
    # Récupérer la date sélectionnée ou utiliser aujourd'hui par défaut
    selected_date_str = request.GET.get('date')
    if selected_date_str:
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()
    
    today = timezone.now().date()
    
    # Production du jour sélectionné pour ce département
    try:
        selected_production = KitchenProduction.objects.get(
            date=selected_date,
            department=department
        )
    except KitchenProduction.DoesNotExist:
        selected_production = None
    
    # Statistiques du département (toujours basées sur la période actuelle)
    week_start = today - timedelta(days=7)
    week_productions = KitchenProduction.objects.filter(
        department=department,
        date__gte=week_start,
        date__lte=today
    )
    
    # Production du jour actuel pour les stats
    try:
        today_production = KitchenProduction.objects.get(
            date=selected_date,
            department=department
        )
    except KitchenProduction.DoesNotExist:
        today_production = None
    
    dept_stats = {
        'today_progress': today_production.progress_percentage if today_production else 0,
        'today_items': today_production.total_items if today_production else 0,
        'week_avg_progress': week_productions.aggregate(Avg('progress_percentage'))['progress_percentage__avg'] or 0,
        'week_productions': week_productions.count(),
    }
    
    # Commandes de produits du département
    pending_orders = ProductOrder.objects.filter(
        department=department,
        requested_by=request.user,
        status__in=['draft', 'pending']
    ).count()
    
    # Produits en stock faible pour ce département
    low_stock_products = KitchenProduct.objects.filter(
        departments__contains=[department],
        current_stock__lte=models.F('min_stock')
    )
    

    # Notifications récentes (seulement les 5 dernières)
    notifications = KitchenNotification.objects.filter(
        recipient=request.user, is_read =False
    ).order_by('-created_at')[:5]
    
    # Nombre de notifications non lues pour le badge de navigation
    unread_notifications_count = KitchenNotification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    context = {
        'department': department,
        'department_name': dict(OrderItem.DEPARTMENT_CHOICES)[department],
        'selected_date': selected_date,
        'selected_production': selected_production,
        'today_production': today_production,
        'dept_stats': dept_stats,
        'pending_orders': pending_orders,
        'low_stock_products': low_stock_products,
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'is_today': selected_date == today,
    }
    
    return render(request, 'JLTsite/department_chef_dashboard.html', context)

@login_required
def department_chef_orders(request):
    """Gestion des commandes par département"""
    if request.user.role not in ['department_chef', 'head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    # Récupérer le département
    try:
        cook_profile = request.user.cook_profile
        department = cook_profile.primary_department
    except:
        department = 'chaud'
    
    date_filter = request.GET.get('date', timezone.now().date().strftime('%Y-%m-%d'))
    status_filter = request.GET.get('status', '')  # NOUVEAU: filtre de statut
    
    try:
        filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
    except ValueError:
        filter_date = timezone.now().date()
    
    # UTILISER LA NOUVELLE FONCTION
    production = create_production_items_for_date(filter_date, department)
    
    # Récupérer les items de production
    production_items = production.production_items.all().select_related(
        'order_item__order', 'order_item__product'
    ).order_by('is_priority', 'order_item__order__delivery_time')
    
    # NOUVEAU: Appliquer le filtre de statut si présent
    if status_filter:
        if status_filter == 'pending':
            production_items = production_items.filter(started_at__isnull=True, is_completed=False)
        elif status_filter == 'in_progress':
            production_items = production_items.filter(started_at__isnull=False, is_completed=False)
        elif status_filter == 'completed':
            production_items = production_items.filter(is_completed=True)
        elif status_filter == 'priority':
            production_items = production_items.filter(is_priority=True)
    
    # Calculs des statistiques
    all_items = production.production_items.all()  # Pour les stats globales
    total_items = all_items.count()
    completed_items = all_items.filter(is_completed=True).count()
    pending_items = total_items - completed_items
    progress_percentage = int((completed_items / total_items * 100)) if total_items > 0 else 0
    
    context = {
        'department': department,
        'department_name': dict(OrderItem.DEPARTMENT_CHOICES)[department],
        'filter_date': filter_date,
        'selected_date': filter_date,
        'production': production,
        'production_items': production_items,  # Items filtrés pour l'affichage
        'total_items': total_items,  # Stats globales
        'completed_items': completed_items,
        'pending_items': pending_items,
        'progress_percentage': progress_percentage,
        'status_filter': status_filter,  # NOUVEAU: pour garder le filtre actif
    }
    
    return render(request, 'JLTsite/department_chef_orders_kitchen.html', context)

def create_production_items_for_date(date, department):
    """Crée automatiquement les items de production pour une date et un département"""
    
    # Récupérer ou créer la production
    production, created = KitchenProduction.objects.get_or_create(
        date=date,
        department=department,
        defaults={'department_chef': None}
    )
    
    # Récupérer toutes les commandes confirmées pour cette date
    order_items = OrderItem.objects.filter(
        order__delivery_date=date,
        department=department,
        order__status__in=['confirmed', 'preparing', 'ready']
    ).select_related('order', 'product')
    
    print(f"Trouvé {order_items.count()} order_items pour {department} le {date}")
    
    # Créer les ProductionItems si ils n'existent pas
    for order_item in order_items:
        production_item, created = ProductionItem.objects.get_or_create(
            production=production,
            order_item=order_item,
            defaults={
                'quantity_to_produce': order_item.quantity,
                'is_priority': order_item.order.delivery_time.hour < 12 if order_item.order.delivery_time else False
            }
        )
        if created:
            print(f"Créé ProductionItem pour {order_item.product_name}")
    
    # Mettre à jour les stats de la production
    production.update_progress()
    
    return production

@login_required
def department_product_orders(request):
    """Gestion des commandes de produits par le chef de département"""
    if request.user.role not in ['department_chef', 'head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    # Récupérer le département
    try:
        cook_profile = request.user.cook_profile
        department = cook_profile.primary_department
    except:
        department = 'chaud'
    
    # Récupérer les commandes de ce département
    product_orders = ProductOrder.objects.filter(
        department=department,
        requested_by=request.user
    ).select_related('supplier').prefetch_related('items').order_by('-created_at')
    
    # Statistiques
    stats = {
        'total_orders': product_orders.count(),
        'pending_orders': product_orders.filter(status='pending').count(),
        'approved_orders': product_orders.filter(status='approved').count(),
        'total_amount': product_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
    }
    
    # Produits disponibles pour ce département
    available_products = KitchenProduct.objects.filter(
        departments__contains=[department],
        is_active=True
    ).order_by('category', 'name')
    
    # Fournisseurs
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    
    context = {
        'department': department,
        'department_name': dict(OrderItem.DEPARTMENT_CHOICES)[department],
        'orders': product_orders,
        'stats': stats,
        'available_products': available_products,
        'suppliers': suppliers,
    }
    
    return render(request, 'JLTsite/department_product_orders_kitchen.html', context)

@login_required
@require_http_methods(["POST"])
def create_product_order(request):
    """Créer une nouvelle commande de produits"""
    if request.user.role not in ['department_chef', 'head_chef', 'admin']:
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'})
    
    try:
        # Récupérer le département
        cook_profile = request.user.cook_profile
        department = cook_profile.primary_department
        
        data = json.loads(request.body)
        
        # Créer la commande
        product_order = ProductOrder.objects.create(
            requested_by=request.user,
            department=department,
            supplier_id=data['supplier_id'],
            needed_date=data['needed_date'],
            priority=data.get('priority', 'normal'),
            notes=data.get('notes', '')
        )
        
        # Ajouter les items
        total_amount = 0
        for item_data in data['items']:
            product = KitchenProduct.objects.get(id=item_data['product_id'])
            item = ProductOrderItem.objects.create(
                order=product_order,
                product=product,
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price']
            )
            total_amount += item.total_price
        
        product_order.total_amount = total_amount
        product_order.save()
        
        return JsonResponse({'success': True, 'order_id': product_order.id})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ========================================
# VUES CUISINIER
# ========================================

@login_required
def cook_dashboard(request):
    """Dashboard du cuisinier - optimisé pour tablette"""
    if request.user.role not in ['cook', 'department_chef', 'head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    # Date sélectionnée (par défaut aujourd'hui)
    date_str = request.GET.get('date', timezone.now().date().strftime('%Y-%m-%d'))
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = timezone.now().date()
    
    # Récupérer le département du cuisinier
    try:
        cook_profile = request.user.cook_profile
        department = cook_profile.primary_department
    except:
        # Si pas de profil, créer un profil par défaut
        department = 'chaud'
        CookProfile.objects.get_or_create(
            user=request.user,
            defaults={
                'primary_department': department,
                'skill_level': 1
            }
        )
    
    # Récupérer la production du jour
    try:
        production = KitchenProduction.objects.get(
            date=selected_date,
            department=department
        )
    except KitchenProduction.DoesNotExist:
        production = None
    
    production_items = []
    if production:
        production_items = production.production_items.filter(
            is_completed=False
        ).select_related(
            'order_item__order', 'order_item__product'
        ).order_by('is_priority', 'order_item__order__delivery_time')
    
    # Items en cours de production par ce cuisinier
    my_items = ProductionItem.objects.filter(
        produced_by=request.user,
        started_at__isnull=False,
        completed_at__isnull=True
    )
    
    # Statistiques du cuisinier
    today_completed = ProductionItem.objects.filter(
        produced_by=request.user,
        completed_at__date=timezone.now().date()
    ).count()
    
    week_start = timezone.now().date() - timedelta(days=7)
    week_completed = ProductionItem.objects.filter(
        produced_by=request.user,
        completed_at__date__gte=week_start
    ).count()
    
    context = {
        'selected_date': selected_date,
        'department': department,
        'department_name': dict(OrderItem.DEPARTMENT_CHOICES)[department],
        'production': production,
        'production_items': production_items,
        'my_items': my_items,
        'today_completed': today_completed,
        'week_completed': week_completed,
        'is_today': selected_date == timezone.now().date(),
    }
    
    return render(request, 'JLTsite/cook_dashboard_kitchen.html', context)

@login_required
@require_http_methods(["POST"])
def start_production_item(request, item_id):
    """Démarrer la production d'un item"""
    if request.user.role not in ['cook', 'department_chef', 'head_chef', 'admin']:
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'})
    
    try:
        item = get_object_or_404(ProductionItem, id=item_id)
        item.start_production(request.user)
        
        return JsonResponse({
            'success': True,
            'started_at': item.started_at.strftime('%H:%M') if item.started_at else ''
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_http_methods(["POST"])
def complete_production_item(request, item_id):
    """Marquer un item comme terminé"""
    if request.user.role not in ['cook', 'department_chef', 'head_chef', 'admin']:
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'})
    
    try:
        item = get_object_or_404(ProductionItem, id=item_id)
        
        data = json.loads(request.body)
        quantity = data.get('quantity', item.quantity_to_produce)
        notes = data.get('notes', '')
        
        if notes:
            item.production_notes = notes
        
        item.mark_completed(request.user, quantity)
        
        # Mettre à jour le profil du cuisinier
        try:
            profile = request.user.cook_profile
            profile.total_items_produced += 1
            profile.save()
        except:
            pass
        
        return JsonResponse({
            'success': True,
            'completed_at': item.completed_at.strftime('%H:%M') if item.completed_at else '',
            'progress': item.production.progress_percentage
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_http_methods(["POST"])
def report_production_issue(request, item_id):
    """Signaler un problème sur un item de production"""
    if request.user.role not in ['cook', 'department_chef', 'head_chef', 'admin']:
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'})
    
    try:
        item = get_object_or_404(ProductionItem, id=item_id)
        
        data = json.loads(request.body)
        issue_description = data.get('description', '')
        
        item.has_issue = True
        item.issue_description = issue_description
        item.save()
        
        # Créer une notification pour le chef de département
        if item.production.department_chef:
            KitchenNotification.objects.create(
                type='quality_issue',
                recipient_type='department_chef',
                recipient=item.production.department_chef,
                title='Problème de production signalé',
                message=f'Problème signalé sur {item.order_item.product_name}: {issue_description}',
                production_item=item,
                is_urgent=True
            )
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ========================================
# VUES COMMUNES ET UTILITAIRES
# ========================================

@login_required
def print_department_dispatch(request, department):
    """Impression du dispatch pour un département spécifique"""
    if request.user.role not in ['cook', 'department_chef', 'head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    date_str = request.GET.get('date', timezone.now().date().strftime('%Y-%m-%d'))
    try:
        dispatch_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        dispatch_date = timezone.now().date()
    
    # Récupérer la production du département
    try:
        production = KitchenProduction.objects.get(
            date=dispatch_date,
            department=department
        )
    except KitchenProduction.DoesNotExist:
        production = KitchenProduction.objects.create(
            date=dispatch_date,
            department=department
        )
    
    # Récupérer les items de production
    production_items = production.production_items.all().select_related(
        'order_item__order', 'order_item__product'
    ).order_by('is_priority', 'order_item__order__delivery_time')
    
    context = {
        'department': department,
        'department_name': dict(OrderItem.DEPARTMENT_CHOICES)[department],
        'dispatch_date': dispatch_date,
        'production': production,
        'production_items': production_items,
        'is_print': True,
    }
    
    return render(request, 'JLTsite/print_department_dispatch_kitchen.html', context)

@login_required
def kitchen_notifications(request):
    """Gestion des notifications de cuisine"""
    notifications = KitchenNotification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')
    
    # Marquer comme lues
    if request.method == 'POST':
        notification_ids = request.POST.getlist('notification_ids')
        KitchenNotification.objects.filter(
            id__in=notification_ids,
            recipient=request.user
        ).update(is_read=True, read_at=timezone.now())
        
        return redirect('kitchen_notifications')
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page = request.GET.get('page')
    notifications = paginator.get_page(page)
    
    context = {
        'notifications': notifications,
    }
    
    return render(request, 'JLTsite/notifications_kitchen.html', context)

@login_required
def create_product_order_view(request):
    """Vue pour créer une nouvelle commande de produits"""
    if request.user.role not in ['department_chef', 'head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    # Récupérer le département
    try:
        cook_profile = request.user.cook_profile
        department = cook_profile.primary_department
    except:
        department = 'chaud'
    
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            supplier_id = request.POST.get('supplier_id')
            needed_date = request.POST.get('needed_date')
            priority = request.POST.get('priority', 'normal')
            notes = request.POST.get('notes', '')
            
            # Créer la commande
            product_order = ProductOrder.objects.create(
                requested_by=request.user,
                department=department,
                supplier_id=supplier_id,
                needed_date=needed_date,
                priority=priority,
                notes=notes,
                status='draft'
            )
            
            # Ajouter les items
            total_amount = 0
            item_count = int(request.POST.get('item_count', 0))
            
            for i in range(item_count):
                product_id = request.POST.get(f'item_{i}_product_id')
                quantity = request.POST.get(f'item_{i}_quantity')
                unit_price = request.POST.get(f'item_{i}_unit_price')
                
                if product_id and quantity and unit_price:
                    product = KitchenProduct.objects.get(id=product_id)
                    item = ProductOrderItem.objects.create(
                        order=product_order,
                        product=product,
                        quantity=float(quantity),
                        unit_price=float(unit_price)
                    )
                    total_amount += item.total_price
            
            product_order.total_amount = total_amount
            product_order.save()
            
            messages.success(request, f"Commande {product_order.order_number} créée avec succès!")
            return redirect('department_product_orders')
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la création: {str(e)}")
    
    # Produits disponibles pour ce département
    available_products = KitchenProduct.objects.filter(
        departments__contains=[department],
        is_active=True
    ).order_by('category', 'name')
    
    # Fournisseurs
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    
    context = {
        'department': department,
        'department_name': dict(OrderItem.DEPARTMENT_CHOICES)[department],
        'available_products': available_products,
        'suppliers': suppliers,
    }
    
    return render(request, 'JLTsite/create_product_order_kitchen.html', context)

@login_required
def edit_product_order_view(request, order_id):
    """Vue pour éditer une commande de produits"""
    if request.user.role not in ['department_chef', 'head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    product_order = get_object_or_404(ProductOrder, id=order_id, requested_by=request.user)
    
    if product_order.status not in ['draft']:
        messages.error(request, "Cette commande ne peut plus être modifiée")
        return redirect('department_product_orders')
    
    if request.method == 'POST':
        try:
            # Mettre à jour la commande
            product_order.supplier_id = request.POST.get('supplier_id')
            product_order.needed_date = request.POST.get('needed_date')
            product_order.priority = request.POST.get('priority', 'normal')
            product_order.notes = request.POST.get('notes', '')
            
            # Supprimer les anciens items
            product_order.items.all().delete()
            
            # Ajouter les nouveaux items
            total_amount = 0
            item_count = int(request.POST.get('item_count', 0))
            
            for i in range(item_count):
                product_id = request.POST.get(f'item_{i}_product_id')
                quantity = request.POST.get(f'item_{i}_quantity')
                unit_price = request.POST.get(f'item_{i}_unit_price')
                
                if product_id and quantity and unit_price:
                    product = KitchenProduct.objects.get(id=product_id)
                    item = ProductOrderItem.objects.create(
                        order=product_order,
                        product=product,
                        quantity=float(quantity),
                        unit_price=float(unit_price)
                    )
                    total_amount += item.total_price
            
            product_order.total_amount = total_amount
            product_order.save()
            
            messages.success(request, "Commande modifiée avec succès!")
            return redirect('department_product_orders')
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la modification: {str(e)}")
    
    # Récupérer le département
    try:
        cook_profile = request.user.cook_profile
        department = cook_profile.primary_department
    except:
        department = 'chaud'
    
    # Produits disponibles pour ce département
    available_products = KitchenProduct.objects.filter(
        departments__contains=[department],
        is_active=True
    ).order_by('category', 'name')
    
    # Fournisseurs
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    
    context = {
        'department': department,
        'department_name': dict(OrderItem.DEPARTMENT_CHOICES)[department],
        'product_order': product_order,
        'available_products': available_products,
        'suppliers': suppliers,
    }
    
    return render(request, 'JLTsite/edit_product_order_kitchen.html', context)

@login_required
def view_product_order(request, order_id):
    """Vue pour voir les détails d'une commande"""
    if request.user.role not in ['department_chef', 'head_chef', 'admin']:
        messages.error(request, "Accès non autorisé")
        return redirect('home')
    
    product_order = get_object_or_404(ProductOrder, id=order_id, requested_by=request.user)
    
    context = {
        'product_order': product_order,
    }
    
    return render(request, 'JLTsite/view_product_order_kitchen.html', context)

# Actions AJAX pour les commandes produits
@login_required
@require_http_methods(["POST"])
def submit_product_order(request, order_id):
    """Soumettre une commande pour approbation"""
    if request.user.role not in ['department_chef', 'head_chef', 'admin']:
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'})
    
    try:
        product_order = get_object_or_404(ProductOrder, id=order_id, requested_by=request.user)
        
        if product_order.status != 'draft':
            return JsonResponse({'success': False, 'error': 'Cette commande ne peut pas être soumise'})
        
        product_order.status = 'pending'
        product_order.save()
        
        # Créer une notification pour le chef de cuisine
        head_chef = User.objects.filter(role='head_chef').first()
        if head_chef:
            KitchenNotification.objects.create(
                type='general',
                recipient_type='head_chef',
                recipient=head_chef,
                title='Nouvelle commande de produits',
                message=f'Commande {product_order.order_number} soumise pour approbation par {request.user.get_full_name()}',
                product_order=product_order
            )
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_http_methods(["POST"])
def cancel_product_order(request, order_id):
    """Annuler/supprimer une commande"""
    if request.user.role not in ['department_chef', 'head_chef', 'admin']:
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'})
    
    try:
        product_order = get_object_or_404(ProductOrder, id=order_id, requested_by=request.user)
        
        if product_order.status in ['draft']:
            # Supprimer complètement si c'est un brouillon
            product_order.delete()
        else:
            # Marquer comme annulée sinon
            product_order.status = 'cancelled'
            product_order.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_http_methods(["POST"])
def mark_product_order_ordered(request, order_id):
    """Marquer une commande comme commandée"""
    if request.user.role not in ['department_chef', 'head_chef', 'admin']:
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'})
    
    try:
        product_order = get_object_or_404(ProductOrder, id=order_id, requested_by=request.user)
        
        if product_order.status != 'approved':
            return JsonResponse({'success': False, 'error': 'Cette commande doit être approuvée avant d\'être commandée'})
        
        product_order.status = 'ordered'
        product_order.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_http_methods(["POST"])
def mark_product_order_received(request, order_id):
    """Marquer une commande comme reçue"""
    if request.user.role not in ['department_chef', 'head_chef', 'admin']:
        return JsonResponse({'success': False, 'error': 'Accès non autorisé'})
    
    try:
        product_order = get_object_or_404(ProductOrder, id=order_id, requested_by=request.user)
        
        if product_order.status != 'ordered':
            return JsonResponse({'success': False, 'error': 'Cette commande doit être commandée avant d\'être marquée comme reçue'})
        
        product_order.status = 'received'
        product_order.delivery_date = timezone.now().date()
        product_order.save()
        
        # Mettre à jour le stock des produits
        for item in product_order.items.all():
            item.received_quantity = item.quantity
            item.received_at = timezone.now()
            item.save()
            
            # Ajouter au stock
            product = item.product
            product.current_stock += item.quantity
            product.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    

# views.py - Ajouter cette vue

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json

@login_required
@require_POST
def mark_notification_read(request, notification_id):
    """Marquer une notification comme lue"""
    try:
        notification = get_object_or_404(
            KitchenNotification, 
            id=notification_id,
            recipient=request.user
        )
        
        if not notification.is_read:
            notification.mark_as_read()
            
        return JsonResponse({
            'success': True,
            'message': 'Notification marquée comme lue'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@login_required
def mark_all_notifications_read(request):
    """Marquer toutes les notifications comme lues"""
    try:
        unread_notifications = KitchenNotification.objects.filter(
            recipient=request.user,
            is_read=False
        )
        
        count = unread_notifications.count()
        unread_notifications.update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return JsonResponse({
            'success': True,
            'message': f'{count} notifications marquées comme lues'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

# Ajouter ces vues dans votre fichier kitchen_views.py

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime

@login_required
def get_order_items(request, order_number):
    """Récupère les items d'une commande pour l'affichage dans le modal"""
    if request.user.role not in ['head_chef', 'admin']:
        return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    
    try:
        order = Order.objects.get(order_number=order_number)
        items = []
        
        for item in order.items.all():
            items.append({
                'id': item.id,
                'product_name': item.product_name,
                'quantity': item.quantity,
                'department': item.department or 'autres',
                'order_number': order.order_number,
                'delivery_date': order.delivery_date.strftime('%Y-%m-%d'),
                'delivery_time': order.delivery_time.strftime('%H:%M'),
                'notes': item.notes
            })
        
        return JsonResponse({
            'success': True,
            'order_number': order.order_number,
            'delivery_date': order.delivery_date.strftime('%Y-%m-%d'),
            'customer': f"{order.first_name} {order.last_name}",
            'items': items
        })
        
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Commande non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
def create_production_from_order(request, order_number):
    """Crée automatiquement la production, les items et les contrôles qualité depuis une commande"""
    if request.user.role not in ['head_chef', 'admin']:
        return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    
    try:
        # Récupérer les données
        data = json.loads(request.body)
        selected_departments = data.get('departments', [])
        create_quality_check = data.get('create_quality_check', True)
        
        # Récupérer la commande
        order = Order.objects.get(order_number=order_number)
        
        # Statistiques pour le retour
        created_productions = []
        created_items = 0
        created_checks = 0
        
        # Pour chaque département sélectionné
        for dept in selected_departments:
            # Récupérer ou créer la production pour ce département et cette date
            production, created = KitchenProduction.objects.get_or_create(
                date=order.delivery_date,
                department=dept,
                defaults={
                    'department_chef': request.user if request.user.role == 'head_chef' else None,
                    'status': 'not_started',
                    'notes': f'Production créée automatiquement depuis la commande {order.order_number}'
                }
            )
            
            if created:
                created_productions.append(dept)
            
            # Récupérer les items de la commande pour ce département
            order_items = order.items.filter(department=dept)
            
            for order_item in order_items:
                # Vérifier si un ProductionItem existe déjà
                production_item, item_created = ProductionItem.objects.get_or_create(
                    production=production,
                    order_item=order_item,
                    defaults={
                        'quantity_to_produce': order_item.quantity,
                        'is_priority': order.delivery_time.hour < 12,  # Prioritaire si livraison le matin
                        'production_notes': f'Commande {order.order_number} - {order.first_name} {order.last_name}'
                    }
                )
                
                if item_created:
                    created_items += 1
                    
                    # Créer le contrôle qualité si demandé
                    if create_quality_check:
                        quality_check = QualityCheck.objects.create(
                            production_item=production_item,
                            appearance_rating=3,  # Note par défaut
                            taste_rating=3,
                            texture_rating=3,
                            overall_rating=3,
                            meets_standards=True,
                            approved_for_service=True,
                            comments='Contrôle qualité à effectuer',
                            checked_by=request.user
                        )
                        created_checks += 1
            
            # Mettre à jour les statistiques de la production
            production.update_progress()
        
        # Message de succès
        message = f"Créé: {len(created_productions)} production(s), {created_items} item(s)"
        if create_quality_check:
            message += f", {created_checks} contrôle(s) qualité"
        
        # Créer une notification
        KitchenNotification.objects.create(
            type='general',
            recipient_type='head_chef',
            recipient=request.user,
            title='Production créée',
            message=f'Production créée pour la commande {order.order_number}',
            is_urgent=False
        )
        
        return JsonResponse({
            'success': True,
            'message': message,
            'created_productions': created_productions,
            'created_items': created_items,
            'created_checks': created_checks
        })
        
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Commande non trouvée'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Données JSON invalides'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def check_production_exists(request, order_number):
    """Vérifie si une production existe déjà pour une commande"""
    if request.user.role not in ['head_chef', 'admin']:
        return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    
    try:
        order = Order.objects.get(order_number=order_number)
        
        # Vérifier s'il existe des ProductionItems pour cette commande
        existing_items = ProductionItem.objects.filter(
            order_item__order=order
        ).select_related('production')
        
        if existing_items.exists():
            departments = {}
            for item in existing_items:
                dept = item.production.department
                if dept not in departments:
                    departments[dept] = {
                        'total': 0,
                        'completed': 0,
                        'progress': item.production.progress_percentage
                    }
                departments[dept]['total'] += 1
                if item.is_completed:
                    departments[dept]['completed'] += 1
            
            return JsonResponse({
                'exists': True,
                'departments': departments
            })
        else:
            return JsonResponse({
                'exists': False
            })
            
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Commande non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def bulk_create_productions(request):
    """Crée des productions en masse pour plusieurs commandes"""
    if request.user.role not in ['head_chef', 'admin']:
        return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    
    try:
        data = json.loads(request.body)
        order_numbers = data.get('order_numbers', [])
        target_date = data.get('date', None)
        
        if target_date:
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        
        results = {
            'success': [],
            'errors': [],
            'total_productions': 0,
            'total_items': 0
        }
        
        for order_number in order_numbers:
            try:
                order = Order.objects.get(order_number=order_number)
                
                # Utiliser la date de livraison de la commande ou la date cible
                production_date = target_date or order.delivery_date
                
                # Grouper les items par département
                items_by_dept = {}
                for item in order.items.all():
                    dept = item.department or 'autres'
                    if dept not in items_by_dept:
                        items_by_dept[dept] = []
                    items_by_dept[dept].append(item)
                
                # Créer les productions
                for dept, items in items_by_dept.items():
                    production, created = KitchenProduction.objects.get_or_create(
                        date=production_date,
                        department=dept,
                        defaults={
                            'department_chef': request.user if request.user.role == 'head_chef' else None,
                            'status': 'not_started'
                        }
                    )
                    
                    if created:
                        results['total_productions'] += 1
                    
                    # Créer les items de production
                    for order_item in items:
                        production_item, item_created = ProductionItem.objects.get_or_create(
                            production=production,
                            order_item=order_item,
                            defaults={
                                'quantity_to_produce': order_item.quantity,
                                'is_priority': order.delivery_time.hour < 12
                            }
                        )
                        
                        if item_created:
                            results['total_items'] += 1
                    
                    production.update_progress()
                
                results['success'].append(order_number)
                
            except Order.DoesNotExist:
                results['errors'].append(f"Commande {order_number} non trouvée")
            except Exception as e:
                results['errors'].append(f"Erreur pour {order_number}: {str(e)}")
        
        return JsonResponse(results)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Données JSON invalides'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)