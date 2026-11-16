#!/usr/bin/env bash
# Sobe o Oráculo ESX desktop (Tauri) em modo desenvolvimento:
# Vite na 5173 -> janela Tauri -> backend Django (iniciado pela própria janela).
# Fechar a janela encerra o backend e o Vite iniciado por este script.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$ROOT/Adito/app"
PY="$APP/.venv/bin/python"
# Mesma pasta que o Tauri usa (app_local_data_dir + identifier do tauri.conf.json).
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/br.edu.ifes.leds.oraculo-esx"
VITE_LOG="/tmp/oraculo-vite.log"

[ -x "$PY" ] || { echo "Falta $PY (veja Adito/app/README.md, seção 2)."; exit 1; }
command -v cargo >/dev/null || source "$HOME/.cargo/env"

# 1. Dados: o app lê dados.duckdb (em $DATA ou em $APP/data/dados.duckdb) e contexts/.
[ -f "$DATA/dados.duckdb" ] || [ -f "$APP/data/dados.duckdb" ] || echo "Aviso: dados.duckdb não encontrado; rode Adito/scripts/gerar_duckdb.py antes de consultar."

# 2. Vite na porta 5173 (o Tauri em dev carrega exatamente essa porta)
VITE_PID=""
cleanup() { [ -n "$VITE_PID" ] && kill "$VITE_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

if curl -s -o /dev/null http://localhost:5173; then
  echo "→ Vite já está rodando na 5173; reaproveitando."
else
  echo "→ Subindo o Vite (log: $VITE_LOG)..."
  (cd "$APP/frontend-vue" && exec ./node_modules/.bin/vite) >"$VITE_LOG" 2>&1 &
  VITE_PID=$!
  for _ in $(seq 1 60); do
    curl -s -o /dev/null http://localhost:5173 && break
    kill -0 "$VITE_PID" 2>/dev/null || { echo "O Vite falhou ao subir:"; cat "$VITE_LOG"; exit 1; }
    sleep 0.5
  done
fi

# 3. Janela Tauri
# No Wayland, o renderizador DMA-BUF do WebKitGTK costuma deixar a janela em branco
# (principalmente com NVIDIA). Desligado por padrão; exporte =0 para religar.
if [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
  export WEBKIT_DISABLE_DMABUF_RENDERER="${WEBKIT_DISABLE_DMABUF_RENDERER:-1}"
fi

echo "→ Abrindo a janela do Oráculo ESX (o backend sobe junto)."
echo "  Log do backend: $DATA/logs/backend.log"
cd "$APP/src-tauri"
cargo run
