from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from edupro360.correo import enviar_correo  # está en la raíz del proyecto

Usuario = get_user_model()


@receiver(post_save, sender=Usuario)
def enviar_correo_activacion_usuario(sender, instance, created, **kwargs):
    """
    Envía correo de activación cuando se crea un usuario NO superuser,
    sin importar si se creó desde el admin web o desde la API.
    """
    if not created:
        return

    # Superusuario no necesita activación ni correo
    if instance.is_superuser:
        return

    # Si ya está activo, no tiene sentido mandar activación
    if instance.is_active:
        return

    # Aseguramos que tenga token de activación
    if not instance.activation_token:
        instance.create_activation_token()

    contexto = {
        "nombre": instance.nombres,
        "correo": instance.correo,
        "token": instance.activation_token,
    }

    enviar_correo(
        asunto="Activa tu cuenta en EduPro360",
        plantilla="Usuarios/correos/activacion_cuenta.html",
        contexto=contexto,
        destinatarios=[instance.correo],
    )
