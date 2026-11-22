"""(Copiado do SRCEtl: src_etl/etl/scraper.py, branch fix/listagem-serial-acoes.) Navegação da consulta pública de ações (Playwright).

Seleciona um campus, pesquisa e percorre todas as páginas do resultado,
capturando o id de cada ação (via iframe do dialog "Detalhes").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urljoin, urlparse

from playwright.async_api import async_playwright

CONSULTA_URL = "https://src.ifes.edu.br/src/public/consulta-acao.xhtml"
BASE = "https://src.ifes.edu.br/src/public/"

# ids PrimeFaces estáveis desta view
_DD_CAMPUS = "j_idt47:j_idt64"
_BTN_PESQUISAR = "j_idt47:j_idt92"
_TABELA = "j_idt47:dtblAcoes"

# a listagem é refeita (unindo resultados) se vier menos que o total informado
_MAX_PASSADAS = 3


@dataclass
class LinhaAcao:
    """Referência a uma ação encontrada na listagem."""

    acao_id: str | None
    url_detalhe: str | None
    linha: list[str] = field(default_factory=list)


async def listar_campi(*, headless: bool = True) -> list[str]:
    """Lê os campi disponíveis no dropdown da consulta (sem 'Selecione')."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        await page.goto(CONSULTA_URL, wait_until="networkidle")
        opts = await page.eval_on_selector_all(
            f"[id='{_DD_CAMPUS}_input'] option",
            "els => els.map(e => e.textContent.trim())",
        )
        await browser.close()
    return [o for o in opts if o and o.lower() != "selecione"]


async def _selecionar_e_pesquisar(page, campus: str) -> tuple[int, int | None]:
    """Abre a consulta, seleciona o campus, pesquisa e ordena por Processo nº.

    Sem ordenação explícita a consulta pagina numa ordem que muda entre uma
    página e outra (e entre sessões): ações se repetem e outras somem.
    Ordenar por "Processo nº" fixa a ordem.

    Devolve (total de páginas, total de registros informado pela consulta).
    """
    await page.goto(CONSULTA_URL, wait_until="networkidle")
    await page.locator(f"[id='{_DD_CAMPUS}']").click()
    await page.wait_for_selector(f"[id='{_DD_CAMPUS}_panel']")
    await page.locator(f"[id='{_DD_CAMPUS}_panel'] li[data-label='{campus}']").click()
    await page.wait_for_selector(f"[id='{_DD_CAMPUS}_panel']", state="hidden")
    await page.locator(f"[id='{_BTN_PESQUISAR}']").click()
    await page.wait_for_selector(
        f"[id='{_TABELA}'] tbody tr button[title='Detalhes']", timeout=20000)

    coluna = page.locator(f"[id='{_TABELA}'] thead th.ui-sortable-column",
                          has_text="Processo")
    await coluna.click()
    await page.wait_for_function(
        "sel => document.querySelector(sel)?.getAttribute('aria-sort') === 'ascending'",
        arg=f"[id='{await coluna.get_attribute('id')}']",
        timeout=20000,
    )
    await page.wait_for_load_state("networkidle")
    await page.wait_for_selector(
        f"[id='{_TABELA}'] tbody tr button[title='Detalhes']", timeout=20000)

    paginas, registros = 1, None
    cur = await page.locator(f"[id='{_TABELA}'] .ui-paginator-current").first.text_content()
    if cur and (m := re.search(r"/(\d+)", cur)):
        paginas = int(m.group(1))
    if cur and (m := re.search(r"Total:\s*(\d+)", cur)):
        registros = int(m.group(1))
    return paginas, registros


async def _scrape_pagina(page, log) -> list[LinhaAcao]:
    """Extrai as ações da página atual (clica cada dialog Detalhes)."""
    await page.wait_for_selector(
        f"[id='{_TABELA}'] tbody tr button[title='Detalhes']", timeout=20000)
    ids = await page.eval_on_selector_all(
        f"[id='{_TABELA}'] tbody tr button[title='Detalhes']", "els=>els.map(e=>e.id)")
    out: list[LinhaAcao] = []
    for bid in ids:
        dlg = f"[id='{bid}_dlg']"
        try:
            botao = page.locator(f"[id='{bid}']")
            linha = botao.locator("xpath=ancestor::tr[1]")
            resumo = [c.strip() for c in await linha.locator("td").all_text_contents()]
            await botao.click()
            await page.wait_for_selector(f"{dlg} iframe", state="attached", timeout=15000)
            src = await page.locator(f"{dlg} iframe").get_attribute("src")
            acao_id = parse_qs(urlparse(src).query).get("acao", [None])[0]
            out.append(LinhaAcao(acao_id=acao_id, url_detalhe=urljoin(BASE, src), linha=resumo))
            await page.locator(f"{dlg} .ui-dialog-titlebar-close").click()
            await page.wait_for_selector(dlg, state="hidden", timeout=10000)
            await page.wait_for_selector(".ui-widget-overlay", state="hidden", timeout=10000)
        except Exception as e:  # uma linha ruim não derruba o crawl
            log(f"  ! falha na linha {bid}: {str(e)[:80]}")
            try:
                await page.keyboard.press("Escape")
                await page.wait_for_timeout(400)
            except Exception:
                pass
    return out


async def _proxima_pagina(page) -> None:
    """Avança de página esperando o indicador mudar (evita re-raspar/pular)."""
    atual = await page.locator(f"[id='{_TABELA}'] .ui-paginator-current").first.text_content()
    await page.locator(f"[id='{_TABELA}'] .ui-paginator-next").first.click()
    try:
        await page.wait_for_function(
            """([sel, prev]) => {
                const e = document.querySelector(sel + ' .ui-paginator-current');
                return e && e.textContent.trim() !== prev;
            }""",
            arg=[f"[id='{_TABELA}']", (atual or "").strip()],
            timeout=10000,
        )
    except Exception:
        await page.wait_for_timeout(1000)


async def coletar_campus(
    campus: str,
    *,
    headless: bool = True,
    max_acoes: int | None = None,
    on_progress=None,
    workers: int = 1,
) -> list[LinhaAcao]:
    """Percorre a consulta pública e devolve as ações de um campus.

    Args:
        campus: nome exato do campus (ex.: "Serra").
        headless: roda o navegador sem interface.
        max_acoes: limite opcional de ações (para testes).
        on_progress: callback(msg:str) para logs de progresso.
        workers: ignorado; mantido só por compatibilidade. A listagem é sempre
                 serial: sem ordem fixa, a consulta pública repete e omite
                 ações entre páginas e sessões (em 2026-11-10, Serra tinha 207
                 ações; 3 sessões paralelas trouxeram 159 e a listagem serial
                 sem ordenação, 196-197).

    A tabela é ordenada por Processo nº antes de paginar, e o resultado é
    conferido com o "Total" da consulta; se faltar ação, a listagem é refeita
    (até _MAX_PASSADAS vezes) e as passadas são unidas por acao_id.
    """
    log = on_progress or (lambda _m: None)
    if workers > 1:
        log(f"aviso: workers={workers} ignorado na listagem pública (sempre serial)")

    vistos: dict[str, LinhaAcao] = {}
    registros: int | None = None
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        for passada in range(1, _MAX_PASSADAS + 1):
            page = await browser.new_page(viewport={"width": 1440, "height": 900})
            total, registros = await _selecionar_e_pesquisar(page, campus)
            log(f"{campus}: {total} páginas, {registros} registros (passada {passada})")
            antes = len(vistos)
            for pag in range(1, total + 1):
                for ln in await _scrape_pagina(page, log):
                    if ln.acao_id:
                        vistos.setdefault(ln.acao_id, ln)
                log(f"página {pag}/{total} -> {len(vistos)} ações únicas")
                if max_acoes and len(vistos) >= max_acoes:
                    await browser.close()
                    log(f"limite max_acoes={max_acoes} atingido")
                    return list(vistos.values())[:max_acoes]
                if pag < total:
                    await _proxima_pagina(page)
            await page.close()
            if registros is None or len(vistos) >= registros:
                break
            log(f"aviso: {len(vistos)} de {registros} ações após a passada {passada} "
                f"(+{len(vistos) - antes} nesta); repetindo a listagem")
        await browser.close()

    if registros is not None and len(vistos) < registros:
        log(f"aviso: listagem incompleta: {len(vistos)} de {registros} ações "
            f"após {_MAX_PASSADAS} passadas")
    return list(vistos.values())
