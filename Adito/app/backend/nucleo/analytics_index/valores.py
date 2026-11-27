"""Índice de valores do `dados.db`: vetores pré-gerados no release, buscados em memória por cosseno.

Quem publica os dados roda `Adito/scripts/gerar_embeddings_dados.py`, que grava duas tabelas
dentro do próprio `dados.db` antes de cifrar:

    adito_embedding_meta(chave TEXT PRIMARY KEY, valor TEXT)       -- modelo, dim, data
    adito_valor_embedding(view, coluna, valor, vetor BLOB float16)  -- um vetor por valor distinto

As tabelas não estão em `exposed_views`, então o SQL gerado pelo LLM nunca as lê.
Se o modelo gravado não for o do app, a busca semântica fica desligada (vetores de modelos
diferentes não se comparam) e o motivo aparece no painel admin.
"""
from __future__ import annotations

import difflib
import logging
import re
import threading
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from core.datastore import connect_dados, dados_db_path

from .modelo_local import modelo_ativo

logger = logging.getLogger(__name__)

TABELA_META = "adito_embedding_meta"
TABELA_VETORES = "adito_valor_embedding"


def normalizar_texto(valor: object) -> str:
    """Minúsculas, sem acento e com espaços simples (mesma ideia do LIKE do Adito)."""
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", texto.lower()).strip()


def parecido_em_letras(termo: str, valor: str) -> float:
    """0 a 1: quanto o termo se parece, letra a letra, com o valor ou com um pedaço dele do mesmo tamanho.

    Serve de segundo filtro da busca semântica: o modelo aproxima "futebol" de algum título, mas as letras não.
    """
    t, v = normalizar_texto(termo).replace("_", " "), normalizar_texto(valor).replace("_", " ")
    if not t or not v:
        return 0.0
    palavras = v.split()
    n = max(1, len(t.split()))
    janelas = {" ".join(palavras[i:i + n]) for i in range(max(1, len(palavras) - n + 1))} | {v}
    return max(difflib.SequenceMatcher(None, t, j).ratio() for j in janelas)


@dataclass
class IndiceValores:
    disponivel: bool
    motivo: str = ""
    modelo: str = ""
    versao: str = ""                       # muda quando o dados.db muda: serve de chave de cache
    views: np.ndarray = field(default_factory=lambda: np.array([], dtype=object))
    colunas: np.ndarray = field(default_factory=lambda: np.array([], dtype=object))
    valores: list[str] = field(default_factory=list)
    matriz: np.ndarray = field(default_factory=lambda: np.zeros((0, 0), dtype=np.float32))
    _catalogo: dict[tuple[str, str], dict[str, str]] | None = None

    def __len__(self) -> int:
        return len(self.valores)

    def catalogo(self) -> dict[tuple[str, str], dict[str, str]]:
        """(view, coluna) → {valor normalizado: valor real}. Serve para conferir literais do SQL."""
        if self._catalogo is None:
            cat: dict[tuple[str, str], dict[str, str]] = {}
            for view, coluna, valor in zip(self.views, self.colunas, self.valores):
                cat.setdefault((view, coluna), {})[normalizar_texto(valor)] = valor
            self._catalogo = cat
        return self._catalogo

    def buscar(
        self,
        consultas: np.ndarray,
        minimo: float,
        por_consulta: int = 3,
        views: set[str] | None = None,
    ) -> list[list[dict]]:
        """Para cada linha de `consultas` (já normalizada), os valores com cosseno >= `minimo`."""
        if not self.disponivel or len(self) == 0 or len(consultas) == 0:
            return [[] for _ in range(len(consultas))]
        sims = consultas @ self.matriz.T
        if views:
            sims[:, ~np.isin(self.views, list(views))] = -1.0
        resultados = []
        for linha in sims:
            ordem = np.argsort(-linha)[:por_consulta]
            resultados.append([
                {
                    "view": self.views[i],
                    "coluna": self.colunas[i],
                    "valor": self.valores[i],
                    "similaridade": float(linha[i]),
                }
                for i in ordem
                if linha[i] >= minimo
            ])
        return resultados


def _versao(caminho: Path) -> str:
    st = caminho.stat()
    return f"{st.st_size}-{st.st_mtime_ns}"


def carregar_indice(caminho: Path | None = None) -> IndiceValores:
    caminho = Path(caminho or dados_db_path())
    modelo = modelo_ativo()
    if not caminho.exists():
        return IndiceValores(False, "dados.db não encontrado.", modelo.chave)
    versao = _versao(caminho)
    with connect_dados(path=caminho) as conn:
        tem = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN (?, ?)",
                [TABELA_META, TABELA_VETORES],
            )
        }
        if tem != {TABELA_META, TABELA_VETORES}:
            return IndiceValores(False, "O dados.db não traz os vetores de busca (publicado sem embeddings).",
                                 modelo.chave, versao)
        meta = dict(conn.execute(f"SELECT chave, valor FROM {TABELA_META}").fetchall())
        if meta.get("modelo") != modelo.chave:
            return IndiceValores(
                False,
                f"Os vetores do dados.db são do modelo {meta.get('modelo')!r}, mas o app usa {modelo.chave!r}.",
                modelo.chave,
                versao,
            )
        linhas = conn.execute(f"SELECT view, coluna, valor, vetor FROM {TABELA_VETORES}").fetchall()
    if not linhas:
        return IndiceValores(True, "", modelo.chave, versao)
    matriz = np.vstack([np.frombuffer(bytes(r[3]), dtype=np.float16) for r in linhas]).astype(np.float32)
    if matriz.shape[1] != modelo.dim:
        return IndiceValores(False, f"Dimensão dos vetores ({matriz.shape[1]}) diferente do modelo ({modelo.dim}).",
                             modelo.chave, versao)
    return IndiceValores(
        True,
        "",
        modelo.chave,
        versao,
        views=np.array([r[0] for r in linhas], dtype=object),
        colunas=np.array([r[1] for r in linhas], dtype=object),
        valores=[r[2] for r in linhas],
        matriz=matriz,
    )


_cache: IndiceValores | None = None
_cache_lock = threading.Lock()


def indice_valores() -> IndiceValores:
    """Índice em memória; recarrega sozinho quando o dados.db é trocado (atualização dos dados)."""
    global _cache
    caminho = Path(dados_db_path())
    versao = _versao(caminho) if caminho.exists() else ""
    with _cache_lock:
        if _cache is None or _cache.versao != versao:
            try:
                _cache = carregar_indice(caminho)
            except Exception as exc:
                logger.warning("Falha ao carregar o índice de valores: %s", exc)
                _cache = IndiceValores(False, f"Falha ao ler os vetores: {exc}", modelo_ativo().chave, versao)
            if not _cache.disponivel:
                logger.warning("Busca semântica de valores desligada: %s", _cache.motivo)
        return _cache


def versao_busca() -> str:
    """Identifica o par modelo + dados.db atual (para invalidar caches de resposta)."""
    indice = indice_valores()
    return f"{indice.modelo}:{indice.versao}"
