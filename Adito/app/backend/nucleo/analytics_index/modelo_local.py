"""Modelo de embedding local (fastembed/ONNX, CPU): o mesmo na publicação dos dados e no app.

Os vetores dos valores do banco são gerados por quem publica o `dados.db` e chegam prontos no
release. Só a pergunta é embedada na máquina do usuário, com este mesmo modelo, sem API e sem cota.
Vetores de modelos diferentes não se comparam; por isso o modelo é um só e o nome dele vai junto
dos vetores (`adito_embedding_meta`) e no `modelo.json` do release.

O modelo é baixado da release `dados` (mesma tag do `dados.db`), sem criptografia, com conferência
de tamanho e SHA-256, para `<pasta de dados>/models/<chave>/`. Em desenvolvimento, sem pacote
baixado, o fastembed busca o modelo no Hugging Face.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import tarfile
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from core.datastore import data_dir

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Modelo:
    chave: str
    nome: str                      # nome no fastembed / Hugging Face
    dim: int
    prefixo_pergunta: str = ""     # e5 exige "query: " e "passage: "
    prefixo_texto: str = ""
    custom: dict = field(default_factory=dict)  # registro via TextEmbedding.add_custom_model


# Candidatos multilíngues em int8. A escolha final sai do eval com o dados.db real.
MODELOS: dict[str, Modelo] = {
    "minilm-l12-int8": Modelo(
        chave="minilm-l12-int8",
        nome="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",  # versão Qdrant já quantizada
        dim=384,
    ),
    "e5-small-int8": Modelo(
        chave="e5-small-int8",
        nome="Xenova/multilingual-e5-small",
        dim=384,
        prefixo_pergunta="query: ",
        prefixo_texto="passage: ",
        custom={"model_file": "onnx/model_quantized.onnx"},
    ),
    "e5-large-int8": Modelo(
        chave="e5-large-int8",
        nome="Xenova/multilingual-e5-large",
        dim=1024,
        prefixo_pergunta="query: ",
        prefixo_texto="passage: ",
        custom={"model_file": "onnx/model_quantized.onnx"},
    ),
}

# Escolhido em 27/11/2026 pela comparação no dados.db real (scripts/teste_busca_valores.py, ADR-0009):
# empata com o e5-large no acerto em 1º, gera 9x mais rápido e ocupa 4x menos.
MODELO_PADRAO = "e5-small-int8"

MANIFESTO_MODELO = "modelo.json"
URL_PADRAO = "https://github.com/SmartIdea-ifes-serra/Adito/releases/download/dados/"


def modelo_ativo() -> Modelo:
    chave = (os.environ.get("ADITO_EMBEDDING_MODELO") or MODELO_PADRAO).strip()
    if chave not in MODELOS:
        raise ValueError(f"Modelo de embedding desconhecido: {chave!r}. Opções: {', '.join(MODELOS)}.")
    return MODELOS[chave]


def pasta_modelos() -> Path:
    return Path(os.environ.get("ADITO_MODELOS_DIR") or data_dir() / "models")


def normalizar(matriz: np.ndarray) -> np.ndarray:
    """Linhas com norma 1: o produto escalar vira similaridade de cosseno."""
    matriz = np.asarray(matriz, dtype=np.float32)
    normas = np.linalg.norm(matriz, axis=-1, keepdims=True)
    return matriz / np.where(normas == 0, 1, normas)


class EmbedderLocal:
    """Mesma interface do `Embeddings` do LangChain (`embed_documents`/`embed_query`), mais `matriz`."""

    def __init__(self, modelo: Modelo | None = None, criar=None):
        self.modelo = modelo or modelo_ativo()
        self._criar = criar or _criar_fastembed
        self._motor = None
        self._lock = threading.Lock()

    def _carregado(self):
        if self._motor is None:
            with self._lock:
                if self._motor is None:
                    self._motor = self._criar(self.modelo)
        return self._motor

    def matriz(self, textos: list[str], pergunta: bool = False) -> np.ndarray:
        if not textos:
            return np.zeros((0, self.modelo.dim), dtype=np.float32)
        prefixo = self.modelo.prefixo_pergunta if pergunta else self.modelo.prefixo_texto
        vetores = list(self._carregado().embed([prefixo + t for t in textos]))
        return normalizar(np.vstack(vetores))

    def embed_documents(self, textos: list[str]) -> list[list[float]]:
        return self.matriz(list(textos)).tolist()

    def embed_query(self, texto: str) -> list[float]:
        return self.matriz([texto], pergunta=True)[0].tolist()


def _criar_fastembed(modelo: Modelo):
    from fastembed import TextEmbedding

    if modelo.custom and modelo.nome not in {m["model"] for m in TextEmbedding.list_supported_models()}:
        from fastembed.common.model_description import ModelSource, PoolingType

        TextEmbedding.add_custom_model(
            model=modelo.nome,
            pooling=PoolingType.MEAN,
            normalization=True,
            sources=ModelSource(hf=modelo.nome),
            dim=modelo.dim,
            model_file=modelo.custom.get("model_file", "onnx/model.onnx"),
        )
    local = pasta_modelos() / modelo.chave
    if (local / ".completo").exists():
        return TextEmbedding(modelo.nome, specific_model_path=str(local), local_files_only=True)
    # Desenvolvimento: sem pacote baixado do release, o fastembed baixa do Hugging Face.
    return TextEmbedding(modelo.nome, cache_dir=str(pasta_modelos() / "cache"))


# ── Download do release (sem criptografia, com SHA-256) ─────────────────────

def _url_base() -> str:
    base = os.environ.get("ADITO_DADOS_URL") or URL_PADRAO
    return base if base.endswith("/") else base + "/"


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def instalar_pacote(pacote: Path, manifesto: dict, destino_base: Path | None = None) -> Path:
    """Confere tamanho e SHA-256 do `.tar.gz` e extrai para `models/<chave>/` (troca atômica)."""
    if pacote.stat().st_size != int(manifesto["tamanho"]) or _sha256(pacote) != manifesto["sha256"].lower():
        raise ValueError("Pacote do modelo corrompido (tamanho ou SHA-256 não confere).")
    base = destino_base or pasta_modelos()
    base.mkdir(parents=True, exist_ok=True)
    destino = base / manifesto["chave"]
    temporaria = Path(tempfile.mkdtemp(prefix=".modelo-", dir=base))
    try:
        with tarfile.open(pacote, "r:gz") as tar:
            tar.extractall(temporaria, filter="data")  # recusa caminhos absolutos e "../"
        (temporaria / ".completo").write_text(json.dumps(manifesto), encoding="utf-8")
        if destino.exists():
            shutil.rmtree(destino)
        temporaria.rename(destino)
    except Exception:
        shutil.rmtree(temporaria, ignore_errors=True)
        raise
    return destino


def baixar_modelo(modelo: Modelo | None = None) -> Path | None:
    """Baixa o modelo do release se ainda não estiver na pasta de dados. None quando já estava."""
    import httpx

    modelo = modelo or modelo_ativo()
    if (pasta_modelos() / modelo.chave / ".completo").exists():
        return None
    resposta = httpx.get(_url_base() + MANIFESTO_MODELO, follow_redirects=True, timeout=30)
    resposta.raise_for_status()
    manifesto = resposta.json()
    if manifesto.get("chave") != modelo.chave:
        raise ValueError(
            f"O release publica o modelo {manifesto.get('chave')!r}, mas este app usa {modelo.chave!r}."
        )
    with tempfile.TemporaryDirectory() as tmp:
        pacote = Path(tmp) / "modelo.tar.gz"
        with httpx.stream("GET", _url_base() + manifesto["arquivo"], follow_redirects=True, timeout=120) as r:
            r.raise_for_status()
            with open(pacote, "wb") as f:
                for bloco in r.iter_bytes():
                    f.write(bloco)
        return instalar_pacote(pacote, manifesto)


# ── Instância única, carregada em segundo plano na abertura ─────────────────

_embedder: EmbedderLocal | None = None
_pronto = threading.Event()
_erro: str | None = None


def get_embedder_local() -> EmbedderLocal:
    global _embedder
    if _embedder is None:
        _embedder = EmbedderLocal()
    return _embedder


def estado() -> dict:
    return {"modelo": modelo_ativo().chave, "pronto": _pronto.is_set() and _erro is None, "erro": _erro}


def aguardar(segundos: float = 30.0) -> bool:
    """Espera o carregamento da abertura terminar. False se não ficou pronto (erro ou tempo)."""
    return _pronto.wait(segundos) and _erro is None


def preparar_em_segundo_plano() -> threading.Thread:
    """Baixa (se preciso), carrega e aquece o modelo sem travar a abertura do app."""

    def tarefa():
        global _erro
        try:
            if os.environ.get("ADITO_MODELO_SEM_DOWNLOAD") != "1":
                try:
                    baixar_modelo()
                except Exception as exc:  # sem rede ou sem release: tenta o que houver localmente
                    logger.warning("Não foi possível baixar o modelo de embedding: %s", exc)
            get_embedder_local().embed_query("aquecimento")
            from .valores import indice_valores
            from .vetores import atualizar_dados_locais

            try:  # valores que o dados.db ganhou e ainda não têm vetor: embeda só esses, aqui na máquina
                atualizar_dados_locais(get_embedder_local())
            except Exception as exc:
                logger.warning("Falha na atualização incremental dos vetores: %s", exc)

            indice_valores()  # carrega a matriz de valores do dados.db, se houver
            _erro = None
        except Exception as exc:
            _erro = str(exc) or exc.__class__.__name__
            logger.warning("Busca semântica indisponível: %s", _erro)
        finally:
            _pronto.set()

    thread = threading.Thread(target=tarefa, name="modelo-embedding", daemon=True)
    thread.start()
    return thread
