"""
Nueva funcionalidad: importar una plantilla de tarea compartida
Tema: Gestor de tareas colaborativo

Producto pide: que un usuario pueda exportar una tarea como plantilla
reutilizable y que otro compañero la importe desde la cola de mensajes
para crear una tarea nueva con los mismos datos. Integra este consumidor
en tu servicio de la cola (SQS o RabbitMQ).

Remediado (Entrega Final): la version original deserializaba el payload de
la cola con pickle.loads(), lo que permite ejecucion remota de codigo si el
mensaje es manipulado (CWE-502, ver docs/clasificacion_hallazgo.md). Se
reemplazo por JSON, que no ejecuta codigo al deserializar, mas validacion
explicita del esquema esperado.
"""
import base64
import json
from tareas import crear_tarea_desde_plantilla

CAMPOS_REQUERIDOS = ("titulo", "descripcion", "usuario_id")


class PlantillaInvalida(ValueError):
    """El mensaje de la cola no tiene el formato esperado de una plantilla."""


def _validar_plantilla(plantilla):
    if not isinstance(plantilla, dict):
        raise PlantillaInvalida("El payload de la plantilla debe ser un objeto JSON")

    for campo in CAMPOS_REQUERIDOS:
        if campo not in plantilla or not isinstance(plantilla[campo], str):
            raise PlantillaInvalida(f"Falta el campo '{campo}' o no es un texto")

    etiquetas = plantilla.get("etiquetas", [])
    if not isinstance(etiquetas, list) or not all(isinstance(e, str) for e in etiquetas):
        raise PlantillaInvalida("El campo 'etiquetas' debe ser una lista de textos")


def procesar_mensaje_plantilla(mensaje_cola):
    """Consume un mensaje de la cola con una plantilla de tarea serializada
    y crea la tarea correspondiente para el usuario que la importa."""
    payload_codificado = mensaje_cola["Body"]
    payload_bytes = base64.b64decode(payload_codificado)

    try:
        plantilla = json.loads(payload_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PlantillaInvalida("El payload no es JSON valido") from exc

    _validar_plantilla(plantilla)

    tarea = crear_tarea_desde_plantilla(
        titulo=plantilla["titulo"],
        descripcion=plantilla["descripcion"],
        etiquetas=plantilla.get("etiquetas", []),
        usuario_id=plantilla["usuario_id"],
    )

    return tarea
