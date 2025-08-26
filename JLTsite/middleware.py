# Créer ce fichier dans JLTsite/middleware.py

from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class ChecklistRoleMiddleware:
    """
    Middleware pour gérer les redirections et accès selon les rôles
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # URLs qui nécessitent le rôle checklist_manager
        checklist_urls = [
            '/checklist-dashboard/',
            '/checklist/',
        ]
        
        # URLs admin
        admin_urls = [
            '/admin-dashboard/',
            '/admin/',
        ]
        
        # Vérifier si l'utilisateur est authentifié
        if request.user.is_authenticated:
            current_path = request.path
            
            # Si c'est un responsable checklist qui essaie d'accéder à l'admin
            if request.user.role == 'checklist_manager':
                if any(current_path.startswith(url) for url in admin_urls):
                    messages.warning(request, "Vous n'avez pas accès à l'administration. Redirection vers votre dashboard.")
                    return redirect('checklist_dashboard')
            
            # Si c'est un client qui essaie d'accéder aux zones restreintes
            elif request.user.role == 'customer':
                if any(current_path.startswith(url) for url in checklist_urls + admin_urls):
                    messages.error(request, "Accès refusé. Cette zone est réservée au personnel.")
                    return redirect('customer_dashboard')
            
            # Si l'utilisateur essaie d'accéder au dashboard checklist sans les droits
            if any(current_path.startswith(url) for url in checklist_urls):
                if request.user.role not in ['checklist_manager', 'admin', 'staff']:
                    messages.error(request, "Accès refusé au dashboard checklist.")
                    return redirect('home')
        
        response = self.get_response(request)
        return response

class AutoRedirectMiddleware:
    """
    Middleware pour rediriger automatiquement vers le bon dashboard après connexion
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Si l'utilisateur vient de se connecter et est sur la page d'accueil
        if request.user.is_authenticated and request.path == '/':
            # Rediriger selon le rôle
            if request.user.role == 'checklist_manager':
                return redirect('checklist_dashboard')
            elif request.user.role in ['admin', 'staff']:
                return redirect('admin_dashboard')
            elif request.user.role == 'customer':
                # Les clients restent sur la page d'accueil ou vont au shop
                pass
        
        response = self.get_response(request)
        return response