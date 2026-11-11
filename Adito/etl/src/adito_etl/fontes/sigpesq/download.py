"""Download dos relatórios do SigPesq pela `sigpesq-agent` e conversão para JSON.

Adaptado do horizon_etl (`SigPesqAdapter._trigger_download`): mesma
retentativa com espera maior quando o portal responde 429, sem Infisical
(credencial em `etl/.env`). Os XLSX vão para `trabalho/sigpesq_xlsx/` e são
apagados ao fim, convertidos ou não (podem ter CPF e e-mail).
"""

from __future__ import annotations

import asyncio
import os
import shutil
import time
from pathlib import Path
from typing import Callable

from ...comum import Execucao, credencial, trabalho_dir
from .converter import converter_pasta

Log = Callable[[str], None]

TENTATIVAS = int(os.getenv("SIGPESQ_MAX_RETRIES", "3"))
ESPERA_429 = int(os.getenv("SIGPESQ_429_WAIT_SECONDS", "60"))


class DownloadSigPesqFalhou(RuntimeError):
    """A sigpesq-agent não conseguiu baixar os relatórios."""


def _importar_agente():
    try:
        from agent_sigpesq.services.reports_service import SigpesqReportService
        from agent_sigpesq.strategies import (
            AdvisorshipsDownloadStrategy,
            ProjectsDownloadStrategy,
            ResearchGroupsDownloadStrategy,
        )
    except ImportError as e:
        raise RuntimeError(
            "sigpesq-agent não instalado: rode `pip install -e '.[sigpesq]'` em etl/"
        ) from e
    estrategias = [ResearchGroupsDownloadStrategy(), ProjectsDownloadStrategy(),
                   AdvisorshipsDownloadStrategy()]
    return SigpesqReportService, estrategias


def _vigiar_429(service, flag: dict) -> None:
    """Marca `flag['429']` se o portal responder 429 durante o login."""
    original = getattr(service, "_login", None)
    if original is None:
        return

    async def login(page):
        def ver(resp):
            if getattr(resp, "status", None) == 429:
                flag["429"] = True
        page.on("response", ver)
        try:
            return await original(page)
        finally:
            page.remove_listener("response", ver)

    service._login = login


def baixar(destino: Path, *, headless: bool = True, log: Log = print) -> None:
    """Baixa os três relatórios em `destino` (limpo antes de cada tentativa)."""
    usuario, senha = credencial(["SIGPESQ_USER", "SIGPESQ_USERNAME"], ["SIGPESQ_PASSWORD"],
                                segredos=("sigpesq-user", "sigpesq-password"))
    os.environ["SIGPESQ_USER"] = usuario          # a sigpesq-agent lê do ambiente
    os.environ["SIGPESQ_PASSWORD"] = senha
    Servico, estrategias = _importar_agente()

    for tentativa in range(1, TENTATIVAS + 1):
        shutil.rmtree(destino, ignore_errors=True)
        destino.mkdir(parents=True, exist_ok=True)
        flag = {"429": False}
        servico = Servico(headless=headless, download_dir=str(destino), strategies=estrategias)
        _vigiar_429(servico, flag)
        if asyncio.run(servico.run()):
            return
        if tentativa < TENTATIVAS:
            espera = ESPERA_429 * 2 ** (tentativa - 1) if flag["429"] else min(5 * 2 ** (tentativa - 1), 60)
            motivo = "429 (limite de requisições)" if flag["429"] else "falha"
            log(f"SigPesq: {motivo} na tentativa {tentativa}/{TENTATIVAS}; esperando {espera}s")
            time.sleep(espera)
    raise DownloadSigPesqFalhou(f"download do SigPesq falhou após {TENTATIVAS} tentativas")


def extrair_sigpesq(*, headless: bool = True, log: Log = print) -> Execucao:
    """Baixa os relatórios, converte para JSON filtrado e apaga os XLSX."""
    exe = Execucao("sigpesq", "download")
    tmp = trabalho_dir() / "sigpesq_xlsx"
    try:
        baixar(tmp, headless=headless, log=log)
        converter_pasta(tmp, exe, apagar=True)
    except Exception as e:
        exe.falha("download", e)
        raise
    finally:
        shutil.rmtree(tmp, ignore_errors=True)   # nenhum XLSX fica em etl/ (CA3)
        exe.finalizar()
    return exe
