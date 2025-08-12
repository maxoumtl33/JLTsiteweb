# services.py - Logique métier
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.db import transaction
from decimal import Decimal
import qrcode
from io import BytesIO
import base64
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

class EmailService:
    """Service d'envoi d'emails"""
    
    @staticmethod
    def send_order_confirmation(order):
        """Envoyer la confirmation de commande"""
        subject = f'Confirmation de commande #{order.order_number}'
        
        context = {
            'order': order,
            'items': order.items.all(),
            'delivery_address': order.delivery_address,
            'delivery_datetime': f"{order.delivery_date} à {order.delivery_time}"
        }
        
        html_content = render_to_string('emails/order_confirmation.html', context)
        text_content = strip_tags(html_content)
        
        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [order.user.email]
        )
        email.attach_alternative(html_content, "text/html")
        
        # Attacher le PDF de la facture
        pdf = InvoiceService.generate_invoice(order)
        email.attach(f'facture_{order.order_number}.pdf', pdf, 'application/pdf')
        
        email.send()
    
    @staticmethod
    def send_order_status_update(order, old_status):
        """Notifier le changement de statut"""
        status_messages = {
            'confirmed': 'Votre commande a été confirmée',
            'preparing': 'Votre commande est en préparation',
            'ready': 'Votre commande est prête',
            'delivered': 'Votre commande a été livrée',
            'cancelled': 'Votre commande a été annulée'
        }
        
        subject = f'Commande #{order.order_number} - {status_messages.get(order.status)}'
        
        context = {
            'order': order,
            'status_message': status_messages.get(order.status),
            'old_status': old_status
        }
        
        html_content = render_to_string('emails/order_status.html', context)
        text_content = strip_tags(html_content)
        
        send_mail(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [order.user.email],
            html_message=html_content
        )
    
    @staticmethod
    def send_promo_code(user, promo_code):
        """Envoyer un code promo personnalisé"""
        subject = f'Code promo exclusif: {promo_code.code}'
        
        context = {
            'user': user,
            'promo_code': promo_code,
            'discount_text': f"{promo_code.discount_value}%" if promo_code.discount_type == 'percentage' 
                           else f"{promo_code.discount_value}$"
        }
        
        html_content = render_to_string('emails/promo_code.html', context)
        text_content = strip_tags(html_content)
        
        send_mail(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_content
        )

class InvoiceService:
    """Service de génération de factures"""
    
    @staticmethod
    def generate_invoice(order):
        """Générer une facture PDF"""
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # En-tête
        p.setFont("Helvetica-Bold", 20)
        p.drawString(50, height - 50, "FACTURE")
        
        p.setFont("Helvetica", 12)
        p.drawString(50, height - 80, f"Numéro: {order.order_number}")
        p.drawString(50, height - 100, f"Date: {order.created_at.strftime('%d/%m/%Y')}")
        
        # Informations client
        p.setFont("Helvetica-Bold", 14)
        p.drawString(50, height - 140, "Client:")
        p.setFont("Helvetica", 12)
        p.drawString(50, height - 160, order.user.get_full_name() or order.user.username)
        p.drawString(50, height - 180, order.user.email)
        p.drawString(50, height - 200, order.delivery_address)
        
        # Tableau des articles
        y_position = height - 250
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y_position, "Article")
        p.drawString(300, y_position, "Qté")
        p.drawString(350, y_position, "Prix unit.")
        p.drawString(450, y_position, "Total")
        
        y_position -= 20
        p.setFont("Helvetica", 11)
        
        for item in order.items.all():
            p.drawString(50, y_position, item.lunch_box.name[:40])
            p.drawString(300, y_position, str(item.quantity))
            p.drawString(350, y_position, f"{item.unit_price:.2f}$")
            p.drawString(450, y_position, f"{item.get_total():.2f}$")
            y_position -= 20
        
        # Totaux
        y_position -= 30
        p.setFont("Helvetica", 12)
        p.drawString(350, y_position, "Sous-total:")
        p.drawString(450, y_position, f"{order.subtotal:.2f}$")
        
        if order.discount_amount > 0:
            y_position -= 20
            p.drawString(350, y_position, "Remise:")
            p.drawString(450, y_position, f"-{order.discount_amount:.2f}$")
        
        y_position -= 20
        p.drawString(350, y_position, "Taxes:")
        p.drawString(450, y_position, f"{order.tax_amount:.2f}$")
        
        if order.delivery_fee > 0:
            y_position -= 20
            p.drawString(350, y_position, "Livraison:")
            p.drawString(450, y_position, f"{order.delivery_fee:.2f}$")
        
        y_position -= 25
        p.setFont("Helvetica-Bold", 14)
        p.drawString(350, y_position, "TOTAL:")
        p.drawString(450, y_position, f"{order.total_amount:.2f}$")
        
        # QR Code pour suivi
        qr_code = InvoiceService.generate_qr_code(order)
        p.drawImage(ImageReader(qr_code), 450, 50, width=100, height=100)
        
        p.showPage()
        p.save()
        
        pdf = buffer.getvalue()
        buffer.close()
        return pdf
    
    @staticmethod
    def generate_qr_code(order):
        """Générer un QR code pour le suivi"""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        tracking_url = f"{settings.SITE_URL}/track/{order.order_number}"
        qr.add_data(tracking_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer

class InventoryService:
    """Service de gestion des stocks"""
    
    @staticmethod
    @transaction.atomic
    def check_availability(lunch_box_id, quantity):
        """Vérifier la disponibilité"""
        lunch_box = LunchBox.objects.select_for_update().get(id=lunch_box_id)
        
        # Ici on pourrait vérifier un stock réel
        # Pour l'instant on vérifie juste is_available
        return lunch_box.is_available
    
    @staticmethod
    def get_low_stock_items(threshold=10):
        """Obtenir les articles en rupture de stock"""
        # À implémenter avec un vrai système de stock
        return []

class RecommendationService:
    """Service de recommandations personnalisées"""
    
    @staticmethod
    def get_user_recommendations(user, limit=6):
        """Obtenir des recommandations basées sur l'historique"""
        from django.db.models import Count
        
        # Catégories préférées de l'utilisateur
        preferred_categories = OrderItem.objects.filter(
            order__user=user
        ).values('lunch_box__category').annotate(
            count=Count('id')
        ).order_by('-count')[:3].values_list('lunch_box__category', flat=True)
        
        # Produits jamais commandés dans ces catégories
        ordered_items = OrderItem.objects.filter(
            order__user=user
        ).values_list('lunch_box_id', flat=True)
        
        recommendations = LunchBox.objects.filter(
            category__in=preferred_categories,
            is_available=True
        ).exclude(
            id__in=ordered_items
        ).order_by('-sales_count')[:limit]
        
        # Si pas assez de recommandations, ajouter des best-sellers
        if recommendations.count() < limit:
            additional = LunchBox.objects.filter(
                is_available=True
            ).exclude(
                id__in=ordered_items
            ).order_by('-sales_count')[:limit - recommendations.count()]
            
            recommendations = list(recommendations) + list(additional)
        
        return recommendations
    
    @staticmethod
    def get_complementary_items(lunch_box, limit=4):
        """Obtenir des articles complémentaires"""
        # Articles souvent commandés ensemble
        orders_with_item = Order.objects.filter(
            items__lunch_box=lunch_box
        ).values_list('id', flat=True)
        
        complementary = OrderItem.objects.filter(
            order__in=orders_with_item
        ).exclude(
            lunch_box=lunch_box
        ).values('lunch_box').annotate(
            count=Count('id')
        ).order_by('-count')[:limit]
        
        return [item['lunch_box'] for item in complementary]