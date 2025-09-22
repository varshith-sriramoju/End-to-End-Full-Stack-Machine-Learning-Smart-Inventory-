import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'smartinventory.settings')

app = Celery('smartinventory')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat Schedule
from celery.schedules import crontab

app.conf.beat_schedule = {
    'model-health-check': {
        'task': 'apps.forecasting.tasks.model_health_check',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    'data-quality-check': {
        'task': 'apps.data_management.tasks.data_quality_check',
        'schedule': crontab(hour=1, minute=0),  # Daily at 1 AM
    },
}

app.conf.task_routes = {
    'apps.forecasting.tasks.train_model': {'queue': 'ml_tasks'},
    'apps.forecasting.tasks.batch_predict': {'queue': 'ml_tasks'},
    'apps.data_management.tasks.process_upload': {'queue': 'data_tasks'},
}