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