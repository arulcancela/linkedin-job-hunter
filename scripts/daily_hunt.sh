#!/usr/bin/env bash
# =====================================================================
# AI Job Hunter - Ejecución Diaria Automatizada
# =====================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

mkdir -p data

echo "==========================================================" >> data/daily_hunt.log
echo "🚀 Inicio de escaneo diario: $(date '+%Y-%m-%d %H:%M:%S')" >> data/daily_hunt.log
echo "==========================================================" >> data/daily_hunt.log

# Ejecutar el modo caza proactiva con el entorno virtual
"$SCRIPT_DIR/.venv/bin/python" main.py \
    --hunt \
    --keywords "AI Engineer Cloud Automation Google Workspace" \
    --limit 5 >> data/daily_hunt.log 2>&1

echo "✔ Fin del escaneo: $(date '+%Y-%m-%d %H:%M:%S')" >> data/daily_hunt.log
