#!/usr/bin/env bash
# Sobe o backend local do Adito para uso no navegador de desenvolvimento (http://localhost:5173).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$ROOT/Adito/app"
PY="$APP/.venv/bin/python"

[ -x "$PY" ] || { echo "Falta $PY (veja Adito/app/README.md)."; exit 1; }

export ORACULO_LOCAL_TOKEN="${ORACULO_LOCAL_TOKEN:-local-dev-token}"
export ORACULO_DADOS_DB="${ORACULO_DADOS_DB:-$APP/data/dados.duckdb}"
if [ -n "${GOOGLE_API_KEY:-}" ] && [ -z "${GEMINI_API_KEY:-}" ]; then
  export GEMINI_API_KEY="$GOOGLE_API_KEY"
fi

echo "→ Subindo o backend do Adito em http://127.0.0.1:8001..."
exec "$PY" "$APP/backend/api/desktop_server.py" --port 8001
