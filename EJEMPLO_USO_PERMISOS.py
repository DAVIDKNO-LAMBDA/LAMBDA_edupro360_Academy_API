"""
EJEMPLOS DE USO DE DECORADORES Y PERMISOS EN EDUPRO 360

Este archivo muestra cómo usar los decoradores y clases de permisos
implementados en edupro360/permissions.py
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from edupro360.permissions import (
    require_permission,
    require_active_user,
    require_owner_or_permission,
    IsDocenteResponsable,
    CanManageAsignatura,
    CanManageTarea,
    CanCalificarTarea,
)


# ==================== EJEMPLO 1: USO BÁSICO DE require_permission ====================

class AsignaturaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar asignaturas.
    """
    # Usar permisos de clase DRF (validación general)
    permission_classes = [CanManageAsignatura]

    # O usar decoradores en métodos específicos
    @require_permission(["crear_asignatura"], app_label="Academico")
    def create(self, request):
        """
        Crear una nueva asignatura.
        Solo usuarios con permiso 'Academico.crear_asignatura'
        """
        # Tu lógica aquí
        return Response({"message": "Asignatura creada"})

    @require_permission(["editar_asignatura"], app_label="Academico")
    def update(self, request, pk=None):
        """
        Editar una asignatura existente.
        Solo usuarios con permiso 'Academico.editar_asignatura'
        """
        return Response({"message": "Asignatura actualizada"})

    @require_permission(["ver_asignaturas_campus"], app_label="Academico")
    def list(self, request):
        """
        Listar todas las asignaturas del campus.
        Solo coordinadores con permiso 'Academico.ver_asignaturas_campus'
        """
        return Response({"asignaturas": []})


# ==================== EJEMPLO 2: MÚLTIPLES PERMISOS CON AND ====================

class TareaViewSet(viewsets.ModelViewSet):
    
    @require_permission(
        ["crear_tarea", "publicar_tarea"],
        app_label="Academico",
        mode="AND"  # Requiere AMBOS permisos
    )
    def create(self, request):
        """
        Crear y publicar una tarea.
        Requiere AMBOS permisos: crear_tarea Y publicar_tarea
        """
        return Response({"message": "Tarea creada y publicada"})


# ==================== EJEMPLO 3: MÚLTIPLES PERMISOS CON OR ====================

class CalificacionViewSet(viewsets.ModelViewSet):
    
    @require_permission(
        ["ver_calificaciones_propias", "ver_calificaciones_asignatura"],
        app_label="Academico",
        mode="OR"  # Requiere AL MENOS UNO
    )
    def list(self, request):
        """
        Ver calificaciones.
        Estudiantes pueden ver las suyas (ver_calificaciones_propias)
        Docentes pueden ver todas de su asignatura (ver_calificaciones_asignatura)
        """
        user = request.user
        
        if user.has_perm("Academico.ver_calificaciones_propias"):
            # Filtrar solo las del estudiante
            calificaciones = []  # Filtrar por estudiante=user
        else:
            # Mostrar todas las de la asignatura
            calificaciones = []  # Todas las calificaciones
        
        return Response({"calificaciones": calificaciones})


# ==================== EJEMPLO 4: VALIDAR USUARIO ACTIVO ====================

class MiPerfilViewSet(viewsets.ViewSet):
    
    @require_active_user
    @action(detail=False, methods=["get"])
    def mi_perfil(self, request):
        """
        Ver mi perfil.
        Solo usuarios activos pueden acceder.
        """
        return Response({
            "id": request.user.id,
            "correo": request.user.correo,
            "nombres": request.user.nombres
        })


# ==================== EJEMPLO 5: PROPIETARIO O PERMISO ====================

class EntregaTareaViewSet(viewsets.ModelViewSet):
    
    @require_owner_or_permission(
        "ver_entregas_asignatura",
        app_label="Academico",
        owner_field="estudiante"
    )
    def retrieve(self, request, pk=None):
        """
        Ver una entrega específica.
        El estudiante puede ver su propia entrega.
        El docente con permiso 'ver_entregas_asignatura' puede ver todas.
        """
        entrega = self.get_object()
        return Response({
            "id": entrega.id,
            "estudiante": entrega.estudiante.correo,
            "fecha_entrega": entrega.fecha_entrega
        })


# ==================== EJEMPLO 6: COMBINAR DECORADORES ====================

class NotasViewSet(viewsets.ViewSet):
    
    @require_active_user
    @require_permission(["calificar_tarea"], app_label="Academico")
    def calificar(self, request):
        """
        Calificar una tarea.
        Usuario debe estar activo Y tener permiso 'calificar_tarea'
        """
        return Response({"message": "Tarea calificada"})


# ==================== EJEMPLO 7: USAR CLASES DE PERMISOS DRF ====================

class GestionTareasViewSet(viewsets.ModelViewSet):
    """
    Usar permisos de clase para validación automática.
    """
    permission_classes = [CanManageTarea]

    def create(self, request):
        # No necesitas decorador, la clase ya valida
        return Response({"message": "Tarea creada"})

    def update(self, request, pk=None):
        # Automáticamente valida con CanManageTarea
        return Response({"message": "Tarea actualizada"})


# ==================== EJEMPLO 8: VALIDAR DOCENTE RESPONSABLE ====================

class MisTareasDocenteViewSet(viewsets.ViewSet):
    """
    Endpoints específicos para docentes.
    """
    permission_classes = [IsDocenteResponsable]

    @action(detail=True, methods=["get"])
    def entregas_pendientes(self, request, pk=None):
        """
        Ver entregas pendientes de una tarea.
        Solo el docente responsable de la asignatura puede acceder.
        """
        tarea = self.get_object()
        # IsDocenteResponsable ya validó que sea el docente responsable
        return Response({"entregas_pendientes": []})


# ==================== EJEMPLO 9: CUSTOM PERMISSION EN ACTION ====================

class ReporteViewSet(viewsets.ViewSet):
    
    @action(
        detail=False,
        methods=["get"],
        url_path="reporte-mensual"
    )
    @require_permission(
        ["recibir_notificacion_estado_mensual"],
        app_label="Usuarios"
    )
    def reporte_mensual(self, request):
        """
        Generar reporte mensual.
        Solo usuarios con permiso 'recibir_notificacion_estado_mensual'
        (Coordinadores académicos)
        """
        # Generar reporte
        return Response({"reporte": "..."})


# ==================== EJEMPLO 10: SIN APP_LABEL (PERMISOS GLOBALES) ====================

class AdminViewSet(viewsets.ViewSet):
    
    @require_permission(
        ["Usuarios.gestionar_usuarios", "Usuarios.gestionar_roles_permisos"],
        mode="AND"
    )
    def gestionar_sistema(self, request):
        """
        Gestión completa del sistema.
        Usa permisos con formato completo 'app.codename'
        """
        return Response({"message": "Acceso completo"})


# ==================== RESUMEN DE USO ====================

"""
1. DECORADOR @require_permission:
   - Usar en métodos individuales de ViewSets
   - Especificar app_label para auto-construir permisos
   - mode="AND" para requerir todos, mode="OR" para al menos uno
   
2. DECORADOR @require_active_user:
   - Validar que el usuario esté activo
   - Combinar con otros decoradores
   
3. DECORADOR @require_owner_or_permission:
   - Validar propietario O permiso específico
   - Útil para recursos privados con excepciones
   
4. CLASES DE PERMISOS (DRF):
   - Usar en permission_classes del ViewSet
   - Validación automática sin decoradores
   - CanManageAsignatura, CanManageTarea, etc.

5. ORDEN DE DECORADORES:
   @require_active_user  # Primero validar activo
   @require_permission(...)  # Luego validar permisos
   def mi_metodo(self, request):
       ...

6. RESPUESTAS DE ERROR:
   - 401 UNAUTHORIZED: No autenticado
   - 403 FORBIDDEN: Autenticado pero sin permisos
"""
