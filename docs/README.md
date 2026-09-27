# Tablero — gestor de tareas colaborativo

> Avance 2 del Reto - LSCA2314 - Periodo AD26
> Alumno: Zeus Samael Aguirre Martinez   |   Matricula: 3098639   |   Tema elegido: 5 — Gestor de tareas colaborativo

## Que hace esta aplicacion

Tablero es un gestor de tareas colaborativo: los usuarios se registran, crean
tableros, agregan tarjetas con fecha limite y las asignan a un correo. Al crear
una tarjeta, la API no envia el recordatorio directamente: publica un mensaje en
una cola de RabbitMQ que un worker independiente consume para generar el
recordatorio, desacoplando la creacion de la tarea del envio del aviso.

## Como se levanta

```bash
cp .env.ejemplo .env     # y llena tus valores
docker compose up --build
```

La aplicacion queda en http://localhost:8000 y su endpoint de salud responde en
`/salud`. El panel de administracion de RabbitMQ queda en http://localhost:15672
(usuario/clave por defecto: guest/guest, solo para uso local).

## Arquitectura

El servicio `api` (FastAPI) expone la interfaz web y REST, guarda tableros,
tarjetas y usuarios en Postgres (RDS en produccion) y sube los adjuntos de las
tarjetas a S3. Al crear una tarjeta, `api` publica un mensaje en la cola
`reminders` de RabbitMQ. El servicio `worker`, un contenedor separado, consume
esa cola, genera el recordatorio y lo guarda en la base de datos — asi la
creacion de la tarjeta nunca espera a que el recordatorio se procese.

Ver el diagrama en `docs/diagrama_arquitectura.png`.

## Servicios de AWS que usa

| Servicio | Para que lo uso | Como lo asegure |
|---|---|---|
| S3 | Guardar los archivos adjuntos de cada tarjeta | Bucket privado, `block_public_access` activo en las 4 opciones, cifrado por defecto SSE-S3 |
| RDS (Postgres) | Guardar usuarios, tableros, tarjetas y recordatorios | `publicly_accessible = false`, cifrado en reposo (`storage_encrypted`), security group que solo permite el puerto 5432 desde la IP/subred de la instancia de la app |

## Requisitos minimos del tema

| Requisito de mi tema | Donde se cumple |
|---|---|
| Tableros, tarjetas, asignaciones y fechas limite | `app/main.py` (`/boards`, `/boards/{id}/cards`), `app/models.py` |
| Cola de mensajes que desacopla creacion de tarea y envio de recordatorio | `app/queue_client.py` publica en RabbitMQ; `app/worker.py` consume y guarda el recordatorio |
| Backend en Python | FastAPI (`app/main.py`) |
| Al menos 2 contenedores propios | `api` y `worker` en `docker-compose.yml`, misma imagen (`Dockerfile`), distinto `command` |
| Bucket S3 real, privado y cifrado | `infra/main.tf` (`aws_s3_bucket.adjuntos` + bloqueo de acceso publico + SSE) |
| RDS real, cifrada y sin acceso publico | `infra/main.tf` (`aws_db_instance.tablero`) |
| Registro e inicio de sesion | `POST /auth/registro`, `POST /auth/login` en `app/main.py` |
| Endpoint /salud | `GET /salud` en `app/main.py` |
| Cero credenciales en el codigo | Todo via variables de entorno (`app/config.py`), `.env` en `.gitignore` |

## Como crear la infraestructura en AWS Academy

```bash
cd infra
cp terraform.tfvars.ejemplo terraform.tfvars   # y llena tus valores
export TF_VAR_db_password="una-password-segura"
terraform init
terraform apply
```

Copia `s3_bucket_name` y `rds_endpoint` de la salida hacia tu `.env` (`S3_BUCKET`
y `DB_HOST`). Las credenciales de AWS Academy (Access Key, Secret Key, Session
Token) se copian desde "AWS Details" en el Learner Lab y se exportan como
variables de entorno (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
`AWS_SESSION_TOKEN`) antes de correr `terraform apply`; expiran cada pocas
horas, asi que hay que repetir este paso si la sesion vence.

## Como se corre el pipeline

```bash
bash pipeline/run_pipeline.sh
```

Corre 5 etapas (secretos, SAST, dependencias, IaC y SBOM) y termina en una sola
decision: `PERMITIDO` o `BLOQUEADO`. Ver `docs/tabla_decisiones_pipeline.md`
para la justificacion de cada etapa y su umbral, y `reportes/corrida_roja.txt` /
`reportes/corrida_verde.txt` para la evidencia de las dos corridas.
