from rest_framework.routers import DefaultRouter
from .views import UsuarioViewSet, GroupViewSet

router = DefaultRouter()
router.register("usuarios", UsuarioViewSet, basename="usuarios")
router.register("roles", GroupViewSet, basename="roles")

urlpatterns = router.urls
