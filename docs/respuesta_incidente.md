# Respuesta al incidente — Entrega Final

Hallazgo: deserialización insegura (CWE-502) en
`app/importar_plantilla_tarea.py` — ver `docs/clasificacion_hallazgo.md` para
el detalle técnico y la justificación de severidad.

## Contención inmediata

Lo que se haría ahora mismo, sin tocar el código, para frenar el riesgo
mientras se prepara el arreglo real:

- **Desactivar el consumidor de la cola `plantillas`** en `worker.py` con una
  bandera de configuración (`PLANTILLAS_HABILITADO`, por defecto `false`),
  de modo que el `worker` deje de registrar el callback
  `_procesar_mensaje_plantilla_cola` hasta que el fix esté desplegado. Los
  mensajes se acumulan en la cola (durable) sin perderse, y sin exponer el
  punto de deserialización.
- Alternativa si no se puede tocar ni siquiera el arranque del worker: cerrar
  el acceso a RabbitMQ desde fuera de la red interna (regla de firewall /
  security group), para que solo la propia API pueda publicar en la cola —
  esto no corrige la causa raíz, solo reduce quién puede llegar a explotarla.

Esto **no corrige nada**, solo detiene el sangrado: el código vulnerable
sigue ahí, simplemente no se ejecuta.

## Prevención (el arreglo real)

Reemplazar `pickle` por un formato de datos que no ejecute código al
deserializar, más validación explícita de esquema:

- Cambiar `pickle.loads(payload_bytes)` por
  `json.loads(payload_bytes.decode("utf-8"))`. JSON no tiene un protocolo de
  reconstrucción de objetos arbitrarios: en el peor caso, un payload
  malformado produce datos basura o un error de parseo, nunca ejecución de
  código.
- Validar explícitamente, antes de usar los datos, que el resultado es un
  `dict` con las claves esperadas (`titulo`, `descripcion`, `usuario_id`) y
  del tipo correcto, y devolver un error controlado si no cumple — en vez de
  dejar que un `KeyError`/`TypeError` tumbe el proceso del worker.
- El productor (`queue_client.publish_plantilla`) se actualizó para publicar
  el mismo formato JSON, así el productor y el consumidor quedan
  consistentes.

Este es el cambio que efectivamente se sube a Producción — ver el commit de
remediación en el historial del repositorio (`app/importar_plantilla_tarea.py`
y `app/queue_client.py`).
