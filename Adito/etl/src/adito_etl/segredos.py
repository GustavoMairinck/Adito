"""Leitura de segredos no Infisical (Universal Auth).

Portado do horizon_etl (commit 13a1cec): `src/adapters/secrets/infisical.py`
(`InfisicalSecretProvider`) e `src/core/ports/secret_provider.py`. O import do
SDK (`infisicalsdk`) é preguiçoso: importar este módulo não exige o SDK nem rede.

Nenhuma mensagem de erro traz o valor do segredo.
"""

from __future__ import annotations

from typing import Callable

PADRAO_HOST = "https://app.infisical.com"
PADRAO_ENV = "dev"
PADRAO_CAMINHO = "/"
OBRIGATORIAS = ("INFISICAL_CLIENT_ID", "INFISICAL_CLIENT_SECRET", "INFISICAL_PROJECT_ID")


class SegredoIndisponivel(RuntimeError):
    """Não foi possível obter o segredo (configuração, acesso ou valor vazio)."""


class Infisical:
    """Lê segredos de um projeto do Infisical com a identidade de máquina da equipe."""

    def __init__(self, config: Callable[[str], str | None]):
        self.host = config("INFISICAL_HOST") or PADRAO_HOST
        self.client_id = config("INFISICAL_CLIENT_ID")
        self.client_secret = config("INFISICAL_CLIENT_SECRET")
        self.project_id = config("INFISICAL_PROJECT_ID")
        self.ambiente = config("INFISICAL_ENV") or PADRAO_ENV
        self.caminho = config("INFISICAL_SECRET_PATH") or PADRAO_CAMINHO

    def _onde(self) -> str:
        return f"projeto={self.project_id} ambiente={self.ambiente} caminho={self.caminho}"

    def _validar(self) -> None:
        valores = {"INFISICAL_CLIENT_ID": self.client_id, "INFISICAL_CLIENT_SECRET": self.client_secret,
                   "INFISICAL_PROJECT_ID": self.project_id}
        faltando = [k for k in OBRIGATORIAS if not valores[k]]
        if faltando:
            raise SegredoIndisponivel(
                "configuração do Infisical incompleta: defina " + ", ".join(faltando) + " em etl/.env")

    def segredo(self, nome: str) -> str:
        self._validar()
        try:
            from infisical_sdk import InfisicalSDKClient
            from infisical_sdk.infisical_requests import APIError, InfisicalError
        except ImportError as e:
            raise SegredoIndisponivel(
                "SDK do Infisical não instalado: rode `pip install -e '.[infisical]'` em etl/") from e
        try:
            with InfisicalSDKClient(host=self.host, cache_ttl=None) as cliente:
                cliente.auth.universal_auth.login(self.client_id, self.client_secret)
                s = cliente.secrets.get_secret_by_name(
                    secret_name=nome, project_id=self.project_id,
                    environment_slug=self.ambiente, secret_path=self.caminho)
        except APIError as e:
            raise self._erro_api(nome, e) from e
        except InfisicalError as e:
            raise SegredoIndisponivel(
                f"não foi possível acessar o Infisical em {self.host} ({self._onde()}): {e}") from e
        except Exception as e:  # noqa: BLE001 — sem expor valores
            raise SegredoIndisponivel(
                f"erro inesperado ao ler o segredo '{nome}' ({self._onde()}): {type(e).__name__}") from e
        valor = getattr(s, "secretValue", None)
        if not valor:
            raise SegredoIndisponivel(f"segredo '{nome}' ausente ou vazio no Infisical ({self._onde()})")
        return valor

    def _erro_api(self, nome: str, e) -> SegredoIndisponivel:
        status = getattr(e, "status_code", None)
        if status == 401:
            return SegredoIndisponivel(
                "Infisical recusou a autenticação (HTTP 401): INFISICAL_CLIENT_ID/INFISICAL_CLIENT_SECRET "
                "inválidos ou expirados")
        if status == 403:
            return SegredoIndisponivel(
                f"Infisical negou acesso ao segredo '{nome}' (HTTP 403) ({self._onde()})")
        if status == 404:
            return SegredoIndisponivel(
                f"segredo '{nome}' não encontrado no Infisical ({self._onde()}); confira "
                "INFISICAL_PROJECT_ID, INFISICAL_ENV e INFISICAL_SECRET_PATH")
        return SegredoIndisponivel(f"Infisical respondeu HTTP {status} ao ler '{nome}' ({self._onde()})")

    def __repr__(self) -> str:  # nunca mostra o client secret
        return f"Infisical(host={self.host!r}, {self._onde()})"
