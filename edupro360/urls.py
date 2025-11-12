"""
URL configuration for edupro360 project.

EduPro 360 - Academic Management API
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API v1
    path('api/auth/', include('Users.urls')),
    path('api/academic/', include('Academic.urls')),
    
    # JWT Token Refresh
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

# Servir archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Personalizar el admin
admin.site.site_header = "EduPro 360 - Administración"
admin.site.site_title = "EduPro 360"
admin.site.index_title = "Panel de Administración"

