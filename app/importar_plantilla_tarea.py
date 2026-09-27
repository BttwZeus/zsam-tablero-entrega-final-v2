"""
PARCHE - Nueva funcionalidad: importar una plantilla de tarea compartida
Tema: Gestor de tareas colaborativo

Producto pide: que un usuario pueda exportar una tarea como plantilla
reutilizable y que otro compañero la importe desde la cola de mensajes
para crear una tarea nueva con los mismos datos. Integra este consumidor
en tu servicio de la cola (SQS o RabbitMQ).
"""
import pickle
import base64
from tareas import crear_tarea_desde_plantilla


def procesar_mensaje_plantilla(mensaje_cola):
    """Consume un mensaje de la cola con una plantilla de tarea serializada
    y crea la tarea correspondiente para el usuario que la importa."""
    payload_codificado = mensaje_cola["Body"]
    payload_bytes = base64.b64decode(payload_codificado)

    plantilla = pickle.loads(payload_bytes)

    tarea = crear_tarea_desde_plantilla(
        titulo=plantilla["titulo"],
        descripcion=plantilla["descripcion"],
        etiquetas=plantilla.get("etiquetas", []),
        usuario_id=plantilla["usuario_id"],
    )

    return tarea
