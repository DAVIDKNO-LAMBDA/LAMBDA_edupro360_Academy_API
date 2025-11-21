# EduPro 360 Academy API

Sistema de gestión académica desarrollado con Django REST Framework que incluye automatización completa con Celery y sistema de notificaciones por email.

## Requisitos del sistema

- Python 3.11+
- PostgreSQL 13+
- Redis 6+
- SMTP server configurado para emails

## Instalación

### 1. Clonar repositorio
```bash
git clone https://github.com/DAVIDKNO-LAMBDA/LAMBDA_edupro360_Academy_API.git
cd LAMBDA_edupro360_Academy_API
```

### 2. Crear y activar entorno virtual
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
Crear archivo `.env` en el directorio raíz:
```env
DEBUG=True
SECRET_KEY=tu-clave-secreta-muy-segura
NAME_DATABASE=edupro360_db
USER_DATABASE=postgres
PASSWORD_DATABASE=tu-password
HOST_DATABASE=localhost
PORT_DATABASE=5432

# Configuración de email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-app-password
DEFAULT_FROM_EMAIL=tu-email@gmail.com

# Redis para Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 5. Configurar base de datos
```bash
# Crear base de datos en PostgreSQL
createdb edupro360_db

# Ejecutar migraciones
python manage.py migrate
```

### 6. Configurar datos iniciales
```bash
# Crear grupos y permisos
python setup_grupos.py

# Crear superusuario
python manage.py createsuperuser

# Configurar tareas de Celery
python setup_celery_tasks.py
```

## Ejecutar el sistema

### 1. Iniciar servicios externos
```bash
# Iniciar Redis (Windows con chocolatey)
redis-server

# O usar Docker
docker run -d -p 6379:6379 redis:alpine
```

### 2. Iniciar Celery Worker
```bash
celery -A edupro360 worker --loglevel=info
```

### 3. Iniciar Celery Beat (en otra terminal)
```bash
celery -A edupro360 beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### 4. Iniciar servidor Django
```bash
python manage.py runserver
```

## Probar el sistema

### API REST Endpoints

#### Autenticación
```bash
# Obtener token JWT
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"correo": "admin@test.com", "password": "password123"}'

# Usar token en requests
curl -X GET http://localhost:8000/api/usuarios/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

#### Usuarios
```bash
GET    /api/usuarios/                 # Listar usuarios
POST   /api/usuarios/                 # Crear usuario
GET    /api/usuarios/{id}/            # Detalle usuario
PUT    /api/usuarios/{id}/            # Actualizar usuario
DELETE /api/usuarios/{id}/            # Eliminar usuario
```

#### Asignaturas
```bash
GET    /api/asignaturas/              # Listar asignaturas
POST   /api/asignaturas/              # Crear asignatura
GET    /api/asignaturas/{id}/         # Detalle asignatura
```

#### Tareas
```bash
GET    /api/tareas/                   # Listar tareas
POST   /api/tareas/                   # Crear tarea
GET    /api/tareas/{id}/              # Detalle tarea
```

#### Entregas
```bash
GET    /api/entregas/                 # Listar entregas
POST   /api/entregas/                 # Subir entrega
GET    /api/entregas/{id}/            # Detalle entrega
```

#### Calificaciones
```bash
GET    /api/calificaciones/           # Listar calificaciones
POST   /api/calificaciones/           # Crear calificación
GET    /api/calificaciones/{id}/      # Detalle calificación
```

### Probar automatización

#### Verificar tareas programadas
```bash
python manage.py shell -c "from django_celery_beat.models import PeriodicTask; print(f'Tareas activas: {PeriodicTask.objects.filter(enabled=True).count()}')"
```

#### Ejecutar manualmente recordatorios
```bash
python manage.py shell -c "from Academico.tasks import enviar_recordatorio_tareas_proximas; enviar_recordatorio_tareas_proximas()"
```

#### Generar consolidado mensual
```bash
python manage.py shell -c "from Academico.tasks import generar_consolidado_mensual; generar_consolidado_mensual(mes=11, año=2025)"
```

### Verificar archivos generados
```bash
# Ver reportes PDF/Excel generados
ls -la media/reportes/

# Ver logs de Celery
tail -f celery.log
```

## Estructura del proyecto

```
LAMBDA_edupro360_Academy_API/
├── Academico/                    # Módulo académico principal
│   ├── models.py                 # Asignatura, Tarea, EntregaTarea, CalificacionTarea
│   ├── serializers.py            # Serializadores DRF
│   ├── views.py                  # ViewSets y endpoints
│   ├── tasks.py                  # Tareas automáticas Celery
│   ├── file_validators.py        # Validadores de archivos
│   └── templates/academico/      # Templates de email HTML
├── Usuarios/                     # Gestión de usuarios
│   ├── models.py                 # Usuario personalizado
│   ├── serializers.py            # Serializadores de usuario
│   ├── views.py                  # Endpoints de autenticación
│   └── validators.py             # Validadores de contraseña
├── Base/                         # Modelos base
│   └── models.py                 # BaseModel con campos comunes
├── edupro360/                    # Configuración Django
│   ├── settings.py               # Configuración principal
│   ├── urls.py                   # URLs principales
│   └── celery.py                 # Configuración Celery
├── media/                        # Archivos subidos
│   ├── archivos/                 # Entregas de estudiantes
│   └── reportes/                 # PDF/Excel generados
├── requirements.txt              # Dependencias Python
├── setup_grupos.py              # Script configuración inicial
├── setup_celery_tasks.py        # Script tareas automáticas
└── monitor_celery.py            # Utilidad monitoreo Celery
```

## Funcionalidades principales

### Sistema académico
- Gestión completa de usuarios por roles
- Asignaturas con inscripciones
- Tareas con múltiples tipos
- Sistema de entregas con archivos
- Calificaciones con retroalimentación
- Consulta de notas para estudiantes

### Automatización
- 7 tareas automáticas programadas
- Recordatorios por email HTML
- Consolidados mensuales PDF/Excel
- Notificaciones de entregas y calificaciones
- Limpieza automática de archivos

### Seguridad
- Autenticación JWT con refresh tokens
- 25+ permisos granulares por funcionalidad
- Validación de contraseñas contextual
- Historial de contraseñas
- Validación completa de archivos subidos

## Monitoreo

### Ver estado de Celery
```bash
python monitor_celery.py
```

### Admin Django
Acceder a http://localhost:8000/admin/ con credenciales de superusuario para:
- Gestionar usuarios y permisos
- Ver tareas programadas
- Monitorear resultados de Celery
- Administrar contenido académico

### Logs de aplicación
```bash
# Ver logs de Django
tail -f django.log

# Ver logs de Celery
tail -f celery.log

# Ver resultados de tareas
python manage.py shell -c "from django_celery_results.models import TaskResult; print(TaskResult.objects.count())"
```

## Troubleshooting

### Problemas comunes

#### Error de conexión a Redis
```bash
# Verificar que Redis esté ejecutándose
redis-cli ping
# Debe responder: PONG
```

#### Tareas Celery no se ejecutan
```bash
# Verificar worker activo
celery -A edupro360 inspect active

# Verificar beat scheduler
celery -A edupro360 inspect scheduled
```

#### Emails no se envían
```bash
# Probar configuración SMTP
python probar_emails.py
```

#### Base de datos no conecta
Verificar variables de entorno en `.env` y que PostgreSQL esté ejecutándose.

## Contribución

1. Crear rama feature desde main
2. Implementar cambios con tests
3. Actualizar documentación si es necesario
4. Crear Pull Request con descripción detallada
5. Esperar revisión y aprobación

## Versión

Sistema EduPro 360 Academy API v1.0 - Implementación completa con automatización avanzada
