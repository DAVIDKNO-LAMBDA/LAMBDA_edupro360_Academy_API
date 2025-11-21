#!/usr/bin/env python
"""
Monitor en tiempo real para tareas de Celery - EduPro 360
Monitorea las colas, workers y ejecución de tareas
"""

import os
import django
import time
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupro360.settings')
django.setup()

from celery import Celery
from django.conf import settings

def monitorear_celery():
    """Monitorear el estado de Celery en tiempo real"""
    print("📊 MONITOR CELERY EN TIEMPO REAL")
    print("=" * 60)
    print("Presiona Ctrl+C para salir")
    print("=" * 60)
    
    # Configurar Celery app
    app = Celery('edupro360')
    app.config_from_object('django.conf:settings', namespace='CELERY')
    
    try:
        while True:
            print(f"\n🕐 {datetime.now().strftime('%H:%M:%S')} - Estado del Sistema")
            print("-" * 40)
            
            # Verificar workers activos
            try:
                inspect = app.control.inspect()
                
                # Workers activos
                active_workers = inspect.active()
                if active_workers:
                    print(f"👷 Workers activos: {len(active_workers)}")
                    for worker, tasks in active_workers.items():
                        print(f"  • {worker}: {len(tasks)} tareas ejecutándose")
                else:
                    print("⚠️  No hay workers activos")
                
                # Tareas programadas
                scheduled = inspect.scheduled()
                if scheduled:
                    total_scheduled = sum(len(tasks) for tasks in scheduled.values())
                    print(f"📅 Tareas programadas: {total_scheduled}")
                
                # Tareas en cola
                reserved = inspect.reserved()
                if reserved:
                    total_reserved = sum(len(tasks) for tasks in reserved.values())
                    print(f"📋 Tareas en cola: {total_reserved}")
                
            except Exception as e:
                print(f"❌ Error conectando con Celery: {str(e)}")
            
            # Esperar 10 segundos antes de la siguiente verificación
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitor detenido por el usuario")

if __name__ == "__main__":
    monitorear_celery()