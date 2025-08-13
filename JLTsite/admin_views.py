
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
    """Liste des commandes avec filtres"""
    
    orders = Order.objects.all().order_by('-created_at')
    
    # Filtres
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
    
    # Statistiques
    stats = {
        'total': orders.count(),
        'pending': orders.filter(status='pending').count(),
        'confirmed': orders.filter(status='confirmed').count(),
        'preparing': orders.filter(status='preparing').count(),
        'ready': orders.filter(status='ready').count(),
        'delivered': orders.filter(status='delivered').count(),
        'cancelled': orders.filter(status='cancelled').count(),
    }
    
    context = {
        'orders': orders,
        'stats': stats,
        'current_status': status,
        'current_date': date_filter,
        'search_query': search,
    }
    
    return render(request, 'JLTsite/orders_list.html', context)

@user_passes_test(admin_required)
def admin_order_detail(request, order_number):
    """Détail et gestion d'une commande"""
    order = get_object_or_404(Order, order_number=order_number)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_status':
            new_status = request.POST.get('status')
            order.status = new_status
            
            if new_status == 'confirmed':
                order.confirmed_at = timezone.now()
            elif new_status == 'delivered':
                order.delivered_at = timezone.now()
            
            order.save()
            
            # Envoyer un email au client
            send_order_status_email(order)
            
            messages.success(request, f'Statut mis à jour: {order.get_status_display()}')
            
        elif action == 'add_note':
            note = request.POST.get('admin_notes')
            order.admin_notes = note
            order.save()
            messages.success(request, 'Note ajoutée')
    
    return render(request, 'JLTsite/order_detail.html', {'order': order})

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
    """Liste des produits avec gestion du stock"""
    
    products = Product.objects.all().order_by('-created_at')
    
    # Filtres
    category = request.GET.get('category')
    stock_filter = request.GET.get('stock')
    search = request.GET.get('search')
    
    if category:
        products = products.filter(category__slug=category)
    
    if stock_filter == 'low':
        products = products.filter(stock__lt=10)
    elif stock_filter == 'out':
        products = products.filter(stock=0)
    
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
        'current_category': category,
        'stock_filter': stock_filter,
        'search_query': search,
    }
    
    return render(request, 'JLTsite/products_list.html', context)

@user_passes_test(admin_required)
def admin_product_update_stock(request):
    """Mise à jour rapide du stock (AJAX)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            new_stock = int(data.get('stock'))
            
            product = Product.objects.get(id=product_id)
            product.stock = new_stock
            
            # Mettre à jour le statut si nécessaire
            if new_stock == 0:
                product.status = 'rupture'
            elif product.status == 'rupture' and new_stock > 0:
                product.status = 'disponible'
            
            product.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Stock mis à jour: {new_stock}',
                'status': product.status
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})

# ========================================
# 5. RAPPORTS ET ANALYSES
# ========================================

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
    ).extra(
        select={'hour': 'EXTRACT(hour FROM created_at)'}
    ).values('hour').annotate(
        count=Count('id')
    ).order_by('hour')
    
    # Analyse des jours de la semaine
    orders_by_weekday = Order.objects.filter(
        created_at__gte=start_date
    ).extra(
        select={'weekday': 'EXTRACT(dow FROM created_at)'}
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
    """Exporter les données en CSV/Excel"""
    
    export_type = request.GET.get('type', 'orders')
    format_type = request.GET.get('format', 'csv')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    import csv
    from django.http import HttpResponse
    
    if export_type == 'orders':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="commandes_{timezone.now().date()}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Numéro', 'Date', 'Client', 'Email', 'Téléphone',
            'Statut', 'Total', 'Type livraison', 'Date livraison'
        ])
        
        orders = Order.objects.all()
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
                order.get_status_display(),
                order.total,
                order.get_delivery_type_display(),
                order.delivery_date.strftime('%d/%m/%Y')
            ])
        
        return response
    
    elif export_type == 'products':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="produits_{timezone.now().date()}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Nom', 'Catégorie', 'Prix', 'Stock', 'Ventes', 'Statut'
        ])
        
        for product in Product.objects.all():
            writer.writerow([
                product.name,
                product.category.name,
                product.price,
                product.stock,
                product.sales_count,
                product.get_status_display()
            ])
        
        return response
    
    return JsonResponse({'error': 'Type d\'export non valide'})

# ========================================
# 6. GESTION DES CLIENTS
# ========================================

@user_passes_test(admin_required)
def admin_customers_list(request):
    """Liste des clients"""
    
    customers = User.objects.filter(role='customer').annotate(
        orders_count=Count('orders'),
        total_spent=Sum('orders__total'),
        last_order=Max('orders__created_at')
    ).order_by('-created_at')
    
    # Filtres
    search = request.GET.get('search')
    if search:
        customers = customers.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(company__icontains=search)
        )
    
    context = {
        'customers': customers,
        'search_query': search,
    }
    
    return render(request, 'JLTsite/customers_list.html', context)

@user_passes_test(admin_required)
def admin_customer_detail(request, user_id):
    """Détail d'un client"""
    customer = get_object_or_404(User, id=user_id, role='customer')
    
    # Commandes du client
    orders = Order.objects.filter(user=customer).order_by('-created_at')
    
    # Statistiques
    stats = {
        'total_orders': orders.count(),
        'total_spent': orders.aggregate(Sum('total'))['total__sum'] or 0,
        'avg_order': orders.aggregate(Avg('total'))['total__avg'] or 0,
        'favorite_products': OrderItem.objects.filter(
            order__user=customer
        ).values(
            'product__name'
        ).annotate(
            times_ordered=Count('id'),
            total_quantity=Sum('quantity')
        ).order_by('-times_ordered')[:5]
    }
    
    context = {
        'customer': customer,
        'orders': orders,
        'stats': stats,
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
    
    html_message = render_to_string('emails/order_status_update.html', context)
    
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
        