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
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
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
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_total_tareas(self, obj):
        """Obtener total de tareas de la asignatura"""
        return obj.tareas.filter(is_active=True).count()
    
    def get_total_estudiantes(self, obj):
        """Obtener total de estudiantes inscritos"""
        return obj.inscripciones.filter(is_active=True).count()
    
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
        if not value.is_active:
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
            'is_active', 'created_at'
        ]
        read_only_fields = ['fecha_inscripcion', 'created_at']
    
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
                is_active=True
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
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_total_entregas(self, obj):
        """Obtener total de entregas de la tarea"""
        return obj.entregas.filter(is_active=True).count()
    
    def get_total_estudiantes(self, obj):
        """Obtener total de estudiantes inscritos en la asignatura"""
        return obj.asignatura.inscripciones.filter(is_active=True).count()
    
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
                is_active=True
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
        if not value.is_active:
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
            'fecha_vencimiento', 'peso_porcentual', 'is_active'
        ]
