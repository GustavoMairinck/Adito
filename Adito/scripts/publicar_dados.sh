#!/usr/bin/env bash
# Publica uma carga nova da base cifrada no GitHub Releases (ADR-0007).
#
# Uso (a chave institucional vem do ambiente, nunca da linha de comando):
#   ADITO_DADOS_CHAVE=<64 hex> Adito/scripts/publicar_dados.sh [caminho/dados.db] [versao]
#
# - tranca o dados.db (AES-256-GCM) e gera o manifest.json com a versão e o SHA-256;
# - publica os dois na release fixa de tag `dados`, marcada como pré-lançamento para nunca
#   virar o "release mais recente" que o atualizador do app lê;
# - cada pacote tem nome único (versão + início do SHA-256) e sobe ANTES do manifesto, então
#   ninguém baixa um arquivo trocado por baixo do manifesto; mantém o pacote novo e o anterior.
#
# Precisa do `gh` autenticado com permissão de escrita no repositório e do Rust (cargo).
# Gerar a chave (uma vez, ou para trocar): make chave-dados
set -euo pipefail

REPO="${ADITO_REPO:-SmartIdea-ifes-serra/Adito}"
TAG="dados"
ADITO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BANCO="${1:-$ADITO_DIR/app/data/dados.db}"
VERSAO="${2:-$(date -u +%Y-%m-%d)}"

if [ -z "${ADITO_DADOS_CHAVE:-}" ]; then
  echo "erro: defina ADITO_DADOS_CHAVE com a chave institucional (64 hex)." >&2
  exit 1
fi
command -v gh >/dev/null || { echo "erro: instale e autentique o GitHub CLI (gh)." >&2; exit 1; }
[ -f "$BANCO" ] || { echo "erro: $BANCO não existe. Rode popular_banco.py antes." >&2; exit 1; }
BANCO="$(cd "$(dirname "$BANCO")" && pwd)/$(basename "$BANCO")"

SAIDA="$(mktemp -d)"
trap 'rm -rf "$SAIDA"' EXIT

echo "→ Trancando $BANCO (versão $VERSAO)…"
(cd "$ADITO_DIR/app/src-tauri" && cargo run --quiet --example empacotar_dados -- empacotar "$BANCO" "$SAIDA" "$VERSAO")
PACOTE="$(find "$SAIDA" -name 'dados-*.db.enc' -print -quit)"

if ! gh release view "$TAG" -R "$REPO" >/dev/null 2>&1; then
  echo "→ Criando a release '$TAG' (pré-lançamento) em $REPO…"
  gh release create "$TAG" -R "$REPO" --prerelease --title "Dados do Adito" \
    --notes "Base acadêmica cifrada (AES-256-GCM) lida pelo app Adito. Sem a chave institucional, o arquivo é ilegível. Não é um release do app."
fi

# Pacote que o manifesto atual aponta: alguém pode estar no meio do download dele.
ANTERIOR="$(gh release download "$TAG" -R "$REPO" -p manifest.json -O - 2>/dev/null \
  | sed -n 's/.*"arquivo": *"\([^"]*\)".*/\1/p' || true)"

echo "→ Enviando o pacote e depois o manifesto…"
gh release upload "$TAG" "$PACOTE" -R "$REPO"
gh release upload "$TAG" "$SAIDA/manifest.json" -R "$REPO" --clobber

# Mantém só o pacote novo e o anterior.
NOVO="$(basename "$PACOTE")"
gh release view "$TAG" -R "$REPO" --json assets -q '.assets[].name' \
  | { grep -E '^dados-.+\.db\.enc$' | grep -vxF -e "$NOVO" -e "${ANTERIOR:-$NOVO}" || true; } \
  | while read -r antigo; do
      echo "→ Removendo pacote antigo $antigo"
      gh release delete-asset "$TAG" "$antigo" -R "$REPO" -y
    done

echo "✓ Dados $VERSAO publicados. Os usuários verão o aviso na próxima vez que abrirem o Adito."
