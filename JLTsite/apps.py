# apps.py - Dans votre app JLTsite
from django.apps import AppConfig

class JLTsiteConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'JLTsite'
    
    def ready(self):
        # Importer les signaux pour qu'ils soient enregistrés
        import JLTsite.signals