"""
Validadores para archivos subidos en entregas de tareas - EduPro 360
Implementa validaciones de seguridad, tipo y tamaño de archivos
"""
import os
import mimetypes
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.conf import settings


class FileValidator:
    """
    Validador personalizado para archivos de entregas de tareas
    """
    
    # Tipos MIME permitidos por categoría
    ALLOWED_MIME_TYPES = {
        # Documentos de texto
        'application/pdf': '.pdf',
        'application/msword': '.doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
        'application/vnd.oasis.opendocument.text': '.odt',
        'text/plain': '.txt',
        'text/rtf': '.rtf',
        
        # Hojas de cálculo
        'application/vnd.ms-excel': '.xls',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
        'application/vnd.oasis.opendocument.spreadsheet': '.ods',
        'text/csv': '.csv',
        
        # Presentaciones
        'application/vnd.ms-powerpoint': '.ppt',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
        'application/vnd.oasis.opendocument.presentation': '.odp',
        
        # Imágenes
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/bmp': '.bmp',
        'image/svg+xml': '.svg',
        
        # Audio/Video (para proyectos multimedia)
        'audio/mpeg': '.mp3',
        'audio/wav': '.wav',
        'video/mp4': '.mp4',
        'video/avi': '.avi',
        
        # Archivos comprimidos
        'application/zip': '.zip',
        'application/x-rar-compressed': '.rar',
        'application/x-7z-compressed': '.7z',
        
        # Código fuente
        'text/x-python': '.py',
        'text/javascript': '.js',
        'text/html': '.html',
        'text/css': '.css',
        'application/json': '.json',
        'text/x-java-source': '.java',
        'text/x-c': '.c',
        'text/x-c++src': '.cpp',
    }
    
    def __init__(self, max_size_mb=50, allowed_extensions=None):
        self.max_size_bytes = max_size_mb * 1024 * 1024  # Convertir MB a bytes
        self.max_size_mb = max_size_mb
        self.allowed_extensions = allowed_extensions or list(self.ALLOWED_MIME_TYPES.values())
    
    def validate_file_size(self, file):
        """Validar tamaño del archivo"""
        if file.size > self.max_size_bytes:
            raise ValidationError(
                f'El archivo es demasiado grande. '
                f'Tamaño actual: {file.size / (1024*1024):.1f}MB. '
                f'Tamaño máximo permitido: {self.max_size_mb}MB.',
                code='file_too_large'
            )
    
    def validate_file_extension(self, file):
        """Validar extensión del archivo"""
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in self.allowed_extensions:
            allowed_list = ', '.join(sorted(self.allowed_extensions))
            raise ValidationError(
                f'Tipo de archivo no permitido: {ext}. '
                f'Extensiones permitidas: {allowed_list}',
                code='invalid_extension'
            )
    
    def validate_file_mime_type(self, file):
        """Validar tipo MIME del archivo usando mimetypes estándar de Python"""
        try:
            # Detectar tipo MIME por extensión
            mime_type, _ = mimetypes.guess_type(file.name)
            
            if mime_type and mime_type not in self.ALLOWED_MIME_TYPES:
                raise ValidationError(
                    f'Tipo de archivo no válido: {mime_type}. '
                    f'Este tipo de archivo no está permitido.',
                    code='invalid_mime_type'
                )
            
            # Validación adicional de contenido para archivos críticos
            self._validate_file_content(file)
                
        except Exception as e:
            # Si no se puede detectar el tipo MIME, validar solo por extensión
            pass
    
    def _validate_file_content(self, file):
        """Validación básica de contenido sin dependencias externas"""
        try:
            file.seek(0)
            header = file.read(512)  # Leer los primeros 512 bytes
            file.seek(0)
            
            # Verificar signatures básicas de archivos
            if file.name.lower().endswith('.pdf'):
                if not header.startswith(b'%PDF'):
                    raise ValidationError(
                        'El archivo no es un PDF válido.',
                        code='invalid_pdf'
                    )
            
            elif file.name.lower().endswith(('.jpg', '.jpeg')):
                if not header.startswith(b'\xff\xd8\xff'):
                    raise ValidationError(
                        'El archivo no es un JPEG válido.',
                        code='invalid_jpeg'
                    )
            
            elif file.name.lower().endswith('.png'):
                if not header.startswith(b'\x89PNG\r\n\x1a\n'):
                    raise ValidationError(
                        'El archivo no es un PNG válido.',
                        code='invalid_png'
                    )
                    
        except Exception:
            # Si hay error en validación de contenido, continuar
            pass
    
    def validate_filename(self, file):
        """Validar nombre del archivo"""
        filename = file.name
        
        # Validar caracteres peligrosos en el nombre
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        if any(char in filename for char in dangerous_chars):
            raise ValidationError(
                'El nombre del archivo contiene caracteres no permitidos. '
                'Evita usar: < > : " | ? * \\ /',
                code='invalid_filename'
            )
        
        # Validar longitud del nombre
        if len(filename) > 255:
            raise ValidationError(
                'El nombre del archivo es demasiado largo (máximo 255 caracteres).',
                code='filename_too_long'
            )
        
        # Validar que no sea un nombre reservado del sistema
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
            'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2',
            'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]
        
        name_without_ext = os.path.splitext(filename)[0].upper()
        if name_without_ext in reserved_names:
            raise ValidationError(
                f'"{filename}" es un nombre de archivo reservado del sistema.',
                code='reserved_filename'
            )
    
    def scan_for_malicious_content(self, file):
        """Escaneo básico de contenido malicioso"""
        try:
            file.seek(0)
            content_sample = file.read(8192).decode('utf-8', errors='ignore').lower()
            file.seek(0)
            
            # Patrones sospechosos básicos
            suspicious_patterns = [
                '<script', 'javascript:', 'vbscript:', 'onload=', 'onerror=',
                'eval(', 'exec(', 'system(', 'shell_exec', 'passthru',
                '<?php', '<%', 'import os', 'subprocess.', '__import__'
            ]
            
            for pattern in suspicious_patterns:
                if pattern in content_sample:
                    raise ValidationError(
                        'El archivo contiene contenido potencialmente peligroso.',
                        code='malicious_content'
                    )
                    
        except UnicodeDecodeError:
            # Archivo binario, no se puede escanear como texto
            pass
        except Exception:
            # Si hay error en el escaneo, continuar (no bloquear por esto)
            pass
    
    def validate(self, file):
        """Ejecutar todas las validaciones"""
        if not file:
            return
        
        # Validaciones básicas
        self.validate_file_size(file)
        self.validate_filename(file)
        self.validate_file_extension(file)
        
        # Validaciones avanzadas
        self.validate_file_mime_type(file)
        
        self.scan_for_malicious_content(file)


def validate_entrega_file(file):
    """
    Función principal para validar archivos de entregas de tareas
    """
    validator = FileValidator(
        max_size_mb=getattr(settings, 'MAX_ENTREGA_FILE_SIZE_MB', 50),
        allowed_extensions=getattr(settings, 'ALLOWED_ENTREGA_EXTENSIONS', None)
    )
    validator.validate(file)


# Configuraciones para settings.py
ENTREGA_FILE_SETTINGS = {
    'MAX_ENTREGA_FILE_SIZE_MB': 50,  # 50 MB máximo por archivo
    'ALLOWED_ENTREGA_EXTENSIONS': [
        # Documentos
        '.pdf', '.doc', '.docx', '.odt', '.txt', '.rtf',
        # Hojas de cálculo
        '.xls', '.xlsx', '.ods', '.csv',
        # Presentaciones
        '.ppt', '.pptx', '.odp',
        # Imágenes
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg',
        # Archivos comprimidos
        '.zip', '.rar', '.7z',
        # Código fuente
        '.py', '.js', '.html', '.css', '.json', '.java', '.c', '.cpp',
        # Multimedia (limitado)
        '.mp3', '.wav', '.mp4'
    ]
}