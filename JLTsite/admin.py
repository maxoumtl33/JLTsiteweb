from django.contrib import admin
from .models import *

from django.contrib import admin
from .models import ContactSubmission

@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    """Configuration de l'admin pour les soumissions"""
    
    list_display = [
        'full_name', 'email', 'phone', 'event_type', 
        'event_date', 'guest_count', 'is_processed', 'created_at'
    ]
    list_filter = ['event_type', 'is_processed', 'newsletter', 'created_at', 'event_date']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'company']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at']
    
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Nom complet'
    
    actions = ['mark_as_processed', 'mark_as_unprocessed']
    
    def mark_as_processed(self, request, queryset):
        queryset.update(is_processed=True)
        self.message_user(request, f"{queryset.count()} soumission(s) marquée(s) comme traitée(s).")
    mark_as_processed.short_description = "Marquer comme traité"
    
    def mark_as_unprocessed(self, request, queryset):
        queryset.update(is_processed=False)
        self.message_user(request, f"{queryset.count()} soumission(s) marquée(s) comme non traitée(s).")
    mark_as_unprocessed.short_description = "Marquer comme non traité"


# ========================================
# admin.py - Interface d'administration personnalisée
# ========================================

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta
import json

from .models import (
    User, Category, Product, Cart, CartItem,
    Order, OrderItem, Coupon, Review
)

# ========================================
# 1. ADMIN UTILISATEUR
# ========================================

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'email_verified', 'newsletter', 'created_at']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'company']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informations supplémentaires', {
            'fields': ('role', 'phone', 'company', 'address', 'postal_code', 'city', 'newsletter', 'email_verified')
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            orders_count=Count('orders'),
            total_spent=Sum('orders__total')
        )

# ========================================
# 2. ADMIN PRODUITS
# ========================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active', 'products_count', 'order']
    list_editable = ['is_active', 'order']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']
    
    def products_count(self, obj):
        return obj.products.count()
    products_count.short_description = 'Nombre de produits'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'thumbnail', 'name', 'category', 'formatted_price', 
        'stock_status', 'is_featured', 'is_active', 'sales_count'
    ]
    list_filter = [
        'category', 'status', 'is_vegetarian', 'is_vegan', 
        'is_gluten_free', 'is_featured', 'is_active'
    ]
    list_editable = ['is_featured', 'is_active']
    search_fields = ['name', 'description', 'ingredients']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['views_count', 'sales_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'slug', 'category', 'description', 'ingredients', 'allergens')
        }),
        ('Prix et Stock', {
            'fields': ('price', 'promo_price', 'stock', 'min_order', 'status')
        }),
        ('Images', {
            'fields': ('image', 'image_2', 'image_3')
        }),
        ('Informations nutritionnelles', {
            'fields': ('calories', 'preparation_time', 'is_vegetarian', 'is_vegan', 'is_gluten_free')
        }),
        ('Visibilité', {
            'fields': ('is_featured', 'is_active')
        }),
        ('Statistiques', {
            'fields': ('views_count', 'sales_count', 'created_at', 'updated_at')
        }),
    )
    
    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;"/>',
                obj.image.url
            )
        return '-'
    thumbnail.short_description = 'Aperçu'
    
    def formatted_price(self, obj):
        if obj.promo_price:
            return format_html(
                '<span style="text-decoration: line-through; color: #999;">${}</span> '
                '<span style="color: #28a745; font-weight: bold;">${}</span>',
                obj.price, obj.promo_price
            )
        return f"${obj.price}"
    formatted_price.short_description = 'Prix'
    
    def stock_status(self, obj):
        if obj.stock == 0:
            color = 'red'
            text = 'Rupture'
        elif obj.stock < 10:
            color = 'orange'
            text = f'Faible ({obj.stock})'
        else:
            color = 'green'
            text = f'En stock ({obj.stock})'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, text
        )
    stock_status.short_description = 'Stock'

# ========================================
# 3. ADMIN COMMANDES
# ========================================

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'product_price', 'quantity', 'subtotal']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_number', 'customer_name', 'status_badge', 
        'delivery_info', 'formatted_total', 'created_at'
    ]
    list_filter = ['status', 'delivery_type', 'payment_status', 'created_at', 'delivery_date']
    search_fields = ['order_number', 'email', 'phone', 'first_name', 'last_name']
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline]
    
    readonly_fields = [
        'order_number', 'user', 'created_at', 'updated_at',
        'subtotal', 'tax_amount', 'total'
    ]
    
    fieldsets = (
        ('Informations de commande', {
            'fields': ('order_number', 'user', 'status', 'created_at', 'updated_at')
        }),
        ('Client', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'company')
        }),
        ('Livraison', {
            'fields': (
                'delivery_type', 'delivery_address', 'delivery_postal_code',
                'delivery_city', 'delivery_date', 'delivery_time', 'delivery_notes'
            )
        }),
        ('Montants', {
            'fields': (
                'subtotal', 'tax_rate', 'tax_amount', 'delivery_fee',
                'discount_amount', 'total'
            )
        }),
        ('Paiement', {
            'fields': ('payment_method', 'payment_status', 'transaction_id')
        }),
        ('Notes internes', {
            'fields': ('admin_notes',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_confirmed', 'mark_as_preparing', 'mark_as_ready', 'mark_as_delivered']
    
    def customer_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    customer_name.short_description = 'Client'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'confirmed': '#17a2b8',
            'preparing': '#fd7e14',
            'ready': '#6f42c1',
            'delivered': '#28a745',
            'cancelled': '#dc3545',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def delivery_info(self, obj):
        icon = '🚚' if obj.delivery_type == 'delivery' else '🏪'
        return format_html(
            '{} {} à {}',
            icon,
            obj.delivery_date.strftime('%d/%m'),
            obj.delivery_time.strftime('%H:%M')
        )
    delivery_info.short_description = 'Livraison'
    
    def formatted_total(self, obj):
        return f"${obj.total}"
    formatted_total.short_description = 'Total'
    formatted_total.admin_order_field = 'total'
    
    def mark_as_confirmed(self, request, queryset):
        queryset.update(status='confirmed', confirmed_at=timezone.now())
    mark_as_confirmed.short_description = "Marquer comme confirmée"
    
    def mark_as_preparing(self, request, queryset):
        queryset.update(status='preparing')
    mark_as_preparing.short_description = "Marquer comme en préparation"
    
    def mark_as_ready(self, request, queryset):
        queryset.update(status='ready')
    mark_as_ready.short_description = "Marquer comme prête"
    
    def mark_as_delivered(self, request, queryset):
        queryset.update(status='delivered', delivered_at=timezone.now())
    mark_as_delivered.short_description = "Marquer comme livrée"

# ========================================
# 4. ADMIN PANIERS
# ========================================

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'get_subtotal']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'items_count', 'cart_total', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__email', 'user__username', 'session_key']
    inlines = [CartItemInline]
    
    def items_count(self, obj):
        return obj.get_items_count()
    items_count.short_description = 'Articles'
    
    def cart_total(self, obj):
        return f"${obj.get_total()}"
    cart_total.short_description = 'Total'

# ========================================
# 5. ADMIN COUPONS
# ========================================

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'discount_display', 'minimum_amount',
        'usage_display', 'validity_display', 'is_active'
    ]
    list_filter = ['is_active', 'discount_type', 'valid_from', 'valid_until']
    search_fields = ['code', 'description']
    list_editable = ['is_active']
    
    def discount_display(self, obj):
        if obj.discount_type == 'percentage':
            return f"{obj.discount_value}%"
        return f"${obj.discount_value}"
    discount_display.short_description = 'Réduction'
    
    def usage_display(self, obj):
        if obj.usage_limit == 0:
            return f"{obj.usage_count} / ∞"
        return f"{obj.usage_count} / {obj.usage_limit}"
    usage_display.short_description = 'Utilisation'
    
    def validity_display(self, obj):
        now = timezone.now()
        if now < obj.valid_from:
            return format_html('<span style="color: orange;">Pas encore valide</span>')
        elif now > obj.valid_until:
            return format_html('<span style="color: red;">Expiré</span>')
        else:
            return format_html('<span style="color: green;">Valide</span>')
    validity_display.short_description = 'Validité'

# ========================================
# 6. ADMIN REVIEWS
# ========================================

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating_stars', 'is_verified_purchase', 'created_at']
    list_filter = ['rating', 'is_verified_purchase', 'created_at']
    search_fields = ['product__name', 'user__username', 'comment']
    readonly_fields = ['is_verified_purchase']
    
    def rating_stars(self, obj):
        stars = '⭐' * obj.rating + '☆' * (5 - obj.rating)
        return format_html(
            '<span style="color: #ffc107; font-size: 16px;">{}</span>',
            stars
        )
    rating_stars.short_description = 'Note'

# ========================================
# 7. PERSONNALISATION DU SITE ADMIN
# ========================================

admin.site.site_header = "Julien-Leblanc Traiteur - Administration"
admin.site.site_title = "JLT Admin"
admin.site.index_title = "Tableau de bord"