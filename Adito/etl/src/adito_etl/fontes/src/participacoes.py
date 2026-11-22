"""US-ETL-02: participações do SRC (área autenticada) -> `brutos/src/participacoes/`.

Copiado do SRCEtl (src_etl/etl/gerenciar.py + run_participacoes de pipeline.py).
Para cada processo: Gerenciar > Ações > pesquisa > atividades; de cada atividade
lê o público-alvo (alunos atendidos) e a equipe de execução.

Diferença do SRCEtl (BR01): cada pessoa guarda só as colunas de
`COLUNAS_PERMITIDAS`. CPF, e-mail e qualquer coluna fora da lista são
descartados na leitura da tabela, antes de qualquer gravação.

O SRC mantém UMA sessão por usuário: um login, coleta sequencial (workers>1 são
abas da mesma sessão, como no SRCEtl).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Callable
from urllib.parse import quote

from playwright.async_api import Page, async_playwright

from ... import pii
from ...comum import Execucao, brutos_dir, credencial, filtrar_colunas, gravar_json, ler_json
from .models import AcaoParticipacoes, AtividadeParticipacoes

LOGIN_URL = "https://src.ifes.edu.br/src"
GER_ACAO = "https://src.ifes.edu.br/src/pages/gerenciar/gerenciar-acao.xhtml"
PUBLICO = "https://src.ifes.edu.br/src/pages/gerenciar/gerenciar-publico-alvo.xhtml?atividade="
EQUIPE = "https://src.ifes.edu.br/src/pages/gerenciar/gerenciar-equipe-execucao.xhtml?atividade="
_TBL = "frmMain:dtblParticipacoes"

# Colunas que ficam no bruto (nome + campos não pessoais), a partir das colunas
# que o SRCEtl usa. Aprovadas pelo usuário em 2026-11-10 (US-ETL-02, CA3).
COLUNAS_PERMITIDAS = frozenset({
    "Nome", "Função", "Vínculo", "Situação", "Início", "Término", "C.H", "Certificado",
})

Log = Callable[[str], None]


class FalhaLogin(RuntimeError):
    """Usuário/senha do SRC recusados ou sessão não estabelecida."""


# ------------------------------------------------------------------ navegação
async def _logado(page: Page) -> bool:
    """True se autenticado (não está na tela de login)."""
    return await page.eval_on_selector_all("input[placeholder='Senha']", "e=>e.length") == 0


async def _login(page: Page, user: str, senha: str) -> None:
    for _ in range(3):
        await page.goto(LOGIN_URL, wait_until="networkidle")
        if await _logado(page):  # sessão ainda válida
            return
        await page.fill("input[placeholder='Usuário']", user)
        await page.fill("input[placeholder='Senha']", senha)
        await page.click("button:has-text('Entrar')")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(1500)
        if await _logado(page):
            return
    raise FalhaLogin("login no SRC recusado: confira SRC_USER e SRC_PASSWORD em etl/.env")


async def _ir_busca(page: Page) -> bool:
    """Vai ao form de busca de ação (espera o campo aparecer; retry tolerante)."""
    for _ in range(5):
        await page.goto(GER_ACAO, wait_until="networkidle")
        try:
            await page.wait_for_selector("input.ui-inputmask", timeout=6000)
            return True
        except Exception:
            await page.wait_for_timeout(1000)  # estado transitório de sessão
    return False


async def _pesquisar(page: Page, processo: str) -> None:
    """Preenche o campo mascarado (dígitos) e clica Pesquisar, com verificação."""
    digitos = "".join(c for c in processo if c.isdigit())
    campo = page.locator("input.ui-inputmask")
    for _ in range(4):
        await campo.click()
        await page.wait_for_timeout(250)
        await campo.press("Control+A")
        await campo.press("Delete")
        await page.wait_for_timeout(150)
        await campo.type(digitos, delay=80)
        if "".join(c for c in await campo.input_value() if c.isdigit()) == digitos:
            break
    await page.click("button[title='Pesquisar']")
    try:
        await page.wait_for_selector(
            "[id$='dtblAtividades'] tbody tr button[title='Público-Alvo']", timeout=9000)
    except Exception:
        await page.wait_for_timeout(800)


async def _coletar_metas(page: Page) -> list[dict[str, str]]:
    """Percorre todas as páginas do dtblAtividades e extrai atividade_id do onclick."""
    metas: list[dict[str, str]] = []
    seen: set[str] = set()
    while True:
        rows = await page.evaluate(
            r"""() => [...document.querySelectorAll("[id$='dtblAtividades'] tbody tr")].map(tr => {
                const c=[...tr.querySelectorAll('td')].map(td=>td.innerText.trim());
                const pa=tr.querySelector("button[title='Público-Alvo']");
                const oc = pa ? (pa.getAttribute('onclick')||'') : '';
                const m = oc.match(/atividade=(\d+)/);
                return {num:c[0]||'', tipo:c[1]||'', atividade:c[2]||'', atividade_id: m?m[1]:null};
            }).filter(r => r.num && r.num.toLowerCase().indexOf('nenhum')<0)"""
        )
        for r in rows:
            if r["atividade_id"] and r["atividade_id"] not in seen:
                seen.add(r["atividade_id"])
                metas.append(r)

        nxt = page.locator("[id$='dtblAtividades'] .ui-paginator-next").first
        if await nxt.count() == 0:
            break
        cls = await nxt.get_attribute("class") or ""
        if "ui-state-disabled" in cls:
            break
        atual = await page.locator(
            "[id$='dtblAtividades'] .ui-paginator-current").first.text_content()
        await nxt.click()
        try:
            await page.wait_for_function(
                """(prev) => {
                    const e = document.querySelector("[id$='dtblAtividades'] .ui-paginator-current");
                    return e && e.textContent.trim() !== prev;
                }""",
                arg=(atual or "").strip(), timeout=8000,
            )
        except Exception:
            await page.wait_for_timeout(800)
    return metas


def linhas_da_tabela(headers: list[str], rows: list[list[str]]) -> list[dict[str, str]]:
    """Linhas cruas da tabela -> dicts com todas as colunas (exceto 'Operação')."""
    manter = [i for i, h in enumerate(headers) if h and h.lower() != "operação"]
    linhas = []
    for r in rows:
        if len(r) <= 1 or (r and "nenhum" in r[0].lower()):
            continue
        linhas.append({headers[i]: (r[i] if i < len(r) else "") for i in manter})
    return linhas


async def _scrape_participacoes(page: Page, avisar: Log) -> list[dict[str, str]]:
    """Lê a tabela dtblParticipacoes em todas as páginas, já filtrada (BR01)."""
    await page.wait_for_selector(f"[id='{_TBL}']", timeout=15000)
    headers = await page.eval_on_selector_all(
        f"[id='{_TBL}'] thead th", "els=>els.map(e=>e.innerText.trim())"
    )
    linhas: list[dict[str, str]] = []
    while True:
        rows = await page.evaluate(
            f"""() => [...document.querySelectorAll("[id='{_TBL}'] tbody tr")]
                    .map(tr => [...tr.querySelectorAll('td')].map(td=>td.innerText.trim()))"""
        )
        filtradas, novas = filtrar_colunas(linhas_da_tabela(headers, rows), COLUNAS_PERMITIDAS)
        for col in novas:
            avisar(f"coluna descartada (fora da lista de permitidas): {col}")
        linhas.extend(filtradas)

        nxt = page.locator(f"[id='{_TBL}'] .ui-paginator-next").first
        if await nxt.count() == 0:
            break
        cls = await nxt.get_attribute("class") or ""
        if "ui-state-disabled" in cls:
            break
        atual = await page.locator(f"[id='{_TBL}'] .ui-paginator-current").first.text_content()
        await nxt.click()
        try:
            await page.wait_for_function(
                """([sel, prev]) => {
                    const e = document.querySelector(sel + ' .ui-paginator-current');
                    return e && e.textContent.trim() !== prev;
                }""",
                arg=[f"[id='{_TBL}']", (atual or "").strip()],
                timeout=8000,
            )
        except Exception:
            await page.wait_for_timeout(700)
    return linhas


async def _coletar_processo(page: Page, processo: str, log: Log, avisar: Log) -> AcaoParticipacoes:
    """Coleta público-alvo + equipe de todas as atividades de um processo."""
    if not await _ir_busca(page):
        raise RuntimeError("não chegou ao formulário de busca (sessão)")
    await _pesquisar(page, processo)
    metas = await _coletar_metas(page)
    log(f"[{processo}] {len(metas)} atividades")

    ativs: list[AtividadeParticipacoes] = []
    for meta in metas:
        atividade_id = meta["atividade_id"]
        await page.goto(PUBLICO + quote(atividade_id, safe=""), wait_until="networkidle")
        publico = await _scrape_participacoes(page, avisar)
        await page.goto(EQUIPE + quote(atividade_id, safe=""), wait_until="networkidle")
        equipe = await _scrape_participacoes(page, avisar)
        ativs.append(AtividadeParticipacoes(
            num=meta["num"], atividade=meta["atividade"], tipo=meta["tipo"],
            atividade_id=atividade_id, publico_alvo=publico, equipe_execucao=equipe,
        ))
        log(f"  ativ {meta['num']} (id={atividade_id}): "
            f"público={len(publico)} equipe={len(equipe)}")

    return AcaoParticipacoes(
        processo=processo,
        total_atividades=len(ativs),
        total_publico_alvo=sum(len(a.publico_alvo) for a in ativs),
        total_equipe=sum(len(a.equipe_execucao) for a in ativs),
        atividades=ativs,
    )


async def _processar_lista(page: Page, processos: list[str], log: Log, avisar: Log,
                           on_processo, on_falha, retry: int = 2) -> None:
    """Processa uma fatia de processos numa aba (com retry por processo)."""
    for proc in processos:
        for tent in range(retry):
            try:
                ap = await _coletar_processo(page, proc, log, avisar)
                on_processo(ap)  # grava já: protege o progresso (FR03)
                break
            except Exception as e:
                if tent + 1 >= retry:
                    on_falha(proc, e)
                    log(f"[{proc}] ERRO (após {retry} tentativas): {str(e)[:70]}")
                else:
                    await page.wait_for_timeout(1500)


async def _coletar(processos: list[str], user: str, senha: str, *, headless: bool,
                   workers: int, log: Log, avisar: Log, on_processo, on_falha) -> None:
    """Um login; coleta participações de vários processos."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        try:
            login_page = await ctx.new_page()
            await _login(login_page, user, senha)
            log(f"login OK ({len(processos)} processos, {max(1, workers)} aba(s))")

            k = max(1, min(workers, len(processos) or 1))
            if k <= 1:
                await _processar_lista(login_page, processos, log, avisar, on_processo, on_falha)
            else:
                fatias = [processos[i::k] for i in range(k)]
                paginas = [login_page] + [await ctx.new_page() for _ in range(k - 1)]
                await asyncio.gather(*[
                    _processar_lista(paginas[i], fatias[i], log, avisar, on_processo, on_falha)
                    for i in range(k)
                ])
            try:  # logout best-effort
                await login_page.locator("[id='logout']").click(timeout=4000, force=True)
            except Exception:
                pass
        finally:
            await browser.close()


# ------------------------------------------------------------------ entrada
def processos_do_index(index_path: Path) -> list[str]:
    """Números de processo do `_index.json` da etapa pública, sem repetir."""
    vistos, out = set(), []
    for item in ler_json(index_path):
        proc = item.get("processo")
        if proc and proc not in vistos:
            vistos.add(proc)
            out.append(proc)
    return out


def arquivo_do_processo(processo: str) -> Path:
    return brutos_dir("src") / "participacoes" / ("participacoes_" + processo.replace("/", "-") + ".json")


def extrair_participacoes(
    processos: list[str] | None = None,
    *,
    headless: bool = True,
    workers: int = 1,
    log: Log = print,
) -> Execucao:
    """Coleta participações e grava um JSON por processo, pulando os já gravados."""
    exe = Execucao("src", "participacoes")
    if not processos:
        index = brutos_dir("src") / "acoes" / "_index.json"
        if not index.exists():
            raise FileNotFoundError(f"{index} não existe: rode antes `adito-etl src-acoes`")
        processos = processos_do_index(index)
    user, senha = credencial(["SRC_USER"], ["SRC_PASSWORD"], segredos=("src-user", "src-password"))

    pendentes = [p for p in processos if not arquivo_do_processo(p).exists()]
    exe.conta("processos", len(processos))
    exe.conta("processos_ja_gravados", len(processos) - len(pendentes))
    if len(pendentes) < len(processos):
        log(f"retomada: {len(processos) - len(pendentes)} já gravados, {len(pendentes)} pendentes")

    def gravar(ap: AcaoParticipacoes) -> None:
        dados, mascarados = pii.sanitizar(ap.model_dump())
        gravar_json(arquivo_do_processo(ap.processo), dados)
        exe.conta("processos_gravados")
        exe.conta("atividades", ap.total_atividades)
        exe.conta("publico_alvo", ap.total_publico_alvo)
        exe.conta("equipe_execucao", ap.total_equipe)
        if mascarados:
            exe.conta("valores_mascarados", mascarados)

    try:
        if pendentes:
            asyncio.run(_coletar(
                pendentes, user, senha, headless=headless, workers=workers, log=log,
                avisar=exe.aviso, on_processo=gravar,
                on_falha=lambda proc, e: exe.falha(f"processo {proc}", e),
            ))
    finally:
        exe.finalizar()
    return exe
