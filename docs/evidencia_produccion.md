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
- Se provisionó tambien una RDS Postgres cifrada con el mismo Terraform del
  Avance 2 para cumplir el requisito de infraestructura, pero se destruyó
  inmediatamente después de confirmarla sana (no la usa esta entrega en
  tiempo de ejecución, ver más abajo) para cuidar el crédito compartido del
  Learner Lab.

## Qué corre en cada instancia

Ambas instancias corren el stack completo autocontenido de
`docker-compose.yml` (`api`, `worker`, `db` de Postgres local, `rabbitmq`),
igual que en desarrollo local — no dependen de la RDS externa para esta
entrega, ya que el checklist de evidencia de la Entrega Final no la requiere
y así se evita duplicar el gasto de una base de datos gestionada que no se
iba a usar activamente.

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
worker ya no se cae ante datos problemáticos (ver commit `a7f80ef`).

## Capturas pendientes de tomar en el navegador/consola AWS

Estas requieren tu sesión de navegador y no pueden generarse desde aquí:

- Consola EC2 → instancias `zsam-qa` y `zsam-produccion` corriendo.
- `http://54.214.155.197:8000/` (QA) y `http://54.190.167.148:8000/` (Producción)
  mostrando la app.
- Terminal con la salida de `reportes/pipeline_bloqueado.txt` y
  `reportes/pipeline_verde.txt`.

## Apagado de Producción

Recordatorio: terminar la instancia `i-03df8befb2048e418` (Producción) en
cuanto se tomen las capturas, para no seguir consumiendo el crédito
compartido del Learner Lab.
