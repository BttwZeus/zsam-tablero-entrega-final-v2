# Declaracion de uso de inteligencia artificial

Las Notas de Ensenanza del curso permiten usar IA como apoyo, no como
sustituto. Esta declaracion es obligatoria y forma parte de la entrega.

## Que genere con ayuda de IA

| Parte del proyecto | Herramienta de IA | Que le pedi | Que cambie yo despues |
|---|---|---|---|
| Backend FastAPI (`app/main.py`, `app/models.py`, `app/auth.py`, `app/queue_client.py`, `app/worker.py`, `app/storage.py`) | Asistente de IA (chat de codigo) | Construir un gestor de tareas colaborativo en FastAPI con registro/login, tableros/tarjetas, un worker de RabbitMQ desacoplado y adjuntos en S3, para el tema 5 del reto. | Revise cada endpoint contra los requisitos del reto (auth por token, `/salud`, cero credenciales en codigo). Probe el flujo completo end-to-end con `docker compose up` y `curl` real: registro, login, creacion de tablero, creacion de tarjeta y verifique en los logs del worker que el recordatorio si se proceso y se guardo. |
| `docker-compose.yml` y `Dockerfile` | Asistente de IA (chat de codigo) | Definir los servicios (api, worker, db, rabbitmq) con healthchecks y un Dockerfile endurecido. | Corri `docker compose up --build` localmente, encontre y corregi dos fallas reales: faltaba `email-validator` como dependencia de Pydantic (el contenedor `api` truncaba sin arrancar) y un conflicto de version entre `passlib` y `bcrypt` >= 4.1 que rompia el hash de contrasenas al registrar un usuario (ver seccion siguiente). |
| `infra/main.tf` | Asistente de IA (chat de codigo) | Escribir el Terraform del bucket S3 y la RDS con acceso privado y cifrado. | Corri `checkov` contra el `.tf` real, revise cada uno de los 16 hallazgos iniciales uno por uno, aplique 3 correcciones gratuitas (quitar el egress abierto 0.0.0.0/0 que no se necesitaba, activar `auto_minor_version_upgrade` y `copy_tags_to_snapshot`) y decidi explicitamente excluir el resto por ser controles de alta disponibilidad fuera de alcance de un Learner Lab (justificado en `docs/tabla_decisiones_pipeline.md`). |
| `pipeline/run_pipeline.sh` | Asistente de IA (chat de codigo) | Armar un pipeline con 5 etapas (secretos, SAST, dependencias, IaC, SBOM) que termine en una sola decision. | Corri el pipeline varias veces contra mi propio repositorio real y lo depure hasta que reflejara resultados correctos: el primer intento marcaba secretos falsos-positivos dentro de las propias dependencias del pipeline (`pipeline/.venv`), y el analisis de dependencias mezclaba CVEs del entorno de auditoria con los de la app. Ambos los corregi yo mismo revisando la salida real de cada herramienta antes de aceptar el resultado. |

## Que hice sin IA

Yo decidi el tema (5 — gestor de tareas colaborativo), la pieza distintiva
(RabbitMQ en vez de SQS, justificado en el ADR), que datos van a RDS y cuales a
S3, y los umbrales de cada etapa del pipeline junto con que controles de
checkov excluir y por que. Tambien corri personalmente las dos corridas del
pipeline (`reportes/corrida_roja.txt` y `reportes/corrida_verde.txt`) y verifique
en la salida cruda de cada herramienta que el hallazgo que bloqueo fuera real
antes de aceptar el resultado como evidencia.

## Algo que la IA me dio mal y tuve que corregir

El primer `docker-compose.yml` generado no arrancaba: faltaba declarar
`email-validator` en `app/requirements.txt` (Pydantic lo necesita para validar
`EmailStr` pero no lo instala por defecto) y ademas `passlib[bcrypt]==1.7.4`
resulto incompatible con las versiones recientes de la libreria `bcrypt`
(>= 4.1), lo que hacia que **cada intento de registro fallara con un error 500**
al calcular el hash de la contrasena. Lo descubri corriendo el flujo real con
`curl` contra la app levantada (no confie en que "deberia funcionar" solo
porque el codigo se veia razonable), lei el traceback completo en
`docker compose logs api`, identifique que era un problema de compatibilidad de
versiones documentado de `passlib`/`bcrypt`, y lo corregi fijando
`bcrypt==4.0.1` en `app/requirements.txt`. Sin correr la aplicacion de verdad
esta falla hubiera pasado directo a la entrega.
