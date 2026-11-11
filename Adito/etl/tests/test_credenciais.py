import sys
import types

import pytest

from adito_etl.comum import CredencialAusente, credencial


def _env(base, texto):
    (base / ".env").write_text(texto, encoding="utf-8")


def test_sem_origem_explicita_para(base, monkeypatch):
    monkeypatch.delenv("ADITO_CREDENCIAIS", raising=False)
    _env(base, "SRC_USER=a\nSRC_PASSWORD=b\n")
    with pytest.raises(CredencialAusente, match="ADITO_CREDENCIAIS"):
        credencial(["SRC_USER"], ["SRC_PASSWORD"], segredos=("src-user", "src-password"))


def test_modo_env(base):
    _env(base, "ADITO_CREDENCIAIS=env\nSRC_USER=a\nSRC_PASSWORD=b\n")
    assert credencial(["SRC_USER"], ["SRC_PASSWORD"], segredos=("x", "y")) == ("a", "b")


def _sdk_falso(monkeypatch, segredos):
    vistos = {}

    class Cliente:
        def __init__(self, host, cache_ttl):
            vistos["host"] = host
            self.auth = types.SimpleNamespace(universal_auth=types.SimpleNamespace(
                login=lambda cid, sec: vistos.update(login=(cid, sec))))
            self.secrets = types.SimpleNamespace(get_secret_by_name=self._get)

        def _get(self, secret_name, project_id, environment_slug, secret_path):
            vistos.setdefault("pedidos", []).append((secret_name, project_id, environment_slug, secret_path))
            return types.SimpleNamespace(secretValue=segredos.get(secret_name))

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class APIError(Exception):
        pass

    class InfisicalError(Exception):
        pass

    sdk = types.ModuleType("infisical_sdk")
    sdk.InfisicalSDKClient = Cliente
    req = types.ModuleType("infisical_sdk.infisical_requests")
    req.APIError, req.InfisicalError = APIError, InfisicalError
    monkeypatch.setitem(sys.modules, "infisical_sdk", sdk)
    monkeypatch.setitem(sys.modules, "infisical_sdk.infisical_requests", req)
    return vistos


INFISICAL = ("ADITO_CREDENCIAIS=infisical\nINFISICAL_CLIENT_ID=id\nINFISICAL_CLIENT_SECRET=sec\n"
             "INFISICAL_PROJECT_ID=proj\n")


def test_modo_infisical_le_os_segredos_padrao(base, monkeypatch):
    vistos = _sdk_falso(monkeypatch, {"sigpesq-user": "u", "sigpesq-password": "p"})
    _env(base, INFISICAL + "SIGPESQ_USER=nao-usar\n")
    assert credencial(["SIGPESQ_USER"], ["SIGPESQ_PASSWORD"],
                      segredos=("sigpesq-user", "sigpesq-password")) == ("u", "p")
    assert vistos["login"] == ("id", "sec")
    assert vistos["pedidos"][0] == ("sigpesq-user", "proj", "dev", "/")


def test_modo_infisical_nome_do_segredo_configuravel(base, monkeypatch):
    _sdk_falso(monkeypatch, {"meu-src-user": "u", "src-password": "p"})
    _env(base, INFISICAL + "INFISICAL_SRC_USER_SECRET=meu-src-user\n")
    assert credencial(["SRC_USER"], ["SRC_PASSWORD"], segredos=("src-user", "src-password")) == ("u", "p")


def test_modo_infisical_segredo_vazio_ou_config_faltando(base, monkeypatch):
    _sdk_falso(monkeypatch, {"src-user": "u"})
    _env(base, INFISICAL)
    with pytest.raises(CredencialAusente, match="src-password"):
        credencial(["SRC_USER"], ["SRC_PASSWORD"], segredos=("src-user", "src-password"))
    _env(base, "ADITO_CREDENCIAIS=infisical\nINFISICAL_CLIENT_ID=id\n")
    with pytest.raises(CredencialAusente, match="INFISICAL_CLIENT_SECRET"):
        credencial(["SRC_USER"], ["SRC_PASSWORD"], segredos=("src-user", "src-password"))
