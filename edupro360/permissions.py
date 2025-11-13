from functools import wraps
from rest_framework.response import Response
from rest_framework import status


def require_permission(perms: list, app_label: str = None, mode: str = "AND"):
    """
    Decorador para validar permisos en views DRF basadas en clase (métodos: get/post/...).

    perms: lista de codenames, ej: ["crear_asignatura"]
    app_label: si se pasa, compone "app_label.codename"
    mode: "AND" (todos) o "OR" (al menos uno)
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            user = request.user

            if not user or not user.is_authenticated:
                return Response({"detail": "No autenticado."}, status=status.HTTP_401_UNAUTHORIZED)

            if app_label:
                full_perms = [f"{app_label}.{p}" for p in perms]
            else:
                full_perms = perms

            if mode == "AND":
                has_perm = user.has_perms(full_perms)
            else:
                has_perm = any(user.has_perm(p) for p in full_perms)

            if not has_perm:
                return Response({"detail": "No autorizado. Permisos insuficientes."}, status=status.HTTP_403_FORBIDDEN)

            return view_func(self, request, *args, **kwargs)

        return wrapper

    return decorator
