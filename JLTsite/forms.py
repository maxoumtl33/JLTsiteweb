from django import forms
from .models import *

class CategorieBoiteALunchForm(forms.ModelForm):
    class Meta:
        model = CategorieBoiteALunch
        fields = ['nom']  # Fields to include in the category form

class BoiteALunchForm(forms.ModelForm):
    class Meta:
        model = BoiteALunch
        fields = ['nom', 'categorie', 'description', 'prix', 'photo1', 'photo2']  # Fields to include in the form


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    message = forms.CharField(widget=forms.Textarea, required=True)