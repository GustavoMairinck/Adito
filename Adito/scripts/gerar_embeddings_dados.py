#!/usr/bin/env python3
"""Gera os vetores de busca dos valores do `dados.db` com o modelo local (sem API de IA).

Lê as `embed_columns` de cada view no `views.json` do contexto, faz `SELECT DISTINCT` **por coluna**
(nunca a combinação de colunas) e grava dentro do próprio banco:

    adito_embedding_meta(chave, valor)            -- modelo, dim, data e totais
    adito_valor_embedding(view, coluna, valor, vetor)  -- float16, já normalizado

Colunas listadas em `multi_valor_columns` (ex.: `campus` em Extensão, que vem como "Serra; Vitória")
são quebradas em `; ` e cada parte vira um valor.

Roda na máquina de quem publica os dados, antes de cifrar (publicar_dados.sh chama este script
numa cópia do banco). Por padrão gera tudo de novo; com `--incremental` reaproveita os vetores do
mesmo modelo e só embeda os valores novos (é o que o app faz sozinho na máquina do usuário quando
o `dados.db` muda). Uso:
    python3 gerar_embeddings_dados.py caminho/dados.db [--contexto pasta/do/contexto] [--modelo chave] [--incremental]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
NUCLEO = AQUI.parent / "app" / "backend" / "nucleo"
CONTEXTO_PADRAO = AQUI.parent / "app" / "contexts" / "pesquisa-extensao-ifes"
sys.path.insert(0, str(NUCLEO))

from analytics_index import vetores  # noqa: E402
from analytics_index.vetores import LOTE, valores_distintos  # noqa: E402,F401


def _spec(contexto: Path) -> dict:
    spec = json.loads((contexto / "views.json").read_text(encoding="utf-8"))
    spec.setdefault("contexto", contexto.name)
    return spec


def gerar(banco: Path, contexto: Path, embedder, lote: int = LOTE, log=print) -> dict:
    return vetores.gerar(banco, [_spec(contexto)], embedder, lote=lote, log=log)


def atualizar(banco: Path, contexto: Path, embedder, lote: int = LOTE, log=print) -> dict:
    return vetores.atualizar(banco, [_spec(contexto)], embedder, lote=lote, log=log)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("banco", type=Path, help="dados.db que vai receber os vetores (use uma cópia)")
    parser.add_argument("--contexto", type=Path, default=CONTEXTO_PADRAO, help="pasta com o views.json")
    parser.add_argument("--modelo", help="chave do modelo (padrão: o do app)")
    parser.add_argument("--incremental", action="store_true",
                        help="reaproveita os vetores do mesmo modelo e só embeda os valores novos")
    args = parser.parse_args()
    if not args.banco.exists():
        print(f"erro: {args.banco} não existe.", file=sys.stderr)
        return 1
    if args.modelo:
        os.environ["ADITO_EMBEDDING_MODELO"] = args.modelo
    from analytics_index.modelo_local import EmbedderLocal

    embedder = EmbedderLocal()
    inicio = time.monotonic()
    if args.incremental:
        print(f"→ Atualizando os vetores com {embedder.modelo.chave} em {args.banco}…")
        resumo = atualizar(args.banco, args.contexto, embedder)
        if not resumo["feito"]:
            print(f"erro: {resumo['motivo']}; rode sem --incremental.", file=sys.stderr)
            return 1
        print(f"✓ +{resumo['novos']} e -{resumo['removidos']} valores em {time.monotonic() - inicio:.0f}s "
              f"({resumo['total']} no total).")
        return 0
    print(f"→ Gerando vetores com {embedder.modelo.chave} ({embedder.modelo.nome}) em {args.banco}…")
    resumo = gerar(args.banco, args.contexto, embedder)
    tamanho = args.banco.stat().st_size / 1_048_576
    print(f"✓ {resumo['meta']['total']} valores em {time.monotonic() - inicio:.0f}s; banco com {tamanho:.1f} MB.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
