# checklist_views.py - Vues pour la gestion des checklists

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, Sum, Prefetch
from django.utils import timezone
from django.contrib import messages
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import (
    Order, OrderChecklist, ChecklistItem, InventoryItem,
    ChecklistTemplate, ChecklistTemplateItem, ChecklistNotification, User
)

# ========================================
# DECORATEURS
# ========================================

def checklist_manager_required(user):
    """Vérifier si l'utilisateur est responsable checklist ou admin"""
    return user.is_authenticated and user.role in ['admin', 'staff', 'checklist_manager']

def admin_required(user):
    """Vérifier si l'utilisateur est admin"""
    return user.is_authenticated and user.role in ['admin', 'staff']

# ========================================
# VUES ADMIN - CRÉATION/GESTION DES CHECKLISTS
# ========================================

@user_passes_test(admin_required)
def admin_create_checklist(request, order_number):
    """Créer une checklist pour une commande"""
    order = get_object_or_404(Order, order_number=order_number)
    
    # Vérifier si une checklist existe déjà
    if hasattr(order, 'checklist'):
        messages.warning(request, 'Une checklist existe déjà pour cette commande.')
        return redirect('admin_edit_checklist', order_number=order_number)
    
    # Récupérer les articles d'inventaire
    inventory_items = InventoryItem.objects.filter(is_active=True).order_by('category', 'name')
    
    # Récupérer les modèles de checklist
    templates = ChecklistTemplate.objects.filter(is_active=True)
    
    # Récupérer les responsables checklist
    checklist_managers = User.objects.filter(
        Q(role='checklist_manager') | Q(role='admin') | Q(role='staff')
    ).order_by('last_name', 'first_name')
    
    if request.method == 'POST':
        # Créer la checklist
        checklist = OrderChecklist.objects.create(
            order=order,
            title=request.POST.get('title', f'Checklist {order.order_number}'),
            assigned_to_id=request.POST.get('assigned_to'),
            priority=int(request.POST.get('priority', 0)),
            notes=request.POST.get('notes', ''),
            created_by=request.user,
            status='pending'
        )
        
        # Si un modèle est sélectionné
        template_id = request.POST.get('template_id')
        if template_id:
            template = ChecklistTemplate.objects.get(id=template_id)
            for template_item in template.checklisttemplateitem_set.all():
                ChecklistItem.objects.create(
                    checklist=checklist,
                    inventory_item=template_item.inventory_item,
                    quantity_needed=template_item.default_quantity,
                    notes=template_item.notes,
                    order=template_item.order
                )
        else:
            # Ajouter les articles sélectionnés manuellement
            selected_items = request.POST.getlist('inventory_items')
            for idx, item_id in enumerate(selected_items):
                if item_id:
                    quantity = request.POST.get(f'quantity_{item_id}', 1)
                    ChecklistItem.objects.create(
                        checklist=checklist,
                        inventory_item_id=item_id,
                        quantity_needed=int(quantity),
                        order=idx
                    )
        
        # Calculer la progression initiale
        checklist.update_progress()
        
        messages.success(request, 'Checklist créée avec succès!')
        
        # Envoyer une notification au responsable
        if checklist.assigned_to:
            send_checklist_notification_email(checklist)
        
        return redirect('admin_edit_checklist', order_number=order_number)
    
    context = {
        'order': order,
        'inventory_items': inventory_items,
        'templates': templates,
        'checklist_managers': checklist_managers,
    }
    
    return render(request, 'JLTsite/admin_create_checklist.html', context)

@user_passes_test(admin_required)
def admin_edit_checklist(request, order_number):
    """Modifier une checklist existante"""
    order = get_object_or_404(Order, order_number=order_number)
    checklist = get_object_or_404(OrderChecklist, order=order)
    
    # Récupérer les articles d'inventaire pour ajouter de nouveaux items
    inventory_items = InventoryItem.objects.filter(is_active=True).order_by('category', 'name')
    
    # Récupérer les responsables
    checklist_managers = User.objects.filter(
        Q(role='checklist_manager') | Q(role='admin') | Q(role='staff')
    ).order_by('last_name', 'first_name')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_checklist':
            # Mettre à jour les informations de la checklist
            checklist.title = request.POST.get('title', checklist.title)
            checklist.assigned_to_id = request.POST.get('assigned_to')
            checklist.priority = int(request.POST.get('priority', 0))
            checklist.notes = request.POST.get('notes', '')
            checklist.save()
            
            messages.success(request, 'Checklist mise à jour!')
            
        elif action == 'add_items':
            # Ajouter de nouveaux items
            selected_items = request.POST.getlist('new_items')
            for item_id in selected_items:
                if item_id:
                    quantity = request.POST.get(f'new_quantity_{item_id}', 1)
                    ChecklistItem.objects.create(
                        checklist=checklist,
                        inventory_item_id=item_id,
                        quantity_needed=int(quantity)
                    )
            
            checklist.update_progress()
            messages.success(request, 'Items ajoutés à la checklist!')
            
        elif action == 'delete_item':
            # Supprimer un item
            item_id = request.POST.get('item_id')
            ChecklistItem.objects.filter(id=item_id, checklist=checklist).delete()
            checklist.update_progress()
            messages.success(request, 'Item supprimé!')
            
        return redirect('admin_edit_checklist', order_number=order_number)
    
    context = {
        'order': order,
        'checklist': checklist,
        'inventory_items': inventory_items,
        'checklist_managers': checklist_managers,
    }
    
    return render(request, 'JLTsite/admin_edit_checklist.html', context)

# ========================================
# DASHBOARD RESPONSABLE CHECKLIST
# ========================================

@login_required
@user_passes_test(checklist_manager_required)
def checklist_dashboard(request):
    """Dashboard principal pour le responsable checklist"""
    
    # Récupérer les checklists assignées à l'utilisateur
    if request.user.role == 'admin':
        # Les admins voient toutes les checklists
        checklists = OrderChecklist.objects.all()
    else:
        # Les responsables voient seulement leurs checklists assignées
        checklists = OrderChecklist.objects.filter(assigned_to=request.user)
    
    # Filtrer par statut
    status = request.GET.get('status')
    if status:
        checklists = checklists.filter(status=status)
    
    # Filtrer par date
    date_filter = request.GET.get('date')
    if date_filter == 'today':
        checklists = checklists.filter(order__delivery_date=timezone.now().date())
    elif date_filter == 'tomorrow':
        tomorrow = timezone.now().date() + timedelta(days=1)
        checklists = checklists.filter(order__delivery_date=tomorrow)
    elif date_filter == 'week':
        week_end = timezone.now().date() + timedelta(days=7)
        checklists = checklists.filter(order__delivery_date__lte=week_end)
    
    # Ordonner par priorité et date de livraison
    checklists = checklists.select_related('order', 'assigned_to').prefetch_related('items')
    checklists = checklists.order_by('-priority', 'order__delivery_date', 'order__delivery_time')
    
    # Statistiques
    stats = {
        'total': checklists.count(),
        'pending': checklists.filter(status='pending').count(),
        'in_progress': checklists.filter(status='in_progress').count(),
        'completed': checklists.filter(status='completed').count(),
        'today': checklists.filter(order__delivery_date=timezone.now().date()).count(),
        'urgent': checklists.filter(priority=1).count(),
    }
    
    # Notifications non lues
    if request.user.role == 'admin':
        notifications = ChecklistNotification.objects.filter(is_read=False).order_by('-created_at')[:10]
    else:
        notifications = ChecklistNotification.objects.filter(
            checklist__assigned_to=request.user,
            is_read=False
        ).order_by('-created_at')[:10]
    
    context = {
        'checklists': checklists,
        'stats': stats,
        'notifications': notifications,
        'current_status': status,
        'current_date': date_filter,
    }
    
    return render(request, 'JLTsite/checklist_dashboard.html', context)

@login_required
@user_passes_test(checklist_manager_required)
def checklist_detail(request, checklist_id):
    """Vue détaillée d'une checklist pour validation (optimisée tablette)"""
    
    if request.user.role == 'admin':
        checklist = get_object_or_404(OrderChecklist, id=checklist_id)
    else:
        checklist = get_object_or_404(OrderChecklist, id=checklist_id, assigned_to=request.user)
    
    # Grouper les items par catégorie
    items_by_category = {}
    for item in checklist.items.all().select_related('inventory_item'):
        category = item.inventory_item.get_category_display()
        if category not in items_by_category:
            items_by_category[category] = []
        items_by_category[category].append(item)
    
    # Commencer la checklist si elle est en attente
    if checklist.status == 'pending' and request.method == 'POST':
        if request.POST.get('action') == 'start':
            checklist.status = 'in_progress'
            checklist.started_at = timezone.now()
            checklist.save()
            messages.info(request, 'Checklist démarrée!')
    
    context = {
        'checklist': checklist,
        'items_by_category': items_by_category,
        'order': checklist.order,
    }
    
    return render(request, 'JLTsite/checklist_detail.html', context)

# ========================================
# VUES AJAX POUR VALIDATION RAPIDE
# ========================================

@login_required
@user_passes_test(checklist_manager_required)
@require_POST
def validate_checklist_item(request):
    """Valider/dévalider un item de checklist (AJAX)"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        action = data.get('action')  # 'check' ou 'uncheck'
        
        item = get_object_or_404(ChecklistItem, id=item_id)
        
        # Vérifier les permissions
        if request.user.role != 'admin' and item.checklist.assigned_to != request.user:
            return JsonResponse({
                'success': False,
                'message': 'Vous n\'avez pas la permission de modifier cette checklist'
            }, status=403)
        
        if action == 'check':
            quantity = data.get('quantity', item.quantity_needed)
            item.validate_item(request.user, quantity)
            message = 'Item validé!'
        else:
            item.unvalidate_item()
            message = 'Validation annulée!'
        
        # Récupérer les stats mises à jour
        checklist = item.checklist
        
        return JsonResponse({
            'success': True,
            'message': message,
            'progress': checklist.progress_percentage,
            'completed_items': checklist.completed_items,
            'total_items': checklist.total_items,
            'checklist_status': checklist.status,
            'item_checked': item.is_checked
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
@user_passes_test(checklist_manager_required)
@require_POST
def report_checklist_issue(request):
    """Signaler un problème sur un item (AJAX)"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        description = data.get('description')
        
        item = get_object_or_404(ChecklistItem, id=item_id)
        
        # Vérifier les permissions
        if request.user.role != 'admin' and item.checklist.assigned_to != request.user:
            return JsonResponse({
                'success': False,
                'message': 'Permission refusée'
            }, status=403)
        
        item.report_issue(description, request.user)
        
        return JsonResponse({
            'success': True,
            'message': 'Problème signalé avec succès'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@login_required
@user_passes_test(checklist_manager_required)
@require_POST
def complete_checklist(request, checklist_id):
    """Marquer une checklist comme complétée"""
    
    if request.user.role == 'admin':
        checklist = get_object_or_404(OrderChecklist, id=checklist_id)
    else:
        checklist = get_object_or_404(OrderChecklist, id=checklist_id, assigned_to=request.user)
    
    # Vérifier que tous les items sont validés
    unchecked_items = checklist.items.filter(is_checked=False).count()
    
    if unchecked_items > 0:
        messages.warning(request, f'Il reste {unchecked_items} item(s) non validé(s).')
        return redirect('checklist_detail', checklist_id=checklist_id)
    
    checklist.status = 'completed'
    checklist.completed_at = timezone.now()
    checklist.save()
    
    # Créer une notification
    ChecklistNotification.objects.create(
        checklist=checklist,
        type='completed',
        message=f'Checklist complétée par {request.user.get_full_name()}',
        created_by=request.user
    )
    
    messages.success(request, 'Checklist complétée avec succès!')
    return redirect('checklist_dashboard')

# ========================================
# UTILITAIRES
# ========================================

def send_checklist_notification_email(checklist):
    """Envoyer un email de notification au responsable checklist"""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    
    if not checklist.assigned_to or not checklist.assigned_to.email:
        return
    
    subject = f'Nouvelle checklist assignée - Commande {checklist.order.order_number}'
    
    context = {
        'checklist': checklist,
        'order': checklist.order,
        'url': f"{settings.SITE_URL}/checklist/{checklist.id}/"
    }
    
    html_message = render_to_string('JLTsite/checklist_notification_email.html', context)
    
    send_mail(
        subject=subject,
        message=f'Une nouvelle checklist vous a été assignée pour la commande {checklist.order.order_number}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[checklist.assigned_to.email],
        html_message=html_message,
        fail_silently=False,
    )

@login_required
@user_passes_test(checklist_manager_required)
def mark_notification_read(request, notification_id):
    """Marquer une notification comme lue"""
    notification = get_object_or_404(ChecklistNotification, id=notification_id)
    notification.is_read = True
    notification.save()
    
    return JsonResponse({'success': True})