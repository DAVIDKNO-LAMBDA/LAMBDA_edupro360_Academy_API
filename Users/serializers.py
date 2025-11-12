from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from datetime import timedelta
import secrets
from .models import CustomUser, Role


class RoleSerializer(serializers.ModelSerializer):
    """Serializer para el modelo Role"""
    
    class Meta:
        model = Role
        fields = [
            'id', 'nombre', 'descripcion', 'estado',
            'puede_crear_asignatura', 'puede_editar_asignatura', 'puede_eliminar_asignatura',
            'puede_crear_tarea', 'puede_editar_tarea', 'puede_eliminar_tarea', 'puede_calificar_tarea',
            'puede_ver_todas_calificaciones', 'puede_entregar_tarea',
            'recibe_notificacion_estado_mensual',
            'creado', 'modificado'
        ]
        read_only_fields = ['id', 'creado', 'modificado']


class CustomUserSerializer(serializers.ModelSerializer):
    """Serializer para el modelo CustomUser"""
    rol_detalle = RoleSerializer(source='rol', read_only=True)
    nombre_completo = serializers.ReadOnlyField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'nombre', 'apellido', 'correo', 'rol', 'rol_detalle',
            'nombre_completo', 'estado', 'is_staff', 'creado', 'modificado'
        ]
        read_only_fields = ['id', 'creado', 'modificado']
        extra_kwargs = {
            'password': {'write_only': True}
        }


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer para registro de usuarios.
    HU-01: Registro de Usuarios
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = CustomUser
        fields = ['correo', 'nombre', 'apellido', 'password', 'password2', 'rol']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "Las contraseñas no coinciden."
            })
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = CustomUser.objects.create_user(**validated_data)
        
        # TODO: Enviar correo de bienvenida
        # self.send_welcome_email(user)
        
        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer para inicio de sesión.
    HU-02: Inicio de Sesión
    """
    correo = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        correo = attrs.get('correo')
        password = attrs.get('password')
        
        if correo and password:
            # Verificar si el usuario existe
            try:
                user = CustomUser.objects.get(correo=correo)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError({
                    "detail": "Usuario no encontrado."
                })
            
            # Verificar si el usuario está activo
            if not user.estado:
                raise serializers.ValidationError({
                    "detail": "Usuario inactivo."
                })
            
            # Autenticar usuario
            user = authenticate(username=correo, password=password)
            if not user:
                raise serializers.ValidationError({
                    "detail": "Contraseña incorrecta."
                })
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError({
                "detail": "Debe proporcionar correo y contraseña."
            })


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer para cambio de contraseña.
    HU-03: Cambio de Contraseña
    """
    password_actual = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    nueva_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    nueva_password2 = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        if attrs['nueva_password'] != attrs['nueva_password2']:
            raise serializers.ValidationError({
                "nueva_password": "Las contraseñas no coinciden."
            })
        return attrs
    
    def validate_password_actual(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Contraseña actual incorrecta.")
        return value
    
    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['nueva_password'])
        user.save()
        
        # TODO: Enviar correo de confirmación
        # self.send_password_changed_email(user)
        
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer para solicitar recuperación de contraseña.
    HU-04: Recuperación de Contraseña
    """
    correo = serializers.EmailField(required=True)
    
    def validate_correo(self, value):
        try:
            user = CustomUser.objects.get(correo=value, estado=True)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Usuario no encontrado o inactivo.")
        return value
    
    def save(self):
        correo = self.validated_data['correo']
        user = CustomUser.objects.get(correo=correo)
        
        # Generar token temporal
        token = secrets.token_urlsafe(32)
        user.token_recuperacion = token
        user.token_recuperacion_expira = timezone.now() + timedelta(
            seconds=3600  # 1 hora
        )
        user.save()
        
        # TODO: Enviar correo con enlace de recuperación
        # self.send_password_reset_email(user, token)
        
        return user


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer para confirmar recuperación de contraseña.
    HU-04: Recuperación de Contraseña
    """
    token = serializers.CharField(required=True)
    nueva_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    nueva_password2 = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        if attrs['nueva_password'] != attrs['nueva_password2']:
            raise serializers.ValidationError({
                "nueva_password": "Las contraseñas no coinciden."
            })
        
        # Validar token
        try:
            user = CustomUser.objects.get(token_recuperacion=attrs['token'])
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({
                "token": "Token inválido."
            })
        
        # Validar expiración
        if user.token_recuperacion_expira < timezone.now():
            raise serializers.ValidationError({
                "token": "Token expirado."
            })
        
        attrs['user'] = user
        return attrs
    
    def save(self):
        user = self.validated_data['user']
        user.set_password(self.validated_data['nueva_password'])
        user.token_recuperacion = None
        user.token_recuperacion_expira = None
        user.save()
        
        return user
