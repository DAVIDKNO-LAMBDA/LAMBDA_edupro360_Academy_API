from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.response import Response

from .serializers import UsuarioSerializer, GroupSerializer
from edupro360.correo import enviar_correo  # archivo en startproject

Usuario = get_user_model()


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAdminUser]  # Admin maneja usuarios

    def perform_create(self, serializer):
        """
        Cuando el admin crea un usuario:
        - Se genera token de activación (modelo)
        - Se envía correo de activación HTML usando enviar_correo
        """
        user = serializer.save()
        if not user.is_superuser:
            user.create_activation_token()
            contexto = {
                "nombre": user.nombres,
                "correo": user.correo,
                "token": user.activation_token,
            }
            enviar_correo(
                asunto="Activa tu cuenta en EduPro360",
                plantilla="Usuarios/correos/activacion_cuenta.html",
                contexto=contexto,
                destinatarios=[user.correo],
            )

    @action(detail=False, methods=["post"], permission_classes=[AllowAny], url_path="activar-cuenta")
    def activar_cuenta(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"detail": "Token requerido."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = Usuario.objects.get(activation_token=token)
        except Usuario.DoesNotExist:
            return Response({"detail": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)

        if not user.validate_activation_token(token):
            return Response({"detail": "Token expirado."}, status=status.HTTP_400_BAD_REQUEST)

        user.activate_user()
        return Response({"detail": "Cuenta activada correctamente."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], permission_classes=[AllowAny], url_path="solicitar-reset-password")
    def solicitar_reset_password(self, request):
        correo = request.data.get("correo")
        if not correo:
            return Response({"detail": "Correo requerido."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = Usuario.objects.get(correo=correo)
        except Usuario.DoesNotExist:
            # No reveles si existe o no
            return Response(
                {"detail": "Si el correo existe, se enviará un enlace de recuperación."},
                status=status.HTTP_200_OK,
            )

        user.create_reset_token()
        contexto = {
            "nombre": user.nombres,
            "correo": user.correo,
            "token": user.reset_password_token,
        }
        enviar_correo(
            asunto="Recupera tu contraseña en EduPro360",
            plantilla="Usuarios/correos/reset_password.html",
            contexto=contexto,
            destinatarios=[user.correo],
        )
        return Response(
            {"detail": "Si el correo existe, se enviará un enlace de recuperación."},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], permission_classes=[AllowAny], url_path="reset-password")
    def reset_password(self, request):
        token = request.data.get("token")
        nueva_password = request.data.get("nueva_password")

        if not token or not nueva_password:
            return Response({"detail": "Token y nueva_password son requeridos."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            user = Usuario.objects.get(reset_password_token=token)
        except Usuario.DoesNotExist:
            return Response({"detail": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)

        if not user.validate_reset_token(token):
            return Response({"detail": "Token expirado."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(nueva_password)
        user.reset_password_token = None
        user.reset_password_token_expires_at = None
        user.save(update_fields=["password", "reset_password_token", "reset_password_token_expires_at"])

        return Response({"detail": "Contraseña actualizada correctamente."}, status=status.HTTP_200_OK)


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAdminUser]
