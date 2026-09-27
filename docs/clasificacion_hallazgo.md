# Clasificación del hallazgo — Entrega Final

## Dónde está

`app/importar_plantilla_tarea.py`, función `procesar_mensaje_plantilla` (línea 21):

```python
payload_bytes = base64.b64decode(payload_codificado)
plantilla = pickle.loads(payload_bytes)
```

Este código consume un mensaje de la cola `plantillas` (RabbitMQ) — publicado
cuando un usuario exporta una tarjeta como plantilla compartida
(`POST /cards/{id}/exportar-plantilla`, `queue_client.publish_plantilla`) — y
lo deserializa directamente con `pickle.loads()` antes de crear la tarea.

## Tipo

**Deserialización insegura de datos no confiables — CWE-502.**

El único procesamiento que recibe el payload antes de deserializarlo es un
`base64.b64decode`, que es una transformación de codificación, no un control
de seguridad. No hay validación de esquema, firma ni verificación de origen
antes de llamar a `pickle.loads()`.

`pickle` no es un formato de datos: es un protocolo de reconstrucción de
objetos Python. Un payload manipulado puede definir un objeto con
`__reduce__` que, al deserializarse, ejecute cualquier función arbitraria
(p. ej. `os.system`, `subprocess.Popen`) con los privilegios del proceso que
lo procesa — en este caso, el contenedor `worker`, que tiene en su entorno las
credenciales de la base de datos y (potencialmente) de AWS.

## Severidad: **Crítica**

- **Impacto**: ejecución remota de código (RCE) en el proceso `worker`. No es
  una fuga de datos ni un error de lógica — es control total del proceso que
  procesa la cola, con acceso directo a las credenciales de RDS y a las
  variables de entorno de AWS del `.env`.
- **Facilidad de explotación**: cualquier actor capaz de publicar un mensaje
  en la cola `plantillas` (una cuenta comprometida que use el endpoint de
  exportar plantilla, o -en un despliegue real- alguien con acceso a
  RabbitMQ, que en este proyecto corre localmente con credenciales por
  defecto `guest/guest` en desarrollo) puede construir el payload malicioso
  con `pickle.dumps(ObjetoConReduce())` + `base64.b64encode(...)`. No requiere
  ningún conocimiento especial del código de la aplicación, solo del formato
  esperado del mensaje.
- No requiere condiciones de carrera, ni bypass de autenticación adicional
  más allá de poder colocar un mensaje en la cola.

## ¿Falso positivo?

No. Bandit lo marca como `B301` (severidad reportada: MEDIUM, confianza
HIGH). Se confirmó manualmente construyendo un objeto de prueba con
`__reduce__` que, al pasar por `pickle.loads()`, ejecuta código arbitrario en
el momento de la deserialización — no hace falta ninguna otra condición.

Es importante notar que la severidad MEDIUM que le asigna bandit por defecto
**no refleja el impacto real** en este contexto (RCE en un proceso con
credenciales de infraestructura). Por eso el pipeline se ajustó (ver
commit "Cierra hueco en el gate de bandit...") para bloquear cualquier
hallazgo de la categoría `B3xx` (funciones de deserialización/ejecución
peligrosas) sin importar la severidad que bandit le asigne por defecto —
la clasificación de severidad de la herramienta es una entrada, no la
decisión final.
