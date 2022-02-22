import os
# from django.conf import settings

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TraceBase.settings')
# settings.configure()

# app = Celery('TraceBase', include=['DataRepo.tasks'])  # Sort of worked, but always PENDING
# app = Celery()  # Works in shell after getting settings.py right
# app = Celery("TraceBase")  # No different from above
# app = Celery('TraceBase', backend='amqp', broker='amqp://tracebase:tracebase@localhost:5672/tracebase', include=['DataRepo.tasks'])
app = Celery('TraceBase', backend='rpc://localhost/tracebase', broker='amqp://tracebase:tracebase@localhost:5672/tracebase', include=['DataRepo.tasks'])

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')