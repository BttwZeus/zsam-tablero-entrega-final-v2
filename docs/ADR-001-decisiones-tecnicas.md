# ADR-001: Decisiones tecnicas de Tablero (gestor de tareas colaborativo)

Fecha: 2026-09-16
Estado: aceptada

## Contexto

Estaba construyendo un gestor de tareas colaborativo individual, con tiempo
limitado a una entrega y sin presupuesto mas alla del credito de AWS Academy
Learner Lab. La instancia del Learner Lab tiene memoria limitada, asi que
evite componentes pesados (Kubernetes, multiples replicas) y me apoye en IA
para generar el andamio inicial de FastAPI y despues lo revise y corregi a mano
(ver `docs/declaracion_uso_ia.md`).

## Decisiones

### 1. Framework del backend

**Elegi:** FastAPI.
**Por que:** valida los cuerpos de las peticiones con Pydantic sin escribir
validacion a mano, genera documentacion OpenAPI automatica que me sirvio para
probar la API mientras la construia, y es asincrono por defecto lo cual encaja
con un servicio que publica en una cola.
**Que descarte y por que:** Flask, porque hubiera tenido que agregar a mano la
validacion de esquemas y la documentacion, y no aportaba nada que necesitara
para este proyecto.

### 2. Separacion en servicios

**Elegi:** dos contenedores propios (`api` y `worker`, misma imagen, distinto
`command`) mas RabbitMQ y Postgres como contenedores de infraestructura en
`docker-compose.yml`.
**Por que:** la pieza distintiva de mi tema es que la creacion de una tarjeta
no debe bloquearse esperando a que se procese su recordatorio. Si el envio del
recordatorio viviera como una funcion dentro del mismo proceso de la API, un
recordatorio lento (o que falle) degradaria el tiempo de respuesta de crear
una tarjeta. Separarlos en un `worker` que consume de una cola aisla ese
riesgo: la API solo tiene que lograr publicar el mensaje, no procesarlo.
**Que descarte y por que:** SQS de AWS Academy, la otra opcion sugerida para
este tema. Lo descarte porque el Learner Lab da credenciales temporales que
expiran cada pocas horas, y mi pipeline y mi entorno de desarrollo necesitan
poder correr sin depender de que esas credenciales esten vigentes en ese
momento. RabbitMQ en contenedor me da la misma desacoplacion sin esa
dependencia externa.

### 3. Almacenamiento

**Elegi:** los datos estructurados (usuarios, tableros, tarjetas, recordatorios)
van a RDS Postgres; los archivos que un usuario adjunta a una tarjeta van a S3.
**Por que:** son dos tipos de dato distintos con dos patrones de acceso
distintos. Los datos estructurados necesitan consultas relacionales (tarjetas
de un tablero, tableros de un usuario); los adjuntos son blobs que solo se
suben y se descargan, y S3 los sirve mejor y mas barato que guardarlos como
bytes en la base de datos.
**Que descarte y por que:** guardar los adjuntos tambien en la base de datos
(como bytea). Lo descarte porque hincha el tamano de la base de datos y de sus
respaldos sin necesidad, y porque el requisito del reto pedia usar S3 de
verdad, no solo tenerlo creado.

## Consecuencias

Lo que se facilito: probar el flujo completo en mi maquina con
`docker compose up` sin tocar AWS, y poder correr el pipeline de seguridad las
veces que quise sin gastar credito del Learner Lab.

Lo que se complico: `docker-compose.yml` corre un Postgres local para
desarrollo, pero en produccion la app debe apuntar a la RDS real cambiando
`DB_HOST` en `.env` (documentado en este README). Tener ambos casos me obligo
a que toda la configuracion de conexion salga de variables de entorno y nunca
quede fija en el codigo, lo cual termino siendo positivo para el requisito de
"cero credenciales en el codigo".
