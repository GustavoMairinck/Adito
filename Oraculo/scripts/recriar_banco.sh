#!/usr/bin/env bash
# ==============================================================================
# recriar_banco.sh: Destroi volumes, recria o banco e executa a validacao
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

if [ ! -f .env ]; then
    echo "Criando .env a partir de .env.example..."
    cp .env.example .env
fi

echo "=========================================================="
echo "1. Parando containers e destruindo volumes anteriores..."
echo "=========================================================="
docker compose down -v --remove-orphans

echo "=========================================================="
echo "2. Subindo PostgreSQL e aguardando inicializacao DDL..."
echo "=========================================================="
docker compose up -d

# Aguarda ate o container completar a inicializacao (status healthy)
echo "Aguardando container PostgreSQL ficar saudavel..."
until [ "$(docker inspect -f '{{.State.Health.Status}}' oraculo_postgres_unificado 2>/dev/null)" = "healthy" ]; do
    sleep 1
done

echo "=========================================================="
echo "3. Executando script de validacao..."
echo "=========================================================="
docker compose exec -T oraculo-postgres psql -U oraculo -d oraculo_db -f /docker-entrypoint-initdb.d/99_validacao.sql

echo "=========================================================="
echo "PostgreSQL Unificado pronto e validado na porta 5435!"
echo "=========================================================="
