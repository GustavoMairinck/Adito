"""Gera um dados.db SQLite com a demonstração de vendas que vinha com o Oráculo web.

Usa as mesmas fontes do antigo bootstrap de vendas (Postgres):
  - backend/training/ddl/schema.sql      tabelas e a view vfactvendasresolved
  - mudanças/mudanca/03-dimensoes-faltantes.sql e 02-schema-dados.sql   os INSERTs (1.200 vendas)

Uso:
    python3 scripts/gerar_dados_demo.py caminho/do/dados.db
"""
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCHEMA = REPO / "backend" / "training" / "ddl" / "schema.sql"
INSERT_FILES = [
    REPO / "mudanças" / "mudanca" / "03-dimensoes-faltantes.sql",
    REPO / "mudanças" / "mudanca" / "02-schema-dados.sql",
]

# View sobre view, para o contexto de exemplo mostrar que views em níveis funcionam.
EXTRA_VIEWS = """
CREATE VIEW v_receita_produto AS
SELECT produto, categoria_produto, ano,
       SUM(receita_liquida) AS receita_liquida,
       SUM(lucro) AS lucro,
       COUNT(id_venda) AS vendas
FROM vfactvendasresolved
GROUP BY produto, categoria_produto, ano;
"""


def insert_statements(path: Path) -> list[str]:
    """Só os INSERTs; os arquivos trazem DDL e comandos de SQL Server (USE/GO) que não valem aqui."""
    return [
        line.strip().rstrip(";")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip().upper().startswith("INSERT INTO")
    ]


def main(target: Path) -> None:
    if target.exists():
        sys.exit(f"{target} já existe; apague-o antes de gerar de novo.")
    conn = sqlite3.connect(target)
    conn.executescript(SCHEMA.read_text(encoding="utf-8").replace("CREATE OR REPLACE VIEW", "CREATE VIEW"))
    with conn:
        for path in INSERT_FILES:
            for statement in insert_statements(path):
                conn.execute(statement)
    conn.executescript(EXTRA_VIEWS)
    conn.commit()

    for name in ("fact_vendas", "dim_produto", "dim_cliente", "dim_vendedor", "vfactvendasresolved", "v_receita_produto"):
        print(f"{name}: {conn.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]} linhas")
    conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
