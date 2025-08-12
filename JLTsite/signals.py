# signals.py - Signaux Django
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Order, Review, User
from .services import EmailService

@receiver(pre_save, sender=Order)
def track_order_status_change(sender, instance, **kwargs):
    """Suivre les changements de statut"""
    if instance.pk:
        try:
            old_order = Order.objects.get(pk=instance.pk)
            if old_order.status != instance.status:
                instance._old_status = old_order.status
        except Order.DoesNotExist:
            pass

@receiver(post_save, sender=Order)
def handle_order_save(sender, instance, created, **kwargs):
    """Gérer la sauvegarde d'une commande"""
    if created:
        # Nouvelle commande
        EmailService.send_order_confirmation(instance)
    else:
        # Mise à jour de commande
        if hasattr(instance, '_old_status'):
            EmailService.send_order_status_update(instance, instance._old_status)

@receiver(post_save, sender=Review)
def update_product_rating(sender, instance, created, **kwargs):
    """Mettre à jour la note du produit"""
    if instance.is_approved:
        # Recalculer la moyenne des avis
        lunch_box = instance.lunch_box
        reviews = Review.objects.filter(lunch_box=lunch_box, is_approved=True)
        avg_rating = reviews.aggregate(models.Avg('rating'))['rating__avg']
        # Vous pouvez stocker cette moyenne dans un champ dédié si nécessaire

@receiver(post_save, sender=User)
def create_welcome_promo(sender, instance, created, **kwargs):
    """Créer un code promo de bienvenue"""
    if created:
        import random
        import string
        from datetime import timedelta
        
        code = 'WELCOME' + ''.join(random.choices(string.digits, k=4))
        
        PromoCode.objects.create(
            code=code,
            description='Code de bienvenue',
            discount_type='percentage',
            discount_value=10,
            minimum_order=30,
            user_limit=1,
            valid_from=timezone.now(),
            valid_until=timezone.now() + timedelta(days=30),
            is_active=True
        )
        
        # Envoyer le code par email
        EmailService.send_promo_code(instance, PromoCode.objects.get(code=code))

# tasks.py - Tâches Celery
from celery import shared_task
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Order, Analytics, User, PromoCode, LunchBox
from .services import EmailService, InventoryService

@shared_task
def process_daily_analytics():
    """Traiter les analytics quotidiennes"""
    from .views import update_daily_analytics
    update_daily_analytics()
    return "Analytics processed successfully"

@shared_task
def send_order_reminders():
    """Envoyer des rappels pour les commandes à venir"""
    tomorrow = timezone.now().date() + timedelta(days=1)
    
    orders = Order.objects.filter(
        delivery_date=tomorrow,
        status__in=['confirmed', 'preparing']
    )
    
    for order in orders:
        subject = f"Rappel: Votre commande #{order.order_number} pour demain"
        context = {
            'order': order,
            'delivery_time': order.delivery_time
        }
        
        html_content = render_to_string('emails/order_reminder.html', context)
        text_content = strip_tags(html_content)
        
        send_mail(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [order.user.email],
            html_message=html_content
        )
    
    return f"Sent {orders.count()} reminders"

@shared_task
def cleanup_abandoned_carts():
    """Nettoyer les paniers abandonnés"""
    threshold = timezone.now() - timedelta(days=7)
    
    # Paniers non connectés de plus de 7 jours
    abandoned_carts = Cart.objects.filter(
        user__isnull=True,
        updated_at__lt=threshold
    )
    
    count = abandoned_carts.count()
    abandoned_carts.delete()
    
    # Envoyer un email de rappel pour les paniers connectés
    user_carts = Cart.objects.filter(
        user__isnull=False,
        updated_at__lt=timezone.now() - timedelta(days=2),
        updated_at__gt=timezone.now() - timedelta(days=3),
        items__isnull=False
    ).distinct()
    
    for cart in user_carts:
        subject = "Votre panier vous attend!"
        context = {
            'user': cart.user,
            'items': cart.items.all()[:3],
            'cart_url': f"{settings.SITE_URL}/cart"
        }
        
        html_content = render_to_string('emails/abandoned_cart.html', context)
        text_content = strip_tags(html_content)
        
        send_mail(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [cart.user.email],
            html_message=html_content
        )
    
    return f"Cleaned {count} abandoned carts, sent {user_carts.count()} reminders"

@shared_task
def check_promo_codes_expiry():
    """Désactiver les codes promo expirés"""
    expired_codes = PromoCode.objects.filter(
        valid_until__lt=timezone.now(),
        is_active=True
    )
    
    count = expired_codes.count()
    expired_codes.update(is_active=False)
    
    return f"Deactivated {count} expired promo codes"

@shared_task
def generate_weekly_report():
    """Générer un rapport hebdomadaire"""
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=7)
    
    # Collecter les statistiques
    stats = {
        'period': f"{start_date} - {end_date}",
        'total_orders': Order.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).count(),
        'total_revenue': Order.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
        'new_customers': User.objects.filter(
            date_joined__date__range=[start_date, end_date]
        ).count(),
        'top_products': list(OrderItem.objects.filter(
            order__created_at__date__range=[start_date, end_date]
        ).values('lunch_box__name').annotate(
            total=Sum('quantity')
        ).order_by('-total')[:5]),
        'average_order_value': Order.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).aggregate(Avg('total_amount'))['total_amount__avg'] or 0
    }
    
    # Envoyer aux administrateurs
    admins = User.objects.filter(is_staff=True, is_active=True)
    
    for admin in admins:
        subject = f"Rapport hebdomadaire - {stats['period']}"
        context = {'stats': stats, 'admin': admin}
        
        html_content = render_to_string('emails/weekly_report.html', context)
        text_content = strip_tags(html_content)
        
        send_mail(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [admin.email],
            html_message=html_content
        )
    
    return f"Weekly report sent to {admins.count()} administrators"

@shared_task
def update_trending_items():
    """Mettre à jour les articles tendance"""
    # Articles tendance des 7 derniers jours
    seven_days_ago = timezone.now() - timedelta(days=7)
    
    trending = OrderItem.objects.filter(
        order__created_at__gte=seven_days_ago
    ).values('lunch_box').annotate(
        recent_sales=Sum('quantity')
    ).order_by('-recent_sales')[:10]
    
    # Marquer les articles tendance (vous pouvez ajouter un champ is_trending au modèle)
    trending_ids = [item['lunch_box'] for item in trending]
    
    # Reset all trending
    LunchBox.objects.update(is_trending=False)
    # Set new trending
    LunchBox.objects.filter(id__in=trending_ids).update(is_trending=True)
    
    return f"Updated {len(trending_ids)} trending items"

@shared_task
def send_birthday_promotions():
    """Envoyer des promotions d'anniversaire"""
    today = timezone.now().date()
    
    # Utilisateurs dont c'est l'anniversaire (nécessite un champ birthday dans User)
    birthday_users = User.objects.filter(
        birthday__month=today.month,
        birthday__day=today.day
    )
    
    for user in birthday_users:
        # Créer un code promo personnalisé
        code = f'BIRTHDAY{user.id}{today.strftime("%m%d")}'
        
        promo, created = PromoCode.objects.get_or_create(
            code=code,
            defaults={
                'description': f'Code anniversaire pour {user.get_full_name()}',
                'discount_type': 'percentage',
                'discount_value': 20,
                'minimum_order': 25,
                'user_limit': 1,
                'valid_from': timezone.now(),
                'valid_until': timezone.now() + timedelta(days=30),
                'is_active': True
            }
        )
        
        if created:
            EmailService.send_promo_code(user, promo)
    
    return f"Sent birthday promotions to {birthday_users.count()} users"