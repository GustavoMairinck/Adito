#!/usr/bin/env python3
"""Empacota o modelo de embedding local para publicar na release `dados` (sem criptografia).

Baixa o modelo pelo fastembed (Hugging Face), junta os arquivos num `.tar.gz` e escreve o
`modelo.json` com chave, tamanho e SHA-256, que o app confere antes de usar.

Uso: python3 empacotar_modelo.py <pasta-saida> [--modelo chave]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tarfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
NUCLEO = AQUI.parent / "app" / "backend" / "nucleo"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("saida", type=Path)
    parser.add_argument("--modelo", help="chave do modelo (padrão: o do app)")
    args = parser.parse_args()
    if args.modelo:
        os.environ["ADITO_EMBEDDING_MODELO"] = args.modelo
    sys.path.insert(0, str(NUCLEO))
    from analytics_index.modelo_local import EmbedderLocal

    embedder = EmbedderLocal()
    embedder.embed_query("teste")  # baixa e carrega
    pasta = Path(embedder._carregado().model._model_dir)  # pasta resolvida pelo fastembed
    args.saida.mkdir(parents=True, exist_ok=True)
    temporario = args.saida / "modelo.tar.gz"
    with tarfile.open(temporario, "w:gz") as tar:
        for arquivo in sorted(p for p in pasta.rglob("*") if p.is_file() or p.is_symlink()):
            if ".cache" in arquivo.parts:
                continue
            tar.add(arquivo.resolve(), arcname=str(arquivo.relative_to(pasta)))  # segue os links do cache do HF
    sha = hashlib.sha256(temporario.read_bytes()).hexdigest()
    nome = f"modelo-{embedder.modelo.chave}-{sha[:12]}.tar.gz"
    final = args.saida / nome
    temporario.rename(final)
    manifesto = {
        "chave": embedder.modelo.chave,
        "nome": embedder.modelo.nome,
        "arquivo": nome,
        "tamanho": final.stat().st_size,
        "sha256": sha,
    }
    (args.saida / "modelo.json").write_text(json.dumps(manifesto, indent=2) + "\n", encoding="utf-8")
    print(f"✓ {nome} ({manifesto['tamanho'] / 1_048_576:.0f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
