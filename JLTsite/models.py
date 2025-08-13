from django.db import models
from django.utils import timezone
from django.conf import settings

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

from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """Utilisateur personnalisé avec informations supplémentaires"""
    
    CUSTOMER = 'customer'
    STAFF = 'staff'
    ADMIN = 'admin'
    
    ROLE_CHOICES = [
        (CUSTOMER, 'Client'),
        (STAFF, 'Personnel'),
        (ADMIN, 'Administrateur'),
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
    image_2 = models.ImageField(upload_to='products/', blank=True, null=True)
    image_3 = models.ImageField(upload_to='products/', blank=True, null=True)
    
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
    
    class Meta:
        verbose_name = 'Article de commande'
        verbose_name_plural = 'Articles de commande'
    
    def __str__(self):
        return f"{self.quantity}x {self.product_name}"
    
    def save(self, *args, **kwargs):
        self.subtotal = self.product_price * self.quantity
        super().save(*args, **kwargs)

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