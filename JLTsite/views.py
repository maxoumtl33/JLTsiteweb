from django.shortcuts import render, redirect


def home(request):
    

    return render(request, 'JLTsite/home.html', {
        
    })

def repas(request):

    return render(request, 'JLTsite/repas.html', {

    })


def evenement(request):

    return render(request, 'JLTsite/evenement.html', {

    })



from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
from .models import *
from .forms import *

def contacts(request):
    """Vue pour afficher la page de contact"""
    form = ContactForm()
    return render(request, 'JLTsite/contacts.html', {'form': form})

@csrf_exempt  # Pour l'API - à utiliser avec précaution
def submit_contact_api(request):
    """API endpoint pour soumettre le formulaire via AJAX"""
    
    if request.method == 'POST':
        try:
            # Parser les données JSON
            data = json.loads(request.body) if request.body else request.POST
            
            # Créer l'instance du formulaire
            form = ContactForm(data)
            
            if form.is_valid():
                # Sauvegarder la soumission
                submission = form.save()
                
                # Envoyer les emails
                send_contact_emails(submission)
                
                return JsonResponse({
                    'success': True,
                    'message': 'Votre demande a été envoyée avec succès!'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'errors': form.errors,
                    'message': 'Veuillez corriger les erreurs dans le formulaire.'
                }, status=400)
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Une erreur est survenue: {str(e)}'
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

def submit_contact_form(request):
    """Vue pour soumettre le formulaire (POST standard)"""
    
    if request.method == 'POST':
        form = ContactForm(request.POST)
        
        if form.is_valid():
            # Sauvegarder la soumission
            submission = form.save()
            
            # Envoyer les emails
            try:
                send_contact_emails(submission)
                messages.success(request, 'Votre demande a été envoyée avec succès! Nous vous contacterons bientôt.')
            except Exception as e:
                messages.warning(request, 'Votre demande a été enregistrée mais l\'email n\'a pas pu être envoyé.')
            
            return redirect('contact_success')
        else:
            messages.error(request, 'Veuillez corriger les erreurs dans le formulaire.')
    else:
        form = ContactForm()
    
    return render(request, 'JLTsite/contact.html', {'form': form})

def send_contact_emails(submission):
    """Envoyer les emails de notification"""
    
    # 1. Email de confirmation au client
    send_client_confirmation(submission)
    
    # 2. Email de notification à l'équipe
    send_team_notification(submission)

def send_client_confirmation(submission):
    """Envoyer un email de confirmation au client"""
    
    subject = f'Confirmation de votre demande - Julien-Leblanc Traiteur'
    
    # Contexte pour le template
    context = {
        'submission': submission,
        'first_name': submission.first_name,
    }
    
    # Générer le contenu HTML et texte
    html_content = render_to_string('JLTsite/client_confirmation.html', context)
    text_content = strip_tags(html_content)
    
    # Créer l'email
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.EMAIL_HOST_USER,
        to=[submission.email],
    )
    email.attach_alternative(html_content, "text/html")
    email.send()

def send_team_notification(submission):
    """Envoyer une notification à l'équipe"""
    
    subject = f'Nouvelle demande de soumission - {submission.first_name} {submission.last_name}'
    
    # Contexte pour le template
    context = {
        'submission': submission,
    }
    
    # Générer le contenu HTML et texte
    html_content = render_to_string('JLTsite/team_notification.html', context)
    text_content = strip_tags(html_content)
    
    # Liste des destinataires de l'équipe
    team_emails = [
        settings.EMAIL_HOST_USER,  # Email principal
        # Ajouter d'autres emails de l'équipe ici
    ]
    
    # Créer l'email
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.EMAIL_HOST_USER,
        to=team_emails,
    )
    email.attach_alternative(html_content, "text/html")
    email.send()

def contact_success(request):
    """Page de succès après soumission"""
    return render(request, 'JLTsite/contact_success.html')



# ========================================
# views.py - Vues pour le système e-commerce
# ========================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from decimal import Decimal
import json
from datetime import datetime, timedelta

from .models import (
    User, Product, Category, Cart, CartItem,
    Order, OrderItem, Coupon, Review
)
from .forms import (
    SignUpForm, LoginForm, CheckoutForm,
    ReviewForm, ProfileForm
)

# ========================================
# 1. VUES AUTHENTIFICATION
# ========================================

def signup_view(request):
    """Inscription d'un nouvel utilisateur"""
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'customer'
            user.save()
            
            # Connexion automatique après inscription
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            
            # Transférer le panier de session vers l'utilisateur
            transfer_cart_to_user(request, user)
            
            messages.success(request, 'Bienvenue! Votre compte a été créé avec succès.')
            return redirect('shop_boites_lunch')
    else:
        form = SignUpForm()
    
    return render(request, 'JLTsite/signup.html', {'form': form})

def login_view(request):
    """Connexion utilisateur"""
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                transfer_cart_to_user(request, user)
                
                # Redirection selon le rôle
                if user.role in ['admin', 'staff']:
                    return redirect('admin_dashboard')
                
                next_url = request.GET.get('next', 'customer_dashboard')
                return redirect(next_url)
            else:
                messages.error(request, 'Identifiants invalides.')
    else:
        form = LoginForm()
    
    return render(request, 'JLTsite/login.html', {'form': form})

def logout_view(request):
    """Déconnexion"""
    logout(request)
    messages.info(request, 'Vous avez été déconnecté.')
    return redirect('home')

# ========================================
# 2. VUES BOUTIQUE
# ========================================
@login_required(login_url='login')
def shop_view(request):
    """Page principale de la boutique"""
    # Filtres
    category_slug = request.GET.get('category')
    search_query = request.GET.get('q')
    sort_by = request.GET.get('sort', '-created_at')
    dietary = request.GET.getlist('dietary')
    
    # Requête de base
    products = Product.objects.filter(is_active=True)
    
    # Appliquer les filtres
    if category_slug:
        products = products.filter(category__slug=category_slug)
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(ingredients__icontains=search_query)
        )
    
    if 'vegetarian' in dietary:
        products = products.filter(is_vegetarian=True)
    if 'vegan' in dietary:
        products = products.filter(is_vegan=True)
    if 'gluten_free' in dietary:
        products = products.filter(is_gluten_free=True)
    
    # Tri
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    elif sort_by == 'popular':
        products = products.order_by('-sales_count')
    elif sort_by == 'rating':
        products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    else:
        products = products.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(products, 12)
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    # Catégories pour le menu
    categories = Category.objects.filter(is_active=True).order_by('order')
    
    # Produits populaires
    featured_products = Product.objects.filter(
        is_active=True,
        is_featured=True
    ).order_by('-sales_count')[:4]
    
    context = {
        'products': products,
        'categories': categories,
        'featured_products': featured_products,
        'current_category': category_slug,
        'search_query': search_query,
        'sort_by': sort_by,
        'dietary': dietary,
    }
    
    return render(request, 'JLTsite/boiteslunch.html', context)

def product_detail_view(request, slug):
    """Détail d'un produit"""
    product = get_object_or_404(Product, slug=slug, is_active=True)
    
    # Incrémenter les vues
    product.views_count += 1
    product.save()
    
    # Avis
    reviews = product.reviews.all().order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Produits similaires
    similar_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id)[:4]
    
    # Vérifier si l'utilisateur peut laisser un avis
    can_review = False
    if request.user.is_authenticated:
        # Vérifier si l'utilisateur a acheté ce produit
        has_purchased = OrderItem.objects.filter(
            order__user=request.user,
            order__status='delivered',
            product=product
        ).exists()
        
        # Vérifier s'il n'a pas déjà laissé un avis
        has_reviewed = Review.objects.filter(
            user=request.user,
            product=product
        ).exists()
        
        can_review = has_purchased and not has_reviewed
    
    context = {
        'product': product,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'similar_products': similar_products,
        'can_review': can_review,
    }
    
    return render(request, 'JLTsite/product_detail.html', context)

# ========================================
# 3. VUES PANIER
# ========================================

def get_or_create_cart(request):
    """Obtenir ou créer un panier pour l'utilisateur/session"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart

def transfer_cart_to_user(request, user):
    """Transférer le panier de session vers l'utilisateur connecté"""
    session_key = request.session.session_key
    if session_key:
        try:
            session_cart = Cart.objects.get(session_key=session_key)
            user_cart, created = Cart.objects.get_or_create(user=user)
            
            # Transférer les articles
            for item in session_cart.items.all():
                user_item, created = CartItem.objects.get_or_create(
                    cart=user_cart,
                    product=item.product,
                    defaults={'quantity': item.quantity, 'notes': item.notes}
                )
                if not created:
                    user_item.quantity += item.quantity
                    user_item.save()
            
            # Supprimer le panier de session
            session_cart.delete()
        except Cart.DoesNotExist:
            pass

def cart_view(request):
    """Afficher le panier"""
    cart = get_or_create_cart(request)
    
    # Calculer les totaux
    subtotal = cart.get_total()
    tax_rate = Decimal('14.975')
    tax_amount = subtotal * (tax_rate / 100)
    delivery_fee = Decimal('5.00') if subtotal < 50 else Decimal('0.00')
    total = subtotal + tax_amount + delivery_fee
    
    context = {
        'cart': cart,
        'subtotal': subtotal,
        'tax_amount': tax_amount,
        'delivery_fee': delivery_fee,
        'total': total,
    }
    
    return render(request, 'JLTsite/cart.html', context)

@require_POST
def add_to_cart(request):
    """Ajouter un produit au panier (AJAX)"""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = int(data.get('quantity', 1))
        notes = data.get('notes', '')
        
        product = get_object_or_404(Product, id=product_id, is_active=True)
        
        # Vérifier le stock
        if not product.is_in_stock():
            return JsonResponse({'success': False, 'message': 'Produit en rupture de stock'})
        
        if quantity > product.stock:
            return JsonResponse({'success': False, 'message': f'Seulement {product.stock} disponibles'})
        
        cart = get_or_create_cart(request)
        
        # Ajouter ou mettre à jour l'article
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity, 'notes': notes}
        )
        
        if not created:
            cart_item.quantity += quantity
            if cart_item.quantity > product.stock:
                cart_item.quantity = product.stock
            cart_item.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Produit ajouté au panier',
            'cart_count': cart.get_items_count(),
            'cart_total': str(cart.get_total())
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@require_POST
def update_cart_item(request):
    """Mettre à jour la quantité d'un article (AJAX)"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        quantity = int(data.get('quantity'))
        
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        
        if quantity <= 0:
            cart_item.delete()
        else:
            if quantity > cart_item.product.stock:
                return JsonResponse({
                    'success': False,
                    'message': f'Seulement {cart_item.product.stock} disponibles'
                })
            cart_item.quantity = quantity
            cart_item.save()
        
        return JsonResponse({
            'success': True,
            'cart_count': cart.get_items_count(),
            'cart_total': str(cart.get_total()),
            'item_subtotal': str(cart_item.get_subtotal()) if quantity > 0 else '0'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@require_POST
def remove_from_cart(request):
    """Retirer un article du panier (AJAX)"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        cart = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        cart_item.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Article retiré du panier',
            'cart_count': cart.get_items_count(),
            'cart_total': str(cart.get_total())
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

# ========================================
# 4. VUES COMMANDE
# ========================================

@login_required
def checkout_view(request):
    """Page de commande"""
    cart = get_or_create_cart(request)
    
    if cart.items.count() == 0:
        messages.warning(request, 'Votre panier est vide.')
        return redirect('shop_boites_lunch')
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Créer la commande
            order = form.save(commit=False)
            order.user = request.user
            order.subtotal = cart.get_total()
            
            # Calculer les montants
            order.tax_amount = order.subtotal * (order.tax_rate / 100)
            order.delivery_fee = Decimal('5.00') if order.subtotal < 50 else Decimal('0.00')
            order.total = order.calculate_totals()
            order.save()
            
            # Créer les articles de commande
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_name=item.product.name,
                    product_price=item.product.get_price(),
                    quantity=item.quantity,
                    notes=item.notes
                )
                
                # Mettre à jour le stock et les ventes
                item.product.stock -= item.quantity
                item.product.sales_count += item.quantity
                item.product.save()
            
            # Vider le panier
            cart.items.all().delete()
            
            # Envoyer les emails
            send_order_confirmation_email(order)
            send_order_notification_to_admin(order)
            
            messages.success(request, 'Votre commande a été confirmée!')
            return redirect('order_confirmation', order_number=order.order_number)
    else:
        initial_data = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'phone': request.user.phone,
            'company': request.user.company,
            'delivery_address': request.user.address,
            'delivery_postal_code': request.user.postal_code,
            'delivery_city': request.user.city,
        }
        form = CheckoutForm(initial=initial_data)
    
    # Calculer les totaux
    subtotal = cart.get_total()
    tax_rate = Decimal('14.975')
    tax_amount = subtotal * (tax_rate / 100)
    delivery_fee = Decimal('5.00') if subtotal < 50 else Decimal('0.00')
    total = subtotal + tax_amount + delivery_fee
    
    context = {
        'form': form,
        'cart': cart,
        'subtotal': subtotal,
        'tax_amount': tax_amount,
        'delivery_fee': delivery_fee,
        'total': total,
    }
    
    return render(request, 'JLTsite/checkout.html', context)

def order_confirmation_view(request, order_number):
    """Page de confirmation de commande"""
    order = get_object_or_404(Order, order_number=order_number)
    
    # Vérifier que l'utilisateur a le droit de voir cette commande
    if request.user != order.user and not request.user.is_staff:
        messages.error(request, 'Vous n\'avez pas accès à cette commande.')
        return redirect('shop')
    
    return render(request, 'JLTsite/order_confirmation.html', {'order': order})

# ========================================
# 5. DASHBOARD CLIENT
# ========================================

@login_required
def customer_dashboard(request):
    """Tableau de bord client"""
    user = request.user
    
    # Commandes récentes
    recent_orders = Order.objects.filter(user=user).order_by('-created_at')[:5]
    
    # Statistiques
    stats = {
        'total_orders': Order.objects.filter(user=user).count(),
        'pending_orders': Order.objects.filter(user=user, status='pending').count(),
        'total_spent': Order.objects.filter(user=user).aggregate(Sum('total'))['total__sum'] or 0,
        'products_bought': OrderItem.objects.filter(order__user=user).aggregate(Sum('quantity'))['quantity__sum'] or 0,
    }
    
    context = {
        'user': user,
        'recent_orders': recent_orders,
        'stats': stats,
    }
    
    return render(request, 'JLTsite/customer_dashboard.html', context)

@login_required
def customer_orders(request):
    """Liste des commandes du client"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    # Filtres
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)
    
    # Pagination
    paginator = Paginator(orders, 10)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    
    return render(request, 'JLTsite/customer_orders.html', {'orders': orders})

@login_required
def customer_order_detail(request, order_number):
    """Détail d'une commande client"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    return render(request, 'JLTsite/customer_order_detail.html', {'order': order})

@login_required
def customer_profile(request):
    """Profil du client"""
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Votre profil a été mis à jour.')
            return redirect('customer_profile')
    else:
        form = ProfileForm(instance=request.user)
    
    return render(request, 'JLTsite/customer_profile.html', {'form': form})

# ========================================
# 6. EMAILS
# ========================================

def send_order_confirmation_email(order):
    """Envoyer l'email de confirmation au client"""
    subject = f'Confirmation de votre commande {order.order_number}'
    
    context = {
        'order': order,
        'site_url': settings.SITE_URL,
    }
    
    html_message = render_to_string('JLTsite/order_confirmation.html', context)
    plain_message = render_to_string('JLTsite/order_confirmation.txt', context)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[order.email],
        html_message=html_message,
        fail_silently=False,
    )

def send_order_notification_to_admin(order):
    """Envoyer une notification de nouvelle commande aux admins"""
    subject = f'Nouvelle commande {order.order_number}'
    
    context = {
        'order': order,
        'admin_url': f"{settings.SITE_URL}/admin/",
    }
    
    html_message = render_to_string('JLTsite/order_notification_admin.html', context)
    
    admin_emails = User.objects.filter(
        role__in=['admin', 'staff'],
        is_active=True
    ).values_list('email', flat=True)
    
    send_mail(
        subject=subject,
        message=f'Nouvelle commande reçue: {order.order_number}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=list(admin_emails),
        html_message=html_message,
        fail_silently=False,
    )

    