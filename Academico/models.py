
from django.db import models
from Base.models import BaseModel, DatoArchivo
from Usuarios.models import Usuario

class PeriodoAcademico(BaseModel):
	nombre = models.CharField(max_length=100, verbose_name="Nombre del período")
	codigo = models.CharField(max_length=50, unique=True, verbose_name="Código del período")
	fecha_inicio = models.DateField(verbose_name="Fecha de inicio")
	fecha_fin = models.DateField(verbose_name="Fecha de fin")

	class Meta:
		verbose_name = "Período académico"
		verbose_name_plural = "Períodos académicos"
		db_table = "periodos_academicos"
		permissions = [
			("gestionar_periodos_academicos", "Puede gestionar períodos académicos"),
		]

	def __str__(self) -> str:
		return f"{self.nombre} ({self.codigo})"

class Asignatura(BaseModel):
	nombre = models.CharField(max_length=150, verbose_name="Nombre de la asignatura")
	codigo = models.CharField(max_length=50, unique=True, verbose_name="Código de la asignatura")
	descripcion = models.TextField(verbose_name="Descripción", blank=True, null=True)
	docente_responsable = models.ForeignKey(
		Usuario,
		on_delete=models.PROTECT,
		related_name="asignaturas_dictadas",
		verbose_name="Docente responsable",
	)
	periodo_academico = models.ForeignKey(
		PeriodoAcademico,
		on_delete=models.PROTECT,
		related_name="asignaturas",
		verbose_name="Período académico",
	)

	class Meta:
		verbose_name = "Asignatura"
		verbose_name_plural = "Asignaturas"
		db_table = "asignaturas"
		permissions = [
			("crear_asignatura", "Puede crear asignaturas"),
			("editar_asignatura", "Puede editar asignaturas"),
			("desactivar_asignatura", "Puede activar o desactivar asignaturas"),
			("asignar_docente_asignatura", "Puede asignar docentes a asignaturas"),
			("ver_asignaturas_campus", "Puede ver todas las asignaturas del campus"),
		]

	def __str__(self) -> str:
		return f"{self.codigo} - {self.nombre}"

class InscripcionAsignatura(BaseModel):
	asignatura = models.ForeignKey(
		Asignatura,
		on_delete=models.CASCADE,
		related_name="inscripciones",
		verbose_name="Asignatura",
	)
	estudiante = models.ForeignKey(
		Usuario,
		on_delete=models.CASCADE,
		related_name="inscripciones_asignaturas",
		verbose_name="Estudiante",
	)
	fecha_inscripcion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de inscripción")

	class Meta:
		verbose_name = "Inscripción en asignatura"
		verbose_name_plural = "Inscripciones en asignaturas"
		db_table = "inscripciones_asignaturas"
		unique_together = ("asignatura", "estudiante")
		permissions = [
			("gestionar_inscripciones_asignaturas", "Puede gestionar inscripciones en asignaturas"),
			("ver_inscripciones_asignaturas", "Puede ver inscripciones en asignaturas"),
		]

	def __str__(self) -> str:
		return f"{self.estudiante} → {self.asignatura}"

class Tarea(BaseModel):
	TIPO_TAREA_CHOICES = (
		("TAREA", "Tarea"),
		("EXAMEN", "Examen"),
		("QUIZ", "Quiz"),
		("PROYECTO", "Proyecto"),
	)

	asignatura = models.ForeignKey(
		Asignatura,
		on_delete=models.CASCADE,
		related_name="tareas",
		verbose_name="Asignatura",
	)
	titulo = models.CharField(max_length=200, verbose_name="Título")
	descripcion = models.TextField(verbose_name="Descripción", blank=True, null=True)
	fecha_publicacion = models.DateTimeField(verbose_name="Fecha de publicación")
	fecha_vencimiento = models.DateTimeField(verbose_name="Fecha de vencimiento")
	peso_porcentual = models.DecimalField(
		max_digits=5,
		decimal_places=2,
		verbose_name="Peso porcentual",
		help_text="Porcentaje de contribución al promedio final de la asignatura (0–100).",
	)
	tipo_tarea = models.CharField(
		max_length=20,
		choices=TIPO_TAREA_CHOICES,
		default="TAREA",
		verbose_name="Tipo de tarea",
	)

	def clean(self):
		"""Validar que los pesos porcentuales no excedan 100% por asignatura"""
		from django.core.exceptions import ValidationError
		from django.db.models import Sum
		
		# Obtener suma actual de pesos para esta asignatura (excluyendo esta instancia)
		total_peso_actual = Tarea.objects.filter(
			asignatura=self.asignatura,
			estado=True
		).exclude(id=self.id).aggregate(
			total=Sum('peso_porcentual')
		)['total'] or 0
		
		# Validar que no exceda 100%
		nuevo_total = float(total_peso_actual) + float(self.peso_porcentual)
		if nuevo_total > 100:
			raise ValidationError({
				'peso_porcentual': f'El peso porcentual ({self.peso_porcentual}%) excede el límite. '
								 f'Peso actual usado: {total_peso_actual}%. '
								 f'Máximo disponible: {100 - total_peso_actual}%'
			})
		
		# Validar fechas
		if self.fecha_vencimiento <= self.fecha_publicacion:
			raise ValidationError({
				'fecha_vencimiento': 'La fecha de vencimiento debe ser posterior a la fecha de publicación.'
			})

	def save(self, *args, **kwargs):
		self.full_clean()
		super().save(*args, **kwargs)

	class Meta:
		verbose_name = "Tarea / Evaluación"
		verbose_name_plural = "Tareas / Evaluaciones"
		db_table = "tareas"
		ordering = ["fecha_vencimiento"]
		permissions = [
			("crear_tarea", "Puede crear tareas y exámenes"),
			("editar_tarea", "Puede editar tareas y exámenes"),
			("eliminar_tarea", "Puede eliminar tareas y exámenes"),
			("publicar_tarea", "Puede publicar tareas y exámenes a estudiantes"),
			("ver_tareas_asignatura", "Puede ver las tareas de sus asignaturas"),
		]

	def __str__(self) -> str:
		return f"{self.asignatura.codigo} - {self.titulo}"

class EntregaTarea(BaseModel):
	tarea = models.ForeignKey(
		Tarea,
		on_delete=models.CASCADE,
		related_name="entregas",
		verbose_name="Tarea",
	)
	estudiante = models.ForeignKey(
		Usuario,
		on_delete=models.CASCADE,
		related_name="entregas_tareas",
		verbose_name="Estudiante",
	)
	archivo_entrega = models.ForeignKey(
		DatoArchivo,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name="entregas_asociadas",
		verbose_name="Archivo de entrega",
	)
	comentarios_estudiante = models.TextField(
		verbose_name="Comentarios del estudiante",
		blank=True,
		null=True,
	)
	fecha_entrega = models.DateTimeField(verbose_name="Fecha de entrega", auto_now_add=True)
	estado_entrega = models.CharField(
		max_length=50,
		verbose_name="Estado de entrega",
		default="ENTREGADA",
		help_text="Ej: ENTREGADA, ATRASADA, RECHAZADA, PENDIENTE_REVISION",
	)

	class Meta:
		verbose_name = "Entrega de tarea"
		verbose_name_plural = "Entregas de tareas"
		db_table = "entregas_tareas"
		unique_together = ("tarea", "estudiante")
		permissions = [
			("entregar_tarea", "Puede registrar entregas de tareas"),
			("ver_entregas_asignatura", "Puede ver entregas de tareas por asignatura"),
		]

	def __str__(self) -> str:
		return f"{self.estudiante} - {self.tarea}"

class CalificacionTarea(BaseModel):
	tarea = models.ForeignKey(
		Tarea,
		on_delete=models.CASCADE,
		related_name="calificaciones",
		verbose_name="Tarea",
	)
	estudiante = models.ForeignKey(
		Usuario,
		on_delete=models.CASCADE,
		related_name="calificaciones_tareas",
		verbose_name="Estudiante",
	)
	nota = models.DecimalField(
		max_digits=5,
		decimal_places=2,
		verbose_name="Nota",
		help_text="Nota numérica de la entrega.",
	)
	retroalimentacion_docente = models.TextField(
		verbose_name="Retroalimentación del docente",
		blank=True,
		null=True,
	)
	fecha_calificacion = models.DateTimeField(
		verbose_name="Fecha de calificación",
		auto_now_add=True,
	)
	estado_calificacion = models.CharField(
		max_length=50,
		verbose_name="Estado de calificación",
		default="CALIFICADA",
		help_text="Ej: CALIFICADA, REVISIÓN, ANULADA",
	)

	class Meta:
		verbose_name = "Calificación de tarea"
		verbose_name_plural = "Calificaciones de tareas"
		db_table = "calificaciones_tareas"
		unique_together = ("tarea", "estudiante")
		permissions = [
			("calificar_tarea", "Puede calificar tareas de estudiantes"),
			("editar_calificacion_tarea", "Puede editar calificaciones de tareas"),
			("ver_calificaciones_asignatura", "Puede ver calificaciones por asignatura"),
			("ver_calificaciones_propias", "Puede ver sus propias calificaciones"),
		]

	def __str__(self) -> str:
		return f"{self.estudiante} - {self.tarea} ({self.nota})"

# Create your models here.
