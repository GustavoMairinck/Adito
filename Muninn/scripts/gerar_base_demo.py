"""
Gera um dados.db de DEMONSTRAÇÃO, 100% fictício, com o mesmo schema do dados.db real.

Serve para testar a distribuição (instalador, GitHub Pages, botão "Atualizar base") sem
publicar nenhum dado real: nomes, títulos e valores são inventados a partir de uma semente.

Uso:
    python gerar_base_demo.py --saida dist/dados.db --linhas 60 --semente 2026

Só usa a biblioteca padrão. Lê os mesmos DDLs (sql/00..04) que o popular_banco.py.
"""
from __future__ import annotations

import argparse
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parent / "sql"
DDLS = [
    "00_schema.sql",
    "01_tipos_e_dominios.sql",
    "02_tabelas.sql",
    "03_relacionamentos_e_juncoes.sql",
    "04_fatos_views.sql",
]

PRENOMES = ["Ana", "Bruno", "Carla", "Diego", "Elisa", "Fábio", "Gabriela", "Heitor", "Iara", "João",
            "Kátia", "Lucas", "Marina", "Nícolas", "Olívia", "Paulo", "Queila", "Rafael", "Sofia", "Tiago"]
SOBRENOMES = ["Fictício", "Exemplo", "Demonstração", "Modelo", "Teste", "Amostra", "Simulado", "Protótipo"]
TEMAS = ["energia solar", "robótica educacional", "qualidade da água", "agricultura urbana",
         "visão computacional", "reciclagem de resíduos", "ensino de matemática", "saúde mental",
         "internet das coisas", "materiais compósitos", "mobilidade urbana", "inclusão digital"]


def nome_pessoa(rng: random.Random, i: int) -> str:
    return f"{rng.choice(PRENOMES)} {rng.choice(SOBRENOMES)} {i:03d}"


def criar_schema(conn: sqlite3.Connection) -> None:
    for nome in DDLS:
        conn.executescript((SQL_DIR / nome).read_text(encoding="utf-8"))


def tabelas(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def ordem_topologica(conn: sqlite3.Connection, nomes: list[str]) -> list[str]:
    deps = {t: {fk[2] for fk in conn.execute(f'PRAGMA foreign_key_list("{t}")') if fk[2] != t} for t in nomes}
    ordem: list[str] = []
    feitos: set[str] = set()
    while len(ordem) < len(nomes):
        prontos = [t for t in nomes if t not in feitos and deps[t] <= feitos]
        if not prontos:  # ciclo: segue na ordem alfabética
            prontos = [t for t in nomes if t not in feitos][:1]
        for t in prontos:
            ordem.append(t)
            feitos.add(t)
    return ordem


def valor(rng: random.Random, tabela: str, coluna: str, tipo: str, i: int):
    c = coluna.lower()
    tipo = (tipo or "").upper()
    if c == "nome":
        if tabela in ("pessoa",):
            return nome_pessoa(rng, i)
        if tabela in ("iniciativa", "projeto_pesquisa", "acao", "producao", "grupo_pesquisa"):
            return f"Projeto fictício sobre {rng.choice(TEMAS)} {i:03d}"
        return f"{tabela.replace('_', ' ').title()} Fictícia {i:03d}"
    if c in ("titulo", "titulo_trabalho") or c.startswith("titulo"):
        return f"Estudo fictício sobre {rng.choice(TEMAS)} {i:03d}"
    if "email" in c or "cpf" in c or "telefone" in c or c == "numero_fax":
        return None  # nada que pareça dado de contato
    if c.startswith("data") or c.endswith("_data") or c.startswith("dt_"):
        return (date(2018, 1, 1) + timedelta(days=rng.randint(0, 365 * 8))).isoformat()
    if c.startswith("ano") or c.endswith("_ano"):
        return rng.randint(2018, 2026)
    if c.startswith("flag") or c.startswith("is_") or c.startswith("eh_") or "aprovado" in c or c.startswith("ativo"):
        return rng.randint(0, 1)
    if c in ("uf",):
        return "ES"
    if c in ("pais",):
        return "Brasil"
    if c == "sigla":
        return f"SIG{i:03d}"
    if "url" in c or "site" in c or "link" in c:
        return f"https://exemplo.invalid/{tabela}/{i}"
    if "INT" in tipo:
        return rng.randint(1, 40)
    if "REAL" in tipo or "NUM" in tipo or "valor" in c:
        return round(rng.uniform(1000, 150000), 2)
    return f"{coluna.replace('_', ' ')} fictício {i:03d}"


def preencher(conn: sqlite3.Connection, linhas: int, rng: random.Random) -> dict[str, int]:
    ja_preenchidas = {t for t in tabelas(conn) if conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] > 0}
    contagem: dict[str, int] = {}
    for t in ordem_topologica(conn, tabelas(conn)):
        if t in ja_preenchidas:  # domínios já semeados pelo DDL
            contagem[t] = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            continue
        cols = list(conn.execute(f'PRAGMA table_info("{t}")'))
        fks = {fk[3]: (fk[2], fk[4] or "id") for fk in conn.execute(f'PRAGMA foreign_key_list("{t}")')}
        pk_cols = [c[1] for c in cols if c[5] > 0]
        # Subclasse (PK que é FK da superclasse): uma linha por id da superclasse, sem repetir.
        subclasse = len(pk_cols) == 1 and pk_cols[0] in fks
        alvo = linhas * 2 if pk_cols and len(pk_cols) > 1 or not pk_cols else linhas
        ids_pai: list[int] = []
        if subclasse:
            pai, col_pai = fks[pk_cols[0]]
            ids_pai = [r[0] for r in conn.execute(f'SELECT "{col_pai}" FROM "{pai}"')]
            rng.shuffle(ids_pai)
            ids_pai = ids_pai[: max(1, len(ids_pai) // 2)]
            alvo = len(ids_pai)
        cache_fk: dict[str, list] = {}
        for i in range(1, alvo + 1):
            nomes, vals = [], []
            for _cid, col, tipo, notnull, _default, pk in cols:
                if pk and col == "id" and not subclasse and "INT" in (tipo or "").upper():
                    continue  # AUTOINCREMENT
                if subclasse and col == pk_cols[0]:
                    v = ids_pai[i - 1]
                elif col in fks:
                    pai, col_pai = fks[col]
                    if pai not in cache_fk:
                        cache_fk[pai] = [r[0] for r in conn.execute(f'SELECT "{col_pai}" FROM "{pai}"')]
                    opcoes = cache_fk[pai]
                    if col == "id_organizacao_pai" or (not notnull and rng.random() < 0.15):
                        v = None
                    else:
                        v = rng.choice(opcoes) if opcoes else None
                else:
                    v = valor(rng, t, col, tipo, i)
                if v is None and notnull:
                    v = valor(rng, t, "texto", "TEXT", i)
                nomes.append(f'"{col}"')
                vals.append(v)
            if not nomes:
                continue
            marcas = ", ".join("?" for _ in vals)
            conn.execute(f'INSERT OR IGNORE INTO "{t}" ({", ".join(nomes)}) VALUES ({marcas})', vals)
        contagem[t] = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    return contagem


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--saida", type=Path, default=Path("dist/dados.db"))
    ap.add_argument("--linhas", type=int, default=60, help="linhas por tabela de entidade")
    ap.add_argument("--semente", type=int, default=2026)
    args = ap.parse_args()

    args.saida.parent.mkdir(parents=True, exist_ok=True)
    if args.saida.exists():
        args.saida.unlink()
    rng = random.Random(args.semente)
    conn = sqlite3.connect(args.saida)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        criar_schema(conn)
        conn.execute("BEGIN")
        contagem = preencher(conn, args.linhas, rng)
        conn.commit()
        problemas = conn.execute("PRAGMA foreign_key_check").fetchall()
        if problemas:
            raise SystemExit(f"foreign_key_check falhou: {problemas[:5]}")
        # Arquivo pronto para ser aberto só-leitura numa pasta só-leitura: sem WAL.
        conn.execute("PRAGMA journal_mode = DELETE")
        conn.execute("VACUUM")
        views = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")]
        for v in views:
            n = conn.execute(f'SELECT COUNT(*) FROM "{v}"').fetchone()[0]
            print(f"  view {v}: {n} linhas")
    finally:
        conn.close()
    print(f"Base fictícia gerada em {args.saida} ({sum(contagem.values())} linhas em {len(contagem)} tabelas).")


if __name__ == "__main__":
    main()
