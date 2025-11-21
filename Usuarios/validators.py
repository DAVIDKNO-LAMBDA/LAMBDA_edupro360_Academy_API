"""
Validadores personalizados para contraseñas - EduPro 360
Implementa validaciones avanzadas según las mejores prácticas de seguridad
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class CustomPasswordValidator:
    """
    Validador personalizado para contraseñas con requisitos de seguridad avanzados
    """
    
    def __init__(self, min_length=8, admin_min_length=12):
        self.min_length = min_length
        self.admin_min_length = admin_min_length
    
    def validate(self, password, user=None):
        """Validar contraseña según el rol del usuario"""
        errors = []
        
        # Determinar longitud mínima según el rol
        is_admin_or_coordinator = False
        if user:
            # Solo verificar grupos si el usuario ya está guardado en la DB
            if user.pk:
                is_admin_or_coordinator = user.groups.filter(
                    name__in=['Administradores', 'Coordinadores Académicos']
                ).exists()
            # Para superusers siempre aplicar validación estricta
            if user.is_superuser:
                is_admin_or_coordinator = True
        
        required_length = self.admin_min_length if is_admin_or_coordinator else self.min_length
        
        # 1. Validar longitud mínima
        if len(password) < required_length:
            role_text = "administradores/coordinadores" if is_admin_or_coordinator else "usuarios"
            errors.append(
                ValidationError(
                    f"La contraseña debe tener al menos {required_length} caracteres para {role_text}.",
                    code='password_too_short',
                )
            )
        
        # 2. Validar que contenga al menos una mayúscula
        if not re.search(r'[A-Z]', password):
            errors.append(
                ValidationError(
                    _("La contraseña debe contener al menos una letra mayúscula."),
                    code='password_no_upper',
                )
            )
        
        # 3. Validar que contenga al menos una minúscula
        if not re.search(r'[a-z]', password):
            errors.append(
                ValidationError(
                    _("La contraseña debe contener al menos una letra minúscula."),
                    code='password_no_lower',
                )
            )
        
        # 4. Validar que contenga al menos un número
        if not re.search(r'\d', password):
            errors.append(
                ValidationError(
                    _("La contraseña debe contener al menos un número."),
                    code='password_no_digit',
                )
            )
        
        # 5. Validar que contenga al menos un carácter especial
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append(
                ValidationError(
                    _("La contraseña debe contener al menos un carácter especial (!@#$%^&*(),.?\":{}|<>)."),
                    code='password_no_symbol',
                )
            )
        
        # 6. Validar que no sea completamente numérica
        if password.isdigit():
            errors.append(
                ValidationError(
                    _("La contraseña no puede ser completamente numérica."),
                    code='password_entirely_numeric',
                )
            )
        
        # 7. Validar patrones comunes débiles
        weak_patterns = [
            r'123', r'abc', r'qwerty', r'password', r'admin',
            r'user', r'test', r'demo', r'letmein'
        ]
        
        for pattern in weak_patterns:
            if re.search(pattern, password.lower()):
                errors.append(
                    ValidationError(
                        _("La contraseña contiene patrones comunes que la hacen vulnerable."),
                        code='password_common_pattern',
                    )
                )
                break
        
        # 8. Para admins/coordinadores: validaciones adicionales
        if is_admin_or_coordinator:
            # No puede contener información personal obvia
            if user and user.nombres and user.nombres.lower() in password.lower():
                errors.append(
                    ValidationError(
                        _("La contraseña no puede contener tu nombre."),
                        code='password_contains_name',
                    )
                )
            
            if user and user.correo:
                email_parts = user.correo.split('@')
                if email_parts[0].lower() in password.lower():
                    errors.append(
                        ValidationError(
                            _("La contraseña no puede contener partes de tu correo electrónico."),
                            code='password_contains_email',
                        )
                    )
        
        if errors:
            raise ValidationError(errors)
    
    def get_help_text(self):
        return _(
            "Tu contraseña debe tener al menos 8 caracteres (12 para administradores), "
            "contener mayúsculas, minúsculas, números y símbolos especiales."
        )


class PasswordHistoryValidator:
    """
    Validador para evitar reutilización de contraseñas anteriores
    """
    
    def __init__(self, history_count=3):
        self.history_count = history_count
    
    def validate(self, password, user=None):
        """Validar que la contraseña no sea una de las últimas usadas"""
        if not user:
            return
        
        # Solo validar si el usuario ya está guardado en la DB
        if not hasattr(user, 'pk') or not user.pk:
            return
        
        try:
            # Importar aquí para evitar importaciones circulares
            from Usuarios.models import PasswordHistory
            
            # Verificar historial de contraseñas
            recent_passwords = PasswordHistory.objects.filter(
                user=user
            ).order_by('-created_at')[:self.history_count]
        except Exception:
            # Si hay error al acceder al modelo, saltear validación
            return
        
        from django.contrib.auth.hashers import check_password
        for history_entry in recent_passwords:
            if check_password(password, history_entry.password_hash):
                raise ValidationError(
                    _(f"No puedes reutilizar una de tus últimas {self.history_count} contraseñas."),
                    code='password_recently_used',
                )
    
    def get_help_text(self):
        return _(f"No puedes reutilizar tus últimas {self.history_count} contraseñas.")


def validate_password_strength(password, user=None):
    """
    Función principal para validar fortaleza de contraseñas
    Combina todas las validaciones personalizadas
    """
    # Aplicar validador principal
    main_validator = CustomPasswordValidator()
    main_validator.validate(password, user)
    
    # Aplicar validador de historial si el usuario existe
    if user and user.pk:
        history_validator = PasswordHistoryValidator()
        history_validator.validate(password, user)


# Lista de validadores para usar en settings.py
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'Usuarios.validators.CustomPasswordValidator',
        'OPTIONS': {
            'min_length': 8,
            'admin_min_length': 12,
        }
    },
    {
        'NAME': 'Usuarios.validators.PasswordHistoryValidator',
        'OPTIONS': {
            'history_count': 3,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]