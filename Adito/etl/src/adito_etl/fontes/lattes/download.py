"""Download dos currículos Lattes pelo `scriptLattes` e conversão para JSON filtrado.

Adaptado do horizon_etl (`src/flows/lattes/download.py` e
`src/core/logic/lattes_generators.py`, commit 13a1cec), sem Prefect, Telegram
nem banco:
- a lista sai de `etl/entradas/lattes.csv` (`nome,lattes_id`, fora do git), não de uma lista fixa no código;
- mesma correção do horizon para o `baixaCVLattes`, que tenta para sempre em
  timeout: aqui são `LATTES_TENTATIVAS` tentativas por currículo (padrão 2);
- o HTML baixado (`trabalho/lattes_cache/`) e o JSON completo do scriptLattes
  (`trabalho/lattes_json/`) são apagados ao fim; só o JSON filtrado fica em `brutos/lattes/`.
"""

from __future__ import annotations

import csv
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable

from ...comum import Execucao, base_dir, trabalho_dir
from .converter import LATTES_ID, converter_pasta

Log = Callable[[str], None]

TENTATIVAS = int(os.getenv("LATTES_TENTATIVAS", "2"))
ESPERA_S = int(os.getenv("LATTES_ESPERA_S", "30"))
TIMEOUT_NAVEGACAO_MS = 50_000


class ScriptLattesIndisponivel(RuntimeError):
    """scriptLattes ou o Chromium do Playwright não estão instalados."""


def lista_padrao() -> Path:
    return base_dir() / "entradas" / "lattes.csv"


def ler_lista(path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    """Lê `nome,lattes_id`. Devolve (válidos sem repetição, linhas inválidas)."""
    validos: list[tuple[str, str]] = []
    invalidos: list[str] = []
    vistos: set[str] = set()
    with path.open(encoding="utf-8", newline="") as f:
        for linha in csv.DictReader(f):
            nome = (linha.get("nome") or "").strip()
            ident = (linha.get("lattes_id") or "").strip()
            if not LATTES_ID.fullmatch(ident) or not nome:
                invalidos.append(f"{nome or '?'},{ident or '?'}")
                continue
            if ident not in vistos:
                vistos.add(ident)
                validos.append((nome, ident))
    return validos, invalidos


def _gerar_config(config: Path, lista: Path, saida: Path, cache: Path) -> None:
    """Mesmo `lattes.config` que o horizon gera (LattesConfigGenerator)."""
    config.write_text(f"""# Gerado por adito-etl
global-nome_do_grupo = Adito
global-diretorio_de_saida = {saida}
global-diretorio_de_armazenamento_de_cvs = {cache}
global-email_do_admin = admin@example.com
global-idioma = PT
global-itens_desde_o_ano = 1950
global-itens_ate_o_ano = 2100
global-itens_por_pagina = 1000
global-producao_bibliografica-itens = artigo,livro,capitulo,texto,trabalho-completo,resumo-expandido,resumo-congresso,apresentacao-trabalho,outro
global-producao_tecnica-itens = software,patente,desenho-industrial,produto-tecnologico,processo-tecnica,trabalho-tecnico,outro
global-producao_artistica-itens = producao
global-identificacao_dos_grupos_de_pesquisa = SIM
global-arquivo_de_entrada = {lista}
global-arquivo_de_entrada_de_grupos =
global-diretorio_de_saida_json = {saida}
""", encoding="utf-8")


def _corrigir_scriptlattes() -> None:
    """Troca o `baixaCVLattes` por uma versão com limite de tentativas (igual ao horizon)."""
    try:
        import scriptLattes.baixaLattes as bl
    except ImportError as e:
        raise ScriptLattesIndisponivel(
            "scriptLattes não instalado: rode `pip install -e '.[lattes]'` em etl/") from e
    if getattr(bl, "_adito_corrigido", False):
        return

    def get_data(id_lattes: str, diretorio: str) -> None:
        rob = bl.LattesRobot(results_dir=diretorio)
        rob.load_codes(id_lattes)
        rob.check_downloaded_cvs()
        try:
            rob.create_browser()
            rob.context.set_default_navigation_timeout(TIMEOUT_NAVEGACAO_MS)
            rob.collect_html_cvs(0, None)
        finally:
            if getattr(rob, "browser", None):
                rob.browser.close()
            if getattr(rob, "playwright", None):
                rob.playwright.stop()

    def baixa_cv(id_lattes: str, diretorio: str) -> None:
        tipo_timeout = getattr(bl, "PlaywrightTimeoutError", None) or Exception
        destino = Path(diretorio) / id_lattes
        for tentativa in range(1, TENTATIVAS + 1):
            if destino.exists():
                return
            try:
                get_data(id_lattes, diretorio)
            except tipo_timeout:
                if tentativa >= TENTATIVAS:
                    raise
                time.sleep(ESPERA_S)
                continue
            except Exception as e:
                texto = str(e)
                if ("ERR_CONNECTION_REFUSED" in texto or "ERR_CONNECTION_RESET" in texto) \
                        and tentativa < TENTATIVAS:
                    time.sleep(ESPERA_S)
                    continue
                raise
            if destino.exists():
                return
        raise RuntimeError(f"scriptLattes não gravou o currículo {id_lattes}")

    bl.__get_data = get_data
    bl.baixaCVLattes = baixa_cv
    bl._adito_corrigido = True


def _baixar_cache(ids: list[str], cache: Path, workers: int, exe: Execucao, log: Log) -> list[str]:
    import scriptLattes.baixaLattes as bl

    cache.mkdir(parents=True, exist_ok=True)
    faltando = [i for i in ids if not (cache / i).exists()]
    ok: list[str] = [i for i in ids if i not in faltando]

    def um(ident: str) -> str:
        bl.baixaCVLattes(ident, str(cache))
        if not (cache / ident).exists():
            raise RuntimeError("scriptLattes não gravou o currículo")
        return ident

    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(faltando) or 1))) as pool:
        futuros = {pool.submit(um, i): i for i in faltando}
        for n, fut in enumerate(as_completed(futuros), 1):
            ident = futuros[fut]
            try:
                ok.append(fut.result())
            except Exception as e:
                exe.falha(f"lattes:{ident}", e)
            if n % 10 == 0 or n == len(faltando):
                log(f"Lattes: {n}/{len(faltando)} currículos baixados")
    return sorted(ok, key=ids.index)


def extrair_lattes(lista: Path | None = None, *, workers: int = 3, max_cv: int | None = None,
                   log: Log = print) -> Execucao:
    """Baixa os currículos da lista, converte para JSON filtrado e apaga o resto."""
    exe = Execucao("lattes", "download")
    trabalho = trabalho_dir()
    cache, saida, run = trabalho / "lattes_cache", trabalho / "lattes_json", trabalho / "lattes_run"
    try:
        validos, invalidos = ler_lista(lista or lista_padrao())
        for linha in invalidos:
            exe.aviso(f"linha ignorada (id Lattes sem 16 dígitos ou sem nome): {linha}")
        if max_cv:
            validos = validos[:max_cv]
        exe.conta("curriculos_listados", len(validos))
        _corrigir_scriptlattes()
        from scriptLattes.run import executar_scriptLattes

        ids = _baixar_cache([i for _, i in validos], cache, workers, exe, log)
        if not ids:
            raise RuntimeError("nenhum currículo baixado")
        nomes = dict((i, n) for n, i in validos)
        shutil.rmtree(saida, ignore_errors=True)
        saida.mkdir(parents=True)
        run.mkdir(parents=True, exist_ok=True)
        (run / "lattes.list").write_text("\n".join(f"{i},{nomes[i]}" for i in ids), encoding="utf-8")
        _gerar_config(run / "lattes.config", run / "lattes.list", saida, cache)
        log(f"Lattes: gerando JSON de {len(ids)} currículos")
        executar_scriptLattes(str(run / "lattes.config"), somente_json=True)
        converter_pasta(saida, exe, apagar=True, cache=cache)
    except Exception as e:
        exe.falha("download", e)
        raise
    finally:
        for pasta in (cache, saida, run):        # HTML e JSON completo têm endereço e telefone
            shutil.rmtree(pasta, ignore_errors=True)
        exe.finalizar()
    return exe
