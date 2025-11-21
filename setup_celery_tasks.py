#!/usr/bin/env python
"""
Script para configurar las tareas programadas de Celery Beat
HU-11: Recordatorios Automáticos
HU-12: Consolidado Mensual

Ejecutar: python setup_celery_tasks.py
"""

import os
import sys
import django
from datetime import datetime
from django.conf import settings

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupro360.settings')
django.setup()

def setup_celery_beat_tasks():
    """Configura las tareas programadas de Celery Beat en la base de datos."""
    try:
        from django_celery_beat.models import PeriodicTask, CrontabSchedule
        import json
        
        print("🔧 Configurando tareas programadas de Celery Beat...")
        
        # =====================================================================
        # HU-11.1: Recordatorio de tareas próximas a vencer (diario 9:00 AM)
        # =====================================================================
        schedule_9am, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='9',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        task_recordatorio_proximas, created = PeriodicTask.objects.get_or_create(
            name='Recordatorio Tareas Próximas',
            defaults={
                'crontab': schedule_9am,
                'task': 'Academico.tasks.enviar_recordatorio_tareas_proximas',
                'enabled': True,
                'description': 'HU-11.1: Envía recordatorios de tareas que vencen en 24h'
            }
        )
        
        if created:
            print("✅ Tarea creada: Recordatorio Tareas Próximas (9:00 AM diario)")
        else:
            print("ℹ️  Tarea ya existe: Recordatorio Tareas Próximas")
        
        # =====================================================================
        # HU-11.2: Recordatorio de tareas vencidas (diario 10:00 AM)
        # =====================================================================
        schedule_10am, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='10',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        task_recordatorio_vencidas, created = PeriodicTask.objects.get_or_create(
            name='Recordatorio Tareas Vencidas',
            defaults={
                'crontab': schedule_10am,
                'task': 'Academico.tasks.enviar_recordatorio_tareas_vencidas',
                'enabled': True,
                'description': 'HU-11.2: Envía recordatorios de tareas vencidas no entregadas'
            }
        )
        
        if created:
            print("✅ Tarea creada: Recordatorio Tareas Vencidas (10:00 AM diario)")
        else:
            print("ℹ️  Tarea ya existe: Recordatorio Tareas Vencidas")
        
        # =====================================================================
        # HU-11.1a: Recordatorio tareas 3 días antes (diario 8:00 AM)
        # =====================================================================
        schedule_8am, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='8',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        task_recordatorio_3_dias, created = PeriodicTask.objects.get_or_create(
            name='Recordatorio Tareas 3 Días Antes',
            defaults={
                'crontab': schedule_8am,
                'task': 'Academico.tasks.enviar_recordatorio_tareas_3_dias',
                'enabled': True,
                'description': 'HU-11.1a: Envía recordatorios de tareas que vencen en 3 días'
            }
        )
        
        if created:
            print("✅ Tarea creada: Recordatorio Tareas 3 Días Antes (8:00 AM diario)")
        else:
            print("ℹ️  Tarea ya existe: Recordatorio Tareas 3 Días Antes")
        
        # =====================================================================
        # HU-11.3: Recordatorio calificaciones pendientes (diario 7:30 AM)
        # =====================================================================
        schedule_730am, created = CrontabSchedule.objects.get_or_create(
            minute='30',
            hour='7',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
        )
        
        task_calificaciones_pendientes, created = PeriodicTask.objects.get_or_create(
            name='Recordatorio Calificaciones Pendientes',
            defaults={
                'crontab': schedule_730am,
                'task': 'Academico.tasks.recordar_calificaciones_pendientes',
                'enabled': True,
                'description': 'HU-11.3: Recuerda a docentes sobre calificaciones pendientes'
            }
        )
        
        if created:
            print("✅ Tarea creada: Recordatorio Calificaciones Pendientes (8:00 AM diario)")
        else:
            print("ℹ️  Tarea ya existe: Recordatorio Calificaciones Pendientes")
        
        # =====================================================================
        # HU-12.1: Consolidado mensual (día 5 de cada mes a las 6:00 AM)
        # =====================================================================
        schedule_monthly, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='6',
            day_of_week='*',
            day_of_month='5',
            month_of_year='*',
        )
        
        task_consolidado_mensual, created = PeriodicTask.objects.get_or_create(
            name='Consolidado Mensual',
            defaults={
                'crontab': schedule_monthly,
                'task': 'Academico.tasks.generar_consolidado_mensual',
                'enabled': True,
                'description': 'HU-12.1: Genera consolidado mensual automático en PDF y Excel'
            }
        )
        
        if created:
            print("✅ Tarea creada: Consolidado Mensual (día 5 de cada mes, 6:00 AM)")
        else:
            print("ℹ️  Tarea ya existe: Consolidado Mensual")
        
        # =====================================================================
        # Tareas adicionales de mantenimiento
        # =====================================================================
        
        # Estadísticas semanales (lunes 7:00 AM)
        schedule_weekly, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='7',
            day_of_week='1',  # Lunes
            day_of_month='*',
            month_of_year='*',
        )
        
        task_stats_semanales, created = PeriodicTask.objects.get_or_create(
            name='Estadísticas Semanales',
            defaults={
                'crontab': schedule_weekly,
                'task': 'Academico.tasks.generar_estadisticas_semanales',
                'enabled': True,
                'description': 'Genera estadísticas semanales para el dashboard'
            }
        )
        
        if created:
            print("✅ Tarea creada: Estadísticas Semanales (lunes 7:00 AM)")
        else:
            print("ℹ️  Tarea ya existe: Estadísticas Semanales")
        
        # Limpieza de archivos antiguos (primer domingo de cada mes, 3:00 AM)
        schedule_cleanup, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='3',
            day_of_week='0',  # Domingo
            day_of_month='1-7',  # Primera semana
            month_of_year='*',
        )
        
        task_cleanup, created = PeriodicTask.objects.get_or_create(
            name='Limpieza Archivos Antiguos',
            defaults={
                'crontab': schedule_cleanup,
                'task': 'Academico.tasks.limpiar_archivos_antiguos',
                'enabled': True,
                'description': 'Elimina archivos de reportes mayores a 6 meses'
            }
        )
        
        if created:
            print("✅ Tarea creada: Limpieza Archivos Antiguos (primer domingo del mes, 3:00 AM)")
        else:
            print("ℹ️  Tarea ya existe: Limpieza Archivos Antiguos")
        
        print("\n" + "="*60)
        print("📋 RESUMEN DE TAREAS PROGRAMADAS")
        print("="*60)
        
        all_tasks = PeriodicTask.objects.all()
        for task in all_tasks:
            status = "✅ Activa" if task.enabled else "❌ Inactiva"
            print(f"{status} | {task.name}")
            print(f"         Horario: {task.crontab}")
            print(f"         Tarea: {task.task}")
            print(f"         Descripción: {task.description}")
            print("-" * 60)
        
        print(f"\n🎉 Configuración completada exitosamente!")
        print(f"📅 Total de tareas programadas: {all_tasks.count()}")
        print(f"⏰ Las tareas se ejecutarán automáticamente según el cronograma configurado")
        
        print("\n" + "="*60)
        print("🚀 PRÓXIMOS PASOS")
        print("="*60)
        print("1. Instalar y ejecutar Redis server:")
        print("   - Descargar desde: https://redis.io/download")
        print("   - O usar Docker: docker run -d -p 6379:6379 redis")
        print("")
        print("2. Ejecutar Celery Worker:")
        print("   celery -A edupro360 worker --loglevel=info")
        print("")
        print("3. Ejecutar Celery Beat (scheduler):")
        print("   celery -A edupro360 beat --loglevel=info")
        print("")
        print("4. Opcional - Monitor de Celery:")
        print("   celery -A edupro360 flower")
        print("="*60)
        
    except Exception as e:
        print(f"❌ Error configurando tareas: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def show_task_schedule():
    """Muestra el cronograma de todas las tareas programadas."""
    try:
        from django_celery_beat.models import PeriodicTask
        
        print("\n📅 CRONOGRAMA DE TAREAS AUTOMÁTICAS")
        print("="*70)
        
        tasks_by_time = [
            ("03:00 - Primer domingo del mes", "Limpieza Archivos Antiguos"),
            ("06:00 - Día 5 de cada mes", "Consolidado Mensual (HU-12)"),
            ("07:00 - Lunes", "Estadísticas Semanales"),
            ("08:00 - Diario", "Recordatorio Calificaciones Pendientes (HU-11.3)"),
            ("09:00 - Diario", "Recordatorio Tareas Próximas (HU-11.1)"),
            ("10:00 - Diario", "Recordatorio Tareas Vencidas (HU-11.2)"),
        ]
        
        for horario, descripcion in tasks_by_time:
            print(f"⏰ {horario:<25} | {descripcion}")
        
        print("="*70)
        print("📧 Los emails se envían automáticamente según estos horarios")
        print("📊 Los reportes PDF/Excel se generan y envían a administradores")
        print("🔄 Las tareas se repiten automáticamente según la programación")
        
    except Exception as e:
        print(f"❌ Error mostrando cronograma: {str(e)}")

if __name__ == '__main__':
    print("🔧 EduPro 360 - Configurador de Tareas Automáticas")
    print("=" * 60)
    print("Configurando sistema de recordatorios y consolidados...")
    print("")
    
    success = setup_celery_beat_tasks()
    
    if success:
        show_task_schedule()
    else:
        print("❌ La configuración falló. Revisa los errores arriba.")
        sys.exit(1)