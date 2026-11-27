#!/usr/bin/env python3
"""Gera os vetores de busca dos valores do `dados.db` com o modelo local (sem API de IA).

Lê as `embed_columns` de cada view no `views.json` do contexto, faz `SELECT DISTINCT` **por coluna**
(nunca a combinação de colunas) e grava dentro do próprio banco:

    adito_embedding_meta(chave, valor)            -- modelo, dim, data e totais
    adito_valor_embedding(view, coluna, valor, vetor)  -- float16, já normalizado

Colunas listadas em `multi_valor_columns` (ex.: `campus` em Extensão, que vem como "Serra; Vitória")
são quebradas em `; ` e cada parte vira um valor.

Roda na máquina de quem publica os dados, antes de cifrar (publicar_dados.sh chama este script
numa cópia do banco). Uso:
    python3 gerar_embeddings_dados.py caminho/dados.db [--contexto pasta/do/contexto] [--modelo chave]
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

AQUI = Path(__file__).resolve().parent
NUCLEO = AQUI.parent / "app" / "backend" / "nucleo"
CONTEXTO_PADRAO = AQUI.parent / "app" / "contexts" / "pesquisa-extensao-ifes"
LOTE = 256


def _aspas(nome: str) -> str:
    return '"' + nome.replace('"', '""') + '"'


def valores_distintos(conn: sqlite3.Connection, view: str, coluna: str, multi: bool) -> list[str]:
    linhas = conn.execute(
        f"SELECT DISTINCT CAST({_aspas(coluna)} AS TEXT) FROM {_aspas(view)} "
        f"WHERE {_aspas(coluna)} IS NOT NULL AND TRIM(CAST({_aspas(coluna)} AS TEXT)) <> ''"
    ).fetchall()
    vistos: dict[str, None] = {}
    for (bruto,) in linhas:
        partes = bruto.split("; ") if multi else [bruto]
        for parte in partes:
            valor = " ".join(parte.split())
            if valor:
                vistos.setdefault(valor, None)
    return list(vistos)


def gerar(banco: Path, contexto: Path, embedder, lote: int = LOTE, log=print) -> dict:
    spec = json.loads((contexto / "views.json").read_text(encoding="utf-8"))
    conn = sqlite3.connect(str(banco))
    try:
        conn.execute("DROP TABLE IF EXISTS adito_valor_embedding")
        conn.execute("DROP TABLE IF EXISTS adito_embedding_meta")
        conn.execute(
            "CREATE TABLE adito_valor_embedding (view TEXT NOT NULL, coluna TEXT NOT NULL, valor TEXT NOT NULL, "
            "vetor BLOB NOT NULL, PRIMARY KEY (view, coluna, valor))"
        )
        conn.execute("CREATE TABLE adito_embedding_meta (chave TEXT PRIMARY KEY, valor TEXT NOT NULL)")
        totais: dict[str, int] = {}
        for view in spec["views"]:
            multi = {c.lower() for c in view.get("multi_valor_columns", [])}
            for coluna in view.get("embed_columns", []):
                valores = valores_distintos(conn, view["name"], coluna, coluna.lower() in multi)
                for inicio in range(0, len(valores), lote):
                    parte = valores[inicio:inicio + lote]
                    vetores = embedder.matriz(parte).astype(np.float16)
                    conn.executemany(
                        "INSERT INTO adito_valor_embedding (view, coluna, valor, vetor) VALUES (?, ?, ?, ?)",
                        [(view["name"], coluna, v, vetor.tobytes()) for v, vetor in zip(parte, vetores)],
                    )
                totais[f"{view['name']}.{coluna}"] = len(valores)
                log(f"  {view['name']}.{coluna}: {len(valores)} valores")
        meta = {
            "modelo": embedder.modelo.chave,
            "modelo_nome": embedder.modelo.nome,
            "dim": str(embedder.modelo.dim),
            "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "total": str(sum(totais.values())),
            "contexto": spec.get("contexto", contexto.name),
        }
        conn.executemany("INSERT INTO adito_embedding_meta (chave, valor) VALUES (?, ?)", list(meta.items()))
        conn.commit()
        conn.execute("VACUUM")
    finally:
        conn.close()
    return {"meta": meta, "totais": totais}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("banco", type=Path, help="dados.db que vai receber os vetores (use uma cópia)")
    parser.add_argument("--contexto", type=Path, default=CONTEXTO_PADRAO, help="pasta com o views.json")
    parser.add_argument("--modelo", help="chave do modelo (padrão: o do app)")
    args = parser.parse_args()
    if not args.banco.exists():
        print(f"erro: {args.banco} não existe.", file=sys.stderr)
        return 1
    if args.modelo:
        os.environ["ADITO_EMBEDDING_MODELO"] = args.modelo
    sys.path.insert(0, str(NUCLEO))
    from analytics_index.modelo_local import EmbedderLocal

    embedder = EmbedderLocal()
    print(f"→ Gerando vetores com {embedder.modelo.chave} ({embedder.modelo.nome}) em {args.banco}…")
    inicio = time.monotonic()
    resumo = gerar(args.banco, args.contexto, embedder)
    tamanho = args.banco.stat().st_size / 1_048_576
    print(f"✓ {resumo['meta']['total']} valores em {time.monotonic() - inicio:.0f}s; banco com {tamanho:.1f} MB.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
