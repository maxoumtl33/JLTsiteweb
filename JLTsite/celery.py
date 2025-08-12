# celery.py - Configuration Celery
from celery import Celery
from celery.schedules import crontab
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project.settings')

app = Celery('your_project')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Configuration des tâches périodiques
app.conf.beat_schedule = {
    'process-daily-analytics': {
        'task': 'your_app.tasks.process_daily_analytics',
        'schedule': crontab(hour=0, minute=0),  # Minuit chaque jour
    },
    'send-order-reminders': {
        'task': 'your_app.tasks.send_order_reminders',
        'schedule': crontab(hour=18, minute=0),  # 18h chaque jour
    },
    'cleanup-abandoned-carts': {
        'task': 'your_app.tasks.cleanup_abandoned_carts',
        'schedule': crontab(hour=2, minute=0),  # 2h du matin chaque jour
    },
    'check-promo-codes-expiry': {
        'task': 'your_app.tasks.check_promo_codes_expiry',
        'schedule': crontab(hour=1, minute=0),  # 1h du matin chaque jour
    },
    'generate-weekly-report': {
        'task': 'your_app.tasks.generate_weekly_report',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),  # Lundi 9h
    },
    'update-trending-items': {
        'task': 'your_app.tasks.update_trending_items',
        'schedule': crontab(hour=3, minute=0),  # 3h du matin chaque jour
    },
    'send-birthday-promotions': {
        'task': 'your_app.tasks.send_birthday_promotions',
        'schedule': crontab(hour=10, minute=0),  # 10h chaque jour
    },
}