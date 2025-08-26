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


from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from .models import (
    InventoryItem, OrderChecklist, ChecklistItem, 
    ChecklistTemplate, ChecklistTemplateItem, ChecklistNotification
)

# ========================================
# ADMIN POUR L'INVENTAIRE
# ========================================

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'stock_status', 'unit', 
        'min_stock', 'is_active', 'created_at'
    ]
    list_filter = ['category', 'is_active', 'created_at']
    list_editable = ['is_active']
    search_fields = ['name', 'description']
    ordering = ['category', 'name']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'category', 'description', 'unit')
        }),
        ('Stock', {
            'fields': ('stock_quantity', 'min_stock')
        }),
        ('Statut', {
            'fields': ('is_active',)
        }),
    )
    
    def stock_status(self, obj):
        if obj.stock_quantity == 0:
            color = 'red'
            text = 'Rupture'
        elif obj.is_low_stock():
            color = 'orange'
            text = f'Faible ({obj.stock_quantity})'
        else:
            color = 'green'
            text = f'OK ({obj.stock_quantity})'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, text
        )
    stock_status.short_description = 'Statut stock'
    
    actions = ['mark_as_inactive', 'mark_as_active', 'reset_stock']
    
    def mark_as_inactive(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} article(s) marqué(s) comme inactif(s).")
    mark_as_inactive.short_description = "Marquer comme inactif"
    
    def mark_as_active(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} article(s) marqué(s) comme actif(s).")
    mark_as_active.short_description = "Marquer comme actif"
    
    def reset_stock(self, request, queryset):
        for item in queryset:
            item.stock_quantity = 100  # Valeur par défaut
            item.save()
        self.message_user(request, f"Stock réinitialisé pour {queryset.count()} article(s).")
    reset_stock.short_description = "Réinitialiser le stock à 100"

# ========================================
# ADMIN POUR LES CHECKLISTS
# ========================================

class ChecklistItemInline(admin.TabularInline):
    model = ChecklistItem
    extra = 0
    fields = [
        'inventory_item', 'quantity_needed', 'quantity_prepared',
        'is_checked', 'checked_by', 'has_issue'
    ]
    readonly_fields = ['checked_by', 'checked_at']

@admin.register(OrderChecklist)
class OrderChecklistAdmin(admin.ModelAdmin):
    list_display = [
        'order_link', 'title', 'assigned_to', 'status_badge',
        'progress_bar', 'priority_badge', 'created_at'
    ]
    list_filter = ['status', 'priority', 'created_at', 'assigned_to']
    search_fields = [
        'order__order_number', 'title', 
        'assigned_to__first_name', 'assigned_to__last_name'
    ]
    inlines = [ChecklistItemInline]
    readonly_fields = [
        'order', 'created_by', 'created_at', 
        'started_at', 'completed_at', 'progress_percentage'
    ]
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('order', 'title', 'assigned_to', 'priority', 'status')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Progression', {
            'fields': (
                'total_items', 'completed_items', 'progress_percentage'
            )
        }),
        ('Historique', {
            'fields': (
                'created_by', 'created_at', 'started_at', 'completed_at'
            )
        }),
    )
    
    def order_link(self, obj):
        url = reverse('admin_order_detail', args=[obj.order.order_number])
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.order.order_number
        )
    order_link.short_description = 'Commande'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#6c757d',
            'in_progress': '#ffc107',
            'completed': '#28a745',
            'cancelled': '#dc3545',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def progress_bar(self, obj):
        return format_html(
            '<div style="width: 100px; height: 20px; background: #e9ecef; '
            'border-radius: 3px; overflow: hidden;">'
            '<div style="width: {}%; height: 100%; background: #28a745;"></div>'
            '</div>'
            '<small style="margin-left: 5px;">{}%</small>',
            obj.progress_percentage, obj.progress_percentage
        )
    progress_bar.short_description = 'Progression'
    
    def priority_badge(self, obj):
        if obj.priority == 1:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">🔥 URGENT</span>'
            )
        return format_html('<span style="color: #6c757d;">Normal</span>')
    priority_badge.short_description = 'Priorité'
    
    actions = ['update_progress', 'mark_as_completed', 'reassign_checklist']
    
    def update_progress(self, request, queryset):
        for checklist in queryset:
            checklist.update_progress()
        self.message_user(request, f"Progression mise à jour pour {queryset.count()} checklist(s).")
    update_progress.short_description = "Mettre à jour la progression"
    
    def mark_as_completed(self, request, queryset):
        from django.utils import timezone
        queryset.update(
            status='completed',
            completed_at=timezone.now(),
            progress_percentage=100
        )
        self.message_user(request, f"{queryset.count()} checklist(s) marquée(s) comme complétée(s).")
    mark_as_completed.short_description = "Marquer comme complétée"

# ========================================
# ADMIN POUR LES MODÈLES DE CHECKLIST
# ========================================

class ChecklistTemplateItemInline(admin.TabularInline):
    model = ChecklistTemplateItem
    extra = 1
    fields = ['inventory_item', 'default_quantity', 'notes', 'order']

@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'event_type', 'items_count', 'is_active', 'created_at']
    list_filter = ['event_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    inlines = [ChecklistTemplateItemInline]
    
    def items_count(self, obj):
        return obj.checklisttemplateitem_set.count()
    items_count.short_description = 'Nombre d\'articles'

# ========================================
# ADMIN POUR LES NOTIFICATIONS
# ========================================

@admin.register(ChecklistNotification)
class ChecklistNotificationAdmin(admin.ModelAdmin):
    list_display = [
        'checklist_order', 'type_badge', 'message',
        'is_read', 'created_at', 'created_by'
    ]
    list_filter = ['type', 'is_read', 'created_at']
    search_fields = ['message', 'checklist__order__order_number']
    readonly_fields = ['created_at', 'created_by']
    
    def checklist_order(self, obj):
        return obj.checklist.order.order_number
    checklist_order.short_description = 'Commande'
    
    def type_badge(self, obj):
        colors = {
            'issue': '#dc3545',
            'completed': '#28a745',
            'urgent': '#ffc107',
            'info': '#17a2b8',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.type, '#6c757d'),
            obj.get_type_display()
        )
    type_badge.short_description = 'Type'
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
        self.message_user(request, f"{queryset.count()} notification(s) marquée(s) comme lue(s).")
    mark_as_read.short_description = "Marquer comme lu"
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
        self.message_user(request, f"{queryset.count()} notification(s) marquée(s) comme non lue(s).")
    mark_as_unread.short_description = "Marquer comme non lu"

    # ========================================
# ADMIN POUR LE SYSTÈME DE LIVRAISON
# ========================================
# Ajouter ceci à votre admin.py existant

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from datetime import timedelta

from .models import (
    Delivery, DeliveryRoute, RouteDelivery, DeliveryPhoto,
    DriverPlanning, DeliveryNotification, DeliverySettings
)

# ========================================
# ADMIN LIVRAISONS
# ========================================

class DeliveryPhotoInline(admin.TabularInline):
    model = DeliveryPhoto
    extra = 0
    readonly_fields = ['photo_type', 'taken_at', 'taken_by', 'caption']
    fields = ['photo', 'photo_type', 'caption', 'taken_at', 'taken_by']

class RouteDeliveryInline(admin.TabularInline):
    model = RouteDelivery
    extra = 0
    readonly_fields = ['route', 'position', 'is_completed', 'completed_at']
    fields = ['route', 'position', 'estimated_arrival', 'estimated_departure', 'is_completed']

@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = [
        'delivery_number', 'type_badge', 'customer_name', 'status_badge',
        'scheduled_info', 'driver_info', 'priority_badge', 'created_at'
    ]
    list_filter = [
        'delivery_type', 'status', 'priority', 'scheduled_date',
        'has_checklist', 'checklist_completed'
    ]
    search_fields = [
        'delivery_number', 'customer_name', 'customer_phone',
        'customer_email', 'delivery_address', 'order__order_number'
    ]
    date_hierarchy = 'scheduled_date'
    readonly_fields = [
        'delivery_number', 'order', 'created_at', 'created_by',
        'delivered_at', 'delivered_by', 'signature', 'updated_at'
    ]
    inlines = [RouteDeliveryInline, DeliveryPhotoInline]
    
    fieldsets = (
        ('Informations de base', {
            'fields': (
                'delivery_number', 'order', 'parent_delivery',
                'delivery_type', 'status', 'priority'
            )
        }),
        ('Informations client', {
            'fields': (
                'customer_name', 'customer_phone', 'customer_email', 'company'
            )
        }),
        ('Adresse de livraison', {
            'fields': (
                'delivery_address', 'delivery_postal_code', 'delivery_city',
                'latitude', 'longitude', 'access_code', 'parking_info'
            )
        }),
        ('Planning', {
            'fields': (
                'scheduled_date', 'scheduled_time_start', 'scheduled_time_end',
                'estimated_duration'
            )
        }),
        ('Instructions et contenu', {
            'fields': (
                'delivery_instructions', 'items_description',
                'total_packages', 'weight'
            )
        }),
        ('Checklist', {
            'fields': ('has_checklist', 'checklist_completed')
        }),
        ('Validation', {
            'fields': (
                'delivered_at', 'delivered_by', 'delivery_notes',
                'signature', 'delivery_photo', 'pickup_photo'
            ),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': (
                'created_at', 'created_by', 'updated_at',
                'reminder_sent', 'reminder_sent_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'mark_as_assigned', 'mark_as_delivered', 'mark_as_failed',
        'send_reminder', 'create_pickup_delivery'
    ]
    
    def type_badge(self, obj):
        if obj.delivery_type == 'pickup':
            color = '#ffc107'
            icon = '♻️'
            text = 'Récupération'
        else:
            color = '#17a2b8'
            icon = '📦'
            text = 'Livraison'
        
        return format_html(
            '{} <span style="background: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            icon, color, text
        )
    type_badge.short_description = 'Type'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#6c757d',
            'assigned': '#17a2b8',
            'in_transit': '#ffc107',
            'delivered': '#28a745',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def priority_badge(self, obj):
        if obj.priority == 'urgent':
            return format_html('<span style="color: red;">🔥 URGENT</span>')
        elif obj.priority == 'high':
            return format_html('<span style="color: orange;">⚠️ Haute</span>')
        return format_html('<span style="color: gray;">Normal</span>')
    priority_badge.short_description = 'Priorité'
    
    def scheduled_info(self, obj):
        return format_html(
            '📅 {} <br> ⏰ {}-{}',
            obj.scheduled_date.strftime('%d/%m/%Y'),
            obj.scheduled_time_start.strftime('%H:%M'),
            obj.scheduled_time_end.strftime('%H:%M')
        )
    scheduled_info.short_description = 'Planification'
    
    def driver_info(self, obj):
        route = obj.route_assignments.first()
        if route:
            driver = route.route.driver
            return format_html(
                '👤 {} <br> 🚚 {}',
                driver.get_full_name(),
                route.route.route_number
            )
        return '-'
    driver_info.short_description = 'Livreur/Route'
    
    def mark_as_assigned(self, request, queryset):
        queryset.update(status='assigned')
        self.message_user(request, f"{queryset.count()} livraison(s) marquée(s) comme assignée(s).")
    mark_as_assigned.short_description = "Marquer comme assignée"
    
    def mark_as_delivered(self, request, queryset):
        queryset.update(status='delivered', delivered_at=timezone.now())
        self.message_user(request, f"{queryset.count()} livraison(s) marquée(s) comme livrée(s).")
    mark_as_delivered.short_description = "Marquer comme livrée"
    
    def mark_as_failed(self, request, queryset):
        queryset.update(status='failed')
        self.message_user(request, f"{queryset.count()} livraison(s) marquée(s) comme échouée(s).")
    mark_as_failed.short_description = "Marquer comme échouée"
    
    def send_reminder(self, request, queryset):
        count = 0
        for delivery in queryset:
            if not delivery.reminder_sent:
                # Logique d'envoi de rappel
                delivery.reminder_sent = True
                delivery.reminder_sent_at = timezone.now()
                delivery.save()
                count += 1
        self.message_user(request, f"{count} rappel(s) envoyé(s).")
    send_reminder.short_description = "Envoyer un rappel"

# ========================================
# ADMIN ROUTES DE LIVRAISON
# ========================================

class RouteDeliveryAdminInline(admin.TabularInline):
    model = RouteDelivery
    extra = 0
    fields = [
        'delivery', 'position', 'estimated_arrival', 'estimated_departure',
        'is_completed', 'distance_from_previous'
    ]
    readonly_fields = ['is_completed', 'completed_at']
    ordering = ['position']

@admin.register(DeliveryRoute)
class DeliveryRouteAdmin(admin.ModelAdmin):
    list_display = [
        'route_number', 'name', 'driver_name', 'date', 'status_badge',
        'deliveries_count', 'progress_info', 'vehicle'
    ]
    list_filter = ['status', 'date', 'driver', 'is_optimized']
    search_fields = ['route_number', 'name', 'driver__first_name', 'driver__last_name']
    date_hierarchy = 'date'
    readonly_fields = [
        'route_number', 'created_at', 'created_by', 'updated_at',
        'started_at', 'completed_at', 'total_deliveries', 'completed_deliveries'
    ]
    inlines = [RouteDeliveryAdminInline]
    
    fieldsets = (
        ('Informations de base', {
            'fields': (
                'route_number', 'name', 'driver', 'date',
                'start_time', 'end_time', 'status'
            )
        }),
        ('Véhicule et départ', {
            'fields': (
                'vehicle', 'start_location', 'start_latitude', 'start_longitude'
            )
        }),
        ('Statistiques', {
            'fields': (
                'total_deliveries', 'completed_deliveries',
                'total_distance', 'estimated_duration'
            )
        }),
        ('Optimisation', {
            'fields': ('is_optimized', 'optimization_data'),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': (
                'started_at', 'completed_at', 'notes'
            )
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'created_by', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['optimize_routes', 'mark_as_completed', 'assign_driver']
    
    def driver_name(self, obj):
        return obj.driver.get_full_name()
    driver_name.short_description = 'Livreur'
    
    def status_badge(self, obj):
        colors = {
            'draft': '#6c757d',
            'planned': '#17a2b8',
            'in_progress': '#ffc107',
            'completed': '#28a745',
            'cancelled': '#dc3545',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    def deliveries_count(self, obj):
        return obj.route_deliveries.count()
    deliveries_count.short_description = 'Livraisons'
    
    def progress_info(self, obj):
        total = obj.total_deliveries
        completed = obj.completed_deliveries
        if total > 0:
            percentage = (completed / total) * 100
            color = '#28a745' if percentage == 100 else '#ffc107' if percentage > 0 else '#dc3545'
            return format_html(
                '<div style="width: 100px; height: 20px; background: #e9ecef; '
                'border-radius: 3px; overflow: hidden; display: inline-block;">'
                '<div style="width: {}%; height: 100%; background: {};"></div>'
                '</div> '
                '<span style="margin-left: 5px;">{}/{}</span>',
                percentage, color, completed, total
            )
        return '-'
    progress_info.short_description = 'Progression'
    
    def optimize_routes(self, request, queryset):
        for route in queryset:
            # Logique d'optimisation
            route.is_optimized = True
            route.save()
        self.message_user(request, f"{queryset.count()} route(s) optimisée(s).")
    optimize_routes.short_description = "Optimiser les routes"

# ========================================
# ADMIN PLANNING LIVREURS
# ========================================

@admin.register(DriverPlanning)
class DriverPlanningAdmin(admin.ModelAdmin):
    list_display = [
        'driver_name', 'date', 'availability_badge', 'schedule_info',
        'max_deliveries', 'zones_info'
    ]
    list_filter = ['date', 'is_available', 'driver']
    search_fields = ['driver__first_name', 'driver__last_name']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Planning', {
            'fields': ('driver', 'date', 'start_time', 'end_time')
        }),
        ('Disponibilité', {
            'fields': ('is_available', 'unavailability_reason')
        }),
        ('Capacité', {
            'fields': ('max_deliveries', 'max_weight')
        }),
        ('Zones', {
            'fields': ('zones',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def driver_name(self, obj):
        return obj.driver.get_full_name()
    driver_name.short_description = 'Livreur'
    
    def availability_badge(self, obj):
        if obj.is_available:
            return format_html(
                '<span style="color: green;">✅ Disponible</span>'
            )
        return format_html(
            '<span style="color: red;">❌ Indisponible</span>'
        )
    availability_badge.short_description = 'Disponibilité'
    
    def schedule_info(self, obj):
        return format_html(
            '⏰ {} - {}',
            obj.start_time.strftime('%H:%M'),
            obj.end_time.strftime('%H:%M')
        )
    schedule_info.short_description = 'Horaires'
    
    def zones_info(self, obj):
        if obj.zones:
            zones_count = len(obj.zones)
            return format_html(
                '<span title="{}">{} zone(s)</span>',
                ', '.join(obj.zones),
                zones_count
            )
        return '-'
    zones_info.short_description = 'Zones'

# ========================================
# ADMIN PHOTOS DE LIVRAISON
# ========================================

@admin.register(DeliveryPhoto)
class DeliveryPhotoAdmin(admin.ModelAdmin):
    list_display = [
        'thumbnail', 'delivery_number', 'photo_type', 'caption',
        'taken_by_name', 'taken_at', 'has_location'
    ]
    list_filter = ['photo_type', 'taken_at']
    search_fields = ['delivery__delivery_number', 'caption']
    date_hierarchy = 'taken_at'
    readonly_fields = ['taken_at', 'latitude', 'longitude']
    
    fieldsets = (
        ('Photo', {
            'fields': ('photo', 'photo_type', 'caption')
        }),
        ('Livraison', {
            'fields': ('delivery',)
        }),
        ('Géolocalisation', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('taken_by', 'taken_at')
        }),
    )
    
    def thumbnail(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" width="75" height="75" style="object-fit: cover; '
                'border-radius: 5px; border: 2px solid #ddd;"/>',
                obj.photo.url
            )
        return '-'
    thumbnail.short_description = 'Aperçu'
    
    def delivery_number(self, obj):
        return obj.delivery.delivery_number
    delivery_number.short_description = 'Livraison'
    
    def taken_by_name(self, obj):
        return obj.taken_by.get_full_name() if obj.taken_by else '-'
    taken_by_name.short_description = 'Prise par'
    
    def has_location(self, obj):
        if obj.latitude and obj.longitude:
            return format_html(
                '<span style="color: green;">📍 Oui</span>'
            )
        return format_html('<span style="color: gray;">Non</span>')
    has_location.short_description = 'Géolocalisée'

# ========================================
# ADMIN NOTIFICATIONS DE LIVRAISON
# ========================================

@admin.register(DeliveryNotification)
class DeliveryNotificationAdmin(admin.ModelAdmin):
    list_display = [
        'type_badge', 'recipient_name', 'title', 'delivery_info',
        'is_read_badge', 'is_urgent_badge', 'created_at'
    ]
    list_filter = ['type', 'recipient_type', 'is_read', 'is_urgent', 'created_at']
    search_fields = ['title', 'message', 'recipient__username']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'read_at', 'sent_at']
    
    fieldsets = (
        ('Notification', {
            'fields': ('type', 'title', 'message', 'is_urgent')
        }),
        ('Destinataire', {
            'fields': ('recipient_type', 'recipient')
        }),
        ('Références', {
            'fields': ('delivery', 'route')
        }),
        ('Statut', {
            'fields': ('is_read', 'read_at')
        }),
        ('Programmation', {
            'fields': ('scheduled_for', 'sent_at'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_unread', 'mark_as_urgent']
    
    def type_badge(self, obj):
        colors = {
            'new_delivery': '#17a2b8',
            'route_assigned': '#6f42c1',
            'delivery_late': '#ffc107',
            'reminder': '#fd7e14',
            'issue': '#dc3545',
            'completed': '#28a745',
        }
        icons = {
            'new_delivery': '📦',
            'route_assigned': '🚚',
            'delivery_late': '⏰',
            'reminder': '🔔',
            'issue': '⚠️',
            'completed': '✅',
        }
        return format_html(
            '{} <span style="background: {}; color: white; padding: 2px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            icons.get(obj.type, ''),
            colors.get(obj.type, '#6c757d'),
            obj.get_type_display()
        )
    type_badge.short_description = 'Type'
    
    def recipient_name(self, obj):
        return f"{obj.recipient.get_full_name()} ({obj.get_recipient_type_display()})"
    recipient_name.short_description = 'Destinataire'
    
    def delivery_info(self, obj):
        if obj.delivery:
            return obj.delivery.delivery_number
        elif obj.route:
            return f"Route: {obj.route.route_number}"
        return '-'
    delivery_info.short_description = 'Référence'
    
    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html('<span style="color: green;">✓ Lu</span>')
        return format_html('<span style="color: orange;">● Non lu</span>')
    is_read_badge.short_description = 'Lu'
    
    def is_urgent_badge(self, obj):
        if obj.is_urgent:
            return format_html('<span style="color: red;">🔥 Urgent</span>')
        return '-'
    is_urgent_badge.short_description = 'Urgence'
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(request, f"{queryset.count()} notification(s) marquée(s) comme lue(s).")
    mark_as_read.short_description = "Marquer comme lu"
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False, read_at=None)
        self.message_user(request, f"{queryset.count()} notification(s) marquée(s) comme non lue(s).")
    mark_as_unread.short_description = "Marquer comme non lu"
    
    def mark_as_urgent(self, request, queryset):
        queryset.update(is_urgent=True)
        self.message_user(request, f"{queryset.count()} notification(s) marquée(s) comme urgente(s).")
    mark_as_urgent.short_description = "Marquer comme urgent"

# ========================================
# ADMIN PARAMÈTRES DE LIVRAISON
# ========================================

@admin.register(DeliverySettings)
class DeliverySettingsAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'delivery_hours', 'notification_status', 'optimization_status']
    
    fieldsets = (
        ('Paramètres par défaut', {
            'fields': (
                'default_delivery_duration',
                'default_pickup_duration'
            )
        }),
        ('Zones de livraison', {
            'fields': (
                'delivery_zones',
                'excluded_postal_codes'
            ),
            'description': 'Configuration des zones et codes postaux exclus'
        }),
        ('Horaires de livraison', {
            'fields': (
                'delivery_start_time',
                'delivery_end_time'
            )
        }),
        ('Notifications', {
            'fields': (
                'send_customer_notifications',
                'notification_advance_time'
            )
        }),
        ('Intégrations', {
            'fields': ('google_maps_api_key',),
            'description': 'Clé API pour Google Maps'
        }),
        ('Optimisation', {
            'fields': (
                'auto_optimize_routes',
                'max_deliveries_per_route'
            )
        }),
    )
    
    def delivery_hours(self, obj):
        return format_html(
            '⏰ {} - {}',
            obj.delivery_start_time.strftime('%H:%M'),
            obj.delivery_end_time.strftime('%H:%M')
        )
    delivery_hours.short_description = 'Horaires'
    
    def notification_status(self, obj):
        if obj.send_customer_notifications:
            return format_html(
                '<span style="color: green;">✅ Activées ({} min avant)</span>',
                obj.notification_advance_time
            )
        return format_html('<span style="color: red;">❌ Désactivées</span>')
    notification_status.short_description = 'Notifications'
    
    def optimization_status(self, obj):
        if obj.auto_optimize_routes:
            return format_html(
                '<span style="color: green;">✅ Auto (max {} livraisons/route)</span>',
                obj.max_deliveries_per_route
            )
        return format_html('<span style="color: orange;">⚠️ Manuelle</span>')
    optimization_status.short_description = 'Optimisation'
    
    def has_add_permission(self, request):
        # Ne permettre qu'une seule instance de paramètres
        return not DeliverySettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Ne pas permettre la suppression des paramètres
        return False
    

from django.contrib import admin
from .models import KitchenProduction

@admin.register(KitchenProduction)
class KitchenProductionAdmin(admin.ModelAdmin):
    list_display = (
        'date', 'department', 'department_chef', 'status',
        'total_items', 'completed_items', 'progress_percentage', 'created_at'
    )
    list_filter = ('department', 'status', 'date')
    search_fields = ('department', 'department_chef__username', 'notes')


from django.contrib import admin
from .models import ProductionItem

@admin.register(ProductionItem)
class ProductionItemAdmin(admin.ModelAdmin):
    list_display = (
        'production', 'order_item', 'quantity_to_produce', 'quantity_produced',
        'is_completed', 'is_priority', 'started_at', 'completed_at', 'produced_by'
    )
    list_filter = ('is_completed', 'is_priority', 'production__department', 'production__date')
    search_fields = ('order_item__product_name', 'production__notes', 'production_notes', 'quality_notes')
    readonly_fields = ('completed_at', 'started_at')
    ordering = ('-production__date', 'production__department', 'is_priority')


from django.contrib import admin
from .models import KitchenNotification

@admin.register(KitchenNotification)
class KitchenNotificationAdmin(admin.ModelAdmin):
    list_display = (
        'type', 'title', 'recipient', 'recipient_type', 'is_read', 'is_urgent', 'created_at'
    )
    list_filter = ('type', 'recipient_type', 'is_read', 'is_urgent', 'created_at')
    search_fields = ('title', 'message', 'recipient__username')