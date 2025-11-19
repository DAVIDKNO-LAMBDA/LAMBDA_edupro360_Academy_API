from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    model = Usuario
    list_display = ("correo", "nombres", "apellidos", "is_active", "is_staff", "is_superuser")
    list_filter = ("is_active", "is_staff", "is_superuser", "groups")

    search_fields = ("correo", "nombres", "apellidos")
    ordering = ("correo",)

    fieldsets = (
        (None, {"fields": ("correo", "password")}),
        ("Información personal", {"fields": ("nombres", "apellidos")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Tokens", {"fields": ("activation_token", "activation_token_expires_at")}),
        ("Tiempos", {"fields": ("creado", "modificado")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("correo", "nombres", "apellidos", "password1", "password2"),
        }),
    )

    readonly_fields = ("creado", "modificado", "activation_token", "activation_token_expires_at")

    filter_horizontal = ("groups", "user_permissions")
