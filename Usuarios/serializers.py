from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission

Usuario = get_user_model()


class UsuarioSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True, required=False)
    user_permissions = serializers.SerializerMethodField()
    def get_user_permissions(self, obj):
        return list(obj.user_permissions.values_list('codename', flat=True))

    class Meta:
        model = Usuario
        fields = [
            "id", "correo", "nombres", "apellidos",
            "is_active", "is_staff",
            "groups", "user_permissions",
            "password",
        ]


    def create(self, validated_data):
        import secrets
        password = validated_data.pop("password", None)
        perms = validated_data.pop("user_permissions", [])
        groups = validated_data.pop("groups", [])  # Extraer groups
        
        user = Usuario.objects.create(**validated_data)
        
        # Si no se proporciona password, generar una temporal
        if password:
            user.set_password(password)
        else:
            # Password temporal aleatoria (el usuario la cambiará al activar)
            # Usamos directamente set_password de Django sin validaciones adicionales
            password_temporal = secrets.token_urlsafe(16) + "!Temp1"  # Agregamos caracteres para cumplir validaciones
            from django.contrib.auth.models import AbstractBaseUser
            AbstractBaseUser.set_password(user, password_temporal)
        
        user.save()
        
        # Asignar grupos
        if groups:
            user.groups.set(groups)
        
        # Asignar permisos individuales
        if perms:
            from django.contrib.auth.models import Permission
            permisos = Permission.objects.filter(codename__in=perms)
            user.user_permissions.set(permisos)
        
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        perms = validated_data.pop("user_permissions", None)
        groups = validated_data.pop("groups", None)  # Extraer groups
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        # Actualizar grupos
        if groups is not None:
            instance.groups.set(groups)
        
        # Actualizar permisos individuales
        if perms is not None:
            from django.contrib.auth.models import Permission
            permisos = Permission.objects.filter(codename__in=perms)
            instance.user_permissions.set(permisos)
        
        instance.save()
        return instance


class ActivarCuentaSerializer(serializers.Serializer):
    """
    Serializer para activar cuenta y establecer password inicial
    """
    correo = serializers.EmailField(required=True)
    token = serializers.CharField(required=True, max_length=100)
    password = serializers.CharField(required=True, write_only=True, min_length=8)
    nombres = serializers.CharField(required=False, max_length=100)
    apellidos = serializers.CharField(required=False, max_length=100)
    
    def validate_password(self, value):
        """Validar que la password cumpla con políticas de seguridad"""
        if len(value) < 8:
            raise serializers.ValidationError("La contraseña debe tener al menos 8 caracteres")
        
        # TODO: Agregar más validaciones (mayúsculas, minúsculas, números, etc.)
        
        return value


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name", "permissions"]
