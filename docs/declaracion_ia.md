# Declaración de uso de inteligencia artificial — Entrega Final

Las Notas de Enseñanza del curso permiten usar IA como apoyo, no como
sustituto. A diferencia del Avance 2 (donde la IA generó fragmentos de código
que yo revisé después), en esta entrega usé un agente de IA con acceso
directo a mi terminal y a mi cuenta de AWS (Claude Code) para ejecutar el
flujo completo: integrar el parche, correr el pipeline, clasificar el
hallazgo, remediar el código, y provisionar/desplegar en AWS. Lo dejo
declarado con ese nivel de detalle porque es el uso real que le di, no una
versión suavizada.

## Qué hizo el agente de IA, con mi dirección y aprobación

| Parte | Qué hizo el agente | Qué decidí/aprobé yo |
|---|---|---|
| Integración del parche (`app/importar_plantilla_tarea.py`, `app/tareas.py`, `app/queue_client.py`, `app/main.py`, `app/worker.py`) | Copió el archivo del parche tal cual se entregó, y diseñó el resto del wiring (endpoint de exportar plantilla, productor, consumidor en el worker) para integrarlo a mi app existente sin inventar entidades nuevas. | Confirmé que la integración debía dejar la falla intacta en el primer commit, sin "arreglarla" de entrada, tal como piden las instrucciones. |
| Clasificación del hallazgo | Identificó la falla (CWE-502, `pickle.loads` sobre datos de la cola) leyendo el propio código del parche, y notó que el pipeline original no la bloqueaba porque bandit la reporta como MEDIUM y el script solo contaba HIGH/CRITICAL. | Yo no verifiqué esto de forma independiente antes de que el pipeline corriera; la corrida real del pipeline (`reportes/pipeline_bloqueado.txt` inicial, que salió en verde) confirmó la predicción antes de aceptarla como cierta. |
| Corrección del gate del pipeline (`pipeline/run_pipeline.sh`) | Propuso y aplicó el criterio adicional de bloquear por cualquier hallazgo `B3xx` de bandit, no solo HIGH/CRITICAL. | Aprobé el cambio después de ver que era el único hallazgo MEDIUM en todo el proyecto (no escondía otros hallazgos "ruido"). |
| Remediación (`pickle` → `json` + validación de esquema) | Escribió el reemplazo y una prueba manual (payload JSON válido vs. payload `pickle` malicioso) para confirmar que la RCE ya no ocurre y que la funcionalidad legítima sigue funcionando. | Revisé el resultado de esa prueba antes de aceptar el commit de remediación como válido. |
| Infraestructura AWS (Terraform, EC2, S3, security groups) | Provisionó y luego destruyó la RDS, creó el bucket S3, lanzó las instancias EC2 de QA y Producción, configuró los security groups y desplegó el código por SSH. | Aprobé explícitamente cada acción de creación/destrucción de infraestructura real y cada apertura de puertos antes de que se ejecutara (el propio entorno del agente exige esa confirmación para acciones de este tipo). También decidí usar temporalmente el Learner Lab de un compañero porque el mío se quedó sin crédito (ver `docs/evidencia_produccion.md`). |
| Hallazgo de un bug adicional (worker se caía) | Detectó, durante la prueba end-to-end en QA, que un mensaje con datos inconsistentes (no inválidos en formato, pero con un `usuario_id` inexistente) tumbaba el proceso `worker` completo por una excepción no capturada, y lo corrigió. | Este bug no estaba buscado por las instrucciones del reto; lo acepté como una corrección de robustez necesaria porque afectaba mi verificación de que "la funcionalidad se mantiene intacta". |

## Qué decidí yo, sin delegarlo

El tema, la estructura de la app y del pipeline vienen del Avance 2 (decisión
mía, documentada en `docs/ADR-001-decisiones-tecnicas.md`). En esta entrega,
las decisiones que fueron mías y no del agente: aceptar clasificar la falla
como Crítica (no MEDIUM, la severidad por defecto de bandit) dado el impacto
real de RCE; usar el Learner Lab de un compañero identificando mis recursos
con el prefijo `zsam`; y la revisión final de todo lo documentado en
`docs/clasificacion_hallazgo.md` y `docs/respuesta_incidente.md` antes de
subir la entrega.

## Algo que verifiqué en vez de solo confiar en la IA

Antes de aceptar que el pipeline bloqueaba "de verdad" el hallazgo, exigí ver
la corrida completa y el `bandit.json` real (no un resumen) mostrando la
línea exacta y la regla `B301` en `app/importar_plantilla_tarea.py`. Y antes
de aceptar que la remediación "mantiene la funcionalidad", exigí una prueba
end-to-end real contra la instancia de QA desplegada (registro, tablero,
tarjeta, exportar plantilla, y confirmar en los logs del worker que la
tarjeta importada aparece), no solo que el pipeline pasara en verde.
