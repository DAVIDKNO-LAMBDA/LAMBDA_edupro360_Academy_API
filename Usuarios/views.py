from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, AllowAny, IsAuthenticated
from rest_framework.response import Response

from .serializers import UsuarioSerializer, GroupSerializer
from edupro360.correo import enviar_correo
from edupro360.permissions import require_permission, require_active_user, IsAdminOrSuperuser

Usuario = get_user_model()


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [IsAdminOrSuperuser]  # Admins del grupo o superuser

    def perform_create(self, serializer):
        """
        Cuando el admin crea un usuario:
        - NO se requiere password (se genera una temporal automática)
        - TODOS los usuarios deben activar su cuenta y establecer su password
        - Se genera token de activación y se envía correo
        - Los admins NO tienen acceso a Django Admin (is_staff = False)
        """
        user = serializer.save()
        
        # Configurar permisos para admins
        from django.contrib.auth.models import Group
        grupo_admin = Group.objects.filter(name='Administradores').first()
        es_admin = grupo_admin and user.groups.filter(id=grupo_admin.id).exists()
        
        if es_admin:
            # Los admins NO acceden a Django Admin
            user.is_staff = False
            user.save()
        
        # TODOS los usuarios deben activar su cuenta (excepto superusers)
        if not user.is_superuser:
            user.create_activation_token()
            
            rol = "usuario"
            if es_admin:
                rol = "administrador"
            elif user.groups.filter(name='Coordinadores Académicos').exists():
                rol = "coordinador académico"
            elif user.groups.filter(name='Docentes').exists():
                rol = "docente"
            elif user.groups.filter(name='Estudiantes').exists():
                rol = "estudiante"
            
            contexto = {
                "nombre": user.nombres,
                "correo": user.correo,
                "token": user.activation_token,
                "rol": rol,
            }
            enviar_correo(
                asunto=f"Activa tu cuenta en EduPro360 - Rol: {rol.title()}",
                plantilla="users/activacion_cuenta.html",
                contexto=contexto,
                destinatarios=[user.correo],
            )

    @action(detail=False, methods=["post"], permission_classes=[AllowAny], url_path="activar-cuenta")
    def activar_cuenta(self, request):
        """
        Activar cuenta y completar perfil
        POST /api/usuarios/activar-cuenta/
        Body: {
            "correo": "...",
            "token": "...",
            "password": "...",
            "nombres": "..." (opcional, actualizar),
            "apellidos": "..." (opcional, actualizar)
        }
        """
        from .serializers import ActivarCuentaSerializer
        
        serializer = ActivarCuentaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        correo = serializer.validated_data['correo']
        token = serializer.validated_data['token']
        password = serializer.validated_data['password']
        nombres = serializer.validated_data.get('nombres')
        apellidos = serializer.validated_data.get('apellidos')
        
        try:
            user = Usuario.objects.get(correo=correo, activation_token=token)
        except Usuario.DoesNotExist:
            return Response(
                {"detail": "Correo o token inválidos."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.validate_activation_token(token):
            return Response(
                {"detail": "Token expirado. Solicita uno nuevo."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Actualizar password
        user.set_password(password)
        
        # Actualizar perfil si se proporcionaron datos
        if nombres:
            user.nombres = nombres
        if apellidos:
            user.apellidos = apellidos
        
        # Activar cuenta
        user.activate_user()
        
        return Response(
            {
                "detail": "Cuenta activada exitosamente.",
                "correo": user.correo,
                "nombres": user.nombres,
                "apellidos": user.apellidos
            }, 
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["post"], permission_classes=[AllowAny], url_path="solicitar-reset-password")
    def solicitar_reset_password(self, request):
        correo = request.data.get("correo")
        if not correo:
            return Response({"detail": "Correo requerido."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = Usuario.objects.get(correo=correo)
        except Usuario.DoesNotExist:
            # No reveles si existe o no
            return Response(
                {"detail": "Si el correo existe, se enviará un enlace de recuperación."},
                status=status.HTTP_200_OK,
            )

        user.create_reset_token()
        contexto = {
            "nombre": user.nombres,
            "correo": user.correo,
            "token": user.reset_password_token,
        }
        enviar_correo(
            asunto="Recupera tu contraseña en EduPro360",
            plantilla="users/reset_password.html",
            contexto=contexto,
            destinatarios=[user.correo],
        )
        return Response(
            {"detail": "Si el correo existe, se enviará un enlace de recuperación."},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], permission_classes=[AllowAny], url_path="reset-password")
    def reset_password(self, request):
        token = request.data.get("token")
        nueva_password = request.data.get("nueva_password")

        if not token or not nueva_password:
            return Response({"detail": "Token y nueva_password son requeridos."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            user = Usuario.objects.get(reset_password_token=token)
        except Usuario.DoesNotExist:
            return Response({"detail": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)

        if not user.validate_reset_token(token):
            return Response({"detail": "Token expirado."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(nueva_password)
        user.reset_password_token = None
        user.reset_password_token_expires_at = None
        user.save(update_fields=["password", "reset_password_token", "reset_password_token_expires_at"])

        return Response({"detail": "Contraseña actualizada correctamente."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated], url_path="cambiar-password")
    @require_active_user
    @require_permission(["cambiar_password_propio"], app_label="Usuarios")
    def cambiar_password(self, request):
        """
        HU-03: Cambio de contraseña del usuario autenticado.
        POST /api/usuarios/cambiar-password/
        Body: {"password_actual": "...", "nueva_password": "..."}
        """
        user = request.user
        password_actual = request.data.get("password_actual")
        nueva_password = request.data.get("nueva_password")

        if not password_actual or not nueva_password:
            return Response(
                {"detail": "password_actual y nueva_password son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar contraseña actual
        if not user.check_password(password_actual):
            return Response(
                {"detail": "Contraseña actual incorrecta."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validar que la nueva contraseña sea diferente
        if password_actual == nueva_password:
            return Response(
                {"detail": "La nueva contraseña debe ser diferente a la actual."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # TODO: Agregar validación de políticas de seguridad aquí
        # - Mínimo 8 caracteres
        # - Al menos una mayúscula, minúscula, número
        # - No usar contraseñas comunes

        # Cambiar contraseña
        user.set_password(nueva_password)
        user.save(update_fields=["password"])

        # Enviar correo de confirmación
        contexto = {
            "nombre": user.nombres,
            "correo": user.correo,
        }
        enviar_correo(
            asunto="Contraseña actualizada - EduPro360",
            plantilla="users/cambio_password.html",
            contexto=contexto,
            destinatarios=[user.correo],
        )

        return Response({"detail": "Contraseña actualizada correctamente."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated], url_path="mi-perfil")
    @require_active_user
    def mi_perfil(self, request):
        """
        Ver el perfil del usuario autenticado.
        GET /api/usuarios/mi-perfil/
        """
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @action(detail=False, methods=["patch"], permission_classes=[IsAuthenticated], url_path="actualizar-perfil")
    @require_active_user
    def actualizar_perfil(self, request):
        """
        Actualizar datos del perfil del usuario autenticado.
        PATCH /api/usuarios/actualizar-perfil/
        Body: {"nombres": "...", "apellidos": "..."}
        """
        user = request.user
        serializer = self.get_serializer(user, data=request.data, partial=True)
        
        # No permitir cambio de correo, password, permisos por este endpoint
        datos_no_permitidos = {"correo", "password", "is_staff", "is_superuser", "groups", "user_permissions"}
        if any(campo in request.data for campo in datos_no_permitidos):
            return Response(
                {"detail": "No puede modificar campos protegidos desde este endpoint."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrSuperuser], url_path="asignar-rol")
    @require_permission(["gestionar_roles_permisos"], app_label="Usuarios")
    def asignar_rol(self, request, pk=None):
        """
        Asignar un rol (grupo) a un usuario.
        POST /api/usuarios/{id}/asignar-rol/
        Body: {"rol_id": 1}
        """
        user = self.get_object()
        rol_id = request.data.get("rol_id")
        
        if not rol_id:
            return Response(
                {"detail": "rol_id es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            rol = Group.objects.get(id=rol_id)
        except Group.DoesNotExist:
            return Response(
                {"detail": "Rol no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        user.groups.add(rol)
        
        return Response({
            "detail": f"Rol '{rol.name}' asignado a {user.correo}."
        })

    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrSuperuser], url_path="remover-rol")
    @require_permission(["gestionar_roles_permisos"], app_label="Usuarios")
    def remover_rol(self, request, pk=None):
        """
        Remover un rol (grupo) de un usuario.
        POST /api/usuarios/{id}/remover-rol/
        Body: {"rol_id": 1}
        """
        user = self.get_object()
        rol_id = request.data.get("rol_id")
        
        if not rol_id:
            return Response(
                {"detail": "rol_id es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            rol = Group.objects.get(id=rol_id)
        except Group.DoesNotExist:
            return Response(
                {"detail": "Rol no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        user.groups.remove(rol)
        
        return Response({
            "detail": f"Rol '{rol.name}' removido de {user.correo}."
        })

    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrSuperuser], url_path="asignar-permisos")
    @require_permission(["gestionar_roles_permisos"], app_label="Usuarios")
    def asignar_permisos(self, request, pk=None):
        """
        Asignar permisos específicos directamente a un usuario.
        POST /api/usuarios/{id}/asignar-permisos/
        Body: {"permisos": [1, 2, 3]} (IDs de permisos)
        """
        from django.contrib.auth.models import Permission
        
        user = self.get_object()
        permisos_ids = request.data.get("permisos", [])
        
        if not isinstance(permisos_ids, list):
            return Response(
                {"detail": "El campo 'permisos' debe ser una lista de IDs."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        permisos = Permission.objects.filter(id__in=permisos_ids)
        
        if permisos.count() != len(permisos_ids):
            return Response(
                {"detail": "Algunos IDs de permisos no son válidos."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Añadir permisos (no reemplaza, solo agrega)
        user.user_permissions.add(*permisos)
        
        return Response({
            "detail": f"Se asignaron {permisos.count()} permisos individuales a {user.correo}.",
            "permisos_asignados": [
                {
                    "id": p.id,
                    "name": p.name,
                    "codename": p.codename
                } for p in permisos
            ]
        })

    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrSuperuser], url_path="remover-permisos")
    @require_permission(["gestionar_roles_permisos"], app_label="Usuarios")
    def remover_permisos(self, request, pk=None):
        """
        Remover permisos específicos de un usuario.
        POST /api/usuarios/{id}/remover-permisos/
        Body: {"permisos": [1, 2, 3]} (IDs de permisos)
        """
        from django.contrib.auth.models import Permission
        
        user = self.get_object()
        permisos_ids = request.data.get("permisos", [])
        
        if not isinstance(permisos_ids, list):
            return Response(
                {"detail": "El campo 'permisos' debe ser una lista de IDs."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        permisos = Permission.objects.filter(id__in=permisos_ids)
        user.user_permissions.remove(*permisos)
        
        return Response({
            "detail": f"Se removieron {permisos.count()} permisos individuales de {user.correo}.",
            "permisos_removidos": [
                {
                    "id": p.id,
                    "name": p.name,
                    "codename": p.codename
                } for p in permisos
            ]
        })

    @action(detail=True, methods=["get"], permission_classes=[IsAdminOrSuperuser], url_path="permisos-efectivos")
    def permisos_efectivos(self, request, pk=None):
        """
        Ver todos los permisos efectivos de un usuario (grupos + individuales).
        GET /api/usuarios/{id}/permisos-efectivos/
        """
        user = self.get_object()
        
        # Permisos de grupos
        permisos_grupos = []
        for grupo in user.groups.all():
            permisos_grupos.extend([
                {
                    "id": p.id,
                    "name": p.name,
                    "codename": p.codename,
                    "origen": f"Grupo: {grupo.name}"
                } for p in grupo.permissions.all()
            ])
        
        # Permisos individuales
        permisos_individuales = [
            {
                "id": p.id,
                "name": p.name,
                "codename": p.codename,
                "origen": "Permiso individual"
            } for p in user.user_permissions.all()
        ]
        
        # Combinar y eliminar duplicados
        todos_permisos = permisos_grupos + permisos_individuales
        permisos_unicos = {p['id']: p for p in todos_permisos}.values()
        
        return Response({
            "usuario": user.correo,
            "total_permisos": len(permisos_unicos),
            "grupos": [g.name for g in user.groups.all()],
            "permisos": list(permisos_unicos)
        })


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAdminOrSuperuser]

    @action(detail=False, methods=["get"], permission_classes=[IsAdminOrSuperuser], url_path="todos-permisos")
    def todos_permisos(self, request):
        """
        Lista todos los permisos disponibles en el sistema.
        GET /api/roles/todos-permisos/
        """
        from django.contrib.auth.models import Permission
        permisos = Permission.objects.all()
        resultado = []
        for permiso in permisos:
            resultado.append({
                "id": permiso.id,
                "codename": permiso.codename,
                "name": permiso.name,
                "content_type": permiso.content_type.model
            })
        return Response(resultado)

    @action(detail=True, methods=["get"], permission_classes=[IsAdminOrSuperuser], url_path="permisos")
    def listar_permisos(self, request, pk=None):
        """
        Lista todos los permisos e indica cuáles están asignados al rol.
        GET /api/roles/{id}/permisos/
        """
        from django.contrib.auth.models import Permission
        grupo = self.get_object()
        permisos = Permission.objects.all()
        resultado = []
        for permiso in permisos:
            resultado.append({
                "id": permiso.id,
                "codename": permiso.codename,
                "name": permiso.name,
                "asignado": grupo.permissions.filter(id=permiso.id).exists()
            })
        return Response(resultado)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrSuperuser], url_path="asignar-permisos")
    def asignar_permisos(self, request, pk=None):
        """
        Asigna permisos a un rol.
        POST /api/roles/{id}/asignar-permisos/
        Body: {"permisos": [1, 2, 3]} (IDs de permisos)
        """
        from django.contrib.auth.models import Permission
        grupo = self.get_object()
        permisos_ids = request.data.get("permisos", [])
        
        if not isinstance(permisos_ids, list):
            return Response(
                {"detail": "El campo 'permisos' debe ser una lista de IDs."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        permisos = Permission.objects.filter(id__in=permisos_ids)
        grupo.permissions.set(permisos)
        
        return Response({
            "detail": f"Se asignaron {permisos.count()} permisos al rol {grupo.name}."
        })

    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrSuperuser], url_path="remover-permisos")
    def remover_permisos(self, request, pk=None):
        """
        Remueve permisos de un rol.
        POST /api/roles/{id}/remover-permisos/
        Body: {"permisos": [1, 2, 3]} (IDs de permisos)
        """
        from django.contrib.auth.models import Permission
        grupo = self.get_object()
        permisos_ids = request.data.get("permisos", [])
        
        if not isinstance(permisos_ids, list):
            return Response(
                {"detail": "El campo 'permisos' debe ser una lista de IDs."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        permisos = Permission.objects.filter(id__in=permisos_ids)
        grupo.permissions.remove(*permisos)
        
        return Response({
            "detail": f"Se removieron {permisos.count()} permisos del rol {grupo.name}."
        })
