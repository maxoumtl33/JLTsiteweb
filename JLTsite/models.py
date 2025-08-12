# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
import string
import random
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, default='Montreal')
    postal_code = models.CharField(max_length=10, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    email_verified = models.BooleanField(default=False)
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='jltsite_user', # <-- change this
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='jltsite_user', # <-- change this
        blank=True,
    )
    
    def get_full_address(self):
        return f"{self.address}, {self.city} {self.postal_code}"

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return self.name

class LunchBox(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='lunch_boxes')
    description = models.TextField()
    ingredients = models.TextField(help_text="Liste des ingrédients")
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to='lunch_boxes/')
    thumbnail = models.ImageField(upload_to='lunch_boxes/thumbs/', blank=True)
    calories = models.IntegerField(null=True, blank=True)
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_gluten_free = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    preparation_time = models.IntegerField(help_text="Temps de préparation en minutes", default=30)
    min_order_quantity = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.IntegerField(default=0)
    sales_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Lunch Boxes'
    
    def __str__(self):
        return self.name
    
    def get_rating(self):
        reviews = self.reviews.filter(is_approved=True)
        if reviews:
            return reviews.aggregate(models.Avg('rating'))['rating__avg']
        return 0

class PromoCode(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Pourcentage'),
        ('fixed', 'Montant fixe'),
    ]
    
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_order = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    usage_limit = models.IntegerField(null=True, blank=True, help_text="Laisser vide pour illimité")
    usage_count = models.IntegerField(default=0)
    user_limit = models.IntegerField(default=1, help_text="Nombre d'utilisations par client")
    is_combinable = models.BooleanField(default=False, help_text="Peut être combiné avec d'autres codes")
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    applicable_products = models.ManyToManyField(LunchBox, blank=True, related_name='promo_codes')
    applicable_categories = models.ManyToManyField(Category, blank=True, related_name='promo_codes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.code
    
    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if now < self.valid_from or now > self.valid_until:
            return False
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False
        return True
    
    def calculate_discount(self, subtotal):
        if self.discount_type == 'percentage':
            return (subtotal * self.discount_value) / 100
        return min(self.discount_value, subtotal)

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_subtotal(self):
        return sum(item.get_total() for item in self.items.all())
    
    def get_total_with_discounts(self, promo_codes=[]):
        subtotal = self.get_subtotal()
        total_discount = Decimal('0')
        
        for code in promo_codes:
            if code.is_valid() and subtotal >= code.minimum_order:
                total_discount += code.calculate_discount(subtotal)
                if not code.is_combinable:
                    break
        
        return max(subtotal - total_discount, Decimal('0'))

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    lunch_box = models.ForeignKey(LunchBox, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    customization_notes = models.TextField(blank=True)
    added_at = models.DateTimeField(auto_now_add=True)
    
    def get_total(self):
        return self.lunch_box.price * self.quantity

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('confirmed', 'Confirmée'),
        ('preparing', 'En préparation'),
        ('ready', 'Prête'),
        ('delivered', 'Livrée'),
        ('cancelled', 'Annulée'),
    ]
    
    DELIVERY_TYPE_CHOICES = [
        ('pickup', 'Ramassage'),
        ('delivery', 'Livraison'),
    ]
    
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    delivery_type = models.CharField(max_length=20, choices=DELIVERY_TYPE_CHOICES)
    delivery_address = models.TextField()
    delivery_date = models.DateField()
    delivery_time = models.TimeField()
    special_instructions = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    promo_codes_used = models.ManyToManyField(PromoCode, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    payment_id = models.CharField(max_length=100, blank=True)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        prefix = timezone.now().strftime('%Y%m%d')
        random_suffix = ''.join(random.choices(string.digits, k=6))
        return f"CMD-{prefix}-{random_suffix}"
    
    def __str__(self):
        return f"Commande {self.order_number}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    lunch_box = models.ForeignKey(LunchBox, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    customization_notes = models.TextField(blank=True)
    
    def get_total(self):
        return self.unit_price * self.quantity

class Event(models.Model):
    EVENT_TYPE_CHOICES = [
        ('corporate', 'Corporatif'),
        ('wedding', 'Mariage'),
        ('birthday', 'Anniversaire'),
        ('other', 'Autre'),
    ]
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    description = models.TextField()
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=300)
    guest_count = models.IntegerField()
    menu_items = models.ManyToManyField(LunchBox, through='EventMenuItem')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    client = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='events')
    is_confirmed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.date}"

class EventMenuItem(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    lunch_box = models.ForeignKey(LunchBox, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    special_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

class Contact(models.Model):
    SUBJECT_CHOICES = [
        ('general', 'Question générale'),
        ('order', 'Commande'),
        ('event', 'Événement'),
        ('complaint', 'Réclamation'),
        ('other', 'Autre'),
    ]
    
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=20, choices=SUBJECT_CHOICES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    is_answered = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.subject}"

class Review(models.Model):
    lunch_box = models.ForeignKey(LunchBox, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['lunch_box', 'user', 'order']
        ordering = ['-created_at']

class Analytics(models.Model):
    date = models.DateField(unique=True)
    total_orders = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_customers = models.IntegerField(default=0)
    new_customers = models.IntegerField(default=0)
    returning_customers = models.IntegerField(default=0)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    most_sold_item = models.ForeignKey(LunchBox, on_delete=models.SET_NULL, null=True, blank=True)
    promo_codes_used = models.IntegerField(default=0)
    cancelled_orders = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Analytics'

# admin.py
from django.contrib import admin
from .models import *

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'company_name', 'date_joined', 'email_verified']
    search_fields = ['username', 'email', 'company_name']
    list_filter = ['email_verified', 'date_joined']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(LunchBox)
class LunchBoxAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'is_available', 'sales_count']
    list_filter = ['category', 'is_available', 'is_vegetarian', 'is_vegan', 'is_gluten_free']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'discount_value', 'is_combinable', 'is_active', 'usage_count']
    list_filter = ['is_active', 'is_combinable', 'discount_type']
    search_fields = ['code']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'user', 'status', 'total_amount', 'is_paid', 'created_at']
    list_filter = ['status', 'is_paid', 'delivery_type', 'created_at']
    search_fields = ['order_number', 'user__email']
    readonly_fields = ['order_number']

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['name', 'event_type', 'date', 'guest_count', 'is_confirmed']
    list_filter = ['event_type', 'is_confirmed', 'date']
    search_fields = ['name', 'client__email']

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'is_read', 'is_answered', 'created_at']
    list_filter = ['subject', 'is_read', 'is_answered', 'created_at']
    search_fields = ['name', 'email']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['lunch_box', 'user', 'rating', 'is_approved', 'created_at']
    list_filter = ['rating', 'is_approved', 'created_at']

@admin.register(Analytics)
class AnalyticsAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_orders', 'total_revenue', 'average_order_value']
    list_filter = ['date']

# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum, Avg
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.utils import timezone
from decimal import Decimal
import json

def calculate_cart_totals(cart, promo_codes=[]):
    """Calcule les totaux du panier avec taxes et promotions"""
    subtotal = cart.get_subtotal()
    discount = Decimal('0')
    
    # Appliquer les codes promo
    for code in promo_codes:
        if code.is_valid() and subtotal >= code.minimum_order:
            discount += code.calculate_discount(subtotal)
            if not code.is_combinable:
                break
    
    # Calcul des taxes (exemple: 14.975% pour Québec)
    TAX_RATE = Decimal('0.14975')
    subtotal_after_discount = subtotal - discount
    tax = subtotal_after_discount * TAX_RATE
    
    # Frais de livraison
    delivery_fee = Decimal('5.00') if subtotal < 50 else Decimal('0')
    
    total = subtotal_after_discount + tax + delivery_fee
    
    return {
        'subtotal': subtotal,
        'discount': discount,
        'tax': tax,
        'delivery_fee': delivery_fee,
        'total': total
    }

@require_POST
def add_to_cart(request, lunch_box_id):
    """Ajouter un article au panier"""
    lunch_box = get_object_or_404(LunchBox, id=lunch_box_id, is_available=True)
    quantity = int(request.POST.get('quantity', 1))
    customization = request.POST.get('customization', '')
    
    # Obtenir ou créer le panier
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.save()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    
    # Ajouter ou mettre à jour l'article
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        lunch_box=lunch_box,
        defaults={'quantity': quantity, 'customization_notes': customization}
    )
    
    if not created:
        cart_item.quantity += quantity
        cart_item.save()
    
    # Incrémenter le compteur de vues
    lunch_box.views_count += 1
    lunch_box.save()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_count': cart.items.count(),
            'message': f'{lunch_box.name} ajouté au panier'
        })
    
    messages.success(request, f'{lunch_box.name} a été ajouté au panier')
    return redirect('lunch_box_detail', slug=lunch_box.slug)

@require_POST
def apply_promo_code(request):
    """Appliquer un code promo au panier"""
    code = request.POST.get('promo_code', '').upper()
    
    try:
        promo = PromoCode.objects.get(code=code)
        
        if not promo.is_valid():
            return JsonResponse({'success': False, 'message': 'Code promo invalide ou expiré'})
        
        # Vérifier l'utilisation par utilisateur
        if request.user.is_authenticated:
            user_usage = Order.objects.filter(
                user=request.user,
                promo_codes_used=promo
            ).count()
            if user_usage >= promo.user_limit:
                return JsonResponse({'success': False, 'message': 'Vous avez déjà utilisé ce code'})
        
        # Stocker le code en session
        if 'promo_codes' not in request.session:
            request.session['promo_codes'] = []
        
        if code not in request.session['promo_codes']:
            if not promo.is_combinable and request.session['promo_codes']:
                return JsonResponse({'success': False, 'message': 'Ce code ne peut pas être combiné'})
            request.session['promo_codes'].append(code)
            request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'message': f'Code {code} appliqué avec succès',
            'discount_type': promo.discount_type,
            'discount_value': float(promo.discount_value)
        })
        
    except PromoCode.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Code promo invalide'})

@login_required
def checkout(request):
    """Page de paiement"""
    cart = get_object_or_404(Cart, user=request.user)
    
    if not cart.items.exists():
        messages.warning(request, 'Votre panier est vide')
        return redirect('lunch_boxes')
    
    # Récupérer les codes promo de la session
    promo_codes = []
    if 'promo_codes' in request.session:
        promo_codes = PromoCode.objects.filter(
            code__in=request.session['promo_codes'],
            is_active=True
        )
    
    # Calculer les totaux
    totals = calculate_cart_totals(cart, promo_codes)
    
    if request.method == 'POST':
        # Créer la commande
        order = Order.objects.create(
            user=request.user,
            delivery_type=request.POST.get('delivery_type'),
            delivery_address=request.POST.get('delivery_address'),
            delivery_date=request.POST.get('delivery_date'),
            delivery_time=request.POST.get('delivery_time'),
            special_instructions=request.POST.get('special_instructions', ''),
            subtotal=totals['subtotal'],
            discount_amount=totals['discount'],
            delivery_fee=totals['delivery_fee'],
            tax_amount=totals['tax'],
            total_amount=totals['total']
        )
        
        # Ajouter les articles de la commande
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                lunch_box=item.lunch_box,
                quantity=item.quantity,
                unit_price=item.lunch_box.price,
                customization_notes=item.customization_notes
            )
            # Incrémenter les ventes
            item.lunch_box.sales_count += item.quantity
            item.lunch_box.save()
        
        # Ajouter les codes promo utilisés
        order.promo_codes_used.set(promo_codes)
        for promo in promo_codes:
            promo.usage_count += 1
            promo.save()
        
        # Vider le panier et la session
        cart.items.all().delete()
        request.session.pop('promo_codes', None)
        
        # Mise à jour des analytics
        update_daily_analytics()
        
        messages.success(request, f'Commande {order.order_number} créée avec succès')
        return redirect('order_confirmation', order_number=order.order_number)
    
    context = {
        'cart': cart,
        'totals': totals,
        'promo_codes': promo_codes
    }
    return render(request, 'checkout.html', context)

def update_daily_analytics():
    """Met à jour les statistiques quotidiennes"""
    today = timezone.now().date()
    analytics, created = Analytics.objects.get_or_create(date=today)
    
    # Statistiques du jour
    daily_orders = Order.objects.filter(created_at__date=today)
    
    analytics.total_orders = daily_orders.count()
    analytics.total_revenue = daily_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    analytics.cancelled_orders = daily_orders.filter(status='cancelled').count()
    
    # Clients
    customers = daily_orders.values('user').distinct()
    analytics.total_customers = customers.count()
    
    # Nouveaux vs anciens clients
    new_customers = 0
    for order in daily_orders:
        if order.user:
            first_order = Order.objects.filter(user=order.user).order_by('created_at').first()
            if first_order.created_at.date() == today:
                new_customers += 1
    
    analytics.new_customers = new_customers
    analytics.returning_customers = analytics.total_customers - new_customers
    
    # Valeur moyenne des commandes
    if analytics.total_orders > 0:
        analytics.average_order_value = analytics.total_revenue / analytics.total_orders
    
    # Article le plus vendu
    top_item = OrderItem.objects.filter(
        order__created_at__date=today
    ).values('lunch_box').annotate(
        total_qty=Sum('quantity')
    ).order_by('-total_qty').first()
    
    if top_item:
        analytics.most_sold_item_id = top_item['lunch_box']
    
    # Codes promo utilisés
    analytics.promo_codes_used = daily_orders.filter(
        promo_codes_used__isnull=False
    ).distinct().count()
    
    analytics.save()

