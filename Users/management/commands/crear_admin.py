"""
Comando personalizado para crear el primer administrador del sistema
y enviarle correo de bienvenida con sus credenciales
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from Users.models import CustomUser, Role


class Command(BaseCommand):
    help = 'Crea el primer administrador del sistema y envía correo de activación'

    def add_arguments(self, parser):
        parser.add_argument('--correo', type=str, required=True, help='Correo del administrador')
        parser.add_argument('--nombre', type=str, required=True, help='Nombre del administrador')
        parser.add_argument('--apellido', type=str, required=True, help='Apellido del administrador')
        parser.add_argument('--password', type=str, required=True, help='Contraseña del administrador')

    def handle(self, *args, **options):
        correo = options['correo']
        nombre = options['nombre']
        apellido = options['apellido']
        password = options['password']

        # Verificar si ya existe un superusuario
        if CustomUser.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                self.style.WARNING('Ya existe un superusuario en el sistema')
            )
            return

        # Verificar si el correo ya está en uso
        if CustomUser.objects.filter(correo=correo).exists():
            self.stdout.write(
                self.style.ERROR(f'El correo {correo} ya está registrado')
            )
            return

        # Crear o obtener el rol de Administrador
        rol_admin, created = Role.objects.get_or_create(
            nombre='Administrador',
            defaults={
                'descripcion': 'Rol con todos los permisos del sistema',
                'puede_crear_asignatura': True,
                'puede_editar_asignatura': True,
                'puede_eliminar_asignatura': True,
                'puede_crear_tarea': True,
                'puede_editar_tarea': True,
                'puede_eliminar_tarea': True,
                'puede_calificar_tarea': True,
                'puede_ver_todas_calificaciones': True,
                'puede_entregar_tarea': False,
                'recibe_notificacion_estado_mensual': True,
            }
        )

        # Crear el superusuario
        try:
            user = CustomUser.objects.create_superuser(
                correo=correo,
                nombre=nombre,
                apellido=apellido,
                password=password,
                rol=rol_admin
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Superusuario creado: {correo}')
            )

            # Enviar correo de activación
            try:
                asunto = '🎉 Bienvenido a EduPro 360 - Cuenta de Administrador Activada'
                mensaje = f"""
Hola {nombre} {apellido},

¡Tu cuenta de administrador ha sido creada exitosamente en EduPro 360!

🔐 Tus credenciales de acceso son:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Correo:     {correo}
   Contraseña: {password}
   Rol:        Administrador (Todos los permisos)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌐 URL de acceso:
   http://localhost:8000/api/users/login/

📋 Como administrador, ahora puedes:
   • Crear nuevos usuarios del sistema
   • Asignar roles y permisos
   • Gestionar asignaturas y tareas
   • Supervisar calificaciones
   • Administrar todo el sistema académico

🔒 Recomendaciones de seguridad:
   1. Cambia tu contraseña después del primer inicio de sesión
   2. No compartas tus credenciales con nadie
   3. Mantén tu cuenta segura

¡Bienvenido al equipo de EduPro 360!

---
Este es un correo automático del sistema EduPro 360
                """
                
                send_mail(
                    asunto,
                    mensaje,
                    settings.DEFAULT_FROM_EMAIL,
                    [correo],
                    fail_silently=False,
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'📧 Correo de activación enviado a {correo}')
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Usuario creado pero falló el envío del correo: {str(e)}')
                )
                self.stdout.write(
                    self.style.WARNING('Verifica la configuración de EMAIL en settings.py')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creando el superusuario: {str(e)}')
            )
