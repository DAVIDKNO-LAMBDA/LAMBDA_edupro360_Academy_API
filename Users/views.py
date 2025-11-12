from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from .models import Role
from .serializers import (
    CustomUserSerializer, RoleSerializer, RegisterSerializer,
    LoginSerializer, ChangePasswordSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer
)

User = get_user_model()


class RoleViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de roles.
    HU-05: Gestión de Roles y Permisos
    """
    queryset = Role.objects.filter(estado=True)
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_superuser:
            return Role.objects.all()
        return Role.objects.filter(estado=True)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de usuarios.
    Incluye registro, login, cambio de contraseña y recuperación.
    """
    queryset = User.objects.filter(estado=True)
    serializer_class = CustomUserSerializer
    
    def get_permissions(self):
        # Solo login y recuperación de contraseña son públicos
        # El registro ahora requiere ser administrador
        if self.action in ['login', 'password_reset_request', 'password_reset_confirm']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return User.objects.all()
        return User.objects.filter(estado=True)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def register(self, request):
        """
        HU-01: Registro de Usuarios - Solo Administradores
        POST /api/users/register/
        Envía correo de bienvenida con credenciales
        """
        # Solo administradores pueden crear usuarios
        if not (request.user.is_superuser or 
                (request.user.rol and request.user.rol.nombre == 'Administrador')):
            return Response(
                {'error': 'No tiene permisos para crear usuarios'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            # Guardar la contraseña antes de crear el usuario
            password = serializer.validated_data.get('password')
            correo = serializer.validated_data.get('correo')
            nombre = serializer.validated_data.get('nombre')
            apellido = serializer.validated_data.get('apellido')
            rol = serializer.validated_data.get('rol')
            
            # Crear usuario
            user = serializer.save()
            
            # Enviar correo de bienvenida con credenciales
            try:
                asunto = 'Bienvenido a EduPro 360'
                mensaje = f"""
Hola {nombre} {apellido},

Tu cuenta ha sido creada exitosamente en EduPro 360.

Tus credenciales de acceso son:
- Correo: {correo}
- Contraseña: {password}
- Rol asignado: {rol.nombre if rol else 'Sin rol'}

Por seguridad, te recomendamos cambiar tu contraseña después del primer inicio de sesión.

Puedes acceder al sistema en: http://localhost:8000/api/users/login/

¡Bienvenido a EduPro 360!
                """
                send_mail(
                    asunto,
                    mensaje,
                    settings.DEFAULT_FROM_EMAIL,
                    [correo],
                    fail_silently=False,
                )
            except Exception as e:
                # Usuario creado pero falló el envío del correo
                print(f"Error enviando correo: {str(e)}")
            
            return Response({
                "message": "Usuario creado exitosamente. Correo de bienvenida enviado.",
                "user": CustomUserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        """
        HU-02: Inicio de Sesión
        POST /api/users/login/
        """
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generar tokens JWT
            refresh = RefreshToken.for_user(user)
            
            return Response({
                "message": "Login exitoso",
                "user": CustomUserSerializer(user).data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """
        HU-03: Cambio de Contraseña
        POST /api/users/change_password/
        """
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Contraseña cambiada exitosamente"
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def password_reset_request(self, request):
        """
        HU-04: Recuperación de Contraseña (Solicitud)
        POST /api/users/password_reset_request/
        """
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Se ha enviado un correo con instrucciones para recuperar tu contraseña"
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def password_reset_confirm(self, request):
        """
        HU-04: Recuperación de Contraseña (Confirmación)
        POST /api/users/password_reset_confirm/
        """
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Contraseña restablecida exitosamente"
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        Obtener información del usuario autenticado
        GET /api/users/me/
        """
        serializer = CustomUserSerializer(request.user)
        return Response(serializer.data)

