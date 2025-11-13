from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from Base.models import BaseModel


class UserManager(BaseUserManager):
    def create_user(self, correo, nombres, apellidos, password=None, **extra_fields):
        if not correo:
            raise ValueError('El usuario debe tener un correo electrónico.')
        if not nombres:
            raise ValueError('El usuario debe tener un nombre.')
        if not apellidos:
            raise ValueError('El usuario debe tener un apellido.')

        correo = self.normalize_email(correo)
        extra_fields.setdefault("is_active", False)
        extra_fields.setdefault("is_staff", False)

        user = self.model(
            correo=correo,
            nombres=nombres,
            apellidos=apellidos,
            **extra_fields
        )
        user.set_password(password)
        user.create_activation_token()
        user.save(using=self._db)
        return user

    def create_superuser(self, correo, nombres, apellidos, password=None, **extra_fields):
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(correo, nombres, apellidos, password, **extra_fields)


class Usuario(BaseModel, AbstractBaseUser, PermissionsMixin):
    correo = models.EmailField(unique=True, verbose_name="Correo")
    nombres = models.CharField(max_length=100, verbose_name="Nombres")
    apellidos = models.CharField(max_length=100, verbose_name="Apellidos")

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    reset_password_token = models.CharField(max_length=200, null=True, blank=True)
    reset_password_token_expires_at = models.DateTimeField(null=True, blank=True)

    activation_token = models.CharField(max_length=200, null=True, blank=True)
    activation_token_expires_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "correo"
    REQUIRED_FIELDS = ["nombres", "apellidos"]

    objects = UserManager()

    class Meta:
        db_table = "usuarios"
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        permissions = [
            ("gestionar_usuarios", "Puede gestionar usuarios"),
            ("gestionar_roles_permisos", "Puede gestionar roles y permisos"),
        ]

    def __str__(self):
        return f"{self.nombres} {self.apellidos}".title()

    # ---- RESET TOKEN ----
    def create_reset_token(self):
        self.reset_password_token = get_random_string(50)
        self.reset_password_token_expires_at = timezone.now() + timedelta(hours=1)
        self.save()

    def validate_reset_token(self, token):
        return (
            self.reset_password_token == token and
            self.reset_password_token_expires_at and
            timezone.now() < self.reset_password_token_expires_at
        )

    # ---- ACTIVATION TOKEN ----
    def create_activation_token(self):
        self.activation_token = get_random_string(50)
        self.activation_token_expires_at = timezone.now() + timedelta(hours=48)
        self.save()

    def validate_activation_token(self, token):
        return (
            self.activation_token == token and
            self.activation_token_expires_at and
            timezone.now() < self.activation_token_expires_at
        )

    def activate_user(self):
        self.is_active = True
        self.activation_token = None
        self.activation_token_expires_at = None
        self.save()
