from django import forms
from .models import ContactSubmission
from django.utils import timezone

class ContactForm(forms.ModelForm):
    """Formulaire de contact avec validation"""
    
    class Meta:
        model = ContactSubmission
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'company',
            'event_type', 'guest_count', 'event_date', 'budget',
            'message', 'newsletter'
        ]
        widgets = {
            'event_date': forms.DateInput(attrs={'type': 'date'}),
            'message': forms.Textarea(attrs={'rows': 5}),
        }
    
    def clean_event_date(self):
        """Valider que la date est dans le futur"""
        event_date = self.cleaned_data.get('event_date')
        if event_date and event_date < timezone.now().date():
            raise forms.ValidationError("La date de l'événement doit être dans le futur.")
        return event_date
    
    def clean_guest_count(self):
        """Valider le nombre d'invités"""
        guest_count = self.cleaned_data.get('guest_count')
        if guest_count and guest_count < 1:
            raise forms.ValidationError("Le nombre d'invités doit être au moins 1.")
        return guest_count
    
# ========================================
# forms.py - Formulaires pour le système e-commerce
# ========================================

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, time, timedelta
import re

from .models import User, Order, Review

# ========================================
# 1. FORMULAIRES D'AUTHENTIFICATION
# ========================================

class SignUpForm(UserCreationForm):
    """Formulaire d'inscription"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'votre@email.com'
        })
    )
    first_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Prénom'
        })
    )
    last_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom'
        })
    )
    phone = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '514-XXX-XXXX'
        })
    )
    company = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Entreprise (optionnel)'
        })
    )
    newsletter = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Je souhaite recevoir les offres et nouveautés par email'
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 
                 'phone', 'company', 'password1', 'password2', 'newsletter')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom d\'utilisateur'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password1'].widget.attrs['placeholder'] = 'Mot de passe'
        self.fields['password2'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['placeholder'] = 'Confirmer le mot de passe'
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Cette adresse email est déjà utilisée.')
        return email
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        # Nettoyer le numéro de téléphone
        phone = re.sub(r'\D', '', phone)
        
        if len(phone) != 10:
            raise ValidationError('Le numéro de téléphone doit contenir 10 chiffres.')
        
        # Formater le numéro
        return f"{phone[:3]}-{phone[3:6]}-{phone[6:]}"

class LoginForm(forms.Form):
    """Formulaire de connexion"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email ou nom d\'utilisateur'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Se souvenir de moi'
    )

from JLTsite.models import User

class ProfileForm(forms.ModelForm):
    """Formulaire de profil utilisateur"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 
                 'company', 'address', 'postal_code', 'city', 'newsletter']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'company': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'newsletter': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# ========================================
# 2. FORMULAIRE DE COMMANDE
# ========================================

class CheckoutForm(forms.ModelForm):
    """Formulaire de commande"""
    
    # Choix pour les heures de livraison
    DELIVERY_TIME_CHOICES = [
        (time(8, 0), '8h00 - 9h00'),
        (time(9, 0), '9h00 - 10h00'),
        (time(10, 0), '10h00 - 11h00'),
        (time(11, 0), '11h00 - 12h00'),
        (time(12, 0), '12h00 - 13h00'),
        (time(13, 0), '13h00 - 14h00'),
        (time(14, 0), '14h00 - 15h00'),
        (time(15, 0), '15h00 - 16h00'),
        (time(16, 0), '16h00 - 17h00'),
        (time(17, 0), '17h00 - 18h00'),
    ]
    
    delivery_time = forms.ChoiceField(
        choices=DELIVERY_TIME_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    accept_terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='J\'accepte les conditions générales de vente'
    )
    
    class Meta:
        model = Order
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'company',
            'delivery_type', 'delivery_address', 'delivery_postal_code',
            'delivery_city', 'delivery_date', 'delivery_time', 'delivery_notes'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Prénom'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@exemple.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '514-XXX-XXXX'
            }),
            'company': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Entreprise (optionnel)'
            }),
            'delivery_type': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'delivery_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Adresse complète de livraison'
            }),
            'delivery_postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'H0H 0H0'
            }),
            'delivery_city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Montréal'
            }),
            'delivery_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'delivery_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Instructions spéciales (optionnel)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Définir la date minimum à demain
        self.fields['delivery_date'].widget.attrs['min'] = (
            timezone.now().date() + timedelta(days=1)
        ).isoformat()
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        # Nettoyer et formater le numéro
        phone = re.sub(r'\D', '', phone)
        
        if len(phone) != 10:
            raise ValidationError('Le numéro de téléphone doit contenir 10 chiffres.')
        
        return f"{phone[:3]}-{phone[3:6]}-{phone[6:]}"
    
    def clean_delivery_postal_code(self):
        postal_code = self.cleaned_data.get('delivery_postal_code')
        # Valider le format du code postal canadien
        pattern = r'^[A-Z]\d[A-Z]\s?\d[A-Z]\d$'
        
        postal_code = postal_code.upper().replace(' ', '')
        if not re.match(pattern, postal_code):
            raise ValidationError('Format de code postal invalide.')
        
        # Formater avec espace
        return f"{postal_code[:3]} {postal_code[3:]}"
    
    def clean_delivery_date(self):
        delivery_date = self.cleaned_data.get('delivery_date')
        
        # Vérifier que la date n'est pas dans le passé
        if delivery_date <= timezone.now().date():
            raise ValidationError('La date de livraison doit être dans le futur.')
        
        # Vérifier que ce n'est pas un dimanche (fermé)
        if delivery_date.weekday() == 6:
            raise ValidationError('Nous ne livrons pas le dimanche.')
        
        # Vérifier le délai minimum (24h)
        min_date = timezone.now().date() + timedelta(days=1)
        if delivery_date < min_date:
            raise ValidationError('Veuillez prévoir un délai minimum de 24 heures.')
        
        return delivery_date

# ========================================
# 3. FORMULAIRE D'AVIS
# ========================================

class ReviewForm(forms.ModelForm):
    """Formulaire d'avis produit"""
    
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(
                choices=[(i, i) for i in range(1, 6)],
                attrs={'class': 'rating-stars'}
            ),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Partagez votre expérience avec ce produit...'
            })
        }
        labels = {
            'rating': 'Note',
            'comment': 'Votre avis'
        }
    
    def clean_comment(self):
        comment = self.cleaned_data.get('comment')
        
        if len(comment) < 10:
            raise ValidationError('Votre avis doit contenir au moins 10 caractères.')
        
        if len(comment) > 1000:
            raise ValidationError('Votre avis ne peut pas dépasser 1000 caractères.')
        
        return comment

# ========================================
# 4. FORMULAIRE DE COUPON
# ========================================

class CouponForm(forms.Form):
    """Formulaire d'application de coupon"""
    code = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Code promo'
        })
    )
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        return code.upper()


    """Formulaire de contact"""
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre nom'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'votre@email.com'
        })
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Sujet'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Votre message...'
        })
    )
    
    def clean_message(self):
        message = self.cleaned_data.get('message')
        
        if len(message) < 20:
            raise ValidationError('Le message doit contenir au moins 20 caractères.')
        
        return message
    
# JLTsite/forms.py - Formulaires pour le système chef de cuisine

from django import forms
from django.core.exceptions import ValidationError
from .models import (
    KitchenProduct, Supplier, ProductOrder, ProductOrderItem,
    KitchenProduction, ProductionItem, QualityCheck
)
import datetime

class ProductForm(forms.ModelForm):
    """Formulaire pour créer/modifier un produit cuisine"""
    
    class Meta:
        model = KitchenProduct
        fields = [
            'name', 'category', 'unit', 'current_stock', 'min_stock',
            'max_stock', 'unit_price', 'supplier', 'departments',
            'shelf_life_days', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du produit'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'current_stock': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'min_stock': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'max_stock': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'shelf_life_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'departments': forms.CheckboxSelectMultiple(),
        }
        labels = {
            'name': 'Nom du produit',
            'category': 'Catégorie',
            'unit': 'Unité de mesure',
            'current_stock': 'Stock actuel',
            'min_stock': 'Stock minimum',
            'max_stock': 'Stock maximum',
            'unit_price': 'Prix unitaire ($)',
            'supplier': 'Fournisseur principal',
            'departments': 'Départements utilisateurs',
            'shelf_life_days': 'Durée de conservation (jours)',
            'is_active': 'Produit actif'
        }
    
    def clean(self):
        cleaned_data = super().clean()
        min_stock = cleaned_data.get('min_stock')
        max_stock = cleaned_data.get('max_stock')
        current_stock = cleaned_data.get('current_stock')
        
        if min_stock and max_stock:
            if min_stock > max_stock:
                raise ValidationError('Le stock minimum ne peut pas être supérieur au stock maximum.')
        
        if current_stock and current_stock < 0:
            raise ValidationError('Le stock actuel ne peut pas être négatif.')
        
        return cleaned_data

class SupplierForm(forms.ModelForm):
    """Formulaire pour créer/modifier un fournisseur"""
    
    class Meta:
        model = Supplier
        fields = [
            'name', 'contact_name', 'email', 'phone', 'address',
            'specialties', 'min_order_amount', 'delivery_days', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du fournisseur'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du contact'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemple.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(514) 123-4567'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'min_order_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'delivery_days': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lundi, Mercredi, Vendredi'}),
        }
        labels = {
            'name': 'Nom du fournisseur',
            'contact_name': 'Personne contact',
            'email': 'Courriel',
            'phone': 'Téléphone',
            'address': 'Adresse',
            'specialties': 'Spécialités',
            'min_order_amount': 'Montant minimum de commande ($)',
            'delivery_days': 'Jours de livraison',
            'is_active': 'Fournisseur actif'
        }

class ProductOrderForm(forms.ModelForm):
    """Formulaire pour créer une commande de produits"""
    
    class Meta:
        model = ProductOrder
        fields = [
            'department', 'supplier', 'priority', 'needed_date', 'notes'
        ]
        widgets = {
            'department': forms.Select(attrs={'class': 'form-control'}),
            'supplier': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'needed_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'department': 'Département',
            'supplier': 'Fournisseur',
            'priority': 'Priorité',
            'needed_date': 'Date souhaitée',
            'notes': 'Notes de commande'
        }
    
    def clean_needed_date(self):
        needed_date = self.cleaned_data['needed_date']
        if needed_date < datetime.date.today():
            raise ValidationError('La date souhaitée ne peut pas être dans le passé.')
        return needed_date

class ProductOrderItemForm(forms.ModelForm):
    """Formulaire pour ajouter un article à une commande de produits"""
    
    class Meta:
        model = ProductOrderItem
        fields = ['product', 'quantity', 'notes']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'notes': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Notes optionnelles'}),
        }
        labels = {
            'product': 'Produit',
            'quantity': 'Quantité',
            'notes': 'Notes'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrer pour n'afficher que les produits actifs
        self.fields['product'].queryset = KitchenProduct.objects.filter(is_active=True)

class ProductionReportForm(forms.Form):
    """Formulaire pour générer des rapports de production"""
    
    REPORT_TYPE_CHOICES = [
        ('daily', 'Rapport journalier'),
        ('weekly', 'Rapport hebdomadaire'),
        ('monthly', 'Rapport mensuel'),
        ('custom', 'Période personnalisée'),
    ]
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Type de rapport'
    )
    
    department = forms.ChoiceField(
        choices=[('all', 'Tous les départements')] + list(KitchenProduction._meta.get_field('department').choices),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False,
        label='Département'
    )
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False,
        label='Date de début'
    )
    
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False,
        label='Date de fin'
    )
    
    include_quality = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Inclure les contrôles qualité'
    )
    
    include_issues = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Inclure les problèmes signalés'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        report_type = cleaned_data.get('report_type')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if report_type == 'custom':
            if not start_date or not end_date:
                raise ValidationError('Les dates de début et fin sont requises pour une période personnalisée.')
            if start_date > end_date:
                raise ValidationError('La date de début doit être antérieure à la date de fin.')
        
        return cleaned_data

class QualityCheckForm(forms.ModelForm):
    """Formulaire pour les contrôles qualité"""
    
    class Meta:
        model = QualityCheck
        fields = [
            'appearance_rating', 'taste_rating', 'texture_rating', 
            'overall_rating', 'meets_standards', 'approved_for_service',
            'comments', 'improvement_notes'
        ]
        widgets = {
            'appearance_rating': forms.Select(attrs={'class': 'form-control'}),
            'taste_rating': forms.Select(attrs={'class': 'form-control'}),
            'texture_rating': forms.Select(attrs={'class': 'form-control'}),
            'overall_rating': forms.Select(attrs={'class': 'form-control'}),
            'meets_standards': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'approved_for_service': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'comments': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'improvement_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'appearance_rating': 'Apparence',
            'taste_rating': 'Goût',
            'texture_rating': 'Texture',
            'overall_rating': 'Note globale',
            'meets_standards': 'Conforme aux standards',
            'approved_for_service': 'Approuvé pour le service',
            'comments': 'Commentaires',
            'improvement_notes': 'Points d\'amélioration'
        }

class BulkProductUpdateForm(forms.Form):
    """Formulaire pour mise à jour en masse des stocks"""
    
    products = forms.ModelMultipleChoiceField(
        queryset=KitchenProduct.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple(),
        label='Produits à mettre à jour'
    )
    
    action = forms.ChoiceField(
        choices=[
            ('add', 'Ajouter au stock'),
            ('subtract', 'Retirer du stock'),
            ('set', 'Définir le stock à'),
        ],
        widget=forms.RadioSelect(),
        label='Action'
    )
    
    quantity = forms.DecimalField(
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        label='Quantité'
    )
    
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        label='Raison de la modification',
        required=False
    )

class ProductionPlanningForm(forms.Form):
    """Formulaire pour planifier la production"""
    
    date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Date de production'
    )
    
    departments = forms.MultipleChoiceField(
        choices=KitchenProduction._meta.get_field('department').choices,
        widget=forms.CheckboxSelectMultiple(),
        label='Départements à planifier'
    )
    
    auto_assign = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Assigner automatiquement aux chefs de département'
    )
    
    priority_before = forms.TimeField(
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        label='Marquer comme prioritaire si livraison avant',
        initial='12:00'
    )
    
    notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label='Notes générales',
        required=False
    )
    
    def clean_date(self):
        date = self.cleaned_data['date']
        if date < datetime.date.today():
            raise ValidationError('La date de production ne peut pas être dans le passé.')
        return date