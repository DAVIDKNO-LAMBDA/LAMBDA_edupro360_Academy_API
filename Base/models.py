import re
import os
from unidecode import unidecode
from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_delete, pre_save


def normalizar_ruta(ruta):
    """
    Normaliza la ruta eliminando caracteres especiales y convirtiendo a minúsculas.
    """
    ruta = unidecode(ruta)
    ruta = ruta.replace(' ', '-')
    # Eliminar caracteres especiales excepto '-', '/', y '.'
    ruta = re.sub(r'[^a-zA-Z0-9\-\/\.]', '', ruta)
    return ruta


def guardar_archivo(instance, filename):
    """
    Genera la ruta normalizada para guardar el archivo.
    """
    full_path = f"{instance.ruta_archivo}/{filename}"
    normalized_path = normalizar_ruta(full_path)
    return normalized_path


class BaseModel(models.Model):
    """
    Modelo base abstracto que incluye campos comunes para todos los modelos.
    """
    creado = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    modificado = models.DateTimeField(auto_now=True, verbose_name="Fecha de modificación")
    estado = models.BooleanField(default=True, verbose_name="Estado")

    class Meta:
        abstract = True
        
    @property
    def get_estado(self):
        """
        Retorna el estado en formato legible.
        """
        return "Activo" if self.estado else "Inactivo"


class DatoArchivo(BaseModel):
    """
    Modelo para almacenar información sobre los archivos cargados.
    """
    archivo = models.FileField(
        upload_to=guardar_archivo, 
        verbose_name="Archivo", 
        max_length=400
    )
    ruta_archivo = models.TextField(
        verbose_name="Ruta del archivo", 
        null=True, 
        blank=True, 
        default=None
    )
    nombre_archivo = models.TextField(verbose_name="Nombre del archivo")
    url_archivo = models.TextField(
        verbose_name="Url del archivo", 
        null=True, 
        blank=True, 
        default=None
    )
    id_archivo = models.TextField(
        verbose_name="ID del archivo", 
        null=True, 
        blank=True, 
        default=None
    )
    
    class Meta:
        verbose_name = "Archivo"
        verbose_name_plural = "Archivos"
        db_table = "archivos"

    def __str__(self):
        """
        Devuelve el nombre del archivo o la URL si existe.
        """
        if self.url_archivo:
            return f"{self.id_archivo} - {self.url_archivo}"
        else:
            return self.ruta_archivo


@receiver(post_delete, sender=DatoArchivo)
def borrar_archivo(sender, instance, **kwargs):
    """
    Borra el archivo físico cuando el objeto DatoArchivo se elimina de la base de datos.
    """
    if instance.archivo:
        if os.path.isfile(instance.archivo.path):
            os.remove(instance.archivo.path)


@receiver(pre_save, sender=DatoArchivo)
def actualizar_archivo(sender, instance, **kwargs):
    """
    Actualiza el archivo cuando el objeto DatoArchivo se modifica. 
    Elimina el archivo anterior si cambia.
    """
    if not instance.pk:
        return False

    try:
        old_file = DatoArchivo.objects.get(pk=instance.pk).archivo
    except DatoArchivo.DoesNotExist:
        return False

    new_file = instance.archivo
    if not old_file == new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)

