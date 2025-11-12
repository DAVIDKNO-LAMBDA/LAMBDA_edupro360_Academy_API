import os
from celery import Celery
from celery.schedules import crontab

# Establecer el módulo de configuración de Django para Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupro360.settings')

app = Celery('edupro360')

# Usar una cadena aquí significa que el worker no tiene que serializar
# el objeto de configuración a los procesos hijo.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Cargar módulos de tareas de todas las apps registradas de Django.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
