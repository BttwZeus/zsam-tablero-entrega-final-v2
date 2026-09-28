# Evidencia de Producción — Entrega Final

## Nota de transparencia sobre las instancias

La cuenta original de AWS Academy Learner Lab usada en el Avance 2 se quedó
sin crédito/tokens durante esta entrega. Con autorización explícita, se
usaron temporalmente las credenciales del Learner Lab de un compañero de
clase para poder completar el flujo de QA → Producción. Todos los recursos
creados en esa cuenta se etiquetaron con el prefijo `zsam` para dejar clara
su propiedad:

- Instancia **QA**: `zsam-qa` (`i-09e077daf942c49fa`), IP pública `54.214.155.197`.
  No es literalmente la misma instancia EC2 del Avance 2 (esa quedó en la
  cuenta original sin crédito), pero cumple el mismo rol: recibe el código
  antes de promoverlo.
- Instancia **Producción**: `zsam-produccion` (`i-03df8befb2048e418`), IP
  pública `54.190.167.148`.
- Bucket S3: `zsam-tablero-adjuntos-145923749150` (privado, bloqueo de
  acceso público, cifrado SSE-S3).
- RDS Postgres: `zsam-tablero-db` (`zsam-tablero-db.cgoqa4oshj2p.us-west-2.rds.amazonaws.com`),
  cifrada en reposo, sin acceso público, alcanzable solo desde la VPC.

**Corrección aplicada tras retro del profesor en el Avance 2:** la RDS se
había provisionado pero no se estaba usando de verdad en tiempo de ejecución
(la app corría contra el Postgres local del `docker-compose`). Se corrigió
para esta entrega: la instancia de Producción tiene su `.env` apuntando al
endpoint real de la RDS (`DB_HOST=zsam-tablero-db...rds.amazonaws.com`), el
contenedor `db` local se detuvo ahí, y se verificó con datos reales (ver
sección de Verificación) que la app efectivamente lee/escribe en la RDS.

## Qué corre en cada instancia

- **QA** (`zsam-qa`): stack autocontenido de `docker-compose.yml` (`api`,
  `worker`, `db` de Postgres local, `rabbitmq`) — se mantiene local para
  iterar rápido durante la fase de detectar/remediar el hallazgo.
- **Producción** (`zsam-produccion`): mismos contenedores `api`/`worker`/
  `rabbitmq`, pero apuntando a la RDS real (`db` local detenido y sin usarse).
  Es la instancia que demuestra el uso genuino de la infraestructura
  gestionada de AWS.

**Commit desplegado en ambas instancias:** `da83ce5`
("Endurece el consumidor de plantillas y cierra hueco de gitignore en
infra/"), que incluye la remediación de `55416b1`
("Remedia deserializacion insegura en importar_plantilla_tarea (CWE-502)").

## Verificación

```
$ curl http://54.214.155.197:8000/salud   # QA
{"status":"ok"}

$ curl http://54.190.167.148:8000/salud   # Producción
{"status":"ok"}
```

Se probó el flujo completo (registro → tablero → tarjeta →
`POST /cards/{id}/exportar-plantilla` → el worker consume la cola
`plantillas` con JSON y crea la tarjeta importada en un tablero
"Importadas") en la instancia QA después del despliegue del código
remediado, confirmando que la funcionalidad se mantiene intacta y que el
worker ya no se cae ante datos problemáticos (ver commit `da83ce5`).

**Prueba de uso real de la RDS en Producción:**

```
$ curl -X POST http://54.190.167.148:8000/auth/registro \
  -H "Content-Type: application/json" \
  -d '{"email":"prueba-rds@produccion.com","password":"clave12345"}'
{"token":"6edb5def-d7fd-4673-93b8-6804260c5065"}

# Consultado DIRECTAMENTE contra la RDS (no el contenedor local, que esta detenido):
$ psql "postgresql://tablero:***@zsam-tablero-db.cgoqa4oshj2p.us-west-2.rds.amazonaws.com:5432/tablero" \
  -c "select email, created_at from users where email='prueba-rds@produccion.com';"
           email           |         created_at
---------------------------+----------------------------
 prueba-rds@produccion.com | 2026-09-28 01:07:07.910216
(1 row)
```

## Capturas pendientes de tomar en el navegador/consola AWS

Estas requieren tu sesión de navegador y no pueden generarse desde aquí:

- Consola EC2 → instancias `zsam-qa` y `zsam-produccion` corriendo.
- `http://54.214.155.197:8000/` (QA) y `http://54.190.167.148:8000/` (Producción)
  mostrando la app.
- Terminal con la salida de `reportes/pipeline_bloqueado.txt` y
  `reportes/pipeline_verde.txt`.

## Apagado de Producción

Recordatorio: terminar la instancia `i-03df8befb2048e418` (Producción) **y**
la RDS `zsam-tablero-db` en cuanto se tomen las capturas, para no seguir
consumiendo el crédito compartido del Learner Lab (la RDS es el recurso más
caro por hora de todo lo provisionado).
