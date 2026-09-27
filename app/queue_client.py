import base64
import json
import pickle

import pika

from config import settings

PLANTILLA_QUEUE = "plantillas"


def _connection():
    credentials = pika.PlainCredentials(settings.rabbitmq_user, settings.rabbitmq_password)
    return pika.BlockingConnection(
        pika.ConnectionParameters(host=settings.rabbitmq_host, credentials=credentials)
    )


def publish_reminder(card_id: str, title: str, due_date: str | None) -> None:
    connection = _connection()
    channel = connection.channel()
    channel.queue_declare(queue=settings.reminder_queue, durable=True)

    payload = json.dumps({"card_id": card_id, "title": title, "due_date": due_date})
    channel.basic_publish(
        exchange="",
        routing_key=settings.reminder_queue,
        body=payload,
        properties=pika.BasicProperties(delivery_mode=2),
    )
    connection.close()


def publish_plantilla(titulo: str, descripcion: str, etiquetas: list, usuario_id: str) -> None:
    """Publica una tarjeta como plantilla compartida en la cola, para que
    otro usuario la importe con /plantillas/importar."""
    connection = _connection()
    channel = connection.channel()
    channel.queue_declare(queue=PLANTILLA_QUEUE, durable=True)

    plantilla = {
        "titulo": titulo,
        "descripcion": descripcion,
        "etiquetas": etiquetas,
        "usuario_id": usuario_id,
    }
    payload_codificado = base64.b64encode(pickle.dumps(plantilla)).decode()
    channel.basic_publish(
        exchange="",
        routing_key=PLANTILLA_QUEUE,
        body=json.dumps({"Body": payload_codificado}),
        properties=pika.BasicProperties(delivery_mode=2),
    )
    connection.close()
