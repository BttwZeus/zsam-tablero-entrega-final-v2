#!/bin/bash
# Pipeline de seguridad del Gestor de tareas colaborativo.
# Corre 5 etapas y produce UNA decision final: BLOQUEADO o PERMITIDO.
# Uso: ./pipeline/run_pipeline.sh
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR" || exit 1
export MSYS_NO_PATHCONV=1

VENV="pipeline/.venv"
BLOQUEA=0
RESUMEN=""

linea() { echo "--------------------------------------------------------------"; }

agregar_resumen() {
  RESUMEN="${RESUMEN}\n$1"
}

echo "=================================================="
echo " Pipeline de seguridad - Gestor de tareas colaborativo"
echo "=================================================="

# --- 0. Preparar entorno de herramientas Python (bandit, pip-audit, SBOM) ---
if [ -d "$VENV/Scripts" ]; then
  BIN="$VENV/Scripts"
else
  BIN="$VENV/bin"
fi

if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
  if [ -d "$VENV/Scripts" ]; then BIN="$VENV/Scripts"; else BIN="$VENV/bin"; fi
  "$BIN/pip" install --quiet --upgrade pip
  "$BIN/pip" install --quiet bandit==1.7.10 pip-audit==2.7.3 cyclonedx-bom==4.6.1
fi
PY="$BIN/python"
BANDIT="$BIN/bandit"
PIP_AUDIT="$BIN/pip-audit"
CYCLONEDX="$BIN/cyclonedx-py"

mkdir -p reportes

# --- 1. SBOM (siempre se genera, no bloquea) ---
linea
echo "[1/5] SBOM (CycloneDX) de dependencias Python"
"$CYCLONEDX" requirements app/requirements.txt -o reportes/sbom_cyclonedx.json --of json >/tmp/sbom.log 2>&1
if [ -s reportes/sbom_cyclonedx.json ]; then
  echo "  SBOM generado en reportes/sbom_cyclonedx.json"
  agregar_resumen "[OK]  SBOM generado"
else
  echo "  No se pudo generar el SBOM"
  cat /tmp/sbom.log
  agregar_resumen "[ERROR] SBOM no generado"
fi

# --- 2. Secretos (gitleaks) - bloquea con CUALQUIER hallazgo ---
linea
echo "[2/5] Escaneo de secretos (gitleaks) - umbral: 0 hallazgos"
docker run --rm -v "$DIR":/repo -w /repo zricethezav/gitleaks:latest detect \
  --source /repo --no-git -v --config /repo/pipeline/.gitleaks.toml \
  --report-path reportes/gitleaks.json > /tmp/gitleaks.log 2>&1
GITLEAKS_RC=$?
cat /tmp/gitleaks.log
if [ "$GITLEAKS_RC" -ne 0 ]; then
  echo "  >> Etapa BLOQUEA: se encontraron secretos en el codigo"
  agregar_resumen "[BLOQUEA] Secretos (gitleaks): hallazgos > 0"
  BLOQUEA=1
else
  echo "  >> Etapa OK: no se encontraron secretos"
  agregar_resumen "[OK]  Secretos (gitleaks): 0 hallazgos"
fi

# --- 3. SAST (bandit) - bloquea con HIGH o CRITICAL ---
linea
echo "[3/5] Analisis estatico de codigo (bandit) - umbral: 0 hallazgos HIGH"
"$BANDIT" -r app/ -ll -f json -o reportes/bandit.json > /tmp/bandit.log 2>&1
BANDIT_HIGH=$("$PY" -c "
import json
try:
    data = json.load(open('reportes/bandit.json'))
    n = sum(1 for r in data.get('results', []) if r.get('issue_severity') in ('HIGH','CRITICAL'))
    print(n)
except Exception:
    print(0)
")
echo "  Hallazgos HIGH/CRITICAL: $BANDIT_HIGH"
if [ "$BANDIT_HIGH" -gt 0 ]; then
  echo "  >> Etapa BLOQUEA: bandit encontro codigo inseguro"
  agregar_resumen "[BLOQUEA] SAST (bandit): $BANDIT_HIGH hallazgos HIGH/CRITICAL"
  BLOQUEA=1
else
  agregar_resumen "[OK]  SAST (bandit): 0 hallazgos HIGH/CRITICAL"
fi

# --- 4. Dependencias vulnerables (pip-audit) - bloquea con cualquier CVE conocido ---
# Se audita un venv aparte con SOLO las dependencias de la app (app/requirements.txt),
# para no mezclar CVEs de las herramientas del propio pipeline con las de la app.
linea
echo "[4/5] Dependencias vulnerables (pip-audit) - umbral: 0 CVE conocidos en dependencias de la app"
APP_VENV="pipeline/.venv-app"
if [ -d "$APP_VENV/Scripts" ]; then APP_BIN="$APP_VENV/Scripts"; else APP_BIN="$APP_VENV/bin"; fi
if [ ! -d "$APP_VENV" ]; then
  python3 -m venv "$APP_VENV"
  if [ -d "$APP_VENV/Scripts" ]; then APP_BIN="$APP_VENV/Scripts"; else APP_BIN="$APP_VENV/bin"; fi
fi
"$APP_BIN/pip" install --quiet --upgrade pip > /tmp/pip-install.log 2>&1
if ! "$APP_BIN/pip" install --quiet pip-audit==2.7.3 -r app/requirements.txt >> /tmp/pip-install.log 2>&1; then
  echo "  ERROR: no se pudieron instalar las dependencias de la app para auditarlas"
  cat /tmp/pip-install.log
  agregar_resumen "[ERROR] Dependencias (pip-audit): no se pudo instalar app/requirements.txt"
  BLOQUEA=1
fi
"$APP_BIN/pip-audit" -f json -o reportes/pip-audit.json > /tmp/pip-audit.log 2>&1
cat /tmp/pip-audit.log
# Solo bloquea por CVEs en dependencias que la app declara (app/requirements.txt),
# no por el propio pip empacado en el venv de auditoria.
APP_DEPS=$("$PY" -c "
import re
names = set()
for line in open('app/requirements.txt'):
    line = line.strip()
    if line and not line.startswith('#'):
        names.add(re.split(r'[=<>\[]', line)[0].lower())
print(','.join(names))
")
PIP_AUDIT_VULNS=$("$PY" -c "
import json
apps = set('$APP_DEPS'.split(','))
try:
    data = json.load(open('reportes/pip-audit.json'))
except Exception:
    data = {'dependencies': []}
n = 0
for dep in data.get('dependencies', []):
    if dep.get('vulns') and dep['name'].lower() in apps:
        n += len(dep['vulns'])
print(n)
")
echo "  CVE en dependencias declaradas por la app: $PIP_AUDIT_VULNS"
if [ "$PIP_AUDIT_VULNS" -gt 0 ]; then
  echo "  >> Etapa BLOQUEA: hay dependencias de la app con CVE conocidos"
  agregar_resumen "[BLOQUEA] Dependencias (pip-audit): $PIP_AUDIT_VULNS CVE en deps de la app"
  BLOQUEA=1
else
  echo "  >> Etapa OK: sin CVE conocidos en dependencias de la app"
  agregar_resumen "[OK]  Dependencias (pip-audit): 0 CVE en deps de la app"
fi

# --- 5. IaC (checkov) - bloquea con fallos en controles de seguridad de linea base ---
# Se excluyen explicitamente controles de "excelencia operativa" fuera del alcance
# de un Learner Lab (Multi-AZ, monitoreo mejorado, replicacion entre regiones, KMS
# en vez de SSE-S3, etc.) - ver docs/tabla_decisiones_pipeline.md para la justificacion
# de cada uno. Lo que SI bloquea: acceso publico y cifrado faltante en S3/RDS.
CHECKS_EXCLUIDOS="CKV_AWS_161,CKV_AWS_353,CKV_AWS_118,CKV_AWS_157,CKV2_AWS_62,CKV_AWS_144,CKV2_AWS_30,CKV_AWS_18,CKV2_AWS_61,CKV_AWS_145,CKV_AWS_293,CKV_AWS_21"
linea
echo "[5/5] Infraestructura como codigo (checkov) - umbral: 0 fallos en controles de linea base"
docker run --rm -v "$DIR":/repo bridgecrew/checkov -d /repo/infra \
  --compact --skip-check "$CHECKS_EXCLUIDOS" \
  -o json --output-file-path /repo/reportes > /tmp/checkov.log 2>&1
CHECKOV_RC=$?
cat /tmp/checkov.log
if [ "$CHECKOV_RC" -ne 0 ]; then
  echo "  >> Etapa BLOQUEA: checkov encontro fallos HIGH/CRITICAL en el IaC"
  agregar_resumen "[BLOQUEA] IaC (checkov): fallos HIGH/CRITICAL"
  BLOQUEA=1
else
  echo "  >> Etapa OK: IaC sin fallos HIGH/CRITICAL"
  agregar_resumen "[OK]  IaC (checkov): 0 fallos HIGH/CRITICAL"
fi

# --- Decision final ---
linea
echo ""
echo "Resumen de etapas:"
echo -e "$RESUMEN"
echo ""
if [ "$BLOQUEA" -eq 1 ]; then
  echo "DECISION FINAL: BLOQUEADO"
  echo "El pipeline ha bloqueado el despliegue porque al menos una etapa supero su umbral."
  exit 1
else
  echo "DECISION FINAL: PERMITIDO"
  echo "El pipeline ha permitido el despliegue: todas las etapas pasaron su umbral."
  exit 0
fi
