from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.validators import EmailValidator
from Base.models import BaseModel


class Role(BaseModel):
    """
    Modelo para gestionar roles de usuario.
    HU-05: Gestión de Roles y Permisos
    """
    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre del rol")
    descripcion = models.TextField(verbose_name="Descripción del rol", blank=True)
    
    # Permisos específicos del sistema académico
    puede_crear_asignatura = models.BooleanField(default=False, verbose_name="Puede crear asignaturas")
    puede_editar_asignatura = models.BooleanField(default=False, verbose_name="Puede editar asignaturas")
    puede_eliminar_asignatura = models.BooleanField(default=False, verbose_name="Puede eliminar asignaturas")
    
    puede_crear_tarea = models.BooleanField(default=False, verbose_name="Puede crear tareas")
    puede_editar_tarea = models.BooleanField(default=False, verbose_name="Puede editar tareas")
    puede_eliminar_tarea = models.BooleanField(default=False, verbose_name="Puede eliminar tareas")
    puede_calificar_tarea = models.BooleanField(default=False, verbose_name="Puede calificar tareas")
    
    puede_ver_todas_calificaciones = models.BooleanField(default=False, verbose_name="Puede ver todas las calificaciones")
    puede_entregar_tarea = models.BooleanField(default=False, verbose_name="Puede entregar tareas")
    
    recibe_notificacion_estado_mensual = models.BooleanField(
        default=False, 
        verbose_name="Recibe notificación de estado mensual"
    )
    
    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        db_table = "roles"
        
    def __str__(self):
        return self.nombre


class CustomUserManager(BaseUserManager):
    """
    Manager personalizado para el modelo de usuario.
    """
    def create_user(self, correo, password=None, **extra_fields):
        """
        Crea y guarda un usuario con el correo y contraseña dados.
        """
        if not correo:
            raise ValueError('El correo electrónico es obligatorio')
        
        correo = self.normalize_email(correo)
        user = self.model(correo=correo, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, correo, password=None, **extra_fields):
        """
        Crea y guarda un superusuario con el correo y contraseña dados.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True.')
        
        return self.create_user(correo, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin, BaseModel):
    """
    Modelo personalizado de usuario que extiende BaseModel.
    HU-01: Registro de Usuarios
    """
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    apellido = models.CharField(max_length=100, verbose_name="Apellido")
    correo = models.EmailField(
        unique=True, 
        validators=[EmailValidator()],
        verbose_name="Correo electrónico"
    )
    rol = models.ForeignKey(
        Role, 
        on_delete=models.PROTECT, 
        related_name='usuarios',
        verbose_name="Rol",
        null=True,
        blank=True
    )
    
    # Campos adicionales de Django
    is_staff = models.BooleanField(default=False, verbose_name="Es staff")
    is_superuser = models.BooleanField(default=False, verbose_name="Es superusuario")
    
    # Token para recuperación de contraseña
    token_recuperacion = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        verbose_name="Token de recuperación"
    )
    token_recuperacion_expira = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name="Expiración del token"
    )
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'correo'
    REQUIRED_FIELDS = ['nombre', 'apellido']
    
    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        db_table = "usuarios"
        
    def __str__(self):
        return f"{self.nombre} {self.apellido} ({self.correo})"
    
    @property
    def nombre_completo(self):
        """Retorna el nombre completo del usuario."""
        return f"{self.nombre} {self.apellido}"
    
    def tiene_permiso(self, permiso):
        """
        Verifica si el usuario tiene un permiso específico basado en su rol.
        """
        if self.is_superuser:
            return True
        if not self.rol:
            return False
        return getattr(self.rol, permiso, False)

