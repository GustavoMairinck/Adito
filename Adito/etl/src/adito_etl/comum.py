"""Peças comuns aos extratores: pastas, credenciais, gravação segura e `_extracao.json`."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from . import pii


# ------------------------------------------------------------------ pastas
def base_dir() -> Path:
    """Pasta `etl/` (ou `ADITO_ETL_BASE`, usado nos testes)."""
    env = os.environ.get("ADITO_ETL_BASE")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[2]


def brutos_dir(fonte: str) -> Path:
    return base_dir() / "brutos" / fonte


def trabalho_dir() -> Path:
    return base_dir() / "trabalho"


# ------------------------------------------------------------------ credenciais
class CredencialAusente(RuntimeError):
    """Credencial não encontrada (etl/.env, ambiente ou Infisical)."""


def ler_env(path: Path | None = None) -> dict[str, str]:
    """Lê `etl/.env` (CHAVE=valor). Arquivo ausente = dicionário vazio."""
    p = path or (base_dir() / ".env")
    dados: dict[str, str] = {}
    if p.exists():
        for linha in p.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                k, v = linha.split("=", 1)
                dados[k.strip()] = v.strip().strip('"').strip("'")
    return dados


ORIGEM_CREDENCIAIS = "ADITO_CREDENCIAIS"
ORIGENS = ("infisical", "env")


def config(chave: str) -> str | None:
    """Valor de configuração: primeiro `etl/.env`, depois o ambiente."""
    return ler_env().get(chave) or os.environ.get(chave) or None


def origem_credenciais() -> str:
    """`infisical` ou `env`, escolhida explicitamente (como o SIGPESQ_CREDENTIALS_SOURCE do horizon)."""
    v = (config(ORIGEM_CREDENCIAIS) or "").strip().lower()
    if v not in ORIGENS:
        raise CredencialAusente(
            f"defina {ORIGEM_CREDENCIAIS}=infisical ou {ORIGEM_CREDENCIAIS}=env em {base_dir() / '.env'} "
            f"(valor atual: {v or 'vazio'}); não há padrão")
    return v


def credencial(chaves_usuario: Iterable[str], chaves_senha: Iterable[str],
               segredos: tuple[str, str] | None = None) -> tuple[str, str]:
    """Usuário e senha de uma fonte.

    - `ADITO_CREDENCIAIS=infisical`: lê os segredos `segredos` (usuário, senha) no
      Infisical; os nomes podem ser trocados por `INFISICAL_<CHAVE>_SECRET` no .env
      (ex.: INFISICAL_SRC_USER_SECRET).
    - `ADITO_CREDENCIAIS=env`: lê as chaves do `etl/.env` ou do ambiente. Só chaves
      com prefixo da fonte (ex.: SRC_USER), nunca `USER`, que no SO é o usuário logado.
    """
    cu, cs = list(chaves_usuario), list(chaves_senha)
    if origem_credenciais() == "infisical":
        if not segredos:
            raise CredencialAusente(f"fonte sem segredo no Infisical configurado ({cu[0]})")
        from .segredos import Infisical, SegredoIndisponivel
        nome_u = config(f"INFISICAL_{cu[0]}_SECRET") or segredos[0]
        nome_s = config(f"INFISICAL_{cs[0]}_SECRET") or segredos[1]
        try:
            cofre = Infisical(config)
            return cofre.segredo(nome_u), cofre.segredo(nome_s)
        except SegredoIndisponivel as e:
            raise CredencialAusente(str(e)) from e

    def pega(chaves: list[str]) -> str | None:
        return next((config(k) for k in chaves if config(k)), None)

    usuario, senha = pega(cu), pega(cs)
    if not usuario or not senha:
        raise CredencialAusente(
            f"credencial ausente: defina {cu[0]} e {cs[0]} em {base_dir() / '.env'}"
        )
    return usuario, senha


# ------------------------------------------------------------------ gravação
def gravar_json(path: Path, dados: Any) -> None:
    """Grava JSON de forma atômica, depois de passar pela trava de PII."""
    texto = json.dumps(dados, ensure_ascii=False, indent=2)
    pii.auditar(texto, str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(texto + "\n", encoding="utf-8")
    tmp.replace(path)


def ler_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def filtrar_colunas(
    linhas: list[dict[str, Any]],
    permitidas: Iterable[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Mantém só as colunas permitidas (BR01).

    Devolve (linhas filtradas, colunas descartadas que não são pessoais
    conhecidas). Colunas pessoais (CPF, e-mail...) são descartadas sem aviso;
    qualquer outra coluna fora da lista é descartada e devolvida para aviso.
    """
    permitidas = set(permitidas)
    novas: set[str] = set()
    saida = []
    for linha in linhas:
        saida.append({k: v for k, v in linha.items() if k in permitidas})
        for k in linha:
            if k not in permitidas and k and not pii.chave_pessoal(k):
                novas.add(k)
    return saida, sorted(novas)


# ------------------------------------------------------------------ execução
def agora() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def commit_atual() -> str | None:
    try:
        r = subprocess.run(
            ["git", "-C", str(base_dir()), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return r.stdout.strip() or None
    except Exception:
        return None


@dataclass
class Execucao:
    """Registro de uma execução de extrator, gravado em `brutos/<fonte>/_extracao.json`."""

    fonte: str
    etapa: str
    inicio: str = field(default_factory=agora)
    contagens: dict[str, int] = field(default_factory=dict)
    falhas: list[dict[str, str]] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    def conta(self, chave: str, n: int = 1) -> None:
        self.contagens[chave] = self.contagens.get(chave, 0) + n

    def falha(self, unidade: str, erro: object) -> None:
        texto = str(erro).strip() or repr(erro)
        msg, _ = pii.mascarar(texto.splitlines()[0][:200])
        self.falhas.append({"unidade": unidade, "erro": msg})

    def aviso(self, msg: str) -> None:
        if msg not in self.avisos:
            self.avisos.append(msg)

    def finalizar(self) -> Path:
        destino = brutos_dir(self.fonte) / "_extracao.json"
        registro = ler_json(destino) if destino.exists() else {}
        registro[self.etapa] = {
            "inicio": self.inicio,
            "fim": agora(),
            "commit": commit_atual(),
            "contagens": dict(sorted(self.contagens.items())),
            "falhas": self.falhas,
            "avisos": self.avisos,
        }
        gravar_json(destino, registro)
        return destino
