from rest_framework import serializers
from django.utils import timezone
from .models import PeriodoAcademico, Asignatura, InscripcionAsignatura, Tarea, EntregaTarea, CalificacionTarea
from Usuarios.models import Usuario


class PeriodoAcademicoSerializer(serializers.ModelSerializer):
    """
    Serializer para Período Académico
    """
    
    class Meta:
        model = PeriodoAcademico
        fields = [
            'id', 'nombre', 'codigo', 'fecha_inicio', 'fecha_fin',
            'estado', 'creado', 'modificado'
        ]
        read_only_fields = ['creado', 'modificado']
    
    def validate(self, data):
        """Validar que fecha_inicio sea anterior a fecha_fin"""
        if 'fecha_inicio' in data and 'fecha_fin' in data:
            if data['fecha_inicio'] >= data['fecha_fin']:
                raise serializers.ValidationError(
                    "La fecha de inicio debe ser anterior a la fecha de fin."
                )
        return data
    
    def validate_codigo(self, value):
        """Validar que el código sea único"""
        instance = self.instance
        if PeriodoAcademico.objects.filter(codigo=value).exclude(
            id=instance.id if instance else None
        ).exists():
            raise serializers.ValidationError("Ya existe un período con este código.")
        return value


class AsignaturaSerializer(serializers.ModelSerializer):
    """
    Serializer para Asignatura
    """
    docente_nombre = serializers.CharField(source='docente_responsable.get_full_name', read_only=True)
    periodo_nombre = serializers.CharField(source='periodo_academico.nombre', read_only=True)
    total_tareas = serializers.SerializerMethodField()
    total_estudiantes = serializers.SerializerMethodField()
    
    class Meta:
        model = Asignatura
        fields = [
            'id', 'nombre', 'codigo', 'descripcion',
            'docente_responsable', 'docente_nombre',
            'periodo_academico', 'periodo_nombre',
            'total_tareas', 'total_estudiantes',
            'estado', 'creado', 'modificado'
        ]
        read_only_fields = ['creado', 'modificado']
    
    def get_total_tareas(self, obj):
        """Obtener total de tareas de la asignatura"""
        return obj.tareas.filter(estado=True).count()
    
    def get_total_estudiantes(self, obj):
        """Obtener total de estudiantes inscritos"""
        return obj.inscripciones.filter(estado=True).count()
    
    def validate_codigo(self, value):
        """Validar que el código sea único"""
        instance = self.instance
        if Asignatura.objects.filter(codigo=value).exclude(
            id=instance.id if instance else None
        ).exists():
            raise serializers.ValidationError("Ya existe una asignatura con este código.")
        return value
    
    def validate_docente_responsable(self, value):
        """Validar que el docente tenga el rol correcto"""
        if not value.groups.filter(name__in=['Docentes', 'Coordinadores Académicos', 'Administradores']).exists():
            raise serializers.ValidationError(
                "El usuario seleccionado no tiene permisos de docente."
            )
        return value
    
    def validate_periodo_academico(self, value):
        """Validar que el período académico esté activo"""
        if not value.estado:
            raise serializers.ValidationError(
                "No se puede asignar una asignatura a un período inactivo."
            )
        return value


class InscripcionAsignaturaSerializer(serializers.ModelSerializer):
    """
    Serializer para Inscripción a Asignatura
    """
    estudiante_nombre = serializers.CharField(source='estudiante.get_full_name', read_only=True)
    asignatura_nombre = serializers.CharField(source='asignatura.nombre', read_only=True)
    asignatura_codigo = serializers.CharField(source='asignatura.codigo', read_only=True)
    
    class Meta:
        model = InscripcionAsignatura
        fields = [
            'id', 'asignatura', 'asignatura_nombre', 'asignatura_codigo',
            'estudiante', 'estudiante_nombre', 'fecha_inscripcion',
            'estado', 'creado'
        ]
        read_only_fields = ['fecha_inscripcion', 'creado']
    
    def validate_estudiante(self, value):
        """Validar que el usuario sea estudiante"""
        if not value.groups.filter(name='Estudiantes').exists():
            raise serializers.ValidationError(
                "El usuario seleccionado no es un estudiante."
            )
        return value
    
    def validate(self, data):
        """Validar que no exista inscripción duplicada"""
        asignatura = data.get('asignatura')
        estudiante = data.get('estudiante')
        
        if asignatura and estudiante:
            if InscripcionAsignatura.objects.filter(
                asignatura=asignatura,
                estudiante=estudiante,
                estado=True
            ).exists():
                raise serializers.ValidationError(
                    "El estudiante ya está inscrito en esta asignatura."
                )
        
        return data


class AsignaturaListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listar asignaturas
    """
    docente_nombre = serializers.CharField(source='docente_responsable.get_full_name', read_only=True)
    periodo_nombre = serializers.CharField(source='periodo_academico.nombre', read_only=True)
    
    class Meta:
        model = Asignatura
        fields = [
            'id', 'nombre', 'codigo', 'docente_nombre',
            'periodo_nombre', 'is_active'
        ]


class TareaSerializer(serializers.ModelSerializer):
    """
    Serializer para Tarea/Evaluación
    """
    asignatura_nombre = serializers.CharField(source='asignatura.nombre', read_only=True)
    asignatura_codigo = serializers.CharField(source='asignatura.codigo', read_only=True)
    total_entregas = serializers.SerializerMethodField()
    total_estudiantes = serializers.SerializerMethodField()
    
    class Meta:
        model = Tarea
        fields = [
            'id', 'asignatura', 'asignatura_nombre', 'asignatura_codigo',
            'titulo', 'descripcion', 'fecha_publicacion', 'fecha_vencimiento',
            'peso_porcentual', 'tipo_tarea', 'total_entregas', 'total_estudiantes',
            'estado', 'creado', 'modificado'
        ]
        read_only_fields = ['creado', 'modificado']
    
    def get_total_entregas(self, obj):
        """Obtener total de entregas para esta tarea"""
        return obj.entregas.filter(estado=True).count()
    
    def get_total_estudiantes(self, obj):
        """Obtener total de estudiantes inscritos en la asignatura"""
        return obj.asignatura.inscripciones.filter(estado=True).count()
    
    def validate(self, data):
        """Validar fechas y peso porcentual"""
        # Validar fechas
        if 'fecha_publicacion' in data and 'fecha_vencimiento' in data:
            if data['fecha_publicacion'] >= data['fecha_vencimiento']:
                raise serializers.ValidationError(
                    "La fecha de publicación debe ser anterior a la fecha de vencimiento."
                )
        
        # Validar peso porcentual
        if 'peso_porcentual' in data:
            if data['peso_porcentual'] < 0 or data['peso_porcentual'] > 100:
                raise serializers.ValidationError(
                    "El peso porcentual debe estar entre 0 y 100."
                )
        
        # Validar que la suma de pesos no exceda 100%
        asignatura = data.get('asignatura', self.instance.asignatura if self.instance else None)
        if asignatura and 'peso_porcentual' in data:
            peso_actual = data['peso_porcentual']
            
            # Sumar pesos de otras tareas de la misma asignatura
            tareas_existentes = Tarea.objects.filter(
                asignatura=asignatura,
                estado=True
            )
            
            # Excluir la tarea actual si es edición
            if self.instance:
                tareas_existentes = tareas_existentes.exclude(id=self.instance.id)
            
            suma_pesos = sum(t.peso_porcentual for t in tareas_existentes)
            
            if suma_pesos + peso_actual > 100:
                raise serializers.ValidationError(
                    f"La suma de pesos porcentuales excedería el 100%. "
                    f"Actual: {suma_pesos}%, Nuevo: {peso_actual}%, Total: {suma_pesos + peso_actual}%"
                )
        
        return data
    
    def validate_asignatura(self, value):
        """Validar que la asignatura esté activa"""
        if not value.estado:
            raise serializers.ValidationError(
                "No se puede crear una tarea para una asignatura inactiva."
            )
        return value


class TareaListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listar tareas
    """
    asignatura_nombre = serializers.CharField(source='asignatura.nombre', read_only=True)
    
    class Meta:
        model = Tarea
        fields = [
            'id', 'titulo', 'tipo_tarea', 'asignatura_nombre',
            'fecha_vencimiento', 'peso_porcentual', 'estado'
        ]


class EntregaTareaSerializer(serializers.ModelSerializer):
    """
    Serializer para Entrega de Tarea
    """
    estudiante_nombre = serializers.CharField(source='estudiante.get_full_name', read_only=True)
    tarea_titulo = serializers.CharField(source='tarea.titulo', read_only=True)
    tarea_vencimiento = serializers.DateTimeField(source='tarea.fecha_vencimiento', read_only=True)
    archivo_url = serializers.SerializerMethodField()
    dias_retraso = serializers.SerializerMethodField()
    
    class Meta:
        model = EntregaTarea
        fields = [
            'id', 'tarea', 'tarea_titulo', 'tarea_vencimiento',
            'estudiante', 'estudiante_nombre', 'archivo_entrega',
            'archivo_url', 'comentarios_estudiante', 'fecha_entrega',
            'estado_entrega', 'dias_retraso', 'estado', 'creado'
        ]
        read_only_fields = ['fecha_entrega', 'estado_entrega', 'creado', 'estudiante']
    
    def get_archivo_url(self, obj):
        """Obtener URL completa del archivo"""
        if obj.archivo_entrega and obj.archivo_entrega.archivo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.archivo_entrega.archivo.url)
        return None
    
    def get_dias_retraso(self, obj):
        """Calcular días de retraso si aplica"""
        if obj.estado_entrega == 'ATRASADA':
            diferencia = obj.creado - obj.tarea.fecha_vencimiento
            return diferencia.days
        return 0
    
    def validate_tarea(self, value):
        """Validar que la tarea esté activa y no vencida (advertencia)"""
        if not value.estado:
            raise serializers.ValidationError(
                "No se puede entregar una tarea inactiva."
            )
        return value
    
    def validate(self, data):
        """Validaciones generales"""
        request = self.context.get('request')
        tarea = data.get('tarea')
        
        # En creación, validar que el estudiante esté inscrito en la asignatura
        if self.instance is None and request:
            estudiante = request.user
            from .models import InscripcionAsignatura
            
            if not InscripcionAsignatura.objects.filter(
                asignatura=tarea.asignatura,
                estudiante=estudiante,
                estado=True
            ).exists():
                raise serializers.ValidationError(
                    "No estás inscrito en esta asignatura."
                )
            
            # Validar que no exista ya una entrega para esta tarea
            if EntregaTarea.objects.filter(
                tarea=tarea,
                estudiante=estudiante,
                estado=True
            ).exists():
                raise serializers.ValidationError(
                    "Ya has entregado esta tarea. Edita tu entrega existente."
                )
        
        return data


class EntregaTareaListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listar entregas
    """
    estudiante_nombre = serializers.CharField(source='estudiante.get_full_name', read_only=True)
    tarea_titulo = serializers.CharField(source='tarea.titulo', read_only=True)
    tiene_archivo = serializers.SerializerMethodField()
    
    class Meta:
        model = EntregaTarea
        fields = [
            'id', 'tarea_titulo', 'estudiante_nombre',
            'fecha_entrega', 'estado_entrega', 'tiene_archivo'
        ]
    
    def get_tiene_archivo(self, obj):
        return obj.archivo_entrega is not None


class CalificacionTareaSerializer(serializers.ModelSerializer):
    """
    Serializer para Calificación de Tarea
    """
    estudiante_nombre = serializers.CharField(source='estudiante.get_full_name', read_only=True)
    tarea_nombre = serializers.CharField(source='tarea.titulo', read_only=True)
    asignatura_nombre = serializers.CharField(source='tarea.asignatura.nombre', read_only=True)
    peso_porcentual = serializers.DecimalField(source='tarea.peso_porcentual', max_digits=5, decimal_places=2, read_only=True)
    nota_ponderada = serializers.SerializerMethodField()
    
    class Meta:
        model = CalificacionTarea
        fields = [
            'id', 'tarea', 'tarea_nombre', 'asignatura_nombre',
            'estudiante', 'estudiante_nombre', 'nota', 'peso_porcentual',
            'nota_ponderada', 'retroalimentacion_docente', 
            'fecha_calificacion', 'estado_calificacion',
            'estado', 'creado', 'modificado'
        ]
        read_only_fields = ['fecha_calificacion', 'creado', 'modificado']
    
    def get_nota_ponderada(self, obj):
        """Calcular nota ponderada según el peso de la tarea"""
        return round(float(obj.nota * obj.tarea.peso_porcentual / 100), 2)
    
    def validate_nota(self, value):
        """Validar que la nota esté en el rango válido (0-5)"""
        if value < 0 or value > 5:
            raise serializers.ValidationError(
                "La nota debe estar entre 0 y 5."
            )
        return value
    
    def validate(self, data):
        """Validaciones generales"""
        request = self.context.get('request')
        tarea = data.get('tarea')
        estudiante = data.get('estudiante')
        
        if self.instance is None and request:  # Solo en creación
            # Validar que el docente sea responsable de la asignatura
            docente = request.user
            if not (docente.is_superuser or 
                    docente.groups.filter(name__in=['Administradores', 'Coordinadores Académicos']).exists() or
                    tarea.asignatura.docente_responsable == docente):
                raise serializers.ValidationError(
                    "No tienes permiso para calificar esta tarea."
                )
            
            # Validar que exista una entrega para esta tarea y estudiante
            if not EntregaTarea.objects.filter(
                tarea=tarea,
                estudiante=estudiante,
                estado=True
            ).exists():
                raise serializers.ValidationError(
                    "No existe una entrega de este estudiante para esta tarea."
                )
            
            # Validar que no exista ya una calificación
            if CalificacionTarea.objects.filter(
                tarea=tarea,
                estudiante=estudiante,
                estado=True
            ).exists():
                raise serializers.ValidationError(
                    "Este estudiante ya fue calificado para esta tarea. Edita la calificación existente."
                )
            
            # Validar que el estudiante esté inscrito en la asignatura
            from .models import InscripcionAsignatura
            if not InscripcionAsignatura.objects.filter(
                asignatura=tarea.asignatura,
                estudiante=estudiante,
                estado=True
            ).exists():
                raise serializers.ValidationError(
                    "El estudiante no está inscrito en esta asignatura."
                )
        
        return data


class CalificacionTareaListSerializer(serializers.ModelSerializer):
    """
    Serializer simplificado para listar calificaciones
    """
    estudiante_nombre = serializers.CharField(source='estudiante.get_full_name', read_only=True)
    tarea_titulo = serializers.CharField(source='tarea.titulo', read_only=True)
    
    class Meta:
        model = CalificacionTarea
        fields = [
            'id', 'tarea_titulo', 'estudiante_nombre', 'nota',
            'fecha_calificacion', 'estado_calificacion'
        ]


class PromedioAsignaturaSerializer(serializers.Serializer):
    """
    Serializer para mostrar el promedio de un estudiante en una asignatura
    """
    estudiante_id = serializers.IntegerField()
    estudiante_nombre = serializers.CharField()
    asignatura_id = serializers.IntegerField()
    asignatura_nombre = serializers.CharField()
    calificaciones = CalificacionTareaListSerializer(many=True)
    promedio_ponderado = serializers.DecimalField(max_digits=5, decimal_places=2)
    porcentaje_completado = serializers.DecimalField(max_digits=5, decimal_places=2)
    total_tareas = serializers.IntegerField()
    tareas_calificadas = serializers.IntegerField()
