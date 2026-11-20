"""
Prepara um dados.db para publicação: gera `dados-<versão>.db.gz` e o `manifest.json` que o
botão "Atualizar base" do Muninn lê.

Uso:
    python publicar_base.py --base dist/dados.db --versao 2026.11.20 --saida site/dados

Com --se-mudou, não publica nada quando o conteúdo das tabelas é igual ao da base já
publicada (o arquivo pode mudar byte a byte sem os dados mudarem). Isso evita que o app ofereça
uma "atualização" igual à base que o usuário já tem.

Só usa a biblioteca padrão. O sha256 é do .db descompactado (é o que o app confere).
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import sqlite3
from datetime import date
from pathlib import Path


def impressao_conteudo(conn: sqlite3.Connection) -> str:
    """sha256 do dump SQL: muda só quando o schema ou alguma linha muda."""
    h = hashlib.sha256()
    for linha in conn.iterdump():
        h.update(linha.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", type=Path, required=True, help="dados.db pronto")
    ap.add_argument("--versao", required=True, help="ex.: 2026.11.20")
    ap.add_argument("--saida", type=Path, required=True, help="pasta publicada (ex.: site/dados)")
    ap.add_argument("--schema", type=int, default=1)
    ap.add_argument("--manter", type=int, default=2, help="quantas bases antigas manter na pasta")
    ap.add_argument("--se-mudou", action="store_true",
                    help="não publica se o conteúdo for igual ao do manifest.json já existente")
    args = ap.parse_args()

    # Sem WAL: o app abre a base só-leitura e não pode depender de -wal/-shm.
    conn = sqlite3.connect(args.base)
    try:
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise SystemExit("integrity_check falhou")
        conn.execute("PRAGMA journal_mode = DELETE")
        conteudo = impressao_conteudo(conn)
    finally:
        conn.close()

    atual = args.saida / "manifest.json"
    if args.se_mudou and atual.exists():
        anterior = json.loads(atual.read_text(encoding="utf-8"))
        if anterior.get("conteudo") == conteudo and anterior.get("schema") == args.schema:
            print(f"sem mudança: o conteúdo é igual ao da versão {anterior.get('versao')}; nada publicado")
            return 0

    args.saida.mkdir(parents=True, exist_ok=True)
    nome = f"dados-{args.versao}.db.gz"
    with args.base.open("rb") as src, gzip.open(args.saida / nome, "wb", compresslevel=9) as dst:
        shutil.copyfileobj(src, dst, 1 << 20)
    sha = hashlib.sha256(args.base.read_bytes()).hexdigest()

    manifest = {
        "versao": args.versao,
        "schema": args.schema,
        "url": nome,
        "sha256": sha,
        "conteudo": conteudo,
        "tamanho": (args.saida / nome).stat().st_size,
        "publicado_em": date.today().isoformat(),
    }
    # Manifest por último e trocado de uma vez: quem lê nunca vê um manifest apontando para um .gz incompleto.
    tmp = args.saida / "manifest.json.tmp"
    tmp.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(atual)

    antigas = sorted(p for p in args.saida.glob("dados-*.db.gz") if p.name != nome)
    for p in antigas[: max(0, len(antigas) - args.manter)]:
        p.unlink()
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
