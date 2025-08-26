# signals.py - À créer dans votre app JLTsite
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
import uuid, datetime

from .models import Order, Delivery, DeliveryNotification, User

@receiver(pre_save, sender=Order)
def track_order_status_change(sender, instance, **kwargs):
    """Détecte quand une commande passe au statut confirmé"""
    if instance.pk:  # Si l'ordre existe déjà
        try:
            old_order = Order.objects.get(pk=instance.pk)
            # Stocker l'ancien statut dans une variable temporaire
            instance._old_status = old_order.status
        except Order.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None

@receiver(post_save, sender=Order)
def create_delivery_on_order_confirmation(sender, instance, created, **kwargs):
    """
    Crée automatiquement une livraison quand une commande est confirmée
    """
    # Vérifier si le statut vient de passer à 'confirmed'
    old_status = getattr(instance, '_old_status', None)
    
    if instance.status == 'confirmed' and old_status != 'confirmed':
        # Vérifier qu'il n'y a pas déjà une livraison pour cette commande
        existing_delivery = Delivery.objects.filter(
            order=instance,
            delivery_type='delivery'
        ).first()
        
        if not existing_delivery:
            # Créer automatiquement la livraison
            delivery = create_automatic_delivery(instance)
            
            # Envoyer une notification au responsable livraison
            notify_delivery_managers(delivery)
            
            # Logger la création
            print(f"Livraison {delivery.delivery_number} créée automatiquement pour la commande {instance.order_number}")

def create_automatic_delivery(order):
    """
    Crée une livraison à partir d'une commande confirmée
    """
    from .delivery_views import get_order_items_description, geocode_delivery_address
    
    # Créer la livraison
    delivery = Delivery.objects.create(
        order=order,
        delivery_type='delivery',
        customer_name=f"{order.first_name} {order.last_name}",
        customer_phone=order.phone,
        customer_email=order.email,
        company=order.company or '',
        delivery_address=order.delivery_address,
        delivery_postal_code=order.delivery_postal_code,
        delivery_city=order.delivery_city,
        scheduled_date=order.delivery_date,
        scheduled_time_start=order.delivery_time,
        scheduled_time_end=calculate_end_time(order.delivery_time),
        delivery_instructions=order.delivery_notes,
        items_description=get_order_items_description(order),
        total_packages=estimate_packages_count(order),
        priority=determine_priority(order),
        has_checklist=hasattr(order, 'checklist'),
        checklist_completed=order.checklist.status == 'completed' if hasattr(order, 'checklist') else False,
        created_by=None  # Système automatique
    )
    
    # Géocoder l'adresse
    geocode_delivery_address(delivery)
    
    return delivery

def calculate_end_time(start_time):
    """
    Calcule l'heure de fin estimée (30 minutes après le début)
    """
    from datetime import datetime, timedelta
    
    # Convertir l'heure en datetime pour le calcul
    dummy_date = datetime(2000, 1, 1)
    start_datetime = datetime.combine(dummy_date, start_time)
    end_datetime = start_datetime + timedelta(minutes=30)
    
    return end_datetime.time()

def estimate_packages_count(order):
    """
    Estime le nombre de colis basé sur les items de la commande
    """
    total_items = sum(item.quantity for item in order.items.all())
    
    # Logique d'estimation (à adapter selon vos besoins)
    if total_items <= 5:
        return 1
    elif total_items <= 15:
        return 2
    elif total_items <= 30:
        return 3
    else:
        return (total_items // 10) + 1

def determine_priority(order):
    """
    Détermine la priorité de la livraison
    """
    from datetime import datetime, timedelta
    
    # Si la livraison est pour aujourd'hui ou demain = priorité haute
    days_until_delivery = (order.delivery_date - timezone.now().date()).days
    
    if days_until_delivery <= 0:
        return 'urgent'
    elif days_until_delivery == 1:
        return 'high'
    elif order.total > 500:  # Commandes importantes
        return 'high'
    else:
        return 'normal'

def notify_delivery_managers(delivery):
    """
    Notifie les responsables livraison de la nouvelle livraison
    """
    # Récupérer tous les responsables livraison
    managers = User.objects.filter(
        role__in=['delivery_manager', 'admin'],
        is_active=True
    )
    
    for manager in managers:
        DeliveryNotification.objects.create(
            type='new_delivery',
            recipient_type='manager',
            recipient=manager,
            delivery=delivery,
            title='Nouvelle livraison à planifier',
            message=f'La commande {delivery.order.order_number} a été confirmée. '
                   f'Livraison {delivery.delivery_number} créée automatiquement '
                   f'pour le {delivery.scheduled_date.strftime("%d/%m/%Y")}',
            is_urgent=delivery.priority in ['urgent', 'high']
        )

# ========================================
# SIGNAL POUR RÉCUPÉRATION AUTOMATIQUE
# ========================================

@receiver(post_save, sender=Delivery)
def create_pickup_reminder(sender, instance, created, **kwargs):
    """
    Crée un rappel pour planifier une récupération après une livraison
    """
    if created and instance.delivery_type == 'delivery':
        # Si c'est une commande qui nécessite une récupération
        # (ex: location de matériel, événement avec retour)
        if should_create_pickup(instance):
            # Créer une notification pour planifier la récupération
            schedule_pickup_notification(instance)

def should_create_pickup(delivery):
    """
    Détermine si une récupération doit être planifiée
    """
    # Logique pour déterminer si une récupération est nécessaire
    # Par exemple, vérifier si la commande contient des items en location
    
    # Pour l'instant, on peut vérifier les notes ou un champ spécifique
    keywords = ['location', 'récupération', 'retour', 'rental']
    
    if delivery.order.delivery_notes:
        notes_lower = delivery.order.delivery_notes.lower()
        return any(keyword in notes_lower for keyword in keywords)
    
    return False

def schedule_pickup_notification(delivery):
    """
    Programme une notification pour créer une récupération
    """
    # Notification pour le lendemain de la livraison
    scheduled_date = delivery.scheduled_date + timedelta(days=1)
    
    managers = User.objects.filter(
        role__in=['delivery_manager', 'admin'],
        is_active=True
    ).first()
    
    if managers:
        DeliveryNotification.objects.create(
            type='reminder',
            recipient_type='manager',
            recipient=managers,
            delivery=delivery,
            title='Récupération à planifier',
            message=f'Pensez à planifier la récupération pour la livraison {delivery.delivery_number}',
            is_urgent=False,
            scheduled_for=timezone.make_aware(
                datetime.combine(scheduled_date, datetime.min.time())
            )
        )