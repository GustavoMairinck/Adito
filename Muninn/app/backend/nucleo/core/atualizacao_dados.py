"""
Atualização do dados.db sem ETL na máquina do usuário.

A equipe publica, num endereço fixo (GitHub Pages), um `manifest.json`:

    {"versao": "2026.11.20", "schema": 1, "url": "dados-2026.11.20.db.gz",
     "sha256": "<do .db descompactado>", "tamanho": 123456, "publicado_em": "2026-11-20"}

O app compara a versão com a instalada (`dados.versao.json` na pasta de dados), baixa o .gz,
confere o sha256 e a integridade do SQLite, guarda a base anterior em `dados.db.anterior` e troca
o arquivo. As conexões com o dados.db são abertas por consulta, então a troca não exige reiniciar.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin

from .datastore import data_dir

# Endereço do manifest. O padrão aponta para o Pages do fork de teste; troque pela variável
# de ambiente (ou mude aqui) quando a distribuição for para o repositório da organização.
MANIFEST_URL_PADRAO = "https://gustavomairinck.github.io/Adito/dados/manifest.json"
# Versão do schema do dados.db que este app entende. Uma base com schema maior pede app novo.
SCHEMA_SUPORTADO = 1

Progresso = Callable[[str, float | None], None]


def manifest_url() -> str:
    return os.environ.get("MUNINN_DADOS_MANIFEST_URL") or MANIFEST_URL_PADRAO


def _arquivo_versao() -> Path:
    return data_dir() / "dados.versao.json"


def versao_instalada() -> dict | None:
    try:
        return json.loads(_arquivo_versao().read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return None


def buscar_manifest(timeout: float = 15.0) -> dict:
    import httpx

    resp = httpx.get(manifest_url(), timeout=timeout, follow_redirects=True)
    resp.raise_for_status()
    manifest = resp.json()
    for campo in ("versao", "url", "sha256"):
        if not manifest.get(campo):
            raise ValueError(f"manifest.json sem o campo '{campo}'.")
    return manifest


def situacao() -> dict:
    """Versão instalada x publicada, sem baixar nada."""
    instalada = versao_instalada()
    try:
        publicada = buscar_manifest()
        erro = None
    except Exception as exc:  # sem rede, Pages fora do ar, manifest inválido
        publicada, erro = None, str(exc)[:200]
    tem_nova = bool(publicada) and (instalada or {}).get("versao") != publicada["versao"]
    compativel = not publicada or int(publicada.get("schema", 1)) <= SCHEMA_SUPORTADO
    return {
        "instalada": instalada,
        "publicada": publicada,
        "tem_atualizacao": tem_nova and compativel,
        "precisa_app_novo": tem_nova and not compativel,
        "manifest_url": manifest_url(),
        "erro": erro,
    }


def _baixar(url: str, destino: Path, progresso: Progresso) -> None:
    import httpx

    with httpx.stream("GET", url, timeout=60.0, follow_redirects=True) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length") or 0)
        lido = 0
        with destino.open("wb") as f:
            for bloco in resp.iter_bytes(1 << 16):
                f.write(bloco)
                lido += len(bloco)
                progresso("baixando", lido / total if total else None)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _validar_sqlite(path: Path) -> None:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if ok != "ok":
            raise ValueError(f"integrity_check falhou: {ok}")
        views = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view'").fetchone()[0]
        if views == 0:
            raise ValueError("a base baixada não tem nenhuma view analítica.")
    finally:
        conn.close()


def _substituir(origem: Path, destino: Path, tentativas: int = 10) -> None:
    # No Windows a troca falha se alguma consulta estiver com o arquivo aberto naquele instante.
    for i in range(tentativas):
        try:
            os.replace(origem, destino)
            return
        except PermissionError:
            if i == tentativas - 1:
                raise
            time.sleep(0.5)


def atualizar(progresso: Progresso = lambda etapa, fracao: None) -> dict:
    """Baixa e instala a base publicada. Devolve a versão instalada."""
    manifest = buscar_manifest()
    if int(manifest.get("schema", 1)) > SCHEMA_SUPORTADO:
        raise ValueError("Esta base precisa de uma versão mais nova do Muninn. Atualize o app primeiro.")

    pasta = data_dir()
    gz = pasta / "dados.db.baixando"
    novo = pasta / "dados.db.novo"
    atual = pasta / "dados.db"
    anterior = pasta / "dados.db.anterior"
    try:
        _baixar(urljoin(manifest_url(), manifest["url"]), gz, progresso)

        progresso("descompactando", None)
        with gzip.open(gz, "rb") as src, novo.open("wb") as dst:
            shutil.copyfileobj(src, dst, 1 << 20)

        progresso("conferindo", None)
        if _sha256(novo) != manifest["sha256"].lower():
            raise ValueError("O arquivo baixado não confere com o sha256 do manifest. Nada foi trocado.")
        _validar_sqlite(novo)

        progresso("instalando", None)
        # WAL/SHM antigos não podem sobreviver à troca: seriam aplicados sobre a base nova.
        for sufixo in ("-wal", "-shm"):
            Path(f"{atual}{sufixo}").unlink(missing_ok=True)
        if atual.exists():
            _substituir(atual, anterior)
        _substituir(novo, atual)
    finally:
        gz.unlink(missing_ok=True)
        novo.unlink(missing_ok=True)

    instalada = {
        "versao": manifest["versao"],
        "sha256": manifest["sha256"],
        "instalada_em": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    _arquivo_versao().write_text(json.dumps(instalada, ensure_ascii=False, indent=2), encoding="utf-8")
    return instalada


def restaurar_anterior() -> bool:
    """Volta para a base de antes da última atualização, se ela existir."""
    pasta = data_dir()
    anterior, atual = pasta / "dados.db.anterior", pasta / "dados.db"
    if not anterior.exists():
        return False
    _substituir(anterior, atual)
    _arquivo_versao().unlink(missing_ok=True)
    return True
