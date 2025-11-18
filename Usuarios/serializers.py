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
        password = validated_data.pop("password", None)
        perms = validated_data.pop("user_permissions", [])
        user = Usuario.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        if perms:
            from django.contrib.auth.models import Permission
            permisos = Permission.objects.filter(codename__in=perms)
            user.user_permissions.set(permisos)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        perms = validated_data.pop("user_permissions", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        if perms is not None:
            from django.contrib.auth.models import Permission
            permisos = Permission.objects.filter(codename__in=perms)
            instance.user_permissions.set(permisos)
        instance.save()
        return instance


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name", "permissions"]
