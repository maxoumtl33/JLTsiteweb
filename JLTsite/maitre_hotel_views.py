# maitre_hotel_views.py

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
from datetime import datetime, timedelta, date
from .models import *
from .models import User

def maitre_hotel_required(user):
    """Vérifier que l'utilisateur est un maître d'hôtel"""
    return user.is_authenticated and user.role == 'maitre_hotel'

@login_required
def maitre_hotel_dashboard(request):
    """Dashboard principal du maître d'hôtel"""
    
    if not maitre_hotel_required(request.user):
        messages.error(request, "Accès non autorisé.")
        return redirect('home')
    
    # Date sélectionnée (aujourd'hui par défaut)
    selected_date_str = request.GET.get('date')
    if selected_date_str:
        selected_date = datetime.datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    else:
        selected_date = timezone.now().date()
    
    # Événements du maître d'hôtel
    events = EventContract.objects.filter(
        maitre_hotel=request.user,
        event_start_time__date=selected_date
    ).order_by('event_start_time')
    
    # Statistiques
    stats = {
        'total': events.count(),
        'completed': events.filter(status='completed').count(),
        'in_progress': events.filter(status='in_progress').count(),
        'pending': events.filter(status__in=['draft', 'confirmed']).count(),
    }
    
    # Événement actuel (en cours)
    current_event = events.filter(
        status='in_progress',
        event_start_time__lte=timezone.now(),
        event_end_time__gte=timezone.now()
    ).first()
    
    # Prochains événements (7 jours)
    upcoming_events = EventContract.objects.filter(
        maitre_hotel=request.user,
        event_start_time__date__gt=selected_date,
        event_start_time__date__lte=selected_date + timedelta(days=7),
        status__in=['confirmed', 'draft']
    ).order_by('event_start_time')[:5]
    
    # Notifications non lues
    notifications_count = EventNotifications.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    context = {
        'maitre_hotel': request.user,
        'selected_date': selected_date,
        'events': events,
        'stats': stats,
        'current_event': current_event,
        'upcoming_events': upcoming_events,
        'notifications_count': notifications_count,
    }
    
    return render(request, 'JLTsite/dashboard_maitre_hotel.html', context)

@login_required
def maitre_hotel_event_detail(request, contract_id):
    """Détail d'un événement"""
    
    if not maitre_hotel_required(request.user):
        return JsonResponse({'error': 'Accès non autorisé'}, status=403)
    
    event = get_object_or_404(EventContract, id=contract_id, maitre_hotel=request.user)
    
    # Timeline de l'événement
    timeline = event.timeline.all().order_by('-timestamp')[:10]
    
    # Photos récentes
    photos = event.photos.all().order_by('-taken_at')[:6]
    
    # Personnel assigné
    staff_assignments = event.staff_assignments.all().select_related('staff_member')
    
    context = {
        'event': event,
        'timeline': timeline,
        'photos': photos,
        'staff_assignments': staff_assignments,
    }
    
    return render(request, 'JLTsite/event_detail.html', context)

@login_required
@require_http_methods(["POST"])
def start_event(request, contract_id):
    """Démarrer un événement"""
    
    if not maitre_hotel_required(request.user):
        return JsonResponse({'success': False, 'message': 'Accès non autorisé'}, status=403)
    
    event = get_object_or_404(EventContract, id=contract_id, maitre_hotel=request.user)
    
    if event.status != 'confirmed':
        return JsonResponse({
            'success': False, 
            'message': 'L\'événement doit être confirmé pour être démarré'
        })
    
    # Mettre à jour le statut
    event.status = 'in_progress'
    event.save()
    
    # Ajouter à la timeline
    EventTimeline.objects.create(
        event=event,
        timestamp=timezone.now(),
        action_type='event_start',
        description='Événement démarré par le maître d\'hôtel',
        created_by=request.user
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Événement démarré avec succès!'
    })

@login_required
@require_http_methods(["POST"])
def complete_event(request, contract_id):
    """Terminer un événement"""
    
    if not maitre_hotel_required(request.user):
        return JsonResponse({'success': False, 'message': 'Accès non autorisé'}, status=403)
    
    event = get_object_or_404(EventContract, id=contract_id, maitre_hotel=request.user)
    
    if event.status != 'in_progress':
        return JsonResponse({
            'success': False, 
            'message': 'L\'événement doit être en cours pour être terminé'
        })
    
    # Mettre à jour le statut
    event.status = 'completed'
    event.save()
    
    # Ajouter à la timeline
    EventTimeline.objects.create(
        event=event,
        timestamp=timezone.now(),
        action_type='event_end',
        description='Événement terminé par le maître d\'hôtel',
        created_by=request.user
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Événement terminé! Vous pouvez maintenant créer le rapport final.',
        'redirect_url': f'/maitre-hotel/event/{contract_id}/report/create/'
    })

@login_required
def create_event_report(request, contract_id):
    """Créer un rapport de fin d'événement"""
    
    if not maitre_hotel_required(request.user):
        messages.error(request, "Accès non autorisé.")
        return redirect('home')
    
    event = get_object_or_404(EventContract, id=contract_id, maitre_hotel=request.user)
    
    if request.method == 'POST':
        # Créer le rapport
        report = EventReport.objects.create(
            event=event,
            overall_rating=request.POST.get('overall_rating'),
            client_satisfaction=request.POST.get('client_satisfaction'),
            setup_notes=request.POST.get('setup_notes', ''),
            service_notes=request.POST.get('service_notes', ''),
            cleanup_notes=request.POST.get('cleanup_notes', ''),
            issues_encountered=request.POST.get('issues_encountered', ''),
            solutions_applied=request.POST.get('solutions_applied', ''),
            staff_performance=request.POST.get('staff_performance', ''),
            client_feedback=request.POST.get('client_feedback', ''),
            recommendations=request.POST.get('recommendations', ''),
        )
        
        # Gérer les photos uploadées
        photos = request.FILES.getlist('photos')
        for photo in photos:
            EventPhoto.objects.create(
                event=event,
                report=report,
                photo=photo,
                photo_type=request.POST.get('photo_type', 'service'),
                caption=request.POST.get('photo_caption', ''),
                taken_by=request.user
            )
        
        messages.success(request, 'Rapport créé avec succès!')
        return redirect('maitre_hotel_dashboard')
    
    # GET request - afficher le formulaire
    context = {
        'event': event,
        'timeline': event.timeline.all().order_by('timestamp'),
        'photos': event.photos.all(),
    }
    
    return render(request, 'JLTsite/create_report_maitre_hotel.html', context)

@login_required
@require_http_methods(["POST"])
def upload_event_photo(request):
    """Upload d'une photo d'événement via AJAX"""
    
    if not maitre_hotel_required(request.user):
        return JsonResponse({'success': False, 'message': 'Accès non autorisé'}, status=403)
    
    event_id = request.POST.get('event_id')
    photo_type = request.POST.get('photo_type', 'service')
    caption = request.POST.get('caption', '')
    
    if not event_id:
        return JsonResponse({'success': False, 'message': 'Event ID manquant'})
    
    event = get_object_or_404(EventContract, id=event_id, maitre_hotel=request.user)
    
    if 'photo' not in request.FILES:
        return JsonResponse({'success': False, 'message': 'Aucune photo fournie'})
    
    photo = EventPhoto.objects.create(
        event=event,
        photo=request.FILES['photo'],
        photo_type=photo_type,
        caption=caption,
        taken_by=request.user
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Photo uploadée avec succès!',
        'photo_id': photo.id,
        'photo_url': photo.photo.url
    })

@login_required
@require_http_methods(["POST"])
def add_timeline_event(request):
    """Ajouter un événement à la timeline"""
    
    if not maitre_hotel_required(request.user):
        return JsonResponse({'success': False, 'message': 'Accès non autorisé'}, status=403)
    
    try:
        data = json.loads(request.body)
        
        event_id = data.get('event_id')
        action_type = data.get('action_type')
        description = data.get('description')
        is_issue = data.get('is_issue', False)
        
        if not all([event_id, action_type, description]):
            return JsonResponse({'success': False, 'message': 'Données manquantes'})
        
        event = get_object_or_404(EventContract, id=event_id, maitre_hotel=request.user)
        
        timeline_event = EventTimeline.objects.create(
            event=event,
            timestamp=timezone.now(),
            action_type=action_type,
            description=description,
            created_by=request.user,
            is_issue=is_issue,
            is_important=is_issue
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Événement ajouté à la timeline',
            'timeline_event': {
                'id': timeline_event.id,
                'timestamp': timeline_event.timestamp.strftime('%H:%M'),
                'action_type': timeline_event.get_action_type_display(),
                'description': timeline_event.description,
                'is_issue': timeline_event.is_issue
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'JSON invalide'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def maitre_hotel_planning(request):
    """Planning du maître d'hôtel"""
    
    if not maitre_hotel_required(request.user):
        messages.error(request, "Accès non autorisé.")
        return redirect('home')
    
    # Date de début (début de semaine)
    start_date = timezone.now().date()
    if request.GET.get('week'):
        try:
            start_date = datetime.strptime(request.GET.get('week'), '%Y-%m-%d').date()
        except:
            pass
    
    # Calculer les 7 jours suivants
    dates = [start_date + timedelta(days=i) for i in range(7)]
    
    # Événements de la semaine
    events_by_date = {}
    for day in dates:
        events_by_date[day] = EventContract.objects.filter(
            maitre_hotel=request.user,
            event_start_time__date=day
        ).order_by('event_start_time')
    
    context = {
        'start_date': start_date,
        'dates': dates,
        'events_by_date': events_by_date,
    }
    
    return render(request, 'JLTsite/planning_maitre_hotel.html', context)

@login_required
def maitre_hotel_notifications(request):
    """Notifications du maître d'hôtel"""
    
    if not maitre_hotel_required(request.user):
        messages.error(request, "Accès non autorisé.")
        return redirect('home')
    
    notifications = EventNotifications.objects.filter(
        recipient=request.user
    ).order_by('-created_at')
    
    # Marquer comme lues
    notifications.filter(is_read=False).update(is_read=True)
    
    context = {
        'notifications': notifications[:50],  # Limiter à 50
    }
    
    return render(request, 'JLTsite/notifications_maitre_hotel.html', context)

@login_required
def maitre_hotel_profile(request):
    """Profil du maître d'hôtel"""
    
    if not maitre_hotel_required(request.user):
        messages.error(request, "Accès non autorisé.")
        return redirect('home')
    
    if request.method == 'POST':
        # Mettre à jour le profil
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', user.phone)
        user.save()
        
        messages.success(request, 'Profil mis à jour avec succès!')
        return redirect('maitre_hotel_profile')
    
    # Statistiques personnelles
    total_events = EventContract.objects.filter(maitre_hotel=request.user).count()
    completed_events = EventContract.objects.filter(maitre_hotel=request.user, status='completed').count()
    
    context = {
        'total_events': total_events,
        'completed_events': completed_events,
    }
    
    return render(request, 'JLTsite/profile_maitre_hotel.html', context)


@login_required
def maitre_hotel_reports(request):
    """Liste des rapports d'événements du maître d'hôtel"""
    
    if not maitre_hotel_required(request.user):
        messages.error(request, "Accès non autorisé.")
        return redirect('home')
    
    # Filtres
    status_filter = request.GET.get('status', 'all')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    search_query = request.GET.get('search', '')
    
    # Base queryset
    reports = EventReport.objects.filter(
        event__maitre_hotel=request.user
    ).select_related('event', 'event__order').order_by('-created_at')
    
    # Appliquer les filtres
    if status_filter != 'all':
        reports = reports.filter(status=status_filter)
    
    if date_from:
        try:
            date_from_parsed = datetime.strptime(date_from, '%Y-%m-%d').date()
            reports = reports.filter(event__event_start_time__date__gte=date_from_parsed)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_parsed = datetime.strptime(date_to, '%Y-%m-%d').date()
            reports = reports.filter(event__event_start_time__date__lte=date_to_parsed)
        except ValueError:
            pass
    
    # Recherche textuelle
    if search_query:
        reports = reports.filter(
            Q(event__event_name__icontains=search_query) |
            Q(event__order__first_name__icontains=search_query) |
            Q(event__order__last_name__icontains=search_query) |
            Q(event__order__company__icontains=search_query) |
            Q(report_number__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(reports, 15)
    page_number = request.GET.get('page')
    reports_page = paginator.get_page(page_number)
    
    # Statistiques
    all_reports = EventReport.objects.filter(event__maitre_hotel=request.user)
    stats = {
        'total': all_reports.count(),
        'draft': all_reports.filter(status='draft').count(),
        'submitted': all_reports.filter(status='submitted').count(),
        'approved': all_reports.filter(status='approved').count(),
    }
    
    # Événements sans rapport
    completed_events = EventContract.objects.filter(
        maitre_hotel=request.user,
        status='completed'
    )
    events_with_reports = all_reports.values_list('event_id', flat=True)
    events_without_report = completed_events.exclude(
        id__in=events_with_reports
    ).count()
    
    # Statistiques des notes (moyenne)
    from django.db.models import Avg
    rating_stats = all_reports.filter(overall_rating__isnull=False).aggregate(
        avg_overall=Avg('overall_rating'),
        avg_satisfaction=Avg('client_satisfaction')
    )
    
    # Rapports récents (30 derniers jours)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_reports_count = all_reports.filter(created_at__gte=thirty_days_ago).count()
    
    # Rapports par mois (6 derniers mois)
    from django.db.models import Count
    from django.db.models.functions import TruncMonth
    
    monthly_stats = all_reports.filter(
        created_at__gte=timezone.now() - timedelta(days=180)
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    context = {
        'reports': reports_page,
        'stats': stats,
        'events_without_report': events_without_report,
        'rating_stats': rating_stats,
        'recent_reports_count': recent_reports_count,
        'monthly_stats': monthly_stats,
        
        # Filtres actuels pour les repopuler
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
        
        # Choix pour les selects
        'status_choices': EventReport.STATUS_CHOICES,
    }
    
    return render(request, 'JLTsite/report_maitre_hotel.html', context)