"""Grava os vetores dos valores no `dados.db`: a carga completa e a atualização incremental.

- **Carga completa (`gerar`)**: a equipe roda na publicação dos dados (`publicar_dados.sh`). Gera um
  vetor por valor distinto das `embed_columns` e vai no `dados.db` da release.
- **Incremental na publicação (`atualizar`)**: o `--incremental` do script; reaproveita os vetores
  do mesmo modelo dentro da cópia que vai ser publicada.
- **Na máquina do usuário (`completar_no_app_db`)**: o `dados.db` só é lido. Os valores que ainda
  não têm vetor nele são embedados com o modelo local e vão para o app.db
  (`analytics_text_embedding`, `embedding_provider = 'local'`). O índice junta as duas fontes.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np

TABELA_META = "adito_embedding_meta"
TABELA_VETORES = "adito_valor_embedding"
LOTE = 256

logger = logging.getLogger(__name__)


def _aspas(nome: str) -> str:
    return '"' + nome.replace('"', '""') + '"'


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


def _colunas(conn: sqlite3.Connection, specs: Iterable[dict]) -> list[tuple[str, str, bool]]:
    """(view, coluna, multi) das `embed_columns`, só das views que existem neste banco."""
    existentes = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view')")}
    saida: list[tuple[str, str, bool]] = []
    for spec in specs:
        for view in spec.get("views", []):
            if view["name"] not in existentes:
                continue
            multi = {c.lower() for c in view.get("multi_valor_columns", [])}
            for coluna in view.get("embed_columns", []):
                item = (view["name"], coluna, coluna.lower() in multi)
                if item not in saida:
                    saida.append(item)
    return saida


def _inserir(conn, embedder, view: str, coluna: str, valores: list[str], lote: int) -> None:
    for inicio in range(0, len(valores), lote):
        parte = valores[inicio:inicio + lote]
        vetores = embedder.matriz(parte).astype(np.float16)
        conn.executemany(
            f"INSERT OR REPLACE INTO {TABELA_VETORES} (view, coluna, valor, vetor) VALUES (?, ?, ?, ?)",
            [(view, coluna, v, vetor.tobytes()) for v, vetor in zip(parte, vetores)],
        )


def _gravar_meta(conn, embedder, total: int, contexto: str, extra: dict | None = None) -> dict:
    meta = {
        "modelo": embedder.modelo.chave,
        "modelo_nome": embedder.modelo.nome,
        "dim": str(embedder.modelo.dim),
        "total": str(total),
        "contexto": contexto,
        **(extra or {}),
    }
    conn.executemany(f"INSERT OR REPLACE INTO {TABELA_META} (chave, valor) VALUES (?, ?)", list(meta.items()))
    return dict(conn.execute(f"SELECT chave, valor FROM {TABELA_META}").fetchall())


def gerar(banco: Path, specs: list[dict], embedder, lote: int = LOTE, log=print) -> dict:
    """Carga completa: apaga os vetores e gera todos de novo."""
    conn = sqlite3.connect(str(banco), timeout=30)
    try:
        conn.execute(f"DROP TABLE IF EXISTS {TABELA_VETORES}")
        conn.execute(f"DROP TABLE IF EXISTS {TABELA_META}")
        conn.execute(
            f"CREATE TABLE {TABELA_VETORES} (view TEXT NOT NULL, coluna TEXT NOT NULL, valor TEXT NOT NULL, "
            "vetor BLOB NOT NULL, PRIMARY KEY (view, coluna, valor))"
        )
        conn.execute(f"CREATE TABLE {TABELA_META} (chave TEXT PRIMARY KEY, valor TEXT NOT NULL)")
        totais: dict[str, int] = {}
        for view, coluna, multi in _colunas(conn, specs):
            valores = valores_distintos(conn, view, coluna, multi)
            _inserir(conn, embedder, view, coluna, valores, lote)
            totais[f"{view}.{coluna}"] = len(valores)
            log(f"  {view}.{coluna}: {len(valores)} valores")
        contexto = ", ".join(s.get("contexto", "") for s in specs if s.get("contexto"))
        meta = _gravar_meta(conn, embedder, sum(totais.values()), contexto, {"gerado_em": _agora()})
        conn.commit()
        conn.execute("VACUUM")
    finally:
        conn.close()
    return {"meta": meta, "totais": totais}


def atualizar(banco: Path, specs: list[dict], embedder, lote: int = LOTE, log=print) -> dict:
    """Incremental: embeda só os valores que faltam e apaga os que não existem mais.

    Só roda sobre vetores do mesmo modelo. Sem vetores, ou com vetores de outro modelo, não faz
    nada: a carga grande é da publicação dos dados, não da máquina do usuário.
    """
    conn = sqlite3.connect(str(banco), timeout=30)
    try:
        tabelas = {
            r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN (?, ?)", [TABELA_META, TABELA_VETORES]
            )
        }
        if tabelas != {TABELA_META, TABELA_VETORES}:
            return {"feito": False, "motivo": "o dados.db não traz os vetores da publicação", "novos": 0, "removidos": 0}
        meta = dict(conn.execute(f"SELECT chave, valor FROM {TABELA_META}").fetchall())
        if meta.get("modelo") != embedder.modelo.chave:
            return {"feito": False, "motivo": f"vetores do modelo {meta.get('modelo')!r}", "novos": 0, "removidos": 0}

        novos = removidos = total = 0
        colunas = _colunas(conn, specs)
        for view, coluna, multi in colunas:
            atuais = set(valores_distintos(conn, view, coluna, multi))
            gravados = {
                r[0] for r in conn.execute(
                    f"SELECT valor FROM {TABELA_VETORES} WHERE view = ? AND coluna = ?", [view, coluna]
                )
            }
            faltam = sorted(atuais - gravados)
            sobram = gravados - atuais
            if faltam:
                _inserir(conn, embedder, view, coluna, faltam, lote)
                log(f"  {view}.{coluna}: +{len(faltam)} valores")
            if sobram:
                conn.executemany(
                    f"DELETE FROM {TABELA_VETORES} WHERE view = ? AND coluna = ? AND valor = ?",
                    [(view, coluna, v) for v in sobram],
                )
            novos, removidos, total = novos + len(faltam), removidos + len(sobram), total + len(atuais)

        # Colunas que saíram das embed_columns (ou views que sumiram) também saem do índice.
        manter = {(v, c) for v, c, _ in colunas}
        orfas = [p for p in conn.execute(f"SELECT DISTINCT view, coluna FROM {TABELA_VETORES}") if tuple(p) not in manter]
        for view, coluna in orfas:
            removidos += conn.execute(
                f"DELETE FROM {TABELA_VETORES} WHERE view = ? AND coluna = ?", [view, coluna]
            ).rowcount

        if novos or removidos:
            _gravar_meta(conn, embedder, total, meta.get("contexto", ""), {"atualizado_em": _agora()})
            conn.commit()
        return {"feito": True, "motivo": "", "novos": novos, "removidos": removidos, "total": total}
    finally:
        conn.close()


# ── Na máquina do usuário: a diferença vai para o app.db, o dados.db só é lido ────────

PROVEDOR_LOCAL = "local"
TABELA_LOCAL = "analytics_text_embedding"

_feitas: set[str] = set()
_lock = threading.Lock()


def hash_valor(coluna: str, valor: str) -> str:
    return hashlib.sha256(f"{coluna}\x1f{valor}".encode("utf-8")).hexdigest()


def _abrir_leitura(banco: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{Path(banco).resolve().as_uri()}?mode=ro", uri=True, timeout=30)


def _vetores_do_dados(conn: sqlite3.Connection, modelo: str) -> dict[tuple[str, str], set[str]] | None:
    """Valores que já têm vetor no dados.db, ou None se ele não traz vetores deste modelo."""
    tabelas = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN (?, ?)", [TABELA_META, TABELA_VETORES]
        )
    }
    if tabelas != {TABELA_META, TABELA_VETORES}:
        return None
    meta = dict(conn.execute(f"SELECT chave, valor FROM {TABELA_META}").fetchall())
    if meta.get("modelo") != modelo:
        return None
    gravados: dict[tuple[str, str], set[str]] = {}
    for view, coluna, valor in conn.execute(f"SELECT view, coluna, valor FROM {TABELA_VETORES}"):
        gravados.setdefault((view, coluna), set()).add(valor)
    return gravados


def completar_no_app_db(banco: Path, contextos: list, embedder, lote: int = LOTE) -> dict:
    """Grava no app.db (`analytics_text_embedding`) só os valores sem vetor no dados.db.

    `contextos` são os registros `Contexto` ativos (id, tenant_id e views com as embed_columns).
    Apaga as linhas locais que não fazem mais falta e as antigas, geradas por API.
    """
    from core import db

    modelo = embedder.modelo.chave
    with closing(_abrir_leitura(banco)) as conn:
        gravados = _vetores_do_dados(conn, modelo)
        if gravados is None:
            return {"feito": False, "motivo": "o dados.db não traz vetores deste modelo", "novos": 0, "removidos": 0}
        faltam_por_ctx: dict[str, tuple[object, list[tuple[str, str, str]]]] = {}
        for ctx in contextos:
            faltam: list[tuple[str, str, str]] = []
            for view, coluna, multi in _colunas(conn, [{"views": ctx.views}]):
                ja = gravados.get((view, coluna), set())
                faltam += [(view, coluna, v) for v in valores_distintos(conn, view, coluna, multi) if v not in ja]
            faltam_por_ctx[db.to_db_id(ctx.id)] = (ctx, faltam)

    novos = removidos = 0
    removidos += db.execute(
        f"DELETE FROM {TABELA_LOCAL} WHERE embedding_provider IS NULL OR embedding_provider <> ?", [PROVEDOR_LOCAL]
    ).rowcount  # vetores da API, da versão antiga: não servem para o modelo local
    removidos += db.execute(
        f"DELETE FROM {TABELA_LOCAL} WHERE embedding_model <> ?", [modelo]
    ).rowcount
    for ctx_id, (ctx, faltam) in faltam_por_ctx.items():
        querem = {(view, hash_valor(coluna, valor)): (view, coluna, valor) for view, coluna, valor in faltam}
        tem = {
            (r["source_table"], r["value_hash"]): r["id"]
            for r in db.execute(f"SELECT id, source_table, value_hash FROM {TABELA_LOCAL} WHERE contexto_id = ?", [ctx_id])
        }
        sobram = [tem[k] for k in tem.keys() - querem.keys()]
        if sobram:
            db.connect().executemany(f"DELETE FROM {TABELA_LOCAL} WHERE id = ?", [(i,) for i in sobram])
            removidos += len(sobram)
        novas = [querem[k] for k in querem.keys() - tem.keys()]
        for inicio in range(0, len(novas), lote):
            parte = novas[inicio:inicio + lote]
            vetores = embedder.matriz([v for _, _, v in parte])
            agora = db.to_db_dt(db.utcnow())
            with db.transaction() as c:
                c.executemany(
                    f"INSERT OR REPLACE INTO {TABELA_LOCAL} (id, tenant_id, contexto_id, source_table, embedding_text, "
                    "payload_json, value_hash, embedding, embedding_provider, embedding_model, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        (db.new_id(), db.to_db_id(ctx.tenant_id), ctx_id, view, valor,
                         json.dumps({"coluna": coluna, "valor": valor}, ensure_ascii=False),
                         hash_valor(coluna, valor), db.to_blob(vetor), PROVEDOR_LOCAL, modelo, agora, agora)
                        for (view, coluna, valor), vetor in zip(parte, vetores)
                    ],
                )
            novos += len(parte)
    return {"feito": True, "motivo": "", "novos": novos, "removidos": removidos}


def vetores_locais(modelo: str) -> list[tuple[str, str, str, np.ndarray]]:
    """(view, coluna, valor, vetor) gravados no app.db para este modelo. Não cria o app.db."""
    from core.datastore import app_db_path

    caminho = app_db_path()
    if not caminho.exists():
        return []
    try:
        with closing(_abrir_leitura(caminho)) as conn:
            linhas = conn.execute(
                f"SELECT source_table, payload_json, embedding FROM {TABELA_LOCAL} "
                "WHERE embedding_provider = ? AND embedding_model = ? AND embedding IS NOT NULL",
                [PROVEDOR_LOCAL, modelo],
            ).fetchall()
    except sqlite3.Error:
        return []
    saida = []
    for view, payload, blob in linhas:
        dados = json.loads(payload or "{}")
        saida.append((view, dados.get("coluna", ""), dados.get("valor", ""), np.frombuffer(bytes(blob), dtype=np.float32)))
    return saida


def atualizar_dados_locais(embedder, banco: Path | None = None) -> dict | None:
    """Incremental na máquina do usuário, uma vez por versão do dados.db."""
    from core.datastore import dados_db_path
    from core.records import Contexto

    banco = Path(banco or dados_db_path())
    if not banco.exists():
        return None
    with _lock:
        st = banco.stat()
        versao = f"{st.st_size}-{st.st_mtime_ns}:{embedder.modelo.chave}"
        if versao in _feitas:
            return None
        resumo = completar_no_app_db(banco, Contexto.select("is_active = 1"), embedder)
        _feitas.add(versao)
    if resumo["novos"] or resumo["removidos"]:
        from .valores import invalidar_indice

        invalidar_indice()
        logger.info("Vetores locais no app.db: +%s, -%s", resumo["novos"], resumo["removidos"])
    elif not resumo["feito"]:
        logger.info("Atualização incremental dos vetores não rodou: %s", resumo["motivo"])
    return resumo


def atualizar_em_segundo_plano(embedder) -> threading.Thread:
    def tarefa():
        try:
            atualizar_dados_locais(embedder)
        except Exception as exc:
            logger.warning("Falha na atualização incremental dos vetores: %s", exc)

    thread = threading.Thread(target=tarefa, name="vetores-incremental", daemon=True)
    thread.start()
    return thread
