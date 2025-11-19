# 🎓 EduPro 360 – Academic Management API

![Django](https://img.shields.io/badge/Django-5.0-green)
![DRF](https://img.shields.io/badge/DRF-3.14-blue)
![Python](https://img.shields.io/badge/Python-3.8+-yellow)
![License](https://img.shields.io/badge/License-MIT-orange)

## 📋 Descripción del Proyecto

**EduPro 360** es una API REST avanzada desarrollada con Django REST Framework, diseñada para la gestión integral de procesos académicos en instituciones educativas modernas. El proyecto digitaliza, automatiza y optimiza la administración de asignaturas, tareas, calificaciones y reportes institucionales.

### 🎯 Propósito General

- **Centralizar** la información académica (usuarios, asignaturas, tareas y calificaciones)
- **Automatizar** procesos como recordatorios de tareas y reportes mensuales
- **Optimizar** la gestión docente con planes de evaluación ponderados
- **Facilitar** la experiencia del estudiante con acceso estructurado a su progreso
- **Proporcionar** herramientas analíticas para coordinadores

---

## 🏗️ Arquitectura del Proyecto

```
LAMBDA_edupro360_Academy_API/
├── Base/                    # App base con modelos comunes
│   ├── models.py           # BaseModel, DatoArchivo
├── Users/                   # Gestión de usuarios y autenticación
│   ├── models.py           # CustomUser, Role
│   ├── serializers.py      # Serializers de autenticación
│   ├── views.py            # ViewSets de usuarios
│   ├── urls.py             # Rutas de autenticación
│   └── admin.py            # Admin de usuarios
├── Academic/                # Gestión académica
│   ├── models.py           # Asignatura, Tarea, Entrega, Calificacion
│   ├── serializers.py      # Serializers académicos
│   ├── views.py            # ViewSets académicos
│   ├── urls.py             # Rutas académicas
│   └── admin.py            # Admin académico
├── Notifications/           # Sistema de notificaciones (por implementar)
│   └── tasks.py            # Tareas de Celery
├── edupro360/              # Configuración principal
│   ├── settings.py         # Configuración de Django
│   ├── urls.py             # URLs principales
│   ├── celery.py           # Configuración de Celery
│   └── wsgi.py             # WSGI application
├── manage.py               # Comando Django
├── requirements.txt        # Dependencias
├── .env                    # Variables de entorno
├── .env.example            # Ejemplo de configuración
└── README.md               # Este archivo
```

---

## 🚀 Instalación y Configuración

### Prerequisitos

- Python 3.8 o superior
- pip
- Redis (para Celery)
- PostgreSQL (opcional, usa SQLite por defecto)

### Paso 1: Clonar el repositorio

```bash
git clone <repository-url>
cd LAMBDA_edupro360_Academy_API
```

### Paso 2: Crear entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Paso 3: Instalar dependencias

```bash
pip install -r requirements.txt
```

### Paso 4: Configurar variables de entorno

Copia el archivo `.env.example` a `.env` y configura las variables:

```bash
cp .env.example .env
```

Edita el archivo `.env` con tus configuraciones:

```env
SECRET_KEY=tu-clave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=tu-email@gmail.com
EMAIL_HOST_PASSWORD=tu-contraseña-de-aplicacion

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Paso 5: Ejecutar migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

### Paso 6: Crear superusuario

```bash
python manage.py createsuperuser
```

### Paso 7: Ejecutar el servidor

```bash
python manage.py runserver
```

El servidor estará disponible en: `http://localhost:8000`

---

## 📡 Endpoints de la API

### 🔐 Autenticación (`/api/auth/`)

| Método | Endpoint | Descripción | Autenticación |
|--------|----------|-------------|---------------|
| POST | `/api/auth/users/register/` | Registro de usuarios (HU-01) | No |
| POST | `/api/auth/users/login/` | Inicio de sesión (HU-02) | No |
| POST | `/api/auth/users/change_password/` | Cambiar contraseña (HU-03) | Sí |
| POST | `/api/auth/users/password_reset_request/` | Solicitar recuperación (HU-04) | No |
| POST | `/api/auth/users/password_reset_confirm/` | Confirmar recuperación (HU-04) | No |
| GET | `/api/auth/users/me/` | Información del usuario actual | Sí |
| GET/POST | `/api/auth/roles/` | Gestión de roles (HU-05) | Sí |

### 📚 Gestión Académica (`/api/academic/`)

| Método | Endpoint | Descripción | Autenticación |
|--------|----------|-------------|---------------|
| GET/POST | `/api/academic/asignaturas/` | CRUD Asignaturas (HU-06) | Sí |
| GET/POST | `/api/academic/tareas/` | CRUD Tareas (HU-07) | Sí |
| GET/POST | `/api/academic/entregas/` | CRUD Entregas (HU-08) | Sí |
| GET/POST | `/api/academic/calificaciones/` | CRUD Calificaciones (HU-09) | Sí |
| GET | `/api/academic/calificaciones/mis_notas/` | Consultar notas (HU-10) | Sí |

---

## 🔑 Ejemplos de Uso

### Registro de Usuario

```bash
POST /api/auth/users/register/
Content-Type: application/json

{
  "nombre": "Juan",
  "apellido": "Pérez",
  "correo": "juan.perez@example.com",
  "password": "MiPassword123!",
  "password2": "MiPassword123!",
  "rol": 1
}
```

### Login

```bash
POST /api/auth/users/login/
Content-Type: application/json

{
  "correo": "juan.perez@example.com",
  "password": "MiPassword123!"
}
```

**Respuesta:**
```json
{
  "message": "Login exitoso",
  "user": {
    "id": 1,
    "nombre": "Juan",
    "apellido": "Pérez",
    "correo": "juan.perez@example.com"
  },
  "tokens": {
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

### Crear Asignatura

```bash
POST /api/academic/asignaturas/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "nombre": "Matemáticas Avanzadas",
  "codigo": "MAT-401",
  "descripcion": "Curso de matemáticas nivel avanzado",
  "docente_responsable": 1,
  "periodo_academico": "2025-1"
}
```

### Crear Tarea

```bash
POST /api/academic/tareas/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "asignatura": 1,
  "titulo": "Tarea 1: Derivadas",
  "descripcion": "Resolver ejercicios de derivadas",
  "fecha_publicacion": "2025-11-12T10:00:00Z",
  "fecha_vencimiento": "2025-11-20T23:59:59Z",
  "peso_porcentual": 20.00,
  "tipo_tarea": "TAREA"
}
```

### Consultar Mis Notas

```bash
GET /api/academic/calificaciones/mis_notas/
Authorization: Bearer <access_token>
```

---

## 🎭 Roles y Permisos

El sistema implementa un sistema de roles granular con los siguientes permisos:

| Permiso | Administrador | Coordinador | Docente | Estudiante |
|---------|---------------|-------------|---------|------------|
| Crear asignaturas | ✅ | ✅ | ❌ | ❌ |
| Editar asignaturas | ✅ | ✅ | ✅ (propias) | ❌ |
| Crear tareas | ✅ | ✅ | ✅ | ❌ |
| Calificar tareas | ✅ | ✅ | ✅ | ❌ |
| Entregar tareas | ❌ | ❌ | ❌ | ✅ |
| Ver todas las calificaciones | ✅ | ✅ | ✅ (propias) | ✅ (propias) |
| Recibir reporte mensual | ✅ | ✅ | ❌ | ❌ |

---

## 🔄 Celery y Tareas Automáticas

### Configuración de Celery (próximamente)

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery Worker
celery -A edupro360 worker -l info

# Terminal 3: Celery Beat
celery -A edupro360 beat -l info
```

### Tareas Programadas

- **HU-11**: Recordatorios de vencimiento (3 días y 1 día antes)
- **HU-12**: Reporte mensual automático (primer día de cada mes)

---

## 📊 Tecnologías Utilizadas

- **Backend**: Django 5.0 + Django REST Framework 3.14
- **Autenticación**: SimpleJWT
- **Base de datos**: SQLite (desarrollo) / PostgreSQL (producción)
- **Tareas asíncronas**: Celery + Redis
- **Reportes**: Pandas, OpenPyXL, ReportLab
- **Email**: Django Email Backend / SMTP
- **Configuración**: python-dotenv

---

## 📝 Historias de Usuario Implementadas

✅ **HU-01**: Registro de Usuarios  
✅ **HU-02**: Inicio de Sesión  
✅ **HU-03**: Cambio de Contraseña  
✅ **HU-04**: Recuperación de Contraseña  
✅ **HU-05**: Gestión de Roles y Permisos  
✅ **HU-06**: Creación de Asignaturas  
✅ **HU-07**: Creación de Tareas y Exámenes  
✅ **HU-08**: Entrega de Tareas  
✅ **HU-09**: Calificación de Tareas  
✅ **HU-10**: Consulta de Notas  
🚧 **HU-11**: Recordatorios Automáticos (en progreso)  
🚧 **HU-12**: Consolidado Mensual (en progreso)

---

## 🧪 Testing

```bash
# Ejecutar tests
python manage.py test

# Con cobertura
coverage run --source='.' manage.py test
coverage report
```

---

## 📦 Despliegue

### Heroku

```bash
heroku create edupro360-api
heroku addons:create heroku-postgresql:hobby-dev
heroku addons:create heroku-redis:hobby-dev
git push heroku main
heroku run python manage.py migrate
heroku run python manage.py createsuperuser
```

### Docker (próximamente)

```bash
docker-compose up --build
```

---

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver archivo `LICENSE` para más detalles.

---

## 👥 Autores

- **Equipo EduPro 360** - *Desarrollo inicial*

---

## 📞 Soporte

Para soporte, envía un correo a: support@edupro360.com

---

## 🔮 Roadmap

- [ ] Implementar notificaciones push
- [ ] Sistema de inscripción a asignaturas
- [ ] Dashboard con gráficos y estadísticas
- [ ] Exportación de reportes en PDF/Excel
- [ ] Integración con plataformas LMS
- [ ] App móvil con React Native
- [ ] Modo offline con sincronización

---

**🎓 EduPro 360 - Transformando la educación digital**
