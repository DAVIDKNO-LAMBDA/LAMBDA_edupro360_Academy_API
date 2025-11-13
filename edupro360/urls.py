from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    #  Panel de administración
    path("admin/", admin.site.urls),

    #  Autenticación JWT
    # Login: devuelve access + refresh
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    # Refresh: renueva el access token
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    #  Gestión de usuarios y roles (Usuarios/urls.py)
    path("api/", include("Usuarios.urls")),
]