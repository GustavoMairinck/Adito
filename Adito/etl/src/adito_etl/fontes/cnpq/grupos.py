"""Espelho de cada grupo de pesquisa no DGP/CNPq -> `brutos/cnpq/grupo_<id16>.json`.

Adaptado do horizon_etl (commit 13a1cec):
- `src/flows/cnpq/groups.py`: validação da URL do espelho (`DGP_MIRROR_URL`);
- `src/adapters/sources/cnpq_crawler.py`: `normalize_cnpq_url` e a chamada à `dgp-cnpq-lib`.
Sem banco, Prefect nem Telegram: as URLs saem de `brutos/sigpesq/grupos/` (coluna `Column1`).

Filtro (BR01, revisto pelo usuário em 2026-11-11): ficam só as seções de
`SECOES`. De `endereco_contato` fica o endereço e o site do grupo
(`ENDERECO`); telefone, fax e e-mail de contato saem. Em qualquer nível, chave com nome de dado pessoal sai e
todo texto passa por `pii.sanitizar`. Seção nova é descartada e avisada.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Callable

from ... import pii
from ...comum import Execucao, brutos_dir, gravar_json, ler_json

Log = Callable[[str], None]

DGP_MIRROR_URL = re.compile(r"^https?://dgp\.cnpq\.br/dgp/espelhogrupo/(\d{16})$", re.IGNORECASE)

SECOES = frozenset({
    "nome_grupo", "identificacao", "repercussoes", "linhas_de_pesquisa",
    "recursos_humanos", "recursos_humanos_do_grupo", "indicadores_de_recursos_humanos_do_grupo",
    "instituicoes_parceiras_relatadas_pelo_grupo", "incts_parceiras_relatadas_pelo_grupo",
    "equipamentos_e_softwares_relevantes", "endereco_contato",
})
EXCLUIDAS = frozenset({"endereco"})
ENDERECO = frozenset({"logradouro", "numero", "complemento", "bairro", "uf", "localidade", "cep",
                      "caixa_postal", "latitude", "longitude", "website"})  # sem telefone, fax, e-mail


class SemBrutoSigPesq(FileNotFoundError):
    """As URLs de espelho vêm do bruto do SigPesq."""


def normalizar_url(url: str) -> str:
    """Tira barras duplicadas fora do `://` (igual ao `normalize_cnpq_url` do horizon)."""
    return re.sub(r"(?<!:)/{2,}", "/", url.strip())


def id_do_espelho(url: object) -> str | None:
    if not isinstance(url, str) or not url.strip():
        return None
    m = DGP_MIRROR_URL.match(normalizar_url(url))
    return m.group(1) if m else None


def grupos_do_sigpesq(unidade: str | None = None) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """(grupos com URL válida, grupos sem URL ou com URL fora do formato)."""
    pasta = brutos_dir("sigpesq") / "grupos"
    arquivos = sorted(pasta.glob("*.json")) if pasta.exists() else []
    if not arquivos:
        raise SemBrutoSigPesq("bruto do SigPesq ausente em etl/brutos/sigpesq/grupos/: "
                              "rode `adito-etl sigpesq` (ou `sigpesq-converter`) antes")
    validos: dict[str, dict[str, str]] = {}
    invalidos: list[dict[str, str]] = []
    for arq in arquivos:
        for g in ler_json(arq).get("linhas", []):
            if unidade and unidade.lower() not in str(g.get("Unidade") or "").lower():
                continue
            nome = str(g.get("Nome") or g.get("Sigla") or "?")
            url = g.get("Column1")
            ident = id_do_espelho(url)
            if ident:
                validos.setdefault(ident, {"id": ident, "nome": nome, "url": normalizar_url(url)})
            else:
                invalidos.append({"nome": nome, "url": str(url or "")})
    return [validos[k] for k in sorted(validos)], invalidos


def _limpar(v: Any) -> Any:
    if isinstance(v, dict):
        return {k: _limpar(x) for k, x in v.items() if not pii.chave_pessoal(k)}
    if isinstance(v, list):
        return [_limpar(x) for x in v]
    return v


def filtrar_grupo(dados: dict[str, Any]) -> tuple[dict[str, Any], set[str]]:
    descartadas = {k for k in dados if k not in SECOES and k not in EXCLUIDAS}
    saida = {k: _limpar(v) for k, v in dados.items() if k in SECOES}
    if isinstance(saida.get("endereco_contato"), dict):
        end = {k: v for k, v in saida["endereco_contato"].items() if k in ENDERECO}
        for k in ("latitude", "longitude"):  # sem isso, 11+ dígitos seguidos caem na trava de CPF
            try:
                end[k] = f"{float(str(end[k]).replace(',', '.')):.6f}"
            except (KeyError, ValueError):
                end.pop(k, None) if k in end and not str(end[k]).strip() else None
        saida["endereco_contato"] = end
    return saida, descartadas


def _crawler():
    try:
        from dgp_cnpq_lib import CnpqCrawler
    except ImportError as e:
        raise RuntimeError("dgp-cnpq-lib não instalada: rode `pip install -e '.[cnpq]'` em etl/") from e
    return CnpqCrawler()


def extrair_cnpq(*, unidade: str | None = None, max_grupos: int | None = None,
                 refazer: bool = False, pausa_s: float = 1.0, log: Log = print) -> Execucao:
    """Baixa o espelho de cada grupo. Grupos já gravados são pulados (retomada), salvo `refazer`."""
    exe = Execucao("cnpq", "grupos")
    try:
        grupos, invalidos = grupos_do_sigpesq(unidade)
        for g in invalidos:
            exe.aviso(f"grupo sem URL de espelho válida, pulado: {g['nome']} -> {g['url'] or '(vazio)'}")
        exe.conta("urls_invalidas", len(invalidos))
        if max_grupos:
            grupos = grupos[:max_grupos]
        exe.conta("grupos_listados", len(grupos))
        destino = brutos_dir("cnpq")
        crawler = None
        avisadas: set[str] = set()
        for n, g in enumerate(grupos, 1):
            arq = destino / f"grupo_{g['id']}.json"
            if arq.exists() and not refazer:
                exe.conta("grupos_ja_gravados")
                continue
            crawler = crawler or _crawler()
            try:
                dados = crawler.get_data(g["url"])
                if not dados:
                    raise RuntimeError("espelho vazio")
                filtrado, descartadas = filtrar_grupo(dados)
                for s in sorted(descartadas - avisadas):
                    exe.aviso(f"seção descartada (fora da lista de permitidas): {s}")
                avisadas |= descartadas
                filtrado, mascarados = pii.sanitizar(filtrado)
                gravar_json(arq, {"id_espelho": g["id"], "url": g["url"],
                                  "nome_sigpesq": g["nome"], **filtrado})
            except Exception as e:
                exe.falha(f"grupo:{g['id']}", e)
            else:
                exe.conta("grupos_gravados")
                if mascarados:
                    exe.conta("valores_mascarados", mascarados)
            if n % 10 == 0 or n == len(grupos):
                log(f"CNPq: {n}/{len(grupos)} grupos")
            time.sleep(pausa_s)
    except Exception as e:
        exe.falha("cnpq", e)
        raise
    finally:
        exe.finalizar()
    return exe
