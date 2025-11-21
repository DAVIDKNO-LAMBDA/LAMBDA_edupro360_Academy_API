#!/usr/bin/env python
"""
Probador directo de funciones (sin Celery) para Windows
Ejecuta las funciones directamente para verificar que funcionan
"""

import os
import sys
import django
from datetime import datetime

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupro360.settings')
django.setup()

def test_consolidado_directo():
    """Prueba directa de la función de consolidado (sin Celery)."""
    print("🧪 Probando consolidado mensual directamente...")
    
    try:
        # Importar las funciones directamente (no como tareas Celery)
        from Academico.tasks import generar_pdf_consolidado, generar_excel_consolidado
        from Academico.models import CalificacionTarea
        
        # Obtener calificaciones del mes actual
        now = datetime.now()
        calificaciones = CalificacionTarea.objects.filter(
            creado__year=now.year,
            creado__month=now.month,
            estado=True
        ).select_related(
            'tarea', 'tarea__asignatura', 'estudiante'
        )
        
        print(f"📊 Calificaciones encontradas: {calificaciones.count()}")
        
        if calificaciones.exists():
            # Generar PDF
            print("📄 Generando PDF...")
            pdf_path = generar_pdf_consolidado(calificaciones, now.month, now.year)
            print(f"✅ PDF generado: {pdf_path}")
            
            # Generar Excel
            print("📊 Generando Excel...")
            excel_path = generar_excel_consolidado(calificaciones, now.month, now.year)
            print(f"✅ Excel generado: {excel_path}")
            
            return True
        else:
            print("⚠️ No hay calificaciones para el mes actual")
            print("💡 Necesitas crear algunas calificaciones de prueba primero")
            return False
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_recordatorio_directo():
    """Prueba directa de recordatorios."""
    print("🧪 Probando recordatorios directamente...")
    
    try:
        from Academico.models import Tarea
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        from datetime import timedelta
        
        User = get_user_model()
        
        # Buscar tareas próximas a vencer
        limite_24h = timezone.now() + timedelta(hours=24)
        tareas_proximas = Tarea.objects.filter(
            fecha_vencimiento__lte=limite_24h,
            fecha_vencimiento__gt=timezone.now(),
            estado=True
        )
        
        print(f"📅 Tareas próximas a vencer (24h): {tareas_proximas.count()}")
        
        # Buscar tareas vencidas
        hace_7_dias = timezone.now() - timedelta(days=7)
        tareas_vencidas = Tarea.objects.filter(
            fecha_vencimiento__lt=timezone.now(),
            fecha_vencimiento__gte=hace_7_dias,
            estado=True
        )
        
        print(f"⚠️ Tareas vencidas (últimos 7 días): {tareas_vencidas.count()}")
        
        # Contar estudiantes y docentes
        estudiantes = User.objects.filter(groups__name='Estudiantes', is_active=True)
        docentes = User.objects.filter(groups__name='Docentes', is_active=True)
        
        print(f"👥 Estudiantes activos: {estudiantes.count()}")
        print(f"👨‍🏫 Docentes activos: {docentes.count()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_sistema_completo():
    """Verifica el estado general del sistema."""
    print("🔍 Verificando estado del sistema...")
    
    try:
        from django.contrib.auth import get_user_model
        from Academico.models import PeriodoAcademico, Asignatura, Tarea, EntregaTarea, CalificacionTarea
        
        User = get_user_model()
        
        # Estadísticas generales
        stats = {
            'usuarios': User.objects.filter(is_active=True).count(),
            'periodos': PeriodoAcademico.objects.filter(estado=True).count(),
            'asignaturas': Asignatura.objects.filter(estado=True).count(),
            'tareas': Tarea.objects.filter(estado=True).count(),
            'entregas': EntregaTarea.objects.filter(estado=True).count(),
            'calificaciones': CalificacionTarea.objects.filter(estado=True).count(),
        }
        
        print("📊 ESTADÍSTICAS DEL SISTEMA:")
        print("=" * 40)
        for item, count in stats.items():
            print(f"{item.capitalize():<15}: {count:>5}")
        
        # Verificar configuración de email
        from django.conf import settings
        print(f"\n📧 Email backend: {settings.EMAIL_BACKEND}")
        print(f"📧 Email host: {settings.EMAIL_HOST}")
        
        # Verificar carpetas
        import os
        media_path = settings.MEDIA_ROOT
        reportes_path = os.path.join(media_path, 'reportes')
        archivos_path = os.path.join(media_path, 'archivos')
        
        print(f"\n📁 Carpeta media: {'✅' if os.path.exists(media_path) else '❌'}")
        print(f"📁 Carpeta reportes: {'✅' if os.path.exists(reportes_path) else '❌'}")
        print(f"📁 Carpeta archivos: {'✅' if os.path.exists(archivos_path) else '❌'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    """Función principal."""
    print("🎯 EduPro 360 - Probador Directo (Sin Celery)")
    print("=" * 60)
    print("Esta herramienta prueba las funciones directamente sin usar Celery")
    print("Útil para debugging y verificación en Windows\n")
    
    while True:
        print("\n📋 OPCIONES:")
        print("1. Verificar estado del sistema")
        print("2. Probar recordatorios (lógica)")
        print("3. Probar consolidado mensual")
        print("4. Ejecutar TODAS las pruebas")
        print("0. Salir")
        print("-" * 40)
        
        try:
            choice = input("👉 Selecciona una opción: ").strip()
            
            if choice == '0':
                print("👋 ¡Hasta luego!")
                break
            elif choice == '1':
                test_sistema_completo()
            elif choice == '2':
                test_recordatorio_directo()
            elif choice == '3':
                test_consolidado_directo()
            elif choice == '4':
                print("🚀 Ejecutando todas las pruebas...")
                print("-" * 40)
                test_sistema_completo()
                print("-" * 40)
                test_recordatorio_directo()
                print("-" * 40)
                test_consolidado_directo()
            else:
                print("❌ Opción inválida")
                
        except KeyboardInterrupt:
            print("\n👋 Saliendo...")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        input("\n⏸️ Presiona Enter para continuar...")

if __name__ == '__main__':
    main()