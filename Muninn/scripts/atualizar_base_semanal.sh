#!/usr/bin/env bash
# Roda o ETL completo, monta o dados.db e publica a base nova (só se os dados mudaram).
# Pensado para rodar uma vez por semana numa máquina da equipe (timer do systemd ou cron);
# ver Muninn/scripts/systemd/README.md.
#
# A base real tem nomes de pesquisadores: o destino tem de ser PRIVADO (nunca o GitHub Pages).
#
# Configuração (variáveis de ambiente; o timer lê de ~/.config/muninn/semanal.env):
#   MUNINN_PUBLICAR_DESTINO  obrigatória. Pasta local onde ficam manifest.json e dados-<versão>.db.gz.
#   MUNINN_PUBLICAR_RSYNC    opcional. Destino do rsync (ex.: muninn@servidor:/srv/muninn/dados/).
#   MUNINN_ETL_BIN           opcional. Comando muninn-etl (padrão: Muninn/etl/.venv/bin/muninn-etl).
#   MUNINN_PYTHON            opcional. Python para publicar_base.py (padrão: python3).
#   MUNINN_SEMANAL_DIR       opcional. Pasta de trabalho, lock e logs (padrão: ~/.cache/muninn-semanal).
#   MUNINN_SEMANAL_PULAR     opcional. Etapas a pular, separadas por espaço (ex.: "lattes cnpq");
#                            a carga usa os brutos que já existem dessas fontes.
#
# Códigos de saída: 0 = ok (publicou ou não havia mudança); 2 = erro, nada foi publicado.
set -euo pipefail

AQUI=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
MUNINN=$(dirname "$AQUI")
ETL_DIR="$MUNINN/etl"

: "${MUNINN_PUBLICAR_DESTINO:?defina MUNINN_PUBLICAR_DESTINO (pasta privada onde a base é publicada)}"
ETL_BIN="${MUNINN_ETL_BIN:-$ETL_DIR/.venv/bin/muninn-etl}"
PYTHON="${MUNINN_PYTHON:-python3}"
TRABALHO="${MUNINN_SEMANAL_DIR:-$HOME/.cache/muninn-semanal}"
PULAR=" ${MUNINN_SEMANAL_PULAR:-} "

mkdir -p "$TRABALHO" "$MUNINN_PUBLICAR_DESTINO"

# Uma execução por vez: se a da semana passada ainda estiver rodando, esta desiste.
exec 9>"$TRABALHO/lock"
if ! flock -n 9; then
  echo "outra atualização ainda está rodando; saindo"
  exit 0
fi

log() { echo "== $(date '+%F %T') $*"; }
PARCIAIS=()

etapa() {
  local nome=$1; shift
  if [[ "$PULAR" == *" $nome "* ]]; then
    log "$nome: pulada (MUNINN_SEMANAL_PULAR)"
    return
  fi
  log "$nome"
  local rc=0
  "$ETL_BIN" "$@" || rc=$?
  case $rc in
    0) ;;
    1) echo "aviso: $nome terminou com falhas em algumas unidades; seguindo com o que veio"
       PARCIAIS+=("$nome") ;;
    *) echo "erro: $nome falhou (código $rc); a base NÃO foi publicada"
       exit 2 ;;
  esac
}

log "início (ETL em $ETL_DIR)"
etapa src-acoes          src-acoes
etapa src-participacoes  src-participacoes
etapa sigpesq            sigpesq
etapa cnpq               cnpq
etapa lattes             lattes
etapa cruzar             cruzar
etapa verificar-pii      verificar-pii      # código 2 se achar CPF/e-mail: para tudo

BASE="$TRABALHO/dados.db"
rm -f "$BASE" "$BASE-wal" "$BASE-shm"
etapa popular-banco popular-banco --banco "$BASE"
[[ -s "$BASE" ]] || { echo "erro: popular-banco não gerou $BASE"; exit 2; }

log "publicando em $MUNINN_PUBLICAR_DESTINO"
MANIFEST="$MUNINN_PUBLICAR_DESTINO/manifest.json"
ANTES=$(sha256sum "$MANIFEST" 2>/dev/null | cut -d' ' -f1 || true)
"$PYTHON" "$AQUI/publicar_base.py" --base "$BASE" --versao "$(date +%Y.%m.%d.%H%M)" \
  --saida "$MUNINN_PUBLICAR_DESTINO" --se-mudou || { echo "erro: publicar_base.py falhou"; exit 2; }
DEPOIS=$(sha256sum "$MANIFEST" | cut -d' ' -f1)

if [[ "$ANTES" == "$DEPOIS" ]]; then
  log "dados iguais aos da semana passada; nada a enviar"
elif [[ -n "${MUNINN_PUBLICAR_RSYNC:-}" ]]; then
  # Primeiro a base, depois o manifest: o app nunca lê um manifest que aponta para um .gz que ainda não chegou.
  log "enviando para $MUNINN_PUBLICAR_RSYNC"
  rsync -a --delete-after --exclude manifest.json "$MUNINN_PUBLICAR_DESTINO/" "$MUNINN_PUBLICAR_RSYNC"
  rsync -a "$MANIFEST" "$MUNINN_PUBLICAR_RSYNC"
fi

if ((${#PARCIAIS[@]})); then
  log "fim, com falhas parciais em: ${PARCIAIS[*]} (ver o log acima)"
else
  log "fim"
fi
