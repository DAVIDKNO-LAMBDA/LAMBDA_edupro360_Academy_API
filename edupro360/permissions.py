from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import BasePermission


def require_permission(perms: list, app_label: str = None, mode: str = "AND"):
    """
    Decorador para validar permisos en views DRF basadas en clase (métodos: get/post/...).

    Args:
        perms (list): Lista de codenames de permisos, ej: ["crear_asignatura", "editar_asignatura"]
        app_label (str): Nombre de la app, ej: "Academico". Si se proporciona, compone "app_label.codename"
        mode (str): "AND" (requiere todos los permisos) o "OR" (requiere al menos uno)

    Uso:
        @require_permission(["crear_asignatura"], app_label="Academico")
        def create(self, request):
            ...

        @require_permission(["ver_calificaciones_propias", "ver_calificaciones_asignatura"], mode="OR")
        def list(self, request):
            ...
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            user = request.user

            # Validar autenticación
            if not user or not user.is_authenticated:
                return Response(
                    {"detail": "No autenticado."},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Los superusuarios tienen todos los permisos
            if user.is_superuser:
                return view_func(self, request, *args, **kwargs)

            # Construir lista de permisos completos
            if app_label:
                full_perms = [f"{app_label}.{p}" for p in perms]
            else:
                full_perms = perms

            # Validar permisos según el modo
            if mode == "AND":
                has_perm = user.has_perms(full_perms)
                missing_perms = [p for p in full_perms if not user.has_perm(p)]
            else:  # OR
                has_perm = any(user.has_perm(p) for p in full_perms)
                missing_perms = full_perms if not has_perm else []

            if not has_perm:
                return Response(
                    {
                        "detail": "No autorizado. Permisos insuficientes.",
                        "permisos_requeridos": full_perms,
                        "permisos_faltantes": missing_perms,
                        "modo": mode
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            return view_func(self, request, *args, **kwargs)

        return wrapper

    return decorator


def require_active_user(view_func):
    """
    Decorador que valida si el usuario está activo.
    
    Uso:
        @require_active_user
        def create(self, request):
            ...
    """
    @wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        user = request.user

        if not user or not user.is_authenticated:
            return Response(
                {"detail": "No autenticado."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {"detail": "Usuario inactivo. Contacte al administrador."},
                status=status.HTTP_403_FORBIDDEN
            )

        return view_func(self, request, *args, **kwargs)

    return wrapper


def require_owner_or_permission(perm_codename: str, app_label: str = None, owner_field: str = "user"):
    """
    Decorador que valida si el usuario es propietario del recurso O tiene el permiso indicado.
    
    Args:
        perm_codename (str): Codename del permiso
        app_label (str): Nombre de la app
        owner_field (str): Campo que relaciona el objeto con el usuario propietario
    
    Uso:
        @require_owner_or_permission("ver_calificaciones_asignatura", app_label="Academico", owner_field="estudiante")
        def retrieve(self, request, pk=None):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            user = request.user

            if not user or not user.is_authenticated:
                return Response(
                    {"detail": "No autenticado."},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Superusuarios siempre tienen acceso
            if user.is_superuser:
                return view_func(self, request, *args, **kwargs)

            # Verificar si tiene el permiso
            full_perm = f"{app_label}.{perm_codename}" if app_label else perm_codename
            if user.has_perm(full_perm):
                return view_func(self, request, *args, **kwargs)

            # Verificar si es el propietario del objeto
            obj = self.get_object()
            owner = getattr(obj, owner_field, None)
            
            if owner and owner == user:
                return view_func(self, request, *args, **kwargs)

            return Response(
                {"detail": "No autorizado. No es el propietario ni tiene los permisos necesarios."},
                status=status.HTTP_403_FORBIDDEN
            )

        return wrapper

    return decorator


# ==================== CLASES DE PERMISOS PARA DRF ====================

class IsOwnerOrAdmin(BasePermission):
    """
    Permiso que permite acceso si el usuario es propietario del objeto o es admin.
    """
    owner_field = "user"

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        owner = getattr(obj, self.owner_field, None)
        return owner == request.user


class IsEstudianteOwner(BasePermission):
    """
    Permiso específico para validar que el estudiante es propietario.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        return getattr(obj, "estudiante", None) == request.user


class IsDocenteResponsable(BasePermission):
    """
    Permiso específico para validar que el docente es responsable de la asignatura.
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        
        # Si el objeto tiene asignatura directamente
        asignatura = getattr(obj, "asignatura", None)
        if asignatura:
            return asignatura.docente_responsable == request.user
        
        # Si el objeto ES una asignatura
        if hasattr(obj, "docente_responsable"):
            return obj.docente_responsable == request.user
        
        return False


class CanManageAsignatura(BasePermission):
    """
    Permiso para gestionar asignaturas (crear, editar, desactivar).
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        # Validar según el método HTTP
        if request.method == "POST":
            return request.user.has_perm("Academico.crear_asignatura")
        elif request.method in ["PUT", "PATCH"]:
            return request.user.has_perm("Academico.editar_asignatura")
        elif request.method == "DELETE":
            return request.user.has_perm("Academico.desactivar_asignatura")
        
        return request.user.has_perm("Academico.ver_asignaturas_campus")


class CanManageTarea(BasePermission):
    """
    Permiso para gestionar tareas (crear, editar, eliminar, publicar).
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser:
            return True
        
        if request.method == "POST":
            return request.user.has_perm("Academico.crear_tarea")
        elif request.method in ["PUT", "PATCH"]:
            return request.user.has_perm("Academico.editar_tarea")
        elif request.method == "DELETE":
            return request.user.has_perm("Academico.eliminar_tarea")
        
        return request.user.has_perm("Academico.ver_tareas_asignatura")


class CanCalificarTarea(BasePermission):
    """
    Permiso para calificar tareas.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        return (
            request.user.is_superuser or
            request.user.has_perm("Academico.calificar_tarea")
        )


class IsAdminOrSuperuser(BasePermission):
    """
    Permiso para usuarios del grupo 'Administradores' o superusers.
    Los admins tienen is_staff=False pero pertenecen al grupo Administradores.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superuser siempre tiene acceso
        if request.user.is_superuser:
            return True
        
        # Usuarios del grupo "Administradores" tienen acceso
        return request.user.groups.filter(name='Administradores').exists()
