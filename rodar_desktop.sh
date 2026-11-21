#!/usr/bin/env bash
# Sobe o Muninn desktop (Tauri) em modo desenvolvimento:
# Vite na 5173 -> janela Tauri -> núcleo Python (iniciado pela própria janela, sem porta de rede;
# conversa com a janela por stdin/stdout).
# Fechar a janela encerra o núcleo e o Vite iniciado por este script.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$ROOT/Muninn/app"
PY="$APP/.venv/bin/python"
# Mesma pasta que o Tauri usa (app_local_data_dir + identifier do tauri.conf.json).
DATA="${XDG_DATA_HOME:-$HOME/.local/share}/br.edu.ifes.leds.muninn"
VITE_LOG="/tmp/muninn-vite.log"

[ -x "$PY" ] || { echo "Falta $PY (veja Muninn/app/README.md, seção 2)." >&2; exit 1; }
if ! command -v cargo >/dev/null 2>&1; then
  if [ -f "$HOME/.cargo/env" ]; then
    # shellcheck source=/dev/null
    source "$HOME/.cargo/env"
  fi
fi
if ! command -v cargo >/dev/null 2>&1; then
  echo "❌ Erro: O compilador Rust (cargo) não foi encontrado no sistema." >&2
  echo "Instale o Rust executando:" >&2
  echo "  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh" >&2
  echo "Depois reinicie o terminal (ou execute 'source \"\$HOME/.cargo/env\"') e tente novamente." >&2
  exit 1
fi

# 1. Dados: o app lê dados.db (em $DATA ou em $APP/data/dados.db) e contexts/.
[ -f "$DATA/dados.db" ] || [ -f "$APP/data/dados.db" ] || echo "Aviso: dados.db não encontrado; rode Muninn/scripts/popular_banco.py antes de consultar."

# 2. Vite na porta 5173 (o Tauri em dev carrega exatamente essa porta)
VITE_PID=""
cleanup() { [ -n "$VITE_PID" ] && kill "$VITE_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# Só reaproveita o Vite da 5173 se ele for desta pasta. Um Vite de outra cópia do projeto
# (outra worktree, a pasta principal) serviria outro front para este núcleo.
FRONT_DIR="$(cd "$APP/frontend-vue" && pwd -P)"
pasta_do_vite() {
  local pid
  pid="$(lsof -t -iTCP:5173 -sTCP:LISTEN 2>/dev/null | head -1 || true)"
  [ -n "$pid" ] || return 0
  echo "$pid $(readlink -f "/proc/$pid/cwd" 2>/dev/null || lsof -a -p "$pid" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p')"
}

if curl -s -o /dev/null http://localhost:5173; then
  read -r OUTRO_PID OUTRA_PASTA <<<"$(pasta_do_vite)" || true
  if [ "${OUTRA_PASTA:-}" != "$FRONT_DIR" ]; then
    if [ -z "${OUTRO_PID:-}" ]; then
      echo "A porta 5173 está ocupada por um processo que não dá para identificar. Encerre-o e rode de novo."
      exit 1
    fi
    # Só encerra se for mesmo um Vite; qualquer outro serviço na 5173 fica com o usuário.
    OUTRO_CMD="$(ps -p "$OUTRO_PID" -o args= 2>/dev/null || true)"
    if [[ "$OUTRO_CMD" != *vite* ]]; then
      echo "A porta 5173 está ocupada por outro programa (pid $OUTRO_PID: ${OUTRO_CMD:-desconhecido}). Encerre-o e rode de novo."
      exit 1
    fi
    echo "→ O Vite na 5173 é de outra pasta (${OUTRA_PASTA:-desconhecida}); encerrando para subir o desta."
    kill "$OUTRO_PID" 2>/dev/null || true
    for _ in $(seq 1 20); do curl -s -o /dev/null http://localhost:5173 || break; sleep 0.5; done
    if curl -s -o /dev/null http://localhost:5173; then
      echo "O Vite da outra pasta (pid $OUTRO_PID) não encerrou. Encerre-o e rode de novo."
      exit 1
    fi
  fi
fi

if curl -s -o /dev/null http://localhost:5173; then
  echo "→ Vite desta pasta já está rodando na 5173; reaproveitando."
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
# Filtra apenas as entradas apontando para /snap/ (injetadas pelo terminal do VS Code Snap),
# preservando caminhos legítimos em variáveis de lista separadas por ':' (como LD_LIBRARY_PATH).
SNAP_DETECTADO=0
[ -n "${SNAP:-}" ] && SNAP_DETECTADO=1

for _var in GTK_PATH GIO_MODULE_DIR GSETTINGS_SCHEMA_DIR LD_LIBRARY_PATH; do
  _val="${!_var:-}"
  if [[ "$_val" == *"/snap/"* ]]; then
    SNAP_DETECTADO=1
    _limpo=""
    IFS=':' read -r -a _partes <<< "$_val"
    for _p in "${_partes[@]}"; do
      if [ -n "$_p" ] && [[ "$_p" != *"/snap/"* ]]; then
        _limpo="${_limpo:+${_limpo}:}${_p}"
      fi
    done
    if [ -n "$_limpo" ]; then
      export "$_var=$_limpo"
    else
      unset "$_var"
    fi
  fi
done
for _var in GTK_EXE_PREFIX GTK_IM_MODULE_FILE; do
  if [[ "${!_var:-}" == *"/snap/"* ]]; then
    SNAP_DETECTADO=1
    unset "$_var"
  fi
done
unset _var _val _limpo _partes _p

# No Wayland, o renderizador DMA-BUF do WebKitGTK costuma deixar a janela em branco
# (principalmente com NVIDIA). Desligado por padrão; exporte =0 para religar.
# Quando rodando a partir de ambiente Snap (ex.: terminal do VS Code Snap) ou com
# MUNINN_FORCE_X11=1, também força GDK_BACKEND=x11 para contornar o erro de schema
# 'antialiasing' no GTK3 sem impactar sessões Wayland nativas (escala fracionária / sem XWayland).
# Exporte GDK_BACKEND manualmente (ex.: GDK_BACKEND=x11 ou GDK_BACKEND=wayland) para sobrescrever.
if [ "${XDG_SESSION_TYPE:-}" = "wayland" ]; then
  export WEBKIT_DISABLE_DMABUF_RENDERER="${WEBKIT_DISABLE_DMABUF_RENDERER:-1}"
  if [ "$SNAP_DETECTADO" -eq 1 ] || [ "${MUNINN_FORCE_X11:-0}" = "1" ]; then
    export GDK_BACKEND="${GDK_BACKEND:-x11}"
  fi
fi

echo "→ Abrindo a janela do Muninn (o núcleo sobe junto)."
echo "  Log do núcleo: $DATA/logs/backend.log"
cd "$APP/src-tauri"
cargo run
