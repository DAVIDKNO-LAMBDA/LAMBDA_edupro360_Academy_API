#!/usr/bin/env python
"""
Configurador de email para testing - EduPro 360
Permite cambiar temporalmente la configuración de email para pruebas
"""

import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupro360.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

def configurar_email_consola():
    """Cambiar configuración para mostrar emails en consola (para testing)"""
    print("📧 CONFIGURANDO EMAIL PARA TESTING")
    print("=" * 50)
    
    # Cambiar temporalmente el backend de email
    settings.EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    
    print("✅ Email configurado para mostrar en consola")
    print("💡 Los emails se mostrarán aquí en lugar de enviarse")
    
    return True

def probar_todos_los_emails():
    """Enviar ejemplos de todos los tipos de email del sistema"""
    print("\n📬 ENVIANDO TODOS LOS TIPOS DE EMAIL")
    print("=" * 50)
    
    try:
        from django.template.loader import render_to_string
        from Usuarios.models import Usuario
        from Academico.models import Tarea, Asignatura
        
        # Obtener datos para las pruebas
        usuario = Usuario.objects.first()
        if not usuario:
            print("❌ No hay usuarios en la base de datos")
            return
            
        tarea = Tarea.objects.first()
        if not tarea:
            print("❌ No hay tareas en la base de datos")
            return
        
        asignatura = Asignatura.objects.first()
        
        # 1. Email de bienvenida
        print("\n1️⃣ Email de Bienvenida:")
        contexto_bienvenida = {
            'usuario': usuario,
            'token_activacion': 'ABC123TOKEN456',
            'enlace_activacion': 'http://localhost:8000/activate/ABC123TOKEN456'
        }
        mensaje_bienvenida = render_to_string('users/bienvenida.html', contexto_bienvenida)
        send_mail(
            subject="🎉 Bienvenido a EduPro 360",
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[usuario.correo],
            html_message=mensaje_bienvenida,
            fail_silently=False
        )
        
        # 2. Recordatorio de tarea
        print("2️⃣ Recordatorio de Tarea:")
        contexto_recordatorio = {
            'estudiante': usuario,
            'tarea': tarea,
            'asignatura': asignatura,
            'docente': asignatura.docente_responsable if asignatura else usuario,
            'dias_restantes': 2
        }
        mensaje_recordatorio = render_to_string('academico/recordatorio_tarea.html', contexto_recordatorio)
        send_mail(
            subject="🔔 Recordatorio: Tarea próxima a vencer",
            message='',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[usuario.correo],
            html_message=mensaje_recordatorio,
            fail_silently=False
        )
        
        # 3. Nueva tarea asignada
        if tarea and asignatura:
            print("3️⃣ Nueva Tarea:")
            contexto_nueva_tarea = {
                'estudiante': usuario,
                'tarea': tarea,
                'asignatura': asignatura,
                'docente': asignatura.docente_responsable,
                'dias_restantes': 7
            }
            mensaje_nueva_tarea = render_to_string('academico/nueva_tarea.html', contexto_nueva_tarea)
            send_mail(
                subject="📋 Nueva Tarea Asignada",
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.correo],
                html_message=mensaje_nueva_tarea,
                fail_silently=False
            )
        
        # 4. Asignación de docente
        if asignatura:
            print("4️⃣ Asignación Docente:")
            contexto_asignacion = {
                'docente': usuario,
                'asignatura': asignatura,
                'periodo': asignatura.periodo_academico,
                'fecha_asignacion': asignatura.modificado
            }
            mensaje_asignacion = render_to_string('academico/asignacion_docente.html', contexto_asignacion)
            send_mail(
                subject="📚 Nueva Asignación Docente",
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.correo],
                html_message=mensaje_asignacion,
                fail_silently=False
            )
        
        print("\n✅ Todos los emails enviados correctamente")
        print("📺 Revisa la salida de la consola para ver el contenido")
        
    except Exception as e:
        print(f"❌ Error enviando emails: {str(e)}")

def main():
    """Función principal"""
    print("📧 PROBADOR DE EMAILS - EDUPRO 360")
    print("=" * 50)
    
    # Preguntar qué tipo de prueba hacer
    print("\n¿Qué tipo de prueba deseas realizar?")
    print("1. Configurar email para consola (recomendado)")
    print("2. Enviar email real de prueba")
    print("3. Probar todos los tipos de email")
    
    opcion = input("\nSelecciona opción (1-3): ").strip()
    
    if opcion == "1":
        configurar_email_consola()
        probar_todos_los_emails()
    elif opcion == "2":
        email = input("Ingresa email destino: ").strip()
        if email:
            send_mail(
                subject="🧪 Prueba EduPro 360",
                message="Este es un email de prueba del sistema EduPro 360",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False
            )
            print("✅ Email enviado")
        else:
            print("❌ Email inválido")
    elif opcion == "3":
        probar_todos_los_emails()
    else:
        print("❌ Opción inválida")

if __name__ == "__main__":
    main()