from rest_framework.routers import DefaultRouter
from .views import PeriodoAcademicoViewSet, AsignaturaViewSet, InscripcionAsignaturaViewSet, TareaViewSet

router = DefaultRouter()
router.register('periodos', PeriodoAcademicoViewSet, basename='periodos')
router.register('asignaturas', AsignaturaViewSet, basename='asignaturas')
router.register('inscripciones', InscripcionAsignaturaViewSet, basename='inscripciones')
router.register('tareas', TareaViewSet, basename='tareas')

urlpatterns = router.urls
