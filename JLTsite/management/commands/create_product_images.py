# management/commands/create_product_images.py
# Placez ce fichier dans JLTsite/management/commands/create_product_images.py

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from JLTsite.models import Product, Category
import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import random

class Command(BaseCommand):
    help = 'Crée des images placeholder pour les produits'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Création des images de produits...'))
        
        # Créer le répertoire d'images s'il n'existe pas
        os.makedirs('media/images', exist_ok=True)
        
        # Couleurs par catégorie
        category_colors = {
            'boites-a-lunch': ['#FF6B6B', '#4ECDC4', '#45B7D1'],
            'salades': ['#98D8C8', '#52B788', '#40916C'],
            'patisserie': ['#F7DC6F', '#F4A261', '#E76F51'],
            'plats-chauds': ['#E74C3C', '#C0392B', '#A93226'],
            'petit-dejeuner': ['#F39C12', '#E67E22', '#D35400'],
            'sandwichs': ['#3498DB', '#2980B9', '#1F618D'],
            'canapes': ['#9B59B6', '#8E44AD', '#7D3C98']
        }
        
        # Créer des images pour chaque produit
        for product in Product.objects.all():
            if not product.image:
                # Créer une image placeholder
                image = self.create_placeholder_image(
                    product.name, 
                    category_colors.get(product.category.slug, ['#BDC3C7'])
                )
                
                # Sauvegarder l'image
                image_io = BytesIO()
                image.save(image_io, format='JPEG', quality=85)
                image_file = ContentFile(image_io.getvalue())
                
                # Assigner l'image au produit
                filename = f"{product.slug}.jpg"
                product.image.save(filename, image_file, save=True)
                
                self.stdout.write(f'Image créée pour : {product.name}')
        
        # Créer des images pour les catégories
        for category in Category.objects.all():
            if not category.image:
                image = self.create_category_image(
                    category.name,
                    category_colors.get(category.slug, ['#BDC3C7'])
                )
                
                image_io = BytesIO()
                image.save(image_io, format='JPEG', quality=85)
                image_file = ContentFile(image_io.getvalue())
                
                filename = f"{category.slug}-category.jpg"
                category.image.save(filename, image_file, save=True)
                
                self.stdout.write(f'Image de catégorie créée pour : {category.name}')
        
        self.stdout.write(self.style.SUCCESS('Images créées avec succès !'))

    def create_placeholder_image(self, product_name, colors):
        """Crée une image placeholder pour un produit"""
        # Taille de l'image
        width, height = 800, 600
        
        # Créer l'image avec un dégradé
        image = Image.new('RGB', (width, height), color=random.choice(colors))
        draw = ImageDraw.Draw(image)
        
        # Ajouter un effet de dégradé simple
        for i in range(height):
            alpha = i / height
            color = self.interpolate_color(colors[0], '#FFFFFF', alpha * 0.3)
            draw.line([(0, i), (width, i)], fill=color)
        
        # Ajouter le nom du produit
        try:
            # Essayer d'utiliser une police système
            try:
                font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 48)
                font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
            except:
                try:
                    font_large = ImageFont.truetype("arial.ttf", 48)
                    font_small = ImageFont.truetype("arial.ttf", 24)
                except:
                    font_large = ImageFont.load_default()
                    font_small = ImageFont.load_default()
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Ajouter un rectangle semi-transparent pour le texte
        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle([(50, height//2 - 60), (width-50, height//2 + 60)], 
                              fill=(0, 0, 0, 128))
        
        # Fusionner l'overlay avec l'image principale
        image = Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(image)
        
        # Ajouter le texte
        lines = self.wrap_text(product_name, font_large, width - 100)
        y_offset = height//2 - (len(lines) * 30) // 2
        
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font_large)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            draw.text((x, y_offset), line, font=font_large, fill='white')
            y_offset += 50
        
        # Ajouter "Julien-Leblanc Traiteur" en bas
        watermark = "Julien-Leblanc Traiteur"
        bbox = draw.textbbox((0, 0), watermark, font=font_small)
        text_width = bbox[2] - bbox[0]
        draw.text((width - text_width - 20, height - 40), watermark, 
                 font=font_small, fill='white')
        
        return image

    def create_category_image(self, category_name, colors):
        """Crée une image pour une catégorie"""
        width, height = 1200, 400
        
        # Créer l'image avec un dégradé
        image = Image.new('RGB', (width, height), color=colors[0])
        draw = ImageDraw.Draw(image)
        
        # Dégradé horizontal
        for i in range(width):
            alpha = i / width
            if len(colors) > 1:
                color = self.interpolate_color(colors[0], colors[1], alpha)
            else:
                color = self.interpolate_color(colors[0], '#FFFFFF', alpha * 0.5)
            draw.line([(i, 0), (i, height)], fill=color)
        
        # Ajouter le titre de la catégorie
        try:
            font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 72)
        except:
            try:
                font_title = ImageFont.truetype("arial.ttf", 72)
            except:
                font_title = ImageFont.load_default()
        
        # Centrer le texte
        bbox = draw.textbbox((0, 0), category_name, font=font_title)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Ombre du texte
        draw.text((x + 3, y + 3), category_name, font=font_title, fill='black')
        # Texte principal
        draw.text((x, y), category_name, font=font_title, fill='white')
        
        return image

    def wrap_text(self, text, font, max_width):
        """Divise le texte en lignes pour qu'il tienne dans la largeur"""
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = ImageDraw.Draw(Image.new('RGB', (1, 1))).textbbox((0, 0), test_line, font=font)
            text_width = bbox[2] - bbox[0]
            
            if text_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines

    def interpolate_color(self, color1, color2, alpha):
        """Interpole entre deux couleurs"""
        # Convertir les couleurs hex en RGB
        if isinstance(color1, str):
            color1 = tuple(int(color1[i:i+2], 16) for i in (1, 3, 5))
        if isinstance(color2, str):
            color2 = tuple(int(color2[i:i+2], 16) for i in (1, 3, 5))
        
        # Interpoler
        r = int(color1[0] * (1 - alpha) + color2[0] * alpha)
        g = int(color1[1] * (1 - alpha) + color2[1] * alpha)
        b = int(color1[2] * (1 - alpha) + color2[2] * alpha)
        
        return (r, g, b)