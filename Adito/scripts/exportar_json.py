#!/usr/bin/env python3
"""Exporta do banco PostgreSQL `unificado` as tabelas usadas pelas views de fatos.

Lê o schema `unificado` em modo estritamente somente leitura (uma única sessão do
`psql` com `BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;` encerrada
com `ROLLBACK;`) e grava em `<saida>/<tabela>.json` cada uma das 41 tabelas usadas
pela proposta de fatos (`Docs/Fatos/PropostaFatos.md`), além de `<saida>/manifesto.json`
com metadados de colunas, tipos do catálogo, chaves primárias e chaves estrangeiras.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Sequence

AQUI = Path(__file__).resolve().parent
RAIZ_ADITO = AQUI.parent
SAIDA_PADRAO = RAIZ_ADITO / "etl" / "saida" / "json"
SCHEMA = "unificado"

PROPOSTA_ARQUIVO = "Docs/Fatos/PropostaFatos.md"
PROPOSTA_COMMIT = "c91761a"

# Tabelas do schema `unificado` usadas pelas seis views analíticas definidas em
# Docs/Fatos/PropostaFatos.md (commit c91761a da branch development).
TABELAS_POR_VIEW: dict[str, tuple[str, ...]] = {
    "vfact_extensao_acao_resolved": (
        "acao",
        "acao_campus",
        "area_conhecimento",
        "atividade",
        "fomento_acao",
        "grande_area",
        "iniciativa",
        "natureza",
        "organizacao",
        "pessoa",
        "tipo_acao",
    ),
    "vfact_extensao_participacao_resolved": (
        "acao",
        "acao_campus",
        "atividade",
        "iniciativa",
        "organizacao",
        "pessoa",
        "registro_participante",
        "situacao_participante",
        "tipo_acao",
        "tipo_atividade",
    ),
    "vfact_projeto_pesquisa_resolved": (
        "area_conhecimento",
        "grande_area",
        "iniciativa",
        "organizacao",
        "parceiro_demandante_projeto",  # citada no texto da seção 3.3.3 da proposta
        "pesquisador",
        "pessoa",
        "plano_trabalho",
        "projeto_pesquisa",
        "titulacao",
    ),
    "vfact_orientacao_bolsa_resolved": (
        "area_conhecimento",
        "curso",
        "edital",
        "estudante",
        "grande_area",
        "iniciativa",
        "nivel_treinamento",
        "organizacao",
        "orientacao",
        "pesquisador",
        "pessoa",
        "plano_trabalho",
        "programa",
        "projeto_pesquisa",
        "titulacao",
    ),
    "vfact_producao_cientifica_resolved": (
        "artigo_trabalho_evento",
        "autoria_producao",
        "categoria_producao_tecnica",
        "livro_capitulo",
        "organizacao",
        "patente_registro",
        "pesquisador",
        "pessoa",
        "pessoa_lattes",
        "producao",
        "producao_tecnica_artistica_bibliografica",
        "tipo_artigo_evento",
        "tipo_livro_capitulo",
        "tipo_patente_registro",
    ),
    "vfact_grupo_pesquisa_membro_resolved": (
        "area_conhecimento",
        "grande_area",
        "grupo_pesquisa",
        "grupo_pesquisa_cnpq",
        "membro_grupo",
        "membro_grupo_cnpq",
        "organizacao",
        "papel",
        "pesquisador",
        "pessoa",
        "titulacao",
    ),
}

TABELAS_PERMITIDAS: tuple[str, ...] = tuple(
    sorted({t for lista in TABELAS_POR_VIEW.values() for t in lista})
)

_IDENT_RE = re.compile(r"^[a-z_][a-z0-9_]*$")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
CPF_RE = re.compile(r"(?<![\d.])\d{3}\.\d{3}\.\d{3}-\d{2}(?![\d])|(?<!\d)\d{11}(?!\d)")


class ErroExportacao(RuntimeError):
    """Falha operacional de pré-requisito, segurança/LGPD ou validação."""


def ler_env(path: Path) -> dict[str, str]:
    """Lê variáveis simples CHAVE=VALOR de um arquivo .env sem expor valores."""
    env: dict[str, str] = {}
    if path.exists():
        for linha in path.read_text(encoding="utf-8").splitlines():
            if "=" in linha and not linha.lstrip().startswith("#"):
                k, v = linha.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def ler_padroes_compose(compose_path: Path | None = None) -> dict[str, str]:
    """Extrai nome do serviço, banco e usuário do docker-compose.yml e arquivos .env."""
    caminho = compose_path or (AQUI / "docker-compose.yml")
    env = {**ler_env(caminho.parent / ".env.example"), **ler_env(caminho.parent / ".env")}
    servico = ""
    usuario = env.get("POSTGRES_USER", "")
    banco = env.get("POSTGRES_DB", "")

    if caminho.exists():
        texto = caminho.read_text(encoding="utf-8")
        m_srv = re.search(r"(?m)^services:\s*\n\s+([a-zA-Z0-9_-]+):", texto)
        if m_srv:
            servico = m_srv.group(1)

        def _resolver(chave: str, atual: str) -> str:
            if atual:
                return atual
            m = re.search(rf"{chave}:\s*\$\{{{chave}:-([^}}]+)\}}", texto)
            if m:
                return m.group(1).strip()
            m_lit = re.search(rf"{chave}:\s*([^\s#]+)", texto)
            return m_lit.group(1).strip() if m_lit else ""

        usuario = _resolver("POSTGRES_USER", usuario)
        banco = _resolver("POSTGRES_DB", banco)

    return {"servico": servico, "usuario": usuario, "banco": banco}


def resolver_tabelas(especificacao: str | Sequence[str] | None) -> list[str]:
    """Valida e devolve a lista ordenada de tabelas a exportar."""
    if especificacao is None:
        return list(TABELAS_PERMITIDAS)
    if isinstance(especificacao, str):
        itens = [ p.strip() for p in especificacao.split(",") if p.strip() ]
    else:
        itens = [ str(p).strip() for p in especificacao if str(p).strip() ]
    if not itens:
        raise ValueError("A lista de tabelas informada está vazia.")
    permitidas = set(TABELAS_PERMITIDAS)
    invalidas = sorted({t for t in itens if t not in permitidas})
    if invalidas:
        raise ValueError(
            f"Tabela(s) fora da constante da proposta ({PROPOSTA_ARQUIVO}): {', '.join(invalidas)}"
        )
    vistos: list[str] = []
    for t in itens:
        if t not in vistos:
            vistos.append(t)
    return vistos


def _validar_identificador(nome: str) -> str:
    if not _IDENT_RE.fullmatch(nome):
        raise ValueError(f"Identificador SQL inválido: {nome!r}")
    return nome


def montar_sql_exportacao(
    tabela: str,
    chave_primaria: Sequence[str],
    colunas: Sequence[str],
) -> str:
    """Monta o comando SELECT que gera o JSON ordenado da tabela no PostgreSQL.

    - Se a tabela tiver chave primária no catálogo, ordena pelas colunas da PK.
    - Caso contrário (tabela de junção sem PK), ordena por todas as colunas.
    - Recusa qualquer tabela que não pertença a `TABELAS_PERMITIDAS`.
    """
    if tabela not in TABELAS_PERMITIDAS:
        raise ValueError(
            f"Tabela {tabela!r} não pertence à constante da proposta ({PROPOSTA_ARQUIVO})."
        )
    _validar_identificador(tabela)
    ordem_cols = list(chave_primaria) if chave_primaria else list(colunas)
    if not ordem_cols:
        raise ValueError(f"Tabela {tabela!r} sem colunas para ordenação.")
    for col in ordem_cols:
        _validar_identificador(col)
    clausula_ordem = ", ".join(f"t.{col}" for col in ordem_cols)
    return (
        f"SELECT coalesce(json_agg(t ORDER BY {clausula_ordem}), '[]'::json) "
        f"FROM {SCHEMA}.{tabela} t;"
    )


def verificar_pasta_ignorada_git(saida: Path) -> None:
    """Confirma que `<saida>/x.json` é ignorado pelo git antes de gravar qualquer arquivo."""
    saida_abs = saida.expanduser().resolve()
    ancestral = saida_abs
    while not ancestral.exists() and ancestral.parent != ancestral:
        ancestral = ancestral.parent
    alvo = saida_abs / "x.json"
    r = subprocess.run(
        ["git", "check-ignore", "-q", str(alvo)],
        cwd=ancestral,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if r.returncode != 0:
        raise ErroExportacao(
            f"A pasta de saída '{saida}' não está ignorada pelo git "
            "(git check-ignore falhou). Exportação abortada por proteção de LGPD."
        )


def verificar_pasta_saida_existente(saida: Path, forcar: bool) -> None:
    """Recusa sobrescrever uma pasta que já contenha arquivos .json sem `--forcar`."""
    if not saida.exists():
        return
    jsons_existentes = sorted(p.name for p in saida.glob("*.json") if p.is_file())
    if jsons_existentes and not forcar:
        raise ErroExportacao(
            f"A pasta de saída '{saida}' já contém {len(jsons_existentes)} arquivo(s) JSON. "
            "Use --forcar para sobrescrever."
        )


def obter_commit_git(cwd: Path | None = None) -> str | None:
    """Retorna o hash HEAD do repositório git ou None se estiver fora de um clone."""
    r = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=cwd or AQUI,
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        return None
    val = r.stdout.strip()
    return val or None


def gravar_atomico(destino: Path, conteudo: str) -> None:
    """Grava primeiro em arquivo temporário na mesma pasta e renomeia ao final."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_nome = tempfile.mkstemp(
        dir=destino.parent,
        prefix=f".{destino.name}.",
        suffix=".tmp",
    )
    tmp_path = Path(tmp_nome)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(conteudo)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, destino)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def _remover_jsons_gerados(pasta: Path) -> None:
    """Remove todos os arquivos .json e temporários da pasta de saída."""
    if not pasta.exists():
        return
    for padrao in ("*.json", ".*.tmp"):
        for arq in pasta.glob(padrao):
            if arq.is_file():
                arq.unlink(missing_ok=True)


def verificar_pii_arquivos(
    pasta: Path,
    tabelas: Sequence[str] | None = None,
) -> list[tuple[str, str, str]]:
    """Varre os JSONs exportados em busca de CPF ou e-mail.

    Se encontrar qualquer ocorrência, apaga os arquivos gerados na pasta e levanta
    `ErroExportacao` indicando apenas tabela, coluna e tipo de padrão (nunca o valor).
    """
    alvos: list[Path]
    if tabelas is not None:
        alvos = [pasta / f"{t}.json" for t in tabelas if (pasta / f"{t}.json").exists()]
    else:
        alvos = [
            p for p in sorted(pasta.glob("*.json"))
            if p.name != "manifesto.json" and p.is_file()
        ]

    achados: list[tuple[str, str, str]] = []
    for arq in alvos:
        tabela = arq.stem
        dados = json.loads(arq.read_text(encoding="utf-8"))
        if not isinstance(dados, list):
            continue
        for linha in dados:
            if not isinstance(linha, dict):
                continue
            for coluna, valor in linha.items():
                if valor is None or isinstance(valor, (bool, int, float)):
                    continue
                textos = [str(x) for x in valor] if isinstance(valor, list) else [str(valor)]
                for txt in textos:
                    if CPF_RE.search(txt):
                        item = (tabela, str(coluna), "CPF")
                        if item not in achados:
                            achados.append(item)
                    if EMAIL_RE.search(txt):
                        item = (tabela, str(coluna), "e-mail")
                        if item not in achados:
                            achados.append(item)

    if achados:
        _remover_jsons_gerados(pasta)
        locais = ", ".join(
            f"tabela={t} coluna={c} ({tipo})" for t, c, tipo in achados
        )
        raise ErroExportacao(
            f"Dado pessoal proibido detectado nos JSONs exportados ({locais}). "
            "Arquivos gerados foram removidos."
        )
    return achados


def _sql_consulta_catalogo() -> str:
    """Consulta única em pg_catalog que devolve versão, tabelas e metadados do schema."""
    return f"""
SELECT json_build_object(
    'postgres', current_setting('server_version'),
    'tabelas_schema', coalesce((
        SELECT json_agg(c.relname ORDER BY c.relname)
        FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = '{SCHEMA}' AND c.relkind = 'r'
    ), '[]'::json),
    'banco_populado', (
        EXISTS (SELECT 1 FROM {SCHEMA}.pessoa)
        OR EXISTS (SELECT 1 FROM {SCHEMA}.iniciativa)
        OR EXISTS (SELECT 1 FROM {SCHEMA}.organizacao)
        OR EXISTS (SELECT 1 FROM {SCHEMA}.producao)
    ),
    'catalogo', coalesce((
        SELECT json_object_agg(
            c.relname,
            json_build_object(
                'colunas', coalesce((
                    SELECT json_agg(
                        CASE
                            WHEN t.typtype = 'e' THEN json_build_object(
                                'nome', a.attname,
                                'tipo', pg_catalog.format_type(a.atttypid, a.atttypmod),
                                'anulavel', NOT a.attnotnull,
                                'valores_enum', coalesce((
                                    SELECT json_agg(e.enumlabel ORDER BY e.enumsortorder)
                                    FROM pg_catalog.pg_enum e
                                    WHERE e.enumtypid = t.oid
                                ), '[]'::json)
                            )
                            ELSE json_build_object(
                                'nome', a.attname,
                                'tipo', pg_catalog.format_type(a.atttypid, a.atttypmod),
                                'anulavel', NOT a.attnotnull
                            )
                        END
                        ORDER BY a.attnum
                    )
                    FROM pg_catalog.pg_attribute a
                    JOIN pg_catalog.pg_type t ON t.oid = a.atttypid
                    WHERE a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
                ), '[]'::json),
                'chave_primaria', coalesce((
                    SELECT json_agg(a.attname ORDER BY k.ord)
                    FROM pg_catalog.pg_index i
                    CROSS JOIN LATERAL unnest(i.indkey) WITH ORDINALITY AS k(attnum, ord)
                    JOIN pg_catalog.pg_attribute a
                        ON a.attrelid = i.indrelid AND a.attnum = k.attnum
                    WHERE i.indrelid = c.oid AND i.indisprimary
                ), '[]'::json),
                'chaves_estrangeiras', coalesce((
                    SELECT json_agg(
                        json_build_object(
                            'coluna', a_src.attname,
                            'tabela_destino', c_ref.relname,
                            'coluna_destino', a_ref.attname
                        )
                        ORDER BY a_src.attnum, con.conname, ck.ord
                    )
                    FROM pg_catalog.pg_constraint con
                    CROSS JOIN LATERAL unnest(con.conkey, con.confkey)
                        WITH ORDINALITY AS ck(attnum, ref_attnum, ord)
                    JOIN pg_catalog.pg_attribute a_src
                        ON a_src.attrelid = con.conrelid AND a_src.attnum = ck.attnum
                    JOIN pg_catalog.pg_class c_ref
                        ON c_ref.oid = con.confrelid
                    JOIN pg_catalog.pg_attribute a_ref
                        ON a_ref.attrelid = con.confrelid AND a_ref.attnum = ck.ref_attnum
                    WHERE con.conrelid = c.oid AND con.contype = 'f'
                ), '[]'::json)
            )
        )
        FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = '{SCHEMA}' AND c.relkind = 'r'
    ), '{{}}'::json)
)::text;
""".strip()


def montar_comando_psql(
    modo: str,
    servico: str | None = None,
    banco: str | None = None,
    usuario: str | None = None,
) -> list[str]:
    """Monta a linha de comando do `psql` para o modo `docker` ou `conexao`."""
    flags_psql = ["psql", "-X", "-q", "-At", "-v", "ON_ERROR_STOP=1"]
    if modo == "docker":
        padroes = ler_padroes_compose()
        srv = servico or padroes["servico"]
        usr = usuario or padroes["usuario"]
        db = banco or padroes["banco"]
        if not srv or not usr or not db:
            raise ErroExportacao(
                "Não foi possível determinar serviço, usuário ou banco do docker-compose.yml."
            )
        return [
            "docker",
            "compose",
            "exec",
            "-T",
            srv,
            *flags_psql,
            "-U",
            usr,
            "-d",
            db,
        ]
    if modo == "conexao":
        cmd = list(flags_psql)
        if usuario:
            cmd.extend(["-U", usuario])
        if banco:
            cmd.extend(["-d", banco])
        return cmd
    raise ValueError(f"Modo inválido: {modo!r}")


def exportar_do_banco(
    saida: Path,
    tabelas: Sequence[str],
    modo: str = "docker",
    servico: str | None = None,
    banco: str | None = None,
    usuario: str | None = None,
    forcar: bool = False,
) -> dict[str, Any]:
    """Executa toda a leitura numa única sessão REPEATABLE READ READ ONLY + ROLLBACK."""
    tabelas_resolvidas = resolver_tabelas(tabelas)
    verificar_pasta_ignorada_git(saida)
    verificar_pasta_saida_existente(saida, forcar=forcar)

    cmd = montar_comando_psql(modo=modo, servico=servico, banco=banco, usuario=usuario)
    proc = subprocess.Popen(
        cmd,
        cwd=AQUI,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    assert proc.stdin is not None and proc.stdout is not None and proc.stderr is not None

    try:
        bloco_inicial = "\n".join([
            "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;",
            f"SET search_path TO {SCHEMA}, public;",
            "SELECT '__INICIO_CATALOGO__';",
            _sql_consulta_catalogo(),
            "SELECT '__FIM_CATALOGO__';",
            "",
        ])
        proc.stdin.write(bloco_inicial)
        proc.stdin.flush()

        linhas_catalogo: list[str] = []
        lendo_catalogo = False
        for linha in proc.stdout:
            s = linha.rstrip("\r\n")
            if s == "__INICIO_CATALOGO__":
                lendo_catalogo = True
                continue
            if s == "__FIM_CATALOGO__":
                break
            if lendo_catalogo:
                linhas_catalogo.append(s)

        if not linhas_catalogo:
            proc.stdin.close()
            err = proc.stderr.read().strip()
            proc.wait()
            raise ErroExportacao(
                f"Falha ao consultar o catálogo do PostgreSQL no modo {modo!r}: {err or 'sem resposta do psql'}"
            )

        info_banco = json.loads("\n".join(linhas_catalogo))
        tabelas_schema = set(info_banco.get("tabelas_schema") or [])
        faltantes = [t for t in tabelas_resolvidas if t not in tabelas_schema]
        if faltantes:
            proc.stdin.write("ROLLBACK;\n")
            proc.stdin.close()
            proc.wait()
            raise ErroExportacao(
                f"Tabela(s) ausente(s) no schema '{SCHEMA}': {', '.join(faltantes)}. "
                "Nenhuma tabela foi criada."
            )

        if not info_banco.get("banco_populado"):
            proc.stdin.write("ROLLBACK;\n")
            proc.stdin.close()
            proc.wait()
            raise ErroExportacao(
                f"O banco no schema '{SCHEMA}' está vazio. "
                "Popule o banco antes de exportar; nada foi alterado."
            )

        catalogo = info_banco["catalogo"]
        comandos_tabelas: list[str] = []
        for t in tabelas_resolvidas:
            meta_t = catalogo[t]
            pk = meta_t.get("chave_primaria") or []
            cols = [c["nome"] for c in meta_t.get("colunas") or []]
            sql_json = montar_sql_exportacao(t, pk, cols)
            comandos_tabelas.append(
                f"SELECT '__INICIO_TABELA__:{t}:' || (SELECT count(*) FROM {SCHEMA}.{t});"
            )
            comandos_tabelas.append(sql_json)
            comandos_tabelas.append(f"SELECT '__FIM_TABELA__:{t}';")
        comandos_tabelas.append("ROLLBACK;")

        resto_stdout, stderr_txt = proc.communicate(input="\n".join(comandos_tabelas) + "\n")
        if proc.returncode != 0:
            raise ErroExportacao(
                f"Erro durante a leitura das tabelas no psql (código {proc.returncode}): "
                f"{stderr_txt.strip()}"
            )
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()

    # Extrai o JSON e a contagem de cada tabela lida na mesma transação
    contagens_transacao: dict[str, int] = {}
    jsons_brutos: dict[str, str] = {}
    tabela_atual: str | None = None
    buffer_linhas: list[str] = []

    for linha in resto_stdout.splitlines():
        if linha.startswith("__INICIO_TABELA__:"):
            partes = linha.split(":", 2)
            tabela_atual = partes[1]
            contagens_transacao[tabela_atual] = int(partes[2])
            buffer_linhas = []
        elif linha.startswith("__FIM_TABELA__:"):
            fim_t = linha.split(":", 1)[1]
            if tabela_atual != fim_t:
                raise ErroExportacao(
                    f"Marcador de tabela fora de sincronia: esperado {tabela_atual!r}, obtido {fim_t!r}."
                )
            jsons_brutos[tabela_atual] = "\n".join(buffer_linhas).strip()
            tabela_atual = None
            buffer_linhas = []
        elif tabela_atual is not None:
            buffer_linhas.append(linha)

    saida.mkdir(parents=True, exist_ok=True)
    conjunto_exportadas = set(tabelas_resolvidas)
    manifesto_tabelas: dict[str, Any] = {}

    for t in tabelas_resolvidas:
        if t not in jsons_brutos:
            raise ErroExportacao(f"Saída JSON da tabela {t!r} não foi recebida do PostgreSQL.")
        texto_json = jsons_brutos[t]
        arq_tabela = saida / f"{t}.json"
        gravar_atomico(arq_tabela, texto_json + "\n")

        # Confere imediatamente que o arquivo gravado é JSON válido
        try:
            parsed = json.loads(arq_tabela.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            _remover_jsons_gerados(saida)
            raise ErroExportacao(f"Arquivo gravado '{arq_tabela.name}' não é JSON válido: {exc}") from exc
        if not isinstance(parsed, list):
            _remover_jsons_gerados(saida)
            raise ErroExportacao(f"Arquivo '{arq_tabela.name}' não contém uma lista JSON.")

        meta_t = catalogo[t]
        fks_formatadas = [
            {
                "coluna": fk["coluna"],
                "tabela_destino": fk["tabela_destino"],
                "coluna_destino": fk["coluna_destino"],
                "destino_exportado": fk["tabela_destino"] in conjunto_exportadas,
            }
            for fk in (meta_t.get("chaves_estrangeiras") or [])
        ]
        manifesto_tabelas[t] = {
            "linhas": contagens_transacao[t],
            "colunas": meta_t.get("colunas") or [],
            "chave_primaria": meta_t.get("chave_primaria") or [],
            "chaves_estrangeiras": fks_formatadas,
        }

    manifesto = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "commit": obter_commit_git(),
        "proposta": {
            "arquivo": PROPOSTA_ARQUIVO,
            "commit": PROPOSTA_COMMIT,
        },
        "postgres": info_banco.get("postgres"),
        "schema": SCHEMA,
        "tabelas": manifesto_tabelas,
    }
    gravar_atomico(
        saida / "manifesto.json",
        json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n",
    )

    # Varre todos os JSONs gerados atrás de padrões de CPF e e-mail (seção 5.5)
    verificar_pii_arquivos(saida, tabelas_resolvidas)

    # Roda a validação final completa (seção 5.6)
    return validar_exportacao(saida)


def validar_exportacao(pasta: Path) -> dict[str, Any]:
    """Valida JSONs e manifesto em `pasta` sem conectar no banco (seção 5.6)."""
    arq_manifesto = pasta / "manifesto.json"
    if not arq_manifesto.is_file():
        raise ErroExportacao(f"Manifesto não encontrado em '{arq_manifesto}'.")

    try:
        manifesto = json.loads(arq_manifesto.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ErroExportacao(f"'manifesto.json' não é JSON válido: {exc}") from exc

    tabelas_meta = manifesto.get("tabelas")
    if not isinstance(tabelas_meta, dict) or not tabelas_meta:
        raise ErroExportacao("'manifesto.json' não contém dicionário 'tabelas' válido.")

    dados_por_tabela: dict[str, list[dict[str, Any]]] = {}
    tamanhos_por_tabela: dict[str, int] = {}

    for tabela, meta in tabelas_meta.items():
        arq = pasta / f"{tabela}.json"
        if not arq.is_file():
            raise ErroExportacao(f"Arquivo esperado '{arq.name}' não existe na pasta '{pasta}'.")
        tamanhos_por_tabela[tabela] = arq.stat().st_size

        try:
            itens = json.loads(arq.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ErroExportacao(f"Arquivo '{arq.name}' não é JSON válido: {exc}") from exc

        if not isinstance(itens, list):
            raise ErroExportacao(f"Arquivo '{arq.name}' deve conter uma lista JSON.")

        esperado = meta.get("linhas")
        if len(itens) != esperado:
            raise ErroExportacao(
                f"Contagem divergente em '{arq.name}': manifesto registra {esperado} linha(s), "
                f"mas o arquivo tem {len(itens)}."
            )

        colunas_esperadas = [c["nome"] for c in (meta.get("colunas") or [])]
        for idx, obj in enumerate(itens):
            if not isinstance(obj, dict):
                raise ErroExportacao(
                    f"Item #{idx} de '{arq.name}' não é um objeto JSON."
                )
            chaves_obj = list(obj.keys())
            if chaves_obj != colunas_esperadas:
                raise ErroExportacao(
                    f"Colunas divergentes ou fora de ordem em '{arq.name}' (linha #{idx}): "
                    f"esperado {colunas_esperadas}, obtido {chaves_obj}."
                )

        dados_por_tabela[tabela] = itens

    # Integridade referencial entre arquivos exportados
    resumo_tabelas: dict[str, dict[str, Any]] = {}
    fks_fora_lista: list[dict[str, str]] = []
    total_fks_conferidas = 0

    for tabela, meta in tabelas_meta.items():
        fks = meta.get("chaves_estrangeiras") or []
        conferidas_tabela = 0
        for fk in fks:
            col_origem = fk["coluna"]
            tab_dest = fk["tabela_destino"]
            col_dest = fk["coluna_destino"]
            exportado = bool(fk.get("destino_exportado", tab_dest in tabelas_meta))

            if not exportado or tab_dest not in dados_por_tabela:
                fks_fora_lista.append({
                    "tabela_origem": tabela,
                    "coluna_origem": col_origem,
                    "tabela_destino": tab_dest,
                    "coluna_destino": col_dest,
                })
                continue

            valores_destino = {
                linha.get(col_dest)
                for linha in dados_por_tabela[tab_dest]
                if linha.get(col_dest) is not None
            }
            orfaos = sum(
                1
                for linha in dados_por_tabela[tabela]
                if linha.get(col_origem) is not None and linha.get(col_origem) not in valores_destino
            )
            if orfaos:
                raise ErroExportacao(
                    f"FK quebrada em '{tabela}.{col_origem}' -> '{tab_dest}.{col_dest}': "
                    f"{orfaos} registro(s) sem correspondência no arquivo de destino."
                )
            conferidas_tabela += 1
            total_fks_conferidas += 1

        resumo_tabelas[tabela] = {
            "linhas": len(dados_por_tabela[tabela]),
            "colunas": len(meta.get("colunas") or []),
            "tamanho_bytes": tamanhos_por_tabela[tabela],
            "fks_conferidas": conferidas_tabela,
        }

    return {
        "pasta": str(pasta),
        "total_tabelas": len(resumo_tabelas),
        "total_linhas": sum(r["linhas"] for r in resumo_tabelas.values()),
        "total_fks_conferidas": total_fks_conferidas,
        "tabelas": resumo_tabelas,
        "fks_fora_da_lista": fks_fora_lista,
    }


def imprimir_resumo(relatorio: dict[str, Any]) -> None:
    """Imprime o resumo por tabela e as FKs que apontam para fora da lista."""
    print(
        f"Exportação validada em: {relatorio['pasta']} "
        f"({relatorio['total_tabelas']} tabelas, {relatorio['total_linhas']} linhas, "
        f"{relatorio['total_fks_conferidas']} FKs conferidas)"
    )
    print(f"{'Tabela':42s} {'Linhas':>8s} {'Colunas':>8s} {'Tamanho (B)':>12s} {'FKs OK':>8s}")
    print("-" * 82)
    for tabela, info in relatorio["tabelas"].items():
        print(
            f"{tabela:42s} {info['linhas']:8d} {info['colunas']:8d} "
            f"{info['tamanho_bytes']:12d} {info['fks_conferidas']:8d}"
        )
    fora = relatorio.get("fks_fora_da_lista") or []
    if fora:
        print(f"\nFKs que apontam para tabelas fora da lista exportada ({len(fora)}):")
        for fk in fora:
            print(
                f"  - {fk['tabela_origem']}.{fk['coluna_origem']} -> "
                f"{fk['tabela_destino']}.{fk['coluna_destino']}"
            )
    else:
        print("\nFKs que apontam para tabelas fora da lista exportada: 0")


def construir_parser() -> argparse.ArgumentParser:
    padroes = ler_padroes_compose()
    ap = argparse.ArgumentParser(
        prog="exportar_json.py",
        description=(
            "Exporta em JSON (somente leitura) as 41 tabelas do schema `unificado` do "
            "PostgreSQL usadas pelas views analíticas da proposta de fatos "
            f"({PROPOSTA_ARQUIVO}, commit {PROPOSTA_COMMIT}), junto com o manifesto.json."
        ),
    )
    ap.add_argument(
        "--saida",
        type=Path,
        default=SAIDA_PADRAO,
        help=f"Pasta onde serão gravados os JSONs e o manifesto.json (padrão: {SAIDA_PADRAO}).",
    )
    ap.add_argument(
        "--modo",
        choices=("docker", "conexao"),
        default="docker",
        help=(
            "Modo de execução do psql: 'docker' usa `docker compose exec -T <servico> psql` "
            "a partir de Adito/scripts/; 'conexao' usa o `psql` local com as variáveis da libpq "
            "(PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD/.pgpass). Padrão: docker."
        ),
    )
    ap.add_argument(
        "--servico",
        default=padroes["servico"] or None,
        help=(
            "Nome do serviço PostgreSQL no docker-compose.yml para o modo docker "
            f"(padrão lido do compose: {padroes['servico'] or 'auto'})."
        ),
    )
    ap.add_argument(
        "--banco",
        default=None,
        help=(
            "Nome do banco PostgreSQL no modo docker "
            f"(padrão lido do compose/.env: {padroes['banco'] or 'auto'})."
        ),
    )
    ap.add_argument(
        "--usuario",
        default=None,
        help=(
            "Usuário do PostgreSQL no modo docker "
            f"(padrão lido do compose/.env: {padroes['usuario'] or 'auto'})."
        ),
    )
    ap.add_argument(
        "--tabelas",
        default=None,
        help=(
            "Subconjunto de tabelas separado por vírgula (ex.: pessoa,organizacao,acao). "
            "Recusa qualquer nome fora das 41 tabelas da proposta."
        ),
    )
    ap.add_argument(
        "--forcar",
        action="store_true",
        help="Sobrescreve a pasta de saída caso ela já contenha arquivos JSON.",
    )
    ap.add_argument(
        "--so-validar",
        type=Path,
        default=None,
        metavar="PASTA",
        help=(
            "Executa apenas a validação pós-exportação (JSON válido, contagens, ordem das "
            "colunas e integridade referencial das FKs) sobre uma pasta existente, sem "
            "conectar ao banco."
        ),
    )
    return ap


def main(argv: Iterable[str] | None = None) -> int:
    ap = construir_parser()
    args = ap.parse_args(list(argv) if argv is not None else None)

    try:
        if args.so_validar is not None:
            relatorio = validar_exportacao(args.so_validar.expanduser().resolve())
            imprimir_resumo(relatorio)
            return 0

        tabelas = resolver_tabelas(args.tabelas)
        saida = args.saida.expanduser().resolve()
        relatorio = exportar_do_banco(
            saida=saida,
            tabelas=tabelas,
            modo=args.modo,
            servico=args.servico,
            banco=args.banco,
            usuario=args.usuario,
            forcar=args.forcar,
        )
        imprimir_resumo(relatorio)
        return 0
    except (ErroExportacao, ValueError) as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
