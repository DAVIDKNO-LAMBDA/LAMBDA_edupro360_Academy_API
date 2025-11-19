from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .models import PeriodoAcademico, Asignatura, InscripcionAsignatura, Tarea
from .serializers import (
    PeriodoAcademicoSerializer,
    AsignaturaSerializer,
    AsignaturaListSerializer,
    InscripcionAsignaturaSerializer,
    TareaSerializer,
    TareaListSerializer
)
from edupro360.permissions import IsAdminOrSuperuser, require_permission, require_active_user


class PeriodoAcademicoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Períodos Académicos
    
    Permisos:
    - Crear/Editar/Eliminar: Administradores y Coordinadores
    - Ver: Todos los usuarios autenticados
    """
    queryset = PeriodoAcademico.objects.all()
    serializer_class = PeriodoAcademicoSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Permisos dinámicos según la acción"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrSuperuser()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Filtrar períodos activos por defecto"""
        queryset = PeriodoAcademico.objects.all()
        
        # Filtrar por activos si se pide
        only_active = self.request.query_params.get('activos', None)
        if only_active == 'true':
            queryset = queryset.filter(is_active=True)
        
        return queryset.order_by('-fecha_inicio')
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSuperuser])
    @require_permission(['gestionar_periodos_academicos'], app_label='Academico')
    def activar(self, request, pk=None):
        """Activar un período académico"""
        periodo = self.get_object()
        periodo.is_active = True
        periodo.save()
        return Response({
            'detail': f'Período "{periodo.nombre}" activado exitosamente.'
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSuperuser])
    @require_permission(['gestionar_periodos_academicos'], app_label='Academico')
    def desactivar(self, request, pk=None):
        """Desactivar un período académico"""
        periodo = self.get_object()
        periodo.is_active = False
        periodo.save()
        return Response({
            'detail': f'Período "{periodo.nombre}" desactivado exitosamente.'
        })


class AsignaturaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Asignaturas
    
    Permisos:
    - Crear: Administradores y Coordinadores
    - Editar: Administradores, Coordinadores y Docente responsable
    - Ver: Todos los usuarios autenticados
    """
    queryset = Asignatura.objects.all()
    serializer_class = AsignaturaSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Usar serializer simplificado para listar"""
        if self.action == 'list':
            return AsignaturaListSerializer
        return AsignaturaSerializer
    
    def get_queryset(self):
        """Filtrar asignaturas según el usuario y parámetros"""
        user = self.request.user
        queryset = Asignatura.objects.select_related(
            'docente_responsable', 'periodo_academico'
        )
        
        # Estudiantes solo ven asignaturas en las que están inscritos
        if user.groups.filter(name='Estudiantes').exists():
            queryset = queryset.filter(
                inscripciones__estudiante=user,
                inscripciones__is_active=True
            )
        
        # Docentes ven sus asignaturas
        elif user.groups.filter(name='Docentes').exists():
            queryset = queryset.filter(docente_responsable=user)
        
        # Filtros opcionales
        periodo_id = self.request.query_params.get('periodo', None)
        if periodo_id:
            queryset = queryset.filter(periodo_academico_id=periodo_id)
        
        only_active = self.request.query_params.get('activas', None)
        if only_active == 'true':
            queryset = queryset.filter(is_active=True)
        
        return queryset.distinct().order_by('-created_at')
    
    def perform_create(self, serializer):
        """Crear asignatura con validaciones"""
        serializer.save()
    
    def update(self, request, *args, **kwargs):
        """Validar permisos para editar"""
        asignatura = self.get_object()
        user = request.user
        
        # Superuser y Admins siempre pueden editar
        if user.is_superuser or user.groups.filter(name='Administradores').exists():
            return super().update(request, *args, **kwargs)
        
        # Coordinadores pueden editar
        if user.groups.filter(name='Coordinadores Académicos').exists():
            return super().update(request, *args, **kwargs)
        
        # Docente solo puede editar sus propias asignaturas
        if asignatura.docente_responsable == user:
            # Docente no puede cambiar el docente responsable
            if 'docente_responsable' in request.data:
                return Response(
                    {'detail': 'No puedes cambiar el docente responsable.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            return super().update(request, *args, **kwargs)
        
        return Response(
            {'detail': 'No tienes permiso para editar esta asignatura.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def estudiantes(self, request, pk=None):
        """Listar estudiantes inscritos en la asignatura"""
        asignatura = self.get_object()
        inscripciones = InscripcionAsignatura.objects.filter(
            asignatura=asignatura,
            is_active=True
        ).select_related('estudiante')
        
        estudiantes = [{
            'id': insc.estudiante.id,
            'nombre': insc.estudiante.get_full_name(),
            'correo': insc.estudiante.correo,
            'fecha_inscripcion': insc.fecha_inscripcion
        } for insc in inscripciones]
        
        return Response({
            'asignatura': asignatura.nombre,
            'total': len(estudiantes),
            'estudiantes': estudiantes
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrSuperuser])
    def asignar_docente(self, request, pk=None):
        """Cambiar el docente responsable de una asignatura"""
        asignatura = self.get_object()
        nuevo_docente_id = request.data.get('docente_id')
        
        if not nuevo_docente_id:
            return Response(
                {'detail': 'El campo docente_id es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from Usuarios.models import Usuario
            nuevo_docente = Usuario.objects.get(id=nuevo_docente_id)
            
            if not nuevo_docente.groups.filter(name__in=['Docentes', 'Coordinadores Académicos']).exists():
                return Response(
                    {'detail': 'El usuario seleccionado no es un docente.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            asignatura.docente_responsable = nuevo_docente
            asignatura.save()
            
            return Response({
                'detail': f'Docente asignado exitosamente a {asignatura.nombre}.',
                'docente': nuevo_docente.get_full_name()
            })
            
        except Usuario.DoesNotExist:
            return Response(
                {'detail': 'Docente no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )


class InscripcionAsignaturaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Inscripciones a Asignaturas
    
    Permisos:
    - Crear/Eliminar: Administradores y Coordinadores
    - Ver: Todos los usuarios autenticados
    """
    queryset = InscripcionAsignatura.objects.all()
    serializer_class = InscripcionAsignaturaSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Permisos dinámicos según la acción"""
        if self.action in ['create', 'destroy']:
            return [IsAdminOrSuperuser()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Filtrar inscripciones según el usuario"""
        user = self.request.user
        queryset = InscripcionAsignatura.objects.select_related(
            'asignatura', 'estudiante'
        )
        
        # Estudiantes solo ven sus propias inscripciones
        if user.groups.filter(name='Estudiantes').exists():
            queryset = queryset.filter(estudiante=user)
        
        # Filtros opcionales
        asignatura_id = self.request.query_params.get('asignatura', None)
        if asignatura_id:
            queryset = queryset.filter(asignatura_id=asignatura_id)
        
        estudiante_id = self.request.query_params.get('estudiante', None)
        if estudiante_id:
            queryset = queryset.filter(estudiante_id=estudiante_id)
        
        return queryset.filter(is_active=True).order_by('-fecha_inscripcion')
    
    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrSuperuser])
    def inscribir_multiple(self, request):
        """Inscribir múltiples estudiantes a una asignatura"""
        asignatura_id = request.data.get('asignatura_id')
        estudiantes_ids = request.data.get('estudiantes_ids', [])
        
        if not asignatura_id or not estudiantes_ids:
            return Response(
                {'detail': 'Se requieren asignatura_id y estudiantes_ids.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            asignatura = Asignatura.objects.get(id=asignatura_id)
        except Asignatura.DoesNotExist:
            return Response(
                {'detail': 'Asignatura no encontrada.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        inscripciones_creadas = []
        errores = []
        
        from Usuarios.models import Usuario
        for estudiante_id in estudiantes_ids:
            try:
                estudiante = Usuario.objects.get(id=estudiante_id)
                
                # Validar que sea estudiante
                if not estudiante.groups.filter(name='Estudiantes').exists():
                    errores.append(f"{estudiante.correo} no es un estudiante")
                    continue
                
                # Validar que no esté ya inscrito
                if InscripcionAsignatura.objects.filter(
                    asignatura=asignatura,
                    estudiante=estudiante,
                    is_active=True
                ).exists():
                    errores.append(f"{estudiante.correo} ya está inscrito")
                    continue
                
                # Crear inscripción
                inscripcion = InscripcionAsignatura.objects.create(
                    asignatura=asignatura,
                    estudiante=estudiante
                )
                inscripciones_creadas.append(estudiante.correo)
                
            except Usuario.DoesNotExist:
                errores.append(f"Usuario con ID {estudiante_id} no encontrado")
        
        return Response({
            'detail': f'Se inscribieron {len(inscripciones_creadas)} estudiantes.',
            'inscripciones_creadas': inscripciones_creadas,
            'errores': errores
        }, status=status.HTTP_201_CREATED if inscripciones_creadas else status.HTTP_400_BAD_REQUEST)


class TareaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Tareas y Evaluaciones
    
    Permisos:
    - Crear/Editar: Administradores, Coordinadores y Docente de la asignatura
    - Ver: Todos los usuarios autenticados (filtrado por rol)
    - Eliminar: Administradores y Coordinadores
    """
    queryset = Tarea.objects.all()
    serializer_class = TareaSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Usar serializer simplificado para listar"""
        if self.action == 'list':
            return TareaListSerializer
        return TareaSerializer
    
    def get_queryset(self):
        """Filtrar tareas según el usuario y parámetros"""
        user = self.request.user
        queryset = Tarea.objects.select_related('asignatura')
        
        # Estudiantes solo ven tareas de sus asignaturas
        if user.groups.filter(name='Estudiantes').exists():
            queryset = queryset.filter(
                asignatura__inscripciones__estudiante=user,
                asignatura__inscripciones__is_active=True
            )
        
        # Docentes solo ven tareas de sus asignaturas
        elif user.groups.filter(name='Docentes').exists():
            queryset = queryset.filter(asignatura__docente_responsable=user)
        
        # Filtros opcionales
        asignatura_id = self.request.query_params.get('asignatura', None)
        if asignatura_id:
            queryset = queryset.filter(asignatura_id=asignatura_id)
        
        tipo = self.request.query_params.get('tipo', None)
        if tipo:
            queryset = queryset.filter(tipo_tarea=tipo.upper())
        
        only_active = self.request.query_params.get('activas', None)
        if only_active == 'true':
            queryset = queryset.filter(is_active=True)
        
        # Filtrar por próximas a vencer
        proximas = self.request.query_params.get('proximas', None)
        if proximas == 'true':
            from django.utils import timezone
            from datetime import timedelta
            fecha_limite = timezone.now() + timedelta(days=7)
            queryset = queryset.filter(
                fecha_vencimiento__lte=fecha_limite,
                fecha_vencimiento__gte=timezone.now()
            )
        
        return queryset.distinct().order_by('fecha_vencimiento')
    
    def perform_create(self, serializer):
        """Validar que el usuario puede crear tareas en esa asignatura"""
        asignatura = serializer.validated_data['asignatura']
        user = self.request.user
        
        # Admins y Coordinadores pueden crear en cualquier asignatura
        if user.is_superuser or user.groups.filter(
            name__in=['Administradores', 'Coordinadores Académicos']
        ).exists():
            serializer.save()
            return
        
        # Docentes solo pueden crear en sus asignaturas
        if asignatura.docente_responsable == user:
            serializer.save()
            return
        
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("No tienes permiso para crear tareas en esta asignatura.")
    
    def update(self, request, *args, **kwargs):
        """Validar permisos para editar"""
        tarea = self.get_object()
        user = request.user
        
        # Superuser y Admins siempre pueden editar
        if user.is_superuser or user.groups.filter(name='Administradores').exists():
            return super().update(request, *args, **kwargs)
        
        # Coordinadores pueden editar
        if user.groups.filter(name='Coordinadores Académicos').exists():
            return super().update(request, *args, **kwargs)
        
        # Docente solo puede editar tareas de sus asignaturas
        if tarea.asignatura.docente_responsable == user:
            # Docente no puede cambiar la asignatura
            if 'asignatura' in request.data and request.data['asignatura'] != tarea.asignatura.id:
                return Response(
                    {'detail': 'No puedes cambiar la asignatura de la tarea.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            return super().update(request, *args, **kwargs)
        
        return Response(
            {'detail': 'No tienes permiso para editar esta tarea.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    def destroy(self, request, *args, **kwargs):
        """Solo admins y coordinadores pueden eliminar"""
        if not (request.user.is_superuser or request.user.groups.filter(
            name__in=['Administradores', 'Coordinadores Académicos']
        ).exists()):
            return Response(
                {'detail': 'Solo administradores y coordinadores pueden eliminar tareas.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def entregas(self, request, pk=None):
        """Listar entregas de una tarea"""
        tarea = self.get_object()
        user = request.user
        
        # Verificar permisos: docente de la asignatura, admin o coordinador
        if not (user.is_superuser or 
                user.groups.filter(name__in=['Administradores', 'Coordinadores Académicos']).exists() or
                tarea.asignatura.docente_responsable == user):
            return Response(
                {'detail': 'No tienes permiso para ver las entregas de esta tarea.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from .models import EntregaTarea
        entregas = EntregaTarea.objects.filter(
            tarea=tarea,
            is_active=True
        ).select_related('estudiante')
        
        entregas_data = [{
            'id': entrega.id,
            'estudiante': entrega.estudiante.get_full_name(),
            'estudiante_correo': entrega.estudiante.correo,
            'fecha_entrega': entrega.created_at,
            'tiene_archivo': entrega.archivo_entrega is not None,
            'comentario': entrega.comentario_estudiante
        } for entrega in entregas]
        
        return Response({
            'tarea': tarea.titulo,
            'total_entregas': len(entregas_data),
            'total_estudiantes': tarea.asignatura.inscripciones.filter(is_active=True).count(),
            'entregas': entregas_data
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def proximas_vencer(self, request):
        """Obtener tareas próximas a vencer (próximos 7 días)"""
        from django.utils import timezone
        from datetime import timedelta
        
        user = request.user
        fecha_limite = timezone.now() + timedelta(days=7)
        
        queryset = Tarea.objects.filter(
            fecha_vencimiento__lte=fecha_limite,
            fecha_vencimiento__gte=timezone.now(),
            is_active=True
        )
        
        # Filtrar por rol
        if user.groups.filter(name='Estudiantes').exists():
            queryset = queryset.filter(
                asignatura__inscripciones__estudiante=user,
                asignatura__inscripciones__is_active=True
            )
        elif user.groups.filter(name='Docentes').exists():
            queryset = queryset.filter(asignatura__docente_responsable=user)
        
        serializer = TareaListSerializer(queryset, many=True)
        return Response({
            'total': queryset.count(),
            'tareas': serializer.data
        })
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def estadisticas(self, request, pk=None):
        """Obtener estadísticas de una tarea"""
        tarea = self.get_object()
        user = request.user
        
        # Verificar permisos
        if not (user.is_superuser or 
                user.groups.filter(name__in=['Administradores', 'Coordinadores Académicos']).exists() or
                tarea.asignatura.docente_responsable == user):
            return Response(
                {'detail': 'No tienes permiso para ver estadísticas de esta tarea.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from .models import EntregaTarea, CalificacionTarea
        
        total_estudiantes = tarea.asignatura.inscripciones.filter(is_active=True).count()
        total_entregas = EntregaTarea.objects.filter(tarea=tarea, is_active=True).count()
        total_calificadas = CalificacionTarea.objects.filter(tarea=tarea, is_active=True).count()
        
        calificaciones = CalificacionTarea.objects.filter(tarea=tarea, is_active=True)
        if calificaciones.exists():
            from django.db.models import Avg, Max, Min
            promedio = calificaciones.aggregate(Avg('puntaje_obtenido'))['puntaje_obtenido__avg']
            maxima = calificaciones.aggregate(Max('puntaje_obtenido'))['puntaje_obtenido__max']
            minima = calificaciones.aggregate(Min('puntaje_obtenido'))['puntaje_obtenido__min']
        else:
            promedio = maxima = minima = None
        
        return Response({
            'tarea': tarea.titulo,
            'tipo': tarea.tipo_tarea,
            'peso_porcentual': float(tarea.peso_porcentual),
            'total_estudiantes': total_estudiantes,
            'total_entregas': total_entregas,
            'total_calificadas': total_calificadas,
            'porcentaje_entregado': round((total_entregas / total_estudiantes * 100), 2) if total_estudiantes > 0 else 0,
            'porcentaje_calificado': round((total_calificadas / total_estudiantes * 100), 2) if total_estudiantes > 0 else 0,
            'estadisticas_notas': {
                'promedio': round(float(promedio), 2) if promedio else None,
                'maxima': float(maxima) if maxima else None,
                'minima': float(minima) if minima else None
            }
        })
