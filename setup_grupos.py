"""
Script para crear los grupos/roles iniciales del sistema
Ejecutar con: python manage.py shell < setup_grupos.py
"""
from django.contrib.auth.models import Group, Permission

print("🚀 Creando grupos y asignando permisos...\n")

# ============ GRUPO: ADMINISTRADORES ============
print("1️⃣  Creando grupo 'Administradores'...")
grupo_admin, created = Group.objects.get_or_create(name='Administradores')
if created:
    todos_permisos = Permission.objects.all()
    grupo_admin.permissions.set(todos_permisos)
    print(f"   ✅ Creado con {todos_permisos.count()} permisos (TODOS)")
else:
    print("   ⚠️  Ya existe")

# ============ GRUPO: COORDINADORES ACADÉMICOS ============
print("\n2️⃣  Creando grupo 'Coordinadores Académicos'...")
grupo_coord, created = Group.objects.get_or_create(name='Coordinadores Académicos')
if created or True:  # Actualizar permisos siempre
    permisos_coord = Permission.objects.filter(codename__in=[
        # Usuarios
        'gestionar_usuarios',
        
        # Académico
        'gestionar_periodos_academicos',
        'crear_asignatura',
        'editar_asignatura',
        'desactivar_asignatura',
        'asignar_docente_asignatura',
        'ver_asignaturas_campus',
        'gestionar_inscripciones_asignaturas',
        'ver_inscripciones_asignaturas',
        'ver_tareas_asignatura',
        'ver_entregas_asignatura',
        'ver_calificaciones_asignatura',
        
        # Notificaciones
        'recibir_notificacion_estado_mensual',
    ])
    grupo_coord.permissions.set(permisos_coord)
    print(f"   ✅ {'Creado' if created else 'Actualizado'} con {permisos_coord.count()} permisos")
else:
    print("   ⚠️  Ya existe")

# ============ GRUPO: DOCENTES ============
print("\n3️⃣  Creando grupo 'Docentes'...")
grupo_docente, created = Group.objects.get_or_create(name='Docentes')
if created or True:  # Actualizar permisos siempre
    permisos_docente = Permission.objects.filter(codename__in=[
        # Cambiar su propia contraseña
        'cambiar_password_propio',
        
        # Tareas
        'crear_tarea',
        'editar_tarea',
        'eliminar_tarea',
        'publicar_tarea',
        'ver_tareas_asignatura',
        
        # Entregas
        'ver_entregas_asignatura',
        
        # Calificaciones
        'calificar_tarea',
        'editar_calificacion_tarea',
        'ver_calificaciones_asignatura',
    ])
    grupo_docente.permissions.set(permisos_docente)
    print(f"   ✅ {'Creado' if created else 'Actualizado'} con {permisos_docente.count()} permisos")
else:
    print("   ⚠️  Ya existe")

# ============ GRUPO: ESTUDIANTES ============
print("\n4️⃣  Creando grupo 'Estudiantes'...")
grupo_estudiante, created = Group.objects.get_or_create(name='Estudiantes')
if created or True:  # Actualizar permisos siempre
    permisos_estudiante = Permission.objects.filter(codename__in=[
        # Cambiar su propia contraseña
        'cambiar_password_propio',
        
        # Entregas
        'entregar_tarea',
        
        # Calificaciones
        'ver_calificaciones_propias',
    ])
    grupo_estudiante.permissions.set(permisos_estudiante)
    print(f"   ✅ {'Creado' if created else 'Actualizado'} con {permisos_estudiante.count()} permisos")
else:
    print("   ⚠️  Ya existe")

print("\n" + "="*50)
print("✅ Setup de grupos completado!")
print("="*50)
print("\n📋 Resumen:")
print(f"   • Administradores: {grupo_admin.permissions.count()} permisos")
print(f"   • Coordinadores Académicos: {grupo_coord.permissions.count()} permisos")
print(f"   • Docentes: {grupo_docente.permissions.count()} permisos")
print(f"   • Estudiantes: {grupo_estudiante.permissions.count()} permisos")
print("\n🎯 Siguiente paso:")
print("   Crear primer admin: POST /api/usuarios/ con groups:[1]")
