from django.db import models
from django.utils import timezone
from django.conf import settings
import datetime

class ContactSubmission(models.Model):
    """Modèle pour stocker les soumissions de contact"""
    
    EVENT_TYPE_CHOICES = [
        ('business', 'Repas d\'affaires'),
        ('corporate', 'Événement corporatif'),
        ('cocktail', 'Cocktail / 5@7'),
        ('wedding', 'Mariage'),
        ('private', 'Événement privé'),
        ('other', 'Autre'),
    ]
    
    BUDGET_CHOICES = [
        ('<1000', 'Moins de 1 000$'),
        ('1000-2500', '1 000$ - 2 500$'),
        ('2500-5000', '2 500$ - 5 000$'),
        ('5000-10000', '5 000$ - 10 000$'),
        ('>10000', 'Plus de 10 000$'),
    ]
    
    # Informations personnelles
    first_name = models.CharField(max_length=100, verbose_name='Prénom')
    last_name = models.CharField(max_length=100, verbose_name='Nom')
    email = models.EmailField(verbose_name='Courriel')
    phone = models.CharField(max_length=20, verbose_name='Téléphone')
    company = models.CharField(max_length=200, blank=True, null=True, verbose_name='Entreprise')
    
    # Détails de l'événement
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, verbose_name='Type d\'événement')
    guest_count = models.IntegerField(verbose_name='Nombre d\'invités')
    event_date = models.DateField(verbose_name='Date de l\'événement')
    budget = models.CharField(max_length=20, choices=BUDGET_CHOICES, blank=True, null=True, verbose_name='Budget')
    message = models.TextField(verbose_name='Message')
    
    # Autres
    newsletter = models.BooleanField(default=False, verbose_name='Inscription newsletter')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Date de soumission')
    is_processed = models.BooleanField(default=False, verbose_name='Traité')
    
    class Meta:
        verbose_name = 'Soumission de contact'
        verbose_name_plural = 'Soumissions de contact'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.event_date}"
    

    # ========================================
# models.py - Modèles pour le système e-commerce
# ========================================

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

# ========================================
# 1. MODÈLE UTILISATEUR PERSONNALISÉ
# ========================================

from django.db import models

class User(AbstractUser):
    """Utilisateur personnalisé avec informations supplémentaires"""
    
    CUSTOMER = 'customer'
    STAFF = 'staff'
    ADMIN = 'admin'
    CHECKLIST_MANAGER = 'checklist_manager'  # NOUVEAU RÔLE
    DELIVERY_MANAGER = 'delivery_manager'  # NOUVEAU
    DELIVERY_DRIVER = 'delivery_driver'
    MAITRE_HOTEL = 'maitre_hotel'
    HEAD_CHEF = 'head_chef'
    DEPARTMENT_CHEF = 'department_chef'
    COOK = 'cook'



    
    ROLE_CHOICES = [
        (CUSTOMER, 'Client'),
        (STAFF, 'Personnel'),
        (ADMIN, 'Administrateur'),
        (CHECKLIST_MANAGER, 'Checklist'),
        (DELIVERY_MANAGER, 'Responsable Livraison'),  # NOUVEAU
        (DELIVERY_DRIVER, 'Livreur'),
        (MAITRE_HOTEL, 'Maître d\'hôtel'),
        (HEAD_CHEF, 'Chef de cuisine'),
        (DEPARTMENT_CHEF, 'Chef de département'),
        (COOK, 'Cuisinier')
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=CUSTOMER)
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=200, blank=True)
    address = models.TextField(blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    city = models.CharField(max_length=100, blank=True)
    newsletter = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    driver_license = models.CharField(max_length=50, blank=True, verbose_name='Permis de conduire')
    vehicle_info = models.CharField(max_length=200, blank=True, verbose_name='Informations véhicule')
    is_available = models.BooleanField(default=True, verbose_name='Disponible')
    
    # IMPORTANT: Ajouter ces lignes pour résoudre les conflits
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='jltsite_users',  # Changed from user_set
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='jltsite_users',  # Changed from user_set
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )
    
    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

# ========================================
# 2. MODÈLES PRODUITS
# ========================================

class Category(models.Model):
    """Catégories de produits"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Catégorie'
        verbose_name_plural = 'Catégories'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name

class Product(models.Model):
    """Produits (Boîtes à lunch)"""
    
    DISPONIBLE = 'disponible'
    RUPTURE = 'rupture'
    COMMANDE = 'sur_commande'
    
    STATUS_CHOICES = [
        (DISPONIBLE, 'Disponible'),
        (RUPTURE, 'Rupture de stock'),
        (COMMANDE, 'Sur commande'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='Nom')
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    description = models.TextField(verbose_name='Description')
    ingredients = models.TextField(verbose_name='Ingrédients', blank=True)
    allergens = models.CharField(max_length=500, blank=True, verbose_name='Allergènes')
    
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Prix')
    promo_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Prix promo')
    
    image = models.ImageField(upload_to='images/', verbose_name='Image principale')
    image_2 = models.ImageField(upload_to='images/', blank=True, null=True)
    image_3 = models.ImageField(upload_to='images/', blank=True, null=True)
    
    calories = models.IntegerField(null=True, blank=True)
    preparation_time = models.IntegerField(help_text='En minutes', null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=DISPONIBLE)
    stock = models.IntegerField(default=0, verbose_name='Stock disponible')
    min_order = models.IntegerField(default=1, verbose_name='Commande minimum')
    
    is_vegetarian = models.BooleanField(default=False, verbose_name='Végétarien')
    is_vegan = models.BooleanField(default=False, verbose_name='Végane')
    is_gluten_free = models.BooleanField(default=False, verbose_name='Sans gluten')
    is_featured = models.BooleanField(default=False, verbose_name='Mis en avant')
    is_active = models.BooleanField(default=True, verbose_name='Actif')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Statistiques
    views_count = models.IntegerField(default=0)
    sales_count = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = 'Produit'
        verbose_name_plural = 'Produits'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_price(self):
        """Retourne le prix actuel (promo ou normal)"""
        return self.promo_price if self.promo_price else self.price
    
    def is_in_stock(self):
        """Vérifie si le produit est en stock"""
        return self.stock > 0 and self.status == self.DISPONIBLE
    
    def get_discount_percentage(self):
        """Calcule le pourcentage de réduction"""
        if self.promo_price and self.promo_price < self.price:
            return int(((self.price - self.promo_price) / self.price) * 100)
        return 0

# ========================================
# 3. MODÈLES PANIER
# ========================================

class Cart(models.Model):
    """Panier d'achat"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Panier'
        verbose_name_plural = 'Paniers'
    
    def __str__(self):
        return f"Panier {self.id} - {self.user or self.session_key}"
    
    def get_total(self):
        """Calcule le total du panier"""
        total = Decimal('0.00')
        for item in self.items.all():
            total += item.get_subtotal()
        return total
    
    def get_items_count(self):
        """Compte le nombre total d'articles"""
        return sum(item.quantity for item in self.items.all())

class CartItem(models.Model):
    """Article dans le panier"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True, verbose_name='Notes spéciales')
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Article du panier'
        verbose_name_plural = 'Articles du panier'
        unique_together = ['cart', 'product']
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
    
    def get_subtotal(self):
        """Calcule le sous-total de l'article"""
        return self.product.get_price() * self.quantity

# ========================================
# 4. MODÈLES COMMANDES
# ========================================

class Order(models.Model):
    """Commande"""
    
    # Statuts
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    PREPARING = 'preparing'
    READY = 'ready'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (PENDING, 'En attente'),
        (CONFIRMED, 'Confirmée'),
        (PREPARING, 'En préparation'),
        (READY, 'Prête'),
        (DELIVERED, 'Livrée'),
        (CANCELLED, 'Annulée'),
    ]
    
    # Types de livraison
    PICKUP = 'pickup'
    DELIVERY = 'delivery'
    
    DELIVERY_CHOICES = [
        (PICKUP, 'Ramassage'),
        (DELIVERY, 'Livraison'),
    ]
    
    # Informations de base
    order_number = models.CharField(max_length=50, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    
    # Informations de contact
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    company = models.CharField(max_length=200, blank=True)
    
    # Livraison
    delivery_type = models.CharField(max_length=20, choices=DELIVERY_CHOICES, default=DELIVERY)
    delivery_address = models.TextField()
    delivery_postal_code = models.CharField(max_length=10)
    delivery_city = models.CharField(max_length=100)
    delivery_date = models.DateField()
    delivery_time = models.TimeField()
    delivery_notes = models.TextField(blank=True)
    
    # Montants
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('14.975'))
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Paiement
    payment_method = models.CharField(max_length=50, blank=True)
    payment_status = models.CharField(max_length=50, default='pending')
    transaction_id = models.CharField(max_length=200, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Notes internes
    admin_notes = models.TextField(blank=True)

    ORDER_SOURCE_CHOICES = [
        ('online', 'En ligne'),
        ('manual', 'Manuelle (téléphone/sur place)'),
        ('admin', 'Créée par admin'),
    ]
    
    order_source = models.CharField(
        max_length=20, 
        choices=ORDER_SOURCE_CHOICES, 
        default='online',
        verbose_name='Source de la commande'
    )
    
    # NOUVEAU : Qui a créé la commande manuellement
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='orders_created',
        verbose_name='Créée par'
    )
    
    # NOUVEAU : Pour les commandes téléphoniques
    is_phone_order = models.BooleanField(default=False, verbose_name='Commande téléphonique')
    
    class Meta:
        verbose_name = 'Commande'
        verbose_name_plural = 'Commandes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Commande {self.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            # Générer un numéro de commande unique
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        """Génère un numéro de commande unique"""
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(uuid.uuid4())[:6].upper()
        return f"JLT-{date_str}-{random_str}"
    
    def calculate_totals(self):
        """Recalcule les totaux de la commande"""
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        self.total = self.subtotal + self.tax_amount + self.delivery_fee - self.discount_amount
        return self.total

class OrderItem(models.Model):
    """Article d'une commande"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)  # Gardé au cas où le produit est supprimé
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    notes = models.TextField(blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    # NOUVEAU : Département de cuisine
    DEPARTMENT_CHOICES = [
        ('patisserie', 'Pâtisserie'),
        ('chaud', 'Cuisine Chaude'),
        ('sandwichs', 'Sandwichs'),
        ('boites', 'Boîtes à lunch'),
        ('salades', 'Salades'),
        ('dejeuners', 'Déjeuners'),
        ('bouchees', 'Bouchées'),
        ('autres', 'Autres'),
    ]
    
    department = models.CharField(
        max_length=20, 
        choices=DEPARTMENT_CHOICES,
        blank=True,
        verbose_name='Département'
    )
    
    # NOUVEAU : Pour tracking de préparation
    is_prepared = models.BooleanField(default=False, verbose_name='Préparé')
    prepared_at = models.DateTimeField(null=True, blank=True, verbose_name='Préparé le')
    prepared_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items_prepared',
        verbose_name='Préparé par'
    )
    
    class Meta:
        verbose_name = 'Article de commande'
        verbose_name_plural = 'Articles de commande'
    
    def __str__(self):
        return f"{self.quantity}x {self.product_name}"
    
    def save(self, *args, **kwargs):
        self.subtotal = self.product_price * self.quantity
        super().save(*args, **kwargs)


class KitchenProductionNote(models.Model):
    """Notes de production pour la cuisine"""
    
    date = models.DateField(verbose_name='Date de production')
    department = models.CharField(
        max_length=20,
        choices=OrderItem.DEPARTMENT_CHOICES,
        verbose_name='Département'
    )
    notes = models.TextField(verbose_name='Notes')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='kitchen_notes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Note de production'
        verbose_name_plural = 'Notes de production'
        ordering = ['-date', 'department']
    
    def __str__(self):
        return f"Notes {self.department} - {self.date}"

# ========================================
# 5. MODÈLES POUR PROMOTIONS ET COUPONS
# ========================================

class Coupon(models.Model):
    """Codes de réduction"""
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    discount_type = models.CharField(
        max_length=20,
        choices=[
            ('percentage', 'Pourcentage'),
            ('fixed', 'Montant fixe'),
        ]
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    usage_limit = models.IntegerField(default=0, help_text='0 = illimité')
    usage_count = models.IntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Coupon'
        verbose_name_plural = 'Coupons'
    
    def __str__(self):
        return self.code
    
    def is_valid(self):
        """Vérifie si le coupon est valide"""
        now = timezone.now()
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_until and
            (self.usage_limit == 0 or self.usage_count < self.usage_limit)
        )

# ========================================
# 6. MODÈLES POUR REVIEWS
# ========================================

class Review(models.Model):
    """Avis sur les produits"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Avis'
        verbose_name_plural = 'Avis'
        ordering = ['-created_at']
        unique_together = ['product', 'user', 'order']
    
    def __str__(self):
        return f"Avis de {self.user.username} sur {self.product.name}"


# Ajouter ces modèles dans votre models.py existant

# ========================================
# MODÈLES POUR LE SYSTÈME DE CHECKLIST
# ========================================

class InventoryItem(models.Model):
    """Articles d'inventaire pour les checklists"""
    
    CATEGORY_CHOICES = [
        ('ustensiles', 'Ustensiles'),
        ('contenants', 'Contenants'),
        ('nappes', 'Nappes et serviettes'),
        ('decorations', 'Décorations'),
        ('equipements', 'Équipements'),
        ('condiments', 'Condiments et sauces'),
        ('boissons', 'Boissons'),
        ('autres', 'Autres'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='Nom')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, verbose_name='Catégorie')
    description = models.TextField(blank=True, verbose_name='Description')
    unit = models.CharField(max_length=50, default='unité', verbose_name='Unité de mesure')
    stock_quantity = models.IntegerField(default=0, verbose_name='Quantité en stock')
    min_stock = models.IntegerField(default=10, verbose_name='Stock minimum')
    is_active = models.BooleanField(default=True, verbose_name='Actif')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Article d\'inventaire'
        verbose_name_plural = 'Articles d\'inventaire'
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.stock_quantity} {self.unit})"
    
    def is_low_stock(self):
        return self.stock_quantity < self.min_stock

class OrderChecklist(models.Model):
    """Checklist principale pour une commande"""
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('in_progress', 'En cours'),
        ('completed', 'Complétée'),
        ('cancelled', 'Annulée'),
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='checklist')
    title = models.CharField(max_length=200, verbose_name='Titre')
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='assigned_checklists',
        verbose_name='Assignée à'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.IntegerField(default=0, verbose_name='Priorité (0=normale, 1=haute)')
    notes = models.TextField(blank=True, verbose_name='Notes')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_checklists'
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Métadonnées
    total_items = models.IntegerField(default=0)
    completed_items = models.IntegerField(default=0)
    progress_percentage = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = 'Checklist de commande'
        verbose_name_plural = 'Checklists de commandes'
        ordering = ['-priority', 'order__delivery_date', 'order__delivery_time']
    
    def __str__(self):
        return f"Checklist {self.order.order_number} - {self.get_status_display()}"
    
    def update_progress(self):
        """Met à jour le pourcentage de progression"""
        items = self.items.all()
        self.total_items = items.count()
        self.completed_items = items.filter(is_checked=True).count()
        
        if self.total_items > 0:
            self.progress_percentage = int((self.completed_items / self.total_items) * 100)
        else:
            self.progress_percentage = 0
        
        # Mettre à jour le statut
        if self.progress_percentage == 0 and self.status == 'pending':
            pass
        elif 0 < self.progress_percentage < 100:
            self.status = 'in_progress'
            if not self.started_at:
                self.started_at = timezone.now()
        elif self.progress_percentage == 100:
            self.status = 'completed'
            if not self.completed_at:
                self.completed_at = timezone.now()
        
        self.save()
    
    def get_time_spent(self):
        """Calcule le temps passé sur la checklist"""
        if self.started_at:
            end_time = self.completed_at or timezone.now()
            delta = end_time - self.started_at
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            return f"{hours}h {minutes}min"
        return "Non commencé"

class ChecklistItem(models.Model):
    """Élément individuel d'une checklist"""
    
    checklist = models.ForeignKey(
        OrderChecklist,
        on_delete=models.CASCADE,
        related_name='items'
    )
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        verbose_name='Article'
    )
    quantity_needed = models.IntegerField(default=1, verbose_name='Quantité nécessaire')
    quantity_prepared = models.IntegerField(default=0, verbose_name='Quantité préparée')
    
    # Validation
    is_checked = models.BooleanField(default=False, verbose_name='Validé')
    checked_at = models.DateTimeField(null=True, blank=True)
    checked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='checked_items'
    )
    
    # Notes et problèmes
    notes = models.TextField(blank=True, verbose_name='Notes')
    has_issue = models.BooleanField(default=False, verbose_name='Problème signalé')
    issue_description = models.TextField(blank=True, verbose_name='Description du problème')
    
    # Ordre d'affichage
    order = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = 'Élément de checklist'
        verbose_name_plural = 'Éléments de checklist'
        ordering = ['order', 'inventory_item__category', 'inventory_item__name']
    
    def __str__(self):
        return f"{self.inventory_item.name} - {self.quantity_needed} {self.inventory_item.unit}"
    
    def validate_item(self, user, quantity=None):
        """Valide un élément de la checklist"""
        self.is_checked = True
        self.checked_at = timezone.now()
        self.checked_by = user
        if quantity:
            self.quantity_prepared = quantity
        else:
            self.quantity_prepared = self.quantity_needed
        self.save()
        
        # Mettre à jour la progression de la checklist
        self.checklist.update_progress()
    
    def unvalidate_item(self):
        """Annule la validation d'un élément"""
        self.is_checked = False
        self.checked_at = None
        self.checked_by = None
        self.quantity_prepared = 0
        self.save()
        
        # Mettre à jour la progression
        self.checklist.update_progress()
    
    def report_issue(self, description, user):
        """Signale un problème sur cet élément"""
        self.has_issue = True
        self.issue_description = description
        self.save()
        
        # Créer une notification pour l'admin
        ChecklistNotification.objects.create(
            checklist=self.checklist,
            item=self,
            type='issue',
            message=f"Problème signalé sur {self.inventory_item.name}",
            created_by=user
        )

class ChecklistNotification(models.Model):
    """Notifications pour les checklists"""
    
    TYPE_CHOICES = [
        ('issue', 'Problème'),
        ('completed', 'Complétée'),
        ('urgent', 'Urgent'),
        ('info', 'Information'),
    ]
    
    checklist = models.ForeignKey(OrderChecklist, on_delete=models.CASCADE, related_name='notifications')
    item = models.ForeignKey(ChecklistItem, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = 'Notification de checklist'
        verbose_name_plural = 'Notifications de checklist'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.checklist.order.order_number}"

class ChecklistTemplate(models.Model):
    """Modèles de checklist réutilisables"""
    
    name = models.CharField(max_length=200, verbose_name='Nom du modèle')
    description = models.TextField(blank=True)
    event_type = models.CharField(
        max_length=50,
        choices=[
            ('corporate', 'Événement corporatif'),
            ('wedding', 'Mariage'),
            ('cocktail', 'Cocktail'),
            ('lunch', 'Lunch box'),
            ('other', 'Autre'),
        ],
        verbose_name='Type d\'événement'
    )
    items = models.ManyToManyField(
        InventoryItem,
        through='ChecklistTemplateItem',
        related_name='templates'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        verbose_name = 'Modèle de checklist'
        verbose_name_plural = 'Modèles de checklist'
        ordering = ['event_type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_event_type_display()})"

class ChecklistTemplateItem(models.Model):
    """Items d'un modèle de checklist"""
    
    template = models.ForeignKey(ChecklistTemplate, on_delete=models.CASCADE)
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE)
    default_quantity = models.IntegerField(default=1)
    notes = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = 'Item de modèle'
        verbose_name_plural = 'Items de modèle'
        ordering = ['order']


# ========================================
# MODÈLES POUR LE SYSTÈME DE LIVRAISON
# ========================================
# Ajouter ces modèles dans votre models.py existant

from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid

# Note: Les modèles User et Order existent déjà dans votre code
# Assurez-vous que User a les rôles DELIVERY_MANAGER et DELIVERY_DRIVER

class Delivery(models.Model):
    """Livraison basée sur une commande confirmée"""
    
    TYPE_CHOICES = [
        ('delivery', 'Livraison'),
        ('pickup', 'Récupération'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('assigned', 'Assignée'),
        ('in_transit', 'En cours'),
        ('delivered', 'Livrée'),
        ('failed', 'Échec'),
        ('cancelled', 'Annulée'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Basse'),
        ('normal', 'Normale'),
        ('high', 'Haute'),
        ('urgent', 'Urgente'),
    ]
    
    # Identifiant unique
    delivery_number = models.CharField(max_length=50, unique=True, editable=False)
    
    # Référence à la commande originale
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='deliveries')
    parent_delivery = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                                       related_name='pickup_deliveries', 
                                       help_text='Livraison parente pour les récupérations')
    
    # Type et statut
    delivery_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='delivery')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    
    # Informations client (copiées de la commande)
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=20)
    customer_email = models.EmailField()
    company = models.CharField(max_length=200, blank=True)
    
    # Adresse de livraison
    delivery_address = models.TextField()
    delivery_postal_code = models.CharField(max_length=10)
    delivery_city = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    # Planning
    scheduled_date = models.DateField()
    scheduled_time_start = models.TimeField()
    scheduled_time_end = models.TimeField()
    estimated_duration = models.IntegerField(default=30, help_text='Durée estimée en minutes')
    
    # Instructions
    delivery_instructions = models.TextField(blank=True)
    access_code = models.CharField(max_length=50, blank=True, help_text='Code d\'accès immeuble')
    parking_info = models.TextField(blank=True, help_text='Informations de stationnement')
    
    # Contenu de la livraison
    items_description = models.TextField(help_text='Description des items à livrer')
    total_packages = models.IntegerField(default=1)
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text='Poids en kg')
    
    # Checklist associée
    has_checklist = models.BooleanField(default=False)
    checklist_completed = models.BooleanField(default=False)
    
    # Photos et preuves
    delivery_photo = models.ImageField(upload_to='deliveries/photos/', null=True, blank=True)
    pickup_photo = models.ImageField(upload_to='deliveries/pickups/', null=True, blank=True)
    signature = models.TextField(blank=True, help_text='Signature électronique en base64')
    
    # Validation
    delivered_at = models.DateTimeField(null=True, blank=True)
    delivered_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, 
                                    related_name='deliveries_completed')
    delivery_notes = models.TextField(blank=True)
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, 
                                  related_name='deliveries_created')
    updated_at = models.DateTimeField(auto_now=True)
    
    # Notifications
    reminder_sent = models.BooleanField(default=False)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Livraison'
        verbose_name_plural = 'Livraisons'
        ordering = ['scheduled_date', 'scheduled_time_start']
        indexes = [
            models.Index(fields=['scheduled_date', 'status']),
            models.Index(fields=['delivery_type', 'status']),
        ]
    
    def __str__(self):
        return f"Livraison {self.delivery_number} - {self.customer_name}"
    
    def save(self, *args, **kwargs):
        if not self.delivery_number:
            self.delivery_number = self.generate_delivery_number()
        super().save(*args, **kwargs)
    
    def generate_delivery_number(self):
        """Génère un numéro de livraison unique"""
        prefix = 'LIV' if self.delivery_type == 'delivery' else 'REC'
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(uuid.uuid4())[:6].upper()
        return f"{prefix}-{date_str}-{random_str}"
    
    def get_google_maps_url(self):
        """Retourne l'URL Google Maps pour l'adresse"""
        address = f"{self.delivery_address}, {self.delivery_postal_code} {self.delivery_city}"
        return f"https://www.google.com/maps/search/?api=1&query={address}"
    
    def is_late(self):
        """Vérifie si la livraison est en retard"""
        if self.status in ['delivered', 'cancelled']:
            return False
        now = timezone.now()
        from datetime import datetime, timedelta
        scheduled = timezone.make_aware(
            datetime.combine(self.scheduled_date, self.scheduled_time_end)
        )
        return now > scheduled

class DeliveryRoute(models.Model):
    """Route de livraison pour un livreur"""
    
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('planned', 'Planifiée'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminée'),
        ('cancelled', 'Annulée'),
    ]
    
    route_number = models.CharField(max_length=50, unique=True, editable=False)
    name = models.CharField(max_length=200, verbose_name='Nom de la route')
    
    driver = models.ForeignKey('User', on_delete=models.CASCADE, 
                              related_name='delivery_routes',
                              limit_choices_to={'role': 'delivery_driver'})
    
    date = models.DateField(verbose_name='Date de la route')
    start_time = models.TimeField(verbose_name='Heure de départ')
    end_time = models.TimeField(null=True, blank=True, verbose_name='Heure de fin estimée')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Informations véhicule
    vehicle = models.CharField(max_length=100, blank=True)
    
    # Point de départ
    start_location = models.CharField(max_length=200, default='Julien-Leblanc Traiteur')
    start_latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    start_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    # Statistiques
    total_deliveries = models.IntegerField(default=0)
    completed_deliveries = models.IntegerField(default=0)
    total_distance = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Distance totale en km')
    estimated_duration = models.IntegerField(default=0, help_text='Durée estimée en minutes')
    
    # Optimisation
    is_optimized = models.BooleanField(default=False, help_text='Route optimisée automatiquement')
    optimization_data = models.JSONField(default=dict, blank=True)
    
    # Tracking
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, 
                                  related_name='routes_created')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Route de livraison'
        verbose_name_plural = 'Routes de livraison'
        ordering = ['-date', 'start_time']
        unique_together = ['driver', 'date', 'route_number']
    
    def __str__(self):
        return f"Route {self.route_number} - {self.driver.get_full_name()} - {self.date}"
    
    def save(self, *args, **kwargs):
        if not self.route_number:
            self.route_number = self.generate_route_number()
        super().save(*args, **kwargs)
    
    def generate_route_number(self):
        """Génère un numéro de route unique"""
        date_str = self.date.strftime('%Y%m%d')
        driver_initials = ''.join([n[0].upper() for n in self.driver.get_full_name().split()[:2]])
        count = DeliveryRoute.objects.filter(date=self.date, driver=self.driver).count() + 1
        return f"RT-{date_str}-{driver_initials}-{count:02d}"
    
    def update_stats(self):
        """Met à jour les statistiques de la route"""
        deliveries = self.route_deliveries.all()
        self.total_deliveries = deliveries.count()
        self.completed_deliveries = deliveries.filter(delivery__status='delivered').count()
        self.save()

class RouteDelivery(models.Model):
    """Association entre une route et ses livraisons avec ordre"""
    
    route = models.ForeignKey(DeliveryRoute, on_delete=models.CASCADE, 
                             related_name='route_deliveries')
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, 
                                related_name='route_assignments')
    
    position = models.IntegerField(default=0, help_text='Position dans la route')
    
    # Temps estimés
    estimated_arrival = models.TimeField(null=True, blank=True)
    estimated_departure = models.TimeField(null=True, blank=True)
    
    # Temps réels
    actual_arrival = models.TimeField(null=True, blank=True)
    actual_departure = models.TimeField(null=True, blank=True)
    
    # Distance depuis le point précédent
    distance_from_previous = models.DecimalField(max_digits=10, decimal_places=2, 
                                                 default=0, help_text='Distance en km')
    
    # Statut
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Notes spécifiques pour cette livraison dans cette route
    notes = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Livraison de route'
        verbose_name_plural = 'Livraisons de route'
        ordering = ['route', 'position']
        unique_together = ['route', 'delivery']
    
    def __str__(self):
        return f"Route {self.route.route_number} - Position {self.position}: {self.delivery.customer_name}"

class DeliveryPhoto(models.Model):
    """Photos associées aux livraisons"""
    
    PHOTO_TYPE_CHOICES = [
        ('delivery', 'Photo de livraison'),
        ('pickup', 'Photo de récupération'),
        ('package', 'Photo du colis'),
        ('location', 'Photo du lieu'),
        ('issue', 'Photo de problème'),
    ]
    
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name='photos')
    photo_type = models.CharField(max_length=20, choices=PHOTO_TYPE_CHOICES)
    photo = models.ImageField(upload_to='deliveries/photos/%Y/%m/%d/')
    caption = models.CharField(max_length=200, blank=True)
    
    taken_at = models.DateTimeField(auto_now_add=True)
    taken_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True)
    
    # Géolocalisation de la photo
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Photo de livraison'
        verbose_name_plural = 'Photos de livraison'
        ordering = ['-taken_at']
    
    def __str__(self):
        return f"Photo {self.get_photo_type_display()} - {self.delivery.delivery_number}"

class DriverPlanning(models.Model):
    """Planning des livreurs"""
    
    driver = models.ForeignKey('User', on_delete=models.CASCADE, 
                              related_name='planning',
                              limit_choices_to={'role': 'delivery_driver'})
    
    date = models.DateField()
    
    # Horaires de travail
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # Disponibilité
    is_available = models.BooleanField(default=True)
    unavailability_reason = models.CharField(max_length=200, blank=True)
    
    # Capacité
    max_deliveries = models.IntegerField(default=20)
    max_weight = models.DecimalField(max_digits=10, decimal_places=2, 
                                     default=100, help_text='Poids max en kg')
    
    # Zones assignées
    zones = models.JSONField(default=list, blank=True, 
                            help_text='Liste des codes postaux ou zones')
    
    # Notes
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, 
                                  related_name='plannings_created')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Planning livreur'
        verbose_name_plural = 'Plannings livreurs'
        ordering = ['date', 'driver']
        unique_together = ['driver', 'date']
    
    def __str__(self):
        return f"Planning {self.driver.get_full_name()} - {self.date}"
    
    def get_available_slots(self):
        """Retourne les créneaux disponibles"""
        # Logique pour calculer les créneaux disponibles
        pass

class DeliveryNotification(models.Model):
    """Notifications pour le système de livraison"""
    
    TYPE_CHOICES = [
        ('new_delivery', 'Nouvelle livraison'),
        ('route_assigned', 'Route assignée'),
        ('delivery_late', 'Livraison en retard'),
        ('reminder', 'Rappel'),
        ('issue', 'Problème signalé'),
        ('completed', 'Livraison complétée'),
    ]
    
    RECIPIENT_CHOICES = [
        ('driver', 'Livreur'),
        ('manager', 'Responsable'),
        ('customer', 'Client'),
    ]
    
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    recipient_type = models.CharField(max_length=20, choices=RECIPIENT_CHOICES)
    recipient = models.ForeignKey('User', on_delete=models.CASCADE, 
                                 related_name='delivery_notifications')
    
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, 
                                related_name='notifications', null=True, blank=True)
    route = models.ForeignKey(DeliveryRoute, on_delete=models.CASCADE, 
                             related_name='notifications', null=True, blank=True)
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    is_read = models.BooleanField(default=False)
    is_urgent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Pour les notifications programmées
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Notification de livraison'
        verbose_name_plural = 'Notifications de livraison'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.recipient.get_full_name()}"
    
    def mark_as_read(self):
        """Marque la notification comme lue"""
        self.is_read = True
        self.read_at = timezone.now()
        self.save()

class DeliverySettings(models.Model):
    """Paramètres globaux pour le système de livraison"""
    
    # Paramètres par défaut
    default_delivery_duration = models.IntegerField(default=30, help_text='Durée par défaut en minutes')
    default_pickup_duration = models.IntegerField(default=15, help_text='Durée de récupération en minutes')
    
    # Zones de livraison
    delivery_zones = models.JSONField(default=dict, help_text='Zones et leurs tarifs')
    excluded_postal_codes = models.JSONField(default=list, help_text='Codes postaux exclus')
    
    # Horaires
    delivery_start_time = models.TimeField(default='08:00')
    delivery_end_time = models.TimeField(default='18:00')
    
    # Notifications
    send_customer_notifications = models.BooleanField(default=True)
    notification_advance_time = models.IntegerField(default=30, help_text='Minutes avant livraison')
    
    # Google Maps API
    google_maps_api_key = models.CharField(max_length=200, blank=True)
    
    # Optimisation
    auto_optimize_routes = models.BooleanField(default=True)
    max_deliveries_per_route = models.IntegerField(default=20)
    
    class Meta:
        verbose_name = 'Paramètres de livraison'
        verbose_name_plural = 'Paramètres de livraison'
    
    def __str__(self):
        return "Paramètres de livraison"
    


# ========================================
# MODÈLES POUR LE SYSTÈME MAÎTRE D'HÔTEL
# ========================================

class EventNotifications(models.Model):
    """Notifications pour les maîtres d'hôtel"""
    
    TYPE_CHOICES = [
        ('new_event', 'Nouvel événement'),
        ('event_updated', 'Événement modifié'),
        ('reminder', 'Rappel'),
        ('issue', 'Problème signalé'),
        ('staff_update', 'Mise à jour personnel'),
        ('status_change', 'Changement de statut'),
    ]
    
    recipient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='event_notifications',
        verbose_name='Destinataire'
    )
    event = models.ForeignKey(
        'EventContract', 
        on_delete=models.CASCADE, 
        related_name='notifications', 
        null=True, 
        blank=True,
        verbose_name='Événement'
    )
    
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='Type')
    title = models.CharField(max_length=200, verbose_name='Titre')
    message = models.TextField(verbose_name='Message')
    
    is_read = models.BooleanField(default=False, verbose_name='Lu')
    is_urgent = models.BooleanField(default=False, verbose_name='Urgent')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Créé le')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='Lu le')
    
    # Pour les notifications programmées
    scheduled_for = models.DateTimeField(null=True, blank=True, verbose_name='Programmée pour')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='Envoyée le')
    
    class Meta:
        verbose_name = 'Notification d\'événement'
        verbose_name_plural = 'Notifications d\'événement'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.recipient.get_full_name()}"
    
    def mark_as_read(self):
        """Marque la notification comme lue"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    def get_icon(self):
        """Retourne l'icône FontAwesome appropriée"""
        icons = {
            'new_event': 'fas fa-calendar-plus',
            'event_updated': 'fas fa-edit',
            'reminder': 'fas fa-clock',
            'issue': 'fas fa-exclamation-triangle',
            'staff_update': 'fas fa-users',
            'status_change': 'fas fa-sync-alt',
        }
        return icons.get(self.type, 'fas fa-bell')
    
    def get_color_class(self):
        """Retourne la classe CSS pour la couleur"""
        colors = {
            'new_event': 'text-success',
            'event_updated': 'text-info',
            'reminder': 'text-warning',
            'issue': 'text-danger',
            'staff_update': 'text-primary',
            'status_change': 'text-secondary',
        }
        return colors.get(self.type, 'text-info')

class EventContract(models.Model):
    """Contrat d'événement géré par le maître d'hôtel"""
    
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Basse'),
        ('normal', 'Normale'),
        ('high', 'Haute'),
        ('urgent', 'Urgente'),
    ]
    
    # Références
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='event_contract')
    contract_number = models.CharField(max_length=50, unique=True, editable=False)
    
    # Assignment
    maitre_hotel = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='assigned_events',
        limit_choices_to={'role': 'maitre_hotel'},
        verbose_name='Maître d\'hôtel assigné'
    )
    
    # Informations événement
    event_name = models.CharField(max_length=200, verbose_name='Nom de l\'événement')
    event_description = models.TextField(blank=True, verbose_name='Description')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    
    # Dates et horaires
    setup_start_time = models.DateTimeField(verbose_name='Début installation')
    event_start_time = models.DateTimeField(verbose_name='Début événement')
    event_end_time = models.DateTimeField(verbose_name='Fin événement')
    cleanup_end_time = models.DateTimeField(verbose_name='Fin nettoyage')
    
    # Lieu détaillé
    venue_name = models.CharField(max_length=200, blank=True, verbose_name='Nom du lieu')
    venue_contact = models.CharField(max_length=100, blank=True, verbose_name='Contact lieu')
    venue_phone = models.CharField(max_length=20, blank=True, verbose_name='Téléphone lieu')
    venue_instructions = models.TextField(blank=True, verbose_name='Instructions d\'accès')
    
    # Équipe assignée
    service_staff = models.ManyToManyField(
        User,
        through='EventStaffAssignment',
        related_name='events_as_staff',
        limit_choices_to={'role': 'staff'},
        blank=True
    )
    
    # Matériel et équipements
    equipment_needed = models.TextField(blank=True, verbose_name='Équipements nécessaires')
    special_requirements = models.TextField(blank=True, verbose_name='Exigences spéciales')
    
    # Documents
    contract_file = models.FileField(upload_to='contracts/', blank=True, null=True)
    layout_plan = models.ImageField(upload_to='event_plans/', blank=True, null=True)
    
    # Suivi
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='contracts_created')
    updated_at = models.DateTimeField(auto_now=True)
    
    # Validation
    is_validated = models.BooleanField(default=False, verbose_name='Validé')
    validated_at = models.DateTimeField(null=True, blank=True)
    validated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='contracts_validated')
    
    class Meta:
        verbose_name = 'Contrat d\'événement'
        verbose_name_plural = 'Contrats d\'événements'
        ordering = ['event_start_time']
    
    def __str__(self):
        return f"{self.contract_number} - {self.event_name}"
    
    def save(self, *args, **kwargs):
        if not self.contract_number:
            self.contract_number = self.generate_contract_number()
        super().save(*args, **kwargs)
    
    def generate_contract_number(self):
        """Génère un numéro de contrat unique"""
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(uuid.uuid4())[:6].upper()
        return f"CONT-{date_str}-{random_str}"
    
    def get_duration_hours(self):
        """Calcule la durée totale en heures"""
        delta = self.cleanup_end_time - self.setup_start_time
        return delta.total_seconds() / 3600
    
    def is_today(self):
        """Vérifie si l'événement est aujourd'hui"""
        today = timezone.now().date()
        return self.event_start_time.date() == today

class EventStaffAssignment(models.Model):
    """Assignment du personnel à un événement"""
    
    ROLE_CHOICES = [
        ('server', 'Serveur'),
        ('bartender', 'Barman'),
        ('chef', 'Chef'),
        ('assistant', 'Assistant'),
        ('setup', 'Installation'),
        ('cleanup', 'Nettoyage'),
    ]
    
    event = models.ForeignKey(EventContract, on_delete=models.CASCADE, related_name='staff_assignments')
    staff_member = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    
    arrival_time = models.DateTimeField(verbose_name='Heure d\'arrivée')
    departure_time = models.DateTimeField(verbose_name='Heure de départ')
    
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    
    # Tracking présence
    checked_in = models.BooleanField(default=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out = models.BooleanField(default=False)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Assignment personnel'
        verbose_name_plural = 'Assignments personnel'
        unique_together = ['event', 'staff_member']
    
    def __str__(self):
        return f"{self.staff_member.get_full_name()} - {self.get_role_display()}"

class EventReport(models.Model):
    """Rapport de fin d'événement"""
    
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('submitted', 'Soumis'),
        ('approved', 'Approuvé'),
    ]
    
    RATING_CHOICES = [
        (1, 'Très mauvais'),
        (2, 'Mauvais'),
        (3, 'Moyen'),
        (4, 'Bon'),
        (5, 'Excellent'),
    ]
    
    event = models.OneToOneField(EventContract, on_delete=models.CASCADE, related_name='final_report')
    report_number = models.CharField(max_length=50, unique=True, editable=False)
    
    # Évaluation générale
    overall_rating = models.IntegerField(choices=RATING_CHOICES, verbose_name='Note générale')
    client_satisfaction = models.IntegerField(choices=RATING_CHOICES, verbose_name='Satisfaction client')
    
    # Déroulement
    setup_notes = models.TextField(verbose_name='Notes installation')
    service_notes = models.TextField(verbose_name='Notes service')
    cleanup_notes = models.TextField(verbose_name='Notes nettoyage')
    
    # Problèmes et solutions
    issues_encountered = models.TextField(blank=True, verbose_name='Problèmes rencontrés')
    solutions_applied = models.TextField(blank=True, verbose_name='Solutions appliquées')
    
    # Équipe
    staff_performance = models.TextField(blank=True, verbose_name='Performance équipe')
    staff_feedback = models.TextField(blank=True, verbose_name='Retours équipe')
    
    # Client
    client_feedback = models.TextField(blank=True, verbose_name='Retours client')
    client_complaints = models.TextField(blank=True, verbose_name='Plaintes client')
    client_compliments = models.TextField(blank=True, verbose_name='Compliments client')
    
    # Recommandations
    recommendations = models.TextField(blank=True, verbose_name='Recommandations')
    improvements_needed = models.TextField(blank=True, verbose_name='Améliorations nécessaires')
    
    # Validation
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports_approved')
    
    class Meta:
        verbose_name = 'Rapport d\'événement'
        verbose_name_plural = 'Rapports d\'événements'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Rapport {self.report_number} - {self.event.event_name}"
    
    def save(self, *args, **kwargs):
        if not self.report_number:
            self.report_number = self.generate_report_number()
        super().save(*args, **kwargs)
    
    def generate_report_number(self):
        """Génère un numéro de rapport unique"""
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(uuid.uuid4())[:6].upper()
        return f"RPT-{date_str}-{random_str}"

class EventPhoto(models.Model):
    """Photos d'événement pour le rapport"""
    
    PHOTO_TYPE_CHOICES = [
        ('setup', 'Installation'),
        ('service', 'Service'),
        ('decoration', 'Décoration'),
        ('food', 'Nourriture'),
        ('guests', 'Invités'),
        ('staff', 'Équipe'),
        ('cleanup', 'Nettoyage'),
        ('issue', 'Problème'),
        ('before', 'Avant'),
        ('after', 'Après'),
    ]
    
    event = models.ForeignKey(EventContract, on_delete=models.CASCADE, related_name='photos')
    report = models.ForeignKey(EventReport, on_delete=models.CASCADE, related_name='photos', null=True, blank=True)
    
    photo = models.ImageField(upload_to='event_photos/%Y/%m/%d/')
    photo_type = models.CharField(max_length=20, choices=PHOTO_TYPE_CHOICES)
    caption = models.CharField(max_length=200, blank=True, verbose_name='Légende')
    description = models.TextField(blank=True, verbose_name='Description')
    
    # Métadonnées
    taken_at = models.DateTimeField(auto_now_add=True)
    taken_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Géolocalisation
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Photo d\'événement'
        verbose_name_plural = 'Photos d\'événement'
        ordering = ['taken_at']
    
    def __str__(self):
        return f"Photo {self.get_photo_type_display()} - {self.event.event_name}"

class EventTimeline(models.Model):
    """Timeline des actions pendant l'événement"""
    
    ACTION_CHOICES = [
        ('setup_start', 'Début installation'),
        ('setup_complete', 'Installation terminée'),
        ('staff_arrival', 'Arrivée personnel'),
        ('event_start', 'Début événement'),
        ('service_issue', 'Problème service'),
        ('client_request', 'Demande client'),
        ('event_end', 'Fin événement'),
        ('cleanup_start', 'Début nettoyage'),
        ('cleanup_complete', 'Nettoyage terminé'),
        ('departure', 'Départ'),
        ('other', 'Autre'),
    ]
    
    event = models.ForeignKey(EventContract, on_delete=models.CASCADE, related_name='timeline')
    
    timestamp = models.DateTimeField(verbose_name='Horodatage')
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField(verbose_name='Description')
    
    # Personne responsable
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Priorité pour les problèmes
    is_important = models.BooleanField(default=False, verbose_name='Important')
    is_issue = models.BooleanField(default=False, verbose_name='Problème')
    
    class Meta:
        verbose_name = 'Événement timeline'
        verbose_name_plural = 'Événements timeline'
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.timestamp.strftime('%H:%M')} - {self.get_action_type_display()}"


class CookProfile(models.Model):
    """Profil spécifique aux cuisiniers"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cook_profile')
    
    # Département principal
    primary_department = models.CharField(max_length=20, choices=[
        ('patisserie', 'Pâtisserie'),
        ('chaud', 'Cuisine Chaude'),
        ('sandwichs', 'Sandwichs'),
        ('boites', 'Boîtes à lunch'),
        ('salades', 'Salades'),
        ('dejeuners', 'Déjeuners'),
        ('bouchees', 'Bouchées'),
    ], verbose_name='Département principal')
    
    # Départements secondaires
    secondary_departments = models.JSONField(default=list, verbose_name='Départements secondaires')
    
    # Compétences
    specialties = models.JSONField(default=list, verbose_name='Spécialités')
    skill_level = models.IntegerField(default=1, verbose_name='Niveau de compétence (1-5)')
    
    # Horaires
    shift_start = models.TimeField(default='06:00', verbose_name='Début de service')
    shift_end = models.TimeField(default='14:00', verbose_name='Fin de service')
    
    # Statistiques
    total_items_produced = models.IntegerField(default=0, verbose_name='Total d\'articles produits')
    average_quality_score = models.DecimalField(max_digits=3, decimal_places=1, default=0, verbose_name='Score qualité moyen')
    
    is_available = models.BooleanField(default=True, verbose_name='Disponible')
    
    class Meta:
        verbose_name = 'Profil cuisinier'
        verbose_name_plural = 'Profils cuisiniers'
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_primary_department_display()}"
    
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid

# ========================================
# MODÈLES POUR LA GESTION DES PRODUITS/INGRÉDIENTS
# ========================================

class Supplier(models.Model):
    """Fournisseurs pour les commandes de produits"""
    name = models.CharField(max_length=200, verbose_name='Nom du fournisseur')
    contact_name = models.CharField(max_length=100, blank=True, verbose_name='Nom du contact')
    email = models.EmailField(blank=True, verbose_name='Email')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Téléphone')
    address = models.TextField(blank=True, verbose_name='Adresse')
    
    # Spécialités du fournisseur
    specialties = models.JSONField(default=list, verbose_name='Spécialités')
    
    # Conditions
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Commande minimum')
    delivery_days = models.CharField(max_length=200, blank=True, verbose_name='Jours de livraison')
    
    is_active = models.BooleanField(default=True, verbose_name='Actif')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Fournisseur'
        verbose_name_plural = 'Fournisseurs'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class KitchenProduct(models.Model):
    """Produits/ingrédients pour la cuisine"""
    
    CATEGORY_CHOICES = [
        ('viandes', 'Viandes'),
        ('poissons', 'Poissons'),
        ('legumes', 'Légumes'),
        ('fruits', 'Fruits'),
        ('cereales', 'Céréales'),
        ('laitiers', 'Produits laitiers'),
        ('epices', 'Épices et condiments'),
        ('huiles', 'Huiles et vinaigres'),
        ('conserves', 'Conserves'),
        ('surgeles', 'Surgelés'),
        ('autres', 'Autres'),
    ]
    
    UNIT_CHOICES = [
        ('kg', 'Kilogramme'),
        ('g', 'Gramme'),
        ('l', 'Litre'),
        ('ml', 'Millilitre'),
        ('unite', 'Unité'),
        ('boite', 'Boîte'),
        ('sachet', 'Sachet'),
    ]
    
    name = models.CharField(max_length=200, verbose_name='Nom du produit')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name='Catégorie')
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, verbose_name='Unité')
    
    # Stock
    current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Stock actuel')
    min_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Stock minimum')
    max_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Stock maximum')
    
    # Prix
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Prix unitaire')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Fournisseur principal')
    
    # Départements qui utilisent ce produit
    departments = models.JSONField(default=list, verbose_name='Départements utilisateurs')
    
    # Durée de conservation
    shelf_life_days = models.IntegerField(default=7, verbose_name='Durée de conservation (jours)')
    
    is_active = models.BooleanField(default=True, verbose_name='Actif')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Produit cuisine'
        verbose_name_plural = 'Produits cuisine'
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_unit_display()})"
    
    def is_low_stock(self):
        return self.current_stock <= self.min_stock
    
    def needs_restocking(self):
        return self.current_stock < (self.min_stock * 1.2)

class ProductOrder(models.Model):
    """Commandes de produits pour la cuisine"""
    
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('pending', 'En attente d\'approbation'),
        ('approved', 'Approuvée'),
        ('ordered', 'Commandée'),
        ('received', 'Reçue'),
        ('cancelled', 'Annulée'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Basse'),
        ('normal', 'Normale'),
        ('high', 'Haute'),
        ('urgent', 'Urgente'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True, editable=False)
    
    # Qui commande
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_orders_requested')
    department = models.CharField(max_length=20, choices=[
        ('patisserie', 'Pâtisserie'),
        ('chaud', 'Cuisine Chaude'),
        ('sandwichs', 'Sandwichs'),
        ('boites', 'Boîtes à lunch'),
        ('salades', 'Salades'),
        ('dejeuners', 'Déjeuners'),
        ('bouchees', 'Bouchées'),
        ('general', 'Général'),
    ], verbose_name='Département')
    
    # Fournisseur
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name='Fournisseur')
    
    # Statut et priorité
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    
    # Dates
    needed_date = models.DateField(verbose_name='Date souhaitée')
    delivery_date = models.DateField(null=True, blank=True, verbose_name='Date de livraison')
    
    # Notes
    notes = models.TextField(blank=True, verbose_name='Notes')
    internal_notes = models.TextField(blank=True, verbose_name='Notes internes')
    
    # Approbation
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='product_orders_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Totaux
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Montant total')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Commande produit'
        verbose_name_plural = 'Commandes produits'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Commande {self.order_number} - {self.supplier.name}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        date_str = timezone.now().strftime('%Y%m%d')
        random_str = str(uuid.uuid4())[:6].upper()
        return f"CMD-{date_str}-{random_str}"
    
    def calculate_total(self):
        total = sum(item.total_price for item in self.items.all())
        self.total_amount = total
        self.save()
        return total

class ProductOrderItem(models.Model):
    """Articles d'une commande de produits"""
    order = models.ForeignKey(ProductOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(KitchenProduct, on_delete=models.CASCADE)
    
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Quantité')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Prix unitaire')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Prix total')
    
    notes = models.TextField(blank=True, verbose_name='Notes')
    
    # Réception
    received_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Quantité reçue')
    received_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Article commande'
        verbose_name_plural = 'Articles commande'
    
    def __str__(self):
        return f"{self.quantity} {self.product.unit} de {self.product.name}"
    
    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

# ========================================
# MODÈLES POUR LA PRODUCTION CUISINE
# ========================================

class KitchenProduction(models.Model):
    """Production quotidienne par département"""
    
    date = models.DateField(verbose_name='Date de production')
    department = models.CharField(max_length=20, choices=[
        ('patisserie', 'Pâtisserie'),
        ('chaud', 'Cuisine Chaude'),
        ('sandwichs', 'Sandwichs'),
        ('boites', 'Boîtes à lunch'),
        ('salades', 'Salades'),
        ('dejeuners', 'Déjeuners'),
        ('bouchees', 'Bouchées'),
    ], verbose_name='Département')
    
    # Chef responsable du département
    department_chef = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='department_productions',
        limit_choices_to={'role__in': ['department_chef', 'head_chef']},
        verbose_name='Chef de département'
    )
    
    # Statut global de la production
    STATUS_CHOICES = [
        ('not_started', 'Non commencée'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminée'),
        ('delayed', 'En retard'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    
    # Métadonnées
    total_items = models.IntegerField(default=0, verbose_name='Total d\'articles')
    completed_items = models.IntegerField(default=0, verbose_name='Articles terminés')
    progress_percentage = models.IntegerField(default=0, verbose_name='Pourcentage d\'avancement')
    
    # Notes
    notes = models.TextField(blank=True, verbose_name='Notes de production')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Production cuisine'
        verbose_name_plural = 'Productions cuisine'
        unique_together = ['date', 'department']
        ordering = ['date', 'department']
    
    def __str__(self):
        return f"Production {self.get_department_display()} - {self.date}"
    
    def update_progress(self):
        """Met à jour le pourcentage de progression"""
        items = self.production_items.all()
        self.total_items = items.count()
        self.completed_items = items.filter(is_completed=True).count()
        
        if self.total_items > 0:
            self.progress_percentage = int((self.completed_items / self.total_items) * 100)
        else:
            self.progress_percentage = 0
        
        # Mettre à jour le statut
        if self.progress_percentage == 0:
            self.status = 'not_started'
        elif 0 < self.progress_percentage < 100:
            self.status = 'in_progress'
        elif self.progress_percentage == 100:
            self.status = 'completed'
        
        self.save()

class ProductionItem(models.Model):
    """Article à produire dans un département"""
    
    production = models.ForeignKey(KitchenProduction, on_delete=models.CASCADE, related_name='production_items')
    order_item = models.ForeignKey('OrderItem', on_delete=models.CASCADE, verbose_name='Article de commande')
    
    # Quantité à produire
    quantity_to_produce = models.IntegerField(verbose_name='Quantité à produire')
    quantity_produced = models.IntegerField(default=0, verbose_name='Quantité produite')
    
    # Statut
    is_completed = models.BooleanField(default=False, verbose_name='Terminé')
    is_priority = models.BooleanField(default=False, verbose_name='Prioritaire')
    
    # Suivi de production
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Commencé à')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Terminé à')
    produced_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='produced_items',
        verbose_name='Produit par'
    )
    
    # Notes spécifiques
    production_notes = models.TextField(blank=True, verbose_name='Notes de production')
    quality_notes = models.TextField(blank=True, verbose_name='Notes qualité')
    
    # Problèmes
    has_issue = models.BooleanField(default=False, verbose_name='Problème signalé')
    issue_description = models.TextField(blank=True, verbose_name='Description du problème')
    
    class Meta:
        verbose_name = 'Article de production'
        verbose_name_plural = 'Articles de production'
        ordering = ['is_priority', 'order_item__order__delivery_date', 'order_item__order__delivery_time']
    
    def __str__(self):
        return f"{self.order_item.product_name} x{self.quantity_to_produce}"
    
    def mark_completed(self, user, quantity=None):
        """Marque l'article comme terminé"""
        self.is_completed = True
        self.completed_at = timezone.now()
        self.produced_by = user
        if quantity:
            self.quantity_produced = quantity
        else:
            self.quantity_produced = self.quantity_to_produce
        
        if not self.started_at:
            self.started_at = self.completed_at
        
        self.save()
        
        # Mettre à jour la progression de la production
        self.production.update_progress()
    
    def start_production(self, user):
        """Démarre la production de cet article"""
        if not self.started_at:
            self.started_at = timezone.now()
            self.save()

class QualityCheck(models.Model):
    """Contrôle qualité des productions"""
    
    RATING_CHOICES = [
        (1, 'Très mauvais'),
        (2, 'Mauvais'),
        (3, 'Moyen'),
        (4, 'Bon'),
        (5, 'Excellent'),
    ]
    
    production_item = models.ForeignKey(ProductionItem, on_delete=models.CASCADE, related_name='quality_checks')
    
    # Évaluation
    appearance_rating = models.IntegerField(choices=RATING_CHOICES, verbose_name='Apparence')
    taste_rating = models.IntegerField(choices=RATING_CHOICES, verbose_name='Goût')
    texture_rating = models.IntegerField(choices=RATING_CHOICES, verbose_name='Texture')
    overall_rating = models.IntegerField(choices=RATING_CHOICES, verbose_name='Note globale')
    
    # Conformité
    meets_standards = models.BooleanField(default=True, verbose_name='Conforme aux standards')
    approved_for_service = models.BooleanField(default=True, verbose_name='Approuvé pour le service')
    
    # Notes
    comments = models.TextField(blank=True, verbose_name='Commentaires')
    improvement_notes = models.TextField(blank=True, verbose_name='Points d\'amélioration')
    
    # Qui a fait le contrôle
    checked_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quality_checks_performed')
    checked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Contrôle qualité'
        verbose_name_plural = 'Contrôles qualité'
        ordering = ['-checked_at']
    
    def __str__(self):
        return f"Contrôle {self.production_item} - Note: {self.overall_rating}/5"

# ========================================
# MODÈLES POUR LES NOTIFICATIONS ET ALERTES
# ========================================

class KitchenNotification(models.Model):
    """Notifications pour la cuisine"""
    
    TYPE_CHOICES = [
        ('low_stock', 'Stock faible'),
        ('production_delay', 'Retard de production'),
        ('quality_issue', 'Problème qualité'),
        ('order_urgent', 'Commande urgente'),
        ('equipment_issue', 'Problème équipement'),
        ('general', 'Général'),
    ]
    
    RECIPIENT_TYPE_CHOICES = [
        ('head_chef', 'Chef de cuisine'),
        ('department_chef', 'Chef de département'),
        ('cook', 'Cuisinier'),
        ('all_kitchen', 'Toute la cuisine'),
    ]
    
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    recipient_type = models.CharField(max_length=20, choices=RECIPIENT_TYPE_CHOICES)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='kitchen_notifications')
    
    title = models.CharField(max_length=200, verbose_name='Titre')
    message = models.TextField(verbose_name='Message')
    
    # Références
    production_item = models.ForeignKey(ProductionItem, on_delete=models.CASCADE, null=True, blank=True)
    product_order = models.ForeignKey(ProductOrder, on_delete=models.CASCADE, null=True, blank=True)
    
    # Statut
    is_read = models.BooleanField(default=False, verbose_name='Lu')
    is_urgent = models.BooleanField(default=False, verbose_name='Urgent')
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Notification cuisine'
        verbose_name_plural = 'Notifications cuisine'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.recipient.get_full_name()}"
    
    def mark_as_read(self):
        self.is_read = True
        self.read_at = timezone.now()
        self.save()