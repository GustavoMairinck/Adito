import pytest

from adito_etl.comum import CredencialAusente, Execucao, credencial, ler_json


def test_credencial_vem_do_env_do_etl(base, monkeypatch):
    (base / ".env").write_text("ADITO_CREDENCIAIS=env\nSRC_USER=fulano\nSRC_PASSWORD='s3nha'\n",
                               encoding="utf-8")
    monkeypatch.setenv("USER", "usuario_do_so")
    assert credencial(["SRC_USER"], ["SRC_PASSWORD"]) == ("fulano", "s3nha")


def test_credencial_ausente_explica_o_que_falta(base, monkeypatch):
    monkeypatch.delenv("SRC_USER", raising=False)
    monkeypatch.delenv("SRC_PASSWORD", raising=False)
    (base / ".env").write_text("ADITO_CREDENCIAIS=env\n", encoding="utf-8")
    with pytest.raises(CredencialAusente, match="SRC_USER"):
        credencial(["SRC_USER"], ["SRC_PASSWORD"])


def test_extracao_registra_etapas_e_falhas_sem_pii(base):
    exe = Execucao("src", "acoes")
    exe.conta("acoes_gravadas", 2)
    exe.falha("acao 9", RuntimeError("timeout ao falar com fulano@x.com"))
    exe.finalizar()
    Execucao("src", "participacoes").finalizar()

    reg = ler_json(base / "brutos" / "src" / "_extracao.json")
    assert set(reg) == {"acoes", "participacoes"}
    assert reg["acoes"]["contagens"] == {"acoes_gravadas": 2}
    assert reg["acoes"]["falhas"] == [{"unidade": "acao 9", "erro": "timeout ao falar com [e-mail removido]"}]
