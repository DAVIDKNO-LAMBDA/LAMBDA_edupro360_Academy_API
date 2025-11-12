from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, Role


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion', 'get_estado', 'creado')
    list_filter = ('estado', 'recibe_notificacion_estado_mensual')
    search_fields = ('nombre', 'descripcion')
    ordering = ('-creado',)


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('correo', 'nombre', 'apellido', 'rol', 'get_estado', 'is_staff', 'creado')
    list_filter = ('estado', 'is_staff', 'is_superuser', 'rol')
    search_fields = ('correo', 'nombre', 'apellido')
    ordering = ('-creado',)
    
    fieldsets = (
        (None, {'fields': ('correo', 'password')}),
        ('Información Personal', {'fields': ('nombre', 'apellido', 'rol')}),
        ('Permisos', {'fields': ('is_staff', 'is_superuser', 'estado')}),
        ('Recuperación', {'fields': ('token_recuperacion', 'token_recuperacion_expira')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('correo', 'nombre', 'apellido', 'password1', 'password2', 'rol', 'estado'),
        }),
    )

