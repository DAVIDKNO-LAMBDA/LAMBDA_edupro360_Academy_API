"""
Script para crear los 4 roles del sistema EduPro 360
Ejecutar con: Get-Content crear_roles.py | python manage.py shell
"""
from Users.models import Role

# Crear rol Administrador
admin_role, created = Role.objects.get_or_create(
    nombre='Administrador',
    defaults={
        'descripcion': 'Administrador con todos los permisos del sistema',
        'puede_crear_asignatura': True,
        'puede_editar_asignatura': True,
        'puede_eliminar_asignatura': True,
        'puede_crear_tarea': True,
        'puede_editar_tarea': True,
        'puede_eliminar_tarea': True,
        'puede_calificar_tarea': True,
        'puede_ver_todas_calificaciones': True,
        'puede_entregar_tarea': False,
        'recibe_notificacion_estado_mensual': True,
    }
)
print(f"{'✅ Creado' if created else '⚠️  Ya existe'}: Rol Administrador")

# Crear rol Coordinador
coord_role, created = Role.objects.get_or_create(
    nombre='Coordinador',
    defaults={
        'descripcion': 'Coordinador académico con permisos de gestión',
        'puede_crear_asignatura': True,
        'puede_editar_asignatura': True,
        'puede_eliminar_asignatura': True,
        'puede_crear_tarea': True,
        'puede_editar_tarea': True,
        'puede_eliminar_tarea': True,
        'puede_calificar_tarea': True,
        'puede_ver_todas_calificaciones': True,
        'puede_entregar_tarea': False,
        'recibe_notificacion_estado_mensual': True,
    }
)
print(f"{'✅ Creado' if created else '⚠️  Ya existe'}: Rol Coordinador")

# Crear rol Docente
docente_role, created = Role.objects.get_or_create(
    nombre='Docente',
    defaults={
        'descripcion': 'Docente con permisos para gestionar sus asignaturas',
        'puede_crear_asignatura': False,
        'puede_editar_asignatura': False,
        'puede_eliminar_asignatura': False,
        'puede_crear_tarea': True,
        'puede_editar_tarea': True,
        'puede_eliminar_tarea': True,
        'puede_calificar_tarea': True,
        'puede_ver_todas_calificaciones': False,
        'puede_entregar_tarea': False,
        'recibe_notificacion_estado_mensual': False,
    }
)
print(f"{'✅ Creado' if created else '⚠️  Ya existe'}: Rol Docente")

# Crear rol Estudiante
estudiante_role, created = Role.objects.get_or_create(
    nombre='Estudiante',
    defaults={
        'descripcion': 'Estudiante con acceso a entregas y consulta de notas',
        'puede_crear_asignatura': False,
        'puede_editar_asignatura': False,
        'puede_eliminar_asignatura': False,
        'puede_crear_tarea': False,
        'puede_editar_tarea': False,
        'puede_eliminar_tarea': False,
        'puede_calificar_tarea': False,
        'puede_ver_todas_calificaciones': False,
        'puede_entregar_tarea': True,
        'recibe_notificacion_estado_mensual': False,
    }
)
print(f"{'✅ Creado' if created else '⚠️  Ya existe'}: Rol Estudiante")

print("\n🎉 Roles configurados exitosamente!")
print("IDs asignados:")
print(f"  - Administrador: {admin_role.id}")
print(f"  - Coordinador: {coord_role.id}")
print(f"  - Docente: {docente_role.id}")
print(f"  - Estudiante: {estudiante_role.id}")
