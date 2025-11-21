from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .models import PeriodoAcademico, Asignatura, InscripcionAsignatura, Tarea, EntregaTarea, CalificacionTarea
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
        
        return queryset.distinct().order_by('-creado')
    
    def perform_create(self, serializer):
        """Crear asignatura con validaciones y notificación al docente"""
        asignatura = serializer.save()
        
        # Notificar al docente asignado (HU-06)
        self._notificar_docente_asignacion(asignatura)
    
    def perform_update(self, serializer):
        """Actualizar asignatura y notificar si cambia el docente"""
        old_docente = self.get_object().docente_responsable
        asignatura = serializer.save()
        
        # Si cambió el docente, notificar al nuevo
        if old_docente != asignatura.docente_responsable:
            self._notificar_docente_asignacion(asignatura)
    
    def _notificar_docente_asignacion(self, asignatura):
        """Enviar notificación al docente sobre asignación"""
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings
        
        try:
            contexto = {
                'docente': asignatura.docente_responsable,
                'asignatura': asignatura,
                'periodo': asignatura.periodo_academico,
                'fecha_asignacion': asignatura.modificado
            }
            
            asunto = f"📚 Nueva Asignación: {asignatura.nombre}"
            mensaje_html = render_to_string('academico/asignacion_docente.html', contexto)
            
            send_mail(
                subject=asunto,
                message='',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[asignatura.docente_responsable.correo],
                html_message=mensaje_html,
                fail_silently=True
            )
        except Exception as e:
            # Log del error pero no interrumpir el proceso
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error enviando notificación de asignación: {str(e)}")
    
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
        """Validar que el usuario puede crear tareas en esa asignatura y notificar estudiantes"""
        asignatura = serializer.validated_data['asignatura']
        user = self.request.user
        
        # Admins y Coordinadores pueden crear en cualquier asignatura
        if user.is_superuser or user.groups.filter(
            name__in=['Administradores', 'Coordinadores Académicos']
        ).exists():
            tarea = serializer.save()
            self._notificar_nueva_tarea(tarea)
            return
        
        # Docentes solo pueden crear en sus asignaturas
        if asignatura.docente_responsable == user:
            tarea = serializer.save()
            self._notificar_nueva_tarea(tarea)
            return
        
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("No tienes permiso para crear tareas en esta asignatura.")
    
    def _notificar_nueva_tarea(self, tarea):
        """Notificar a estudiantes inscritos sobre nueva tarea (HU-07)"""
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings
        from Usuarios.models import Usuario
        
        try:
            # Obtener estudiantes inscritos en la asignatura
            estudiantes = Usuario.objects.filter(
                inscripciones_asignaturas__asignatura=tarea.asignatura,
                inscripciones_asignaturas__estado=True,
                groups__name='Estudiantes',
                is_active=True
            ).distinct()
            
            for estudiante in estudiantes:
                contexto = {
                    'estudiante': estudiante,
                    'tarea': tarea,
                    'asignatura': tarea.asignatura,
                    'docente': tarea.asignatura.docente_responsable,
                    'dias_restantes': (tarea.fecha_vencimiento - tarea.fecha_publicacion).days
                }
                
                asunto = f"📋 Nueva Tarea: {tarea.titulo} - {tarea.asignatura.nombre}"
                mensaje_html = render_to_string('academico/nueva_tarea.html', contexto)
                
                send_mail(
                    subject=asunto,
                    message='',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[estudiante.correo],
                    html_message=mensaje_html,
                    fail_silently=True
                )
        except Exception as e:
            # Log del error pero no interrumpir el proceso
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error enviando notificación de nueva tarea: {str(e)}")
    
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
            'fecha_entrega': entrega.creado,
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


class EntregaTareaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Entregas de Tareas
    
    Permisos:
    - Crear/Editar: Estudiantes (solo sus propias entregas)
    - Ver: Estudiantes (sus entregas), Docentes (entregas de sus asignaturas), Admins
    - Eliminar: Estudiantes (sus entregas antes del vencimiento), Admins
    """
    queryset = EntregaTarea.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Usar serializer simplificado para listar"""
        from .serializers import EntregaTareaSerializer, EntregaTareaListSerializer
        if self.action == 'list':
            return EntregaTareaListSerializer
        return EntregaTareaSerializer
    
    def get_queryset(self):
        """Filtrar entregas según el usuario"""
        user = self.request.user
        queryset = EntregaTarea.objects.select_related(
            'tarea__asignatura', 'estudiante'
        )
        
        # Estudiantes solo ven sus propias entregas
        if user.groups.filter(name='Estudiantes').exists():
            queryset = queryset.filter(estudiante=user)
        
        # Docentes ven entregas de sus asignaturas
        elif user.groups.filter(name='Docentes').exists():
            queryset = queryset.filter(tarea__asignatura__docente_responsable=user)
        
        # Filtros opcionales
        tarea_id = self.request.query_params.get('tarea', None)
        if tarea_id:
            queryset = queryset.filter(tarea_id=tarea_id)
        
        estudiante_id = self.request.query_params.get('estudiante', None)
        if estudiante_id:
            queryset = queryset.filter(estudiante_id=estudiante_id)
        
        estado = self.request.query_params.get('estado', None)
        if estado:
            queryset = queryset.filter(estado_entrega=estado)
        
        return queryset.filter(estado=True).order_by('-creado')
    
    def perform_create(self, serializer):
        """Crear entrega con validaciones y notificaciones"""
        from django.utils import timezone
        from Base.models import DatoArchivo
        
        estudiante = self.request.user
        tarea = serializer.validated_data['tarea']
        archivo_entrega = serializer.validated_data.get('archivo_entrega')
        
        # Determinar estado según fecha de vencimiento
        estado = 'ENTREGADA'
        if timezone.now() > tarea.fecha_vencimiento:
            estado = 'ATRASADA'
        
        # Guardar entrega
        entrega = serializer.save(
            estudiante=estudiante,
            estado_entrega=estado
        )
        
        # Enviar notificación al docente
        try:
            from edupro360.correo import enviar_correo
            docente = tarea.asignatura.docente_responsable
            
            contexto = {
                'docente_nombre': docente.nombres,
                'estudiante_nombre': estudiante.get_full_name(),
                'tarea_titulo': tarea.titulo,
                'asignatura': tarea.asignatura.nombre,
                'fecha_entrega': entrega.creado,
                'estado': estado,
                'tiene_archivo': archivo_entrega is not None
            }
            
            enviar_correo(
                asunto=f"Nueva entrega: {tarea.titulo}",
                plantilla="academico/nueva_entrega.html",
                contexto=contexto,
                destinatarios=[docente.correo]
            )
        except Exception as e:
            # No fallar si el correo falla
            print(f"Error enviando notificación: {e}")
    
    def update(self, request, *args, **kwargs):
        """Validar permisos para editar"""
        entrega = self.get_object()
        user = request.user
        
        # Solo el estudiante dueño puede editar su entrega
        if not (user.is_superuser or 
                user.groups.filter(name__in=['Administradores', 'Coordinadores Académicos']).exists() or
                entrega.estudiante == user):
            return Response(
                {'detail': 'No tienes permiso para editar esta entrega.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validar si la tarea ya fue calificada
        from .models import CalificacionTarea
        if CalificacionTarea.objects.filter(tarea=entrega.tarea, estudiante=entrega.estudiante, is_active=True).exists():
            return Response(
                {'detail': 'No puedes editar una entrega que ya fue calificada.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Validar permisos para eliminar (desactivar)"""
        entrega = self.get_object()
        user = request.user
        
        # Solo admins o el estudiante dueño (antes de calificar) pueden eliminar
        if not (user.is_superuser or 
                user.groups.filter(name__in=['Administradores', 'Coordinadores Académicos']).exists() or
                entrega.estudiante == user):
            return Response(
                {'detail': 'No tienes permiso para eliminar esta entrega.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validar si ya fue calificada
        from .models import CalificacionTarea
        if CalificacionTarea.objects.filter(tarea=entrega.tarea, estudiante=entrega.estudiante, is_active=True).exists():
            return Response(
                {'detail': 'No puedes eliminar una entrega que ya fue calificada.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Soft delete
        entrega.is_active = False
        entrega.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def mis_entregas(self, request):
        """Listar las entregas del estudiante autenticado"""
        user = request.user
        
        if not user.groups.filter(name='Estudiantes').exists():
            return Response(
                {'detail': 'Este endpoint es solo para estudiantes.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        entregas = EntregaTarea.objects.filter(
            estudiante=user,
            is_active=True
        ).select_related('tarea__asignatura')
        
        # Opcional: filtrar por asignatura
        asignatura_id = request.query_params.get('asignatura', None)
        if asignatura_id:
            entregas = entregas.filter(tarea__asignatura_id=asignatura_id)
        
        serializer = self.get_serializer(entregas, many=True)
        return Response({
            'total': entregas.count(),
            'entregas': serializer.data
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def pendientes(self, request):
        """Listar tareas sin entregar del estudiante"""
        user = request.user
        
        if not user.groups.filter(name='Estudiantes').exists():
            return Response(
                {'detail': 'Este endpoint es solo para estudiantes.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from .models import InscripcionAsignatura
        from django.utils import timezone
        
        # Obtener asignaturas del estudiante
        asignaturas_ids = InscripcionAsignatura.objects.filter(
            estudiante=user,
            is_active=True
        ).values_list('asignatura_id', flat=True)
        
        # Tareas de esas asignaturas que no ha entregado
        tareas_sin_entregar = Tarea.objects.filter(
            asignatura_id__in=asignaturas_ids,
            is_active=True
        ).exclude(
            entregas__estudiante=user,
            entregas__is_active=True
        ).select_related('asignatura')
        
        # Separar en pendientes y vencidas
        ahora = timezone.now()
        pendientes = tareas_sin_entregar.filter(fecha_vencimiento__gt=ahora)
        vencidas = tareas_sin_entregar.filter(fecha_vencimiento__lte=ahora)
        
        from .serializers import TareaListSerializer
        
        return Response({
            'pendientes': TareaListSerializer(pendientes, many=True).data,
            'vencidas': TareaListSerializer(vencidas, many=True).data,
            'total_pendientes': pendientes.count(),
            'total_vencidas': vencidas.count()
        })


class CalificacionTareaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar Calificaciones de Tareas
    
    Permisos:
    - Crear/Editar: Docentes (solo sus asignaturas), Admins, Coordinadores
    - Ver: Docentes (sus asignaturas), Estudiantes (sus calificaciones), Admins
    - Eliminar: Solo Admins
    """
    queryset = CalificacionTarea.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Usar serializer simplificado para listar"""
        from .serializers import CalificacionTareaSerializer, CalificacionTareaListSerializer
        if self.action == 'list':
            return CalificacionTareaListSerializer
        return CalificacionTareaSerializer
    
    def get_queryset(self):
        """Filtrar calificaciones según el usuario"""
        user = self.request.user
        queryset = CalificacionTarea.objects.select_related(
            'tarea__asignatura', 'estudiante'
        )
        
        # Estudiantes solo ven sus propias calificaciones
        if user.groups.filter(name='Estudiantes').exists():
            queryset = queryset.filter(estudiante=user)
        
        # Docentes ven calificaciones de sus asignaturas
        elif user.groups.filter(name='Docentes').exists():
            queryset = queryset.filter(tarea__asignatura__docente_responsable=user)
        
        # Filtros opcionales
        tarea_id = self.request.query_params.get('tarea', None)
        if tarea_id:
            queryset = queryset.filter(tarea_id=tarea_id)
        
        asignatura_id = self.request.query_params.get('asignatura', None)
        if asignatura_id:
            queryset = queryset.filter(tarea__asignatura_id=asignatura_id)
        
        estudiante_id = self.request.query_params.get('estudiante', None)
        if estudiante_id:
            queryset = queryset.filter(estudiante_id=estudiante_id)
        
        return queryset.filter(estado=True).order_by('-creado')
    
    def perform_create(self, serializer):
        """Crear calificación con notificación al estudiante"""
        calificacion = serializer.save()
        
        # Enviar notificación al estudiante
        try:
            from edupro360.correo import enviar_correo
            estudiante = calificacion.estudiante
            tarea = calificacion.tarea
            
            contexto = {
                'estudiante_nombre': estudiante.nombres,
                'tarea_titulo': tarea.titulo,
                'asignatura': tarea.asignatura.nombre,
                'nota': float(calificacion.nota),
                'nota_maxima': 5.0,
                'peso_porcentual': float(tarea.peso_porcentual),
                'retroalimentacion': calificacion.retroalimentacion_docente,
                'fecha_calificacion': calificacion.creado,
                'docente_nombre': tarea.asignatura.docente_responsable.get_full_name()
            }
            
            enviar_correo(
                asunto=f"Calificación publicada: {tarea.titulo}",
                plantilla="academico/calificacion_publicada.html",
                contexto=contexto,
                destinatarios=[estudiante.correo]
            )
        except Exception as e:
            # No fallar si el correo falla
            print(f"Error enviando notificación: {e}")
    
    def update(self, request, *args, **kwargs):
        """Validar permisos para editar calificación"""
        calificacion = self.get_object()
        user = request.user
        
        # Solo el docente responsable, admin o coordinador puede editar
        if not (user.is_superuser or 
                user.groups.filter(name__in=['Administradores', 'Coordinadores Académicos']).exists() or
                calificacion.tarea.asignatura.docente_responsable == user):
            return Response(
                {'detail': 'No tienes permiso para editar esta calificación.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Solo admins pueden eliminar calificaciones"""
        user = request.user
        
        if not (user.is_superuser or 
                user.groups.filter(name__in=['Administradores', 'Coordinadores Académicos']).exists()):
            return Response(
                {'detail': 'Solo administradores pueden eliminar calificaciones.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Soft delete
        calificacion = self.get_object()
        calificacion.is_active = False
        calificacion.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def por_asignatura(self, request):
        """Obtener calificaciones agrupadas por asignatura (para docentes)"""
        user = request.user
        asignatura_id = request.query_params.get('asignatura_id')
        
        if not asignatura_id:
            return Response(
                {'detail': 'Parámetro asignatura_id es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            asignatura = Asignatura.objects.get(id=asignatura_id)
        except Asignatura.DoesNotExist:
            return Response(
                {'detail': 'Asignatura no encontrada.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificar permisos
        if not (user.is_superuser or 
                user.groups.filter(name__in=['Administradores', 'Coordinadores Académicos']).exists() or
                asignatura.docente_responsable == user):
            return Response(
                {'detail': 'No tienes permiso para ver estas calificaciones.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Obtener estudiantes inscritos
        from .models import InscripcionAsignatura
        estudiantes = InscripcionAsignatura.objects.filter(
            asignatura=asignatura,
            is_active=True
        ).select_related('estudiante')
        
        resultado = []
        for inscripcion in estudiantes:
            estudiante = inscripcion.estudiante
            calificaciones = CalificacionTarea.objects.filter(
                tarea__asignatura=asignatura,
                estudiante=estudiante,
                is_active=True
            ).select_related('tarea')
            
            # Calcular promedio ponderado
            total_peso = 0
            suma_ponderada = 0
            
            for cal in calificaciones:
                peso = float(cal.tarea.peso_porcentual)
                nota = float(cal.nota)
                suma_ponderada += (nota * peso)
                total_peso += peso
            
            promedio = round(suma_ponderada / total_peso, 2) if total_peso > 0 else 0
            
            from .serializers import CalificacionTareaListSerializer
            resultado.append({
                'estudiante_id': estudiante.id,
                'estudiante_nombre': estudiante.get_full_name(),
                'calificaciones': CalificacionTareaListSerializer(calificaciones, many=True).data,
                'promedio_ponderado': promedio,
                'porcentaje_completado': round((total_peso / 100) * 100, 2) if total_peso <= 100 else 100,
                'total_calificaciones': calificaciones.count()
            })
        
        return Response({
            'asignatura': asignatura.nombre,
            'total_estudiantes': len(resultado),
            'estudiantes': resultado
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def estadisticas_asignatura(self, request):
        """Estadísticas generales de calificaciones por asignatura"""
        user = request.user
        asignatura_id = request.query_params.get('asignatura_id')
        
        if not asignatura_id:
            return Response(
                {'detail': 'Parámetro asignatura_id es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            asignatura = Asignatura.objects.get(id=asignatura_id)
        except Asignatura.DoesNotExist:
            return Response(
                {'detail': 'Asignatura no encontrada.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Verificar permisos
        if not (user.is_superuser or 
                user.groups.filter(name__in=['Administradores', 'Coordinadores Académicos']).exists() or
                asignatura.docente_responsable == user):
            return Response(
                {'detail': 'No tienes permiso para ver estas estadísticas.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Obtener todas las calificaciones de la asignatura
        calificaciones = CalificacionTarea.objects.filter(
            tarea__asignatura=asignatura,
            is_active=True
        )
        
        if not calificaciones.exists():
            return Response({
                'asignatura': asignatura.nombre,
                'mensaje': 'No hay calificaciones aún',
                'estadisticas': None
            })
        
        # Calcular estadísticas
        from django.db.models import Avg, Max, Min, Count
        
        stats = calificaciones.aggregate(
            promedio_general=Avg('nota'),
            nota_maxima=Max('nota'),
            nota_minima=Min('nota'),
            total_calificaciones=Count('id')
        )
        
        # Distribución por rango de notas
        rangos = {
            'excelente': calificaciones.filter(nota__gte=4.5).count(),  # 4.5 - 5.0
            'bueno': calificaciones.filter(nota__gte=4.0, nota__lt=4.5).count(),  # 4.0 - 4.4
            'aceptable': calificaciones.filter(nota__gte=3.0, nota__lt=4.0).count(),  # 3.0 - 3.9
            'deficiente': calificaciones.filter(nota__lt=3.0).count()  # < 3.0
        }
        
        return Response({
            'asignatura': asignatura.nombre,
            'estadisticas': {
                'promedio_general': round(float(stats['promedio_general']), 2),
                'nota_maxima': float(stats['nota_maxima']),
                'nota_minima': float(stats['nota_minima']),
                'total_calificaciones': stats['total_calificaciones'],
                'distribucion': rangos
            }
        })
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='mis-notas')
    def mis_notas(self, request):
        """
        HU-10: Consulta de Notas
        Endpoint para que estudiantes consulten sus calificaciones y promedios
        
        Query params:
        - asignatura: ID de asignatura específica
        - periodo: ID de período académico específico
        """
        user = request.user
        
        # Solo estudiantes pueden usar este endpoint
        if not user.groups.filter(name='Estudiantes').exists():
            return Response(
                {'detail': 'Este endpoint es solo para estudiantes.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Obtener parámetros de filtro
        asignatura_id = request.query_params.get('asignatura')
        periodo_id = request.query_params.get('periodo')
        
        # Obtener asignaturas del estudiante
        from .models import InscripcionAsignatura
        inscripciones = InscripcionAsignatura.objects.filter(
            estudiante=user,
            estado=True
        ).select_related('asignatura__periodo_academico', 'asignatura__docente_responsable')
        
        # Aplicar filtros
        if asignatura_id:
            inscripciones = inscripciones.filter(asignatura_id=asignatura_id)
        
        if periodo_id:
            inscripciones = inscripciones.filter(asignatura__periodo_academico_id=periodo_id)
        
        resultado_asignaturas = []
        promedio_general_estudiante = 0
        total_creditos = 0
        
        for inscripcion in inscripciones:
            asignatura = inscripcion.asignatura
            
            # Obtener calificaciones del estudiante para esta asignatura
            calificaciones = CalificacionTarea.objects.filter(
                tarea__asignatura=asignatura,
                estudiante=user,
                estado=True
            ).select_related('tarea').order_by('tarea__fecha_vencimiento')
            
            # Obtener todas las tareas de la asignatura para ver progreso
            tareas_asignatura = Tarea.objects.filter(
                asignatura=asignatura,
                estado=True
            )
            
            # Calcular promedio ponderado de la asignatura
            total_peso_calificado = 0
            suma_ponderada = 0
            tareas_detalle = []
            
            for tarea in tareas_asignatura:
                calificacion = calificaciones.filter(tarea=tarea).first()
                
                tarea_info = {
                    'id': tarea.id,
                    'titulo': tarea.titulo,
                    'tipo_tarea': tarea.tipo_tarea,
                    'peso_porcentual': float(tarea.peso_porcentual),
                    'fecha_vencimiento': tarea.fecha_vencimiento,
                    'calificada': False,
                    'nota': None,
                    'retroalimentacion': None,
                    'fecha_calificacion': None,
                    'puntos_obtenidos': 0
                }
                
                if calificacion:
                    peso = float(tarea.peso_porcentual)
                    nota = float(calificacion.nota)
                    puntos = (nota * peso) / 100
                    
                    tarea_info.update({
                        'calificada': True,
                        'nota': nota,
                        'retroalimentacion': calificacion.retroalimentacion_docente,
                        'fecha_calificacion': calificacion.creado,
                        'puntos_obtenidos': round(puntos, 2)
                    })
                    
                    suma_ponderada += (nota * peso)
                    total_peso_calificado += peso
                
                tareas_detalle.append(tarea_info)
            
            # Calcular promedio y porcentaje completado
            promedio_asignatura = 0
            porcentaje_completado = 0
            
            if total_peso_calificado > 0:
                promedio_asignatura = round(suma_ponderada / total_peso_calificado, 2)
                porcentaje_completado = round(total_peso_calificado, 2)
            
            # Información de la asignatura
            asignatura_info = {
                'id': asignatura.id,
                'nombre': asignatura.nombre,
                'codigo': asignatura.codigo,
                'docente': asignatura.docente_responsable.get_full_name(),
                'periodo': {
                    'id': asignatura.periodo_academico.id,
                    'nombre': asignatura.periodo_academico.nombre,
                    'codigo': asignatura.periodo_academico.codigo
                },
                'tareas': tareas_detalle,
                'resumen': {
                    'total_tareas': tareas_asignatura.count(),
                    'tareas_calificadas': calificaciones.count(),
                    'promedio_actual': promedio_asignatura,
                    'porcentaje_completado': porcentaje_completado,
                    'puntos_obtenidos': round(suma_ponderada / 100, 2) if suma_ponderada > 0 else 0,
                    'puntos_posibles': round(porcentaje_completado / 100, 2)
                }
            }
            
            resultado_asignaturas.append(asignatura_info)
            
            # Acumular para promedio general (usando peso igual para todas las asignaturas)
            if promedio_asignatura > 0:
                promedio_general_estudiante += promedio_asignatura
                total_creditos += 1
        
        # Calcular promedio general del estudiante
        promedio_general = 0
        if total_creditos > 0:
            promedio_general = round(promedio_general_estudiante / total_creditos, 2)
        
        # Estadísticas generales
        total_asignaturas = len(resultado_asignaturas)
        asignaturas_con_calificaciones = sum(1 for a in resultado_asignaturas if a['resumen']['tareas_calificadas'] > 0)
        total_tareas_todas = sum(a['resumen']['total_tareas'] for a in resultado_asignaturas)
        total_tareas_calificadas = sum(a['resumen']['tareas_calificadas'] for a in resultado_asignaturas)
        
        return Response({
            'estudiante': {
                'id': user.id,
                'nombre': user.get_full_name(),
                'correo': user.correo
            },
            'resumen_general': {
                'promedio_general': promedio_general,
                'total_asignaturas': total_asignaturas,
                'asignaturas_con_calificaciones': asignaturas_con_calificaciones,
                'total_tareas': total_tareas_todas,
                'tareas_calificadas': total_tareas_calificadas,
                'porcentaje_progreso': round((total_tareas_calificadas / total_tareas_todas * 100), 2) if total_tareas_todas > 0 else 0
            },
            'asignaturas': resultado_asignaturas,
            'filtros_aplicados': {
                'asignatura_id': asignatura_id,
                'periodo_id': periodo_id
            }
        })
