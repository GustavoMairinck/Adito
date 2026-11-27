"""Testes dos embeddings locais (modelo, geração no dados.db, índice e busca).

Rodar de backend/nucleo: `python -m unittest core.test_embeddings_locais`.
Usa um modelo falso (trigramas de caracteres): textos parecidos ficam próximos, sem baixar nada.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import sqlite3
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from analytics_index import modelo_local, valores
from analytics_index.modelo_local import EmbedderLocal, Modelo, instalar_pacote

RAIZ_ADITO = Path(__file__).resolve().parents[4]
DIM = 128


class MotorFalso:
    """Vetor = contagem de trigramas do texto normalizado, espalhada em DIM posições."""

    def embed(self, textos):
        for texto in textos:
            t = f"  {valores.normalizar_texto(texto)}  "
            v = np.zeros(DIM, dtype=np.float32)
            for i in range(len(t) - 2):
                v[int(hashlib.md5(t[i:i + 3].encode()).hexdigest(), 16) % DIM] += 1
            yield v


MODELO_FALSO = Modelo(chave="falso", nome="falso", dim=DIM)


def embedder_falso() -> EmbedderLocal:
    return EmbedderLocal(MODELO_FALSO, criar=lambda m: MotorFalso())


def carregar_script(nome: str):
    spec = importlib.util.spec_from_file_location(nome, RAIZ_ADITO / "scripts" / f"{nome}.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def criar_banco(caminho: Path) -> None:
    conn = sqlite3.connect(caminho)
    conn.execute("CREATE TABLE fonte (campus TEXT, area TEXT, titulo TEXT)")
    conn.executemany(
        "INSERT INTO fonte VALUES (?, ?, ?)",
        [
            ("Serra; Vitória", "Engenharias", "Robótica educacional nas escolas"),
            ("Cariacica", "Ciências Humanas", "Oficina de leitura"),
            ("Serra", "Engenharias", "Robótica educacional nas escolas"),
            (None, " ", "Horta comunitária"),
        ],
    )
    conn.execute("CREATE VIEW vfact_teste AS SELECT * FROM fonte")
    conn.commit()
    conn.close()


def criar_contexto(pasta: Path) -> Path:
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "views.json").write_text(json.dumps({
        "contexto": "teste",
        "views": [{
            "name": "vfact_teste",
            "embed_columns": ["campus", "area", "titulo"],
            "multi_valor_columns": ["campus"],
        }],
    }), encoding="utf-8")
    return pasta


class ModeloLocalTests(unittest.TestCase):
    def test_vetores_saem_normalizados_e_com_prefixo(self):
        vistos = []

        class Motor(MotorFalso):
            def embed(self, textos):
                vistos.extend(textos)
                return super().embed(textos)

        modelo = Modelo(chave="e5", nome="e5", dim=DIM, prefixo_pergunta="query: ", prefixo_texto="passage: ")
        emb = EmbedderLocal(modelo, criar=lambda m: Motor())
        m = emb.matriz(["Serra", "Vitória"])
        self.assertTrue(np.allclose(np.linalg.norm(m, axis=1), 1.0))
        emb.embed_query("campus Serra")
        self.assertEqual(vistos, ["passage: Serra", "passage: Vitória", "query: campus Serra"])

    def test_modelo_desconhecido_falha_com_mensagem_clara(self):
        with patch.dict(os.environ, {"ADITO_EMBEDDING_MODELO": "nao-existe"}):
            with self.assertRaisesRegex(ValueError, "desconhecido"):
                modelo_local.modelo_ativo()


class InstalarPacoteTests(unittest.TestCase):
    def _pacote(self, pasta: Path) -> Path:
        pacote = pasta / "modelo.tar.gz"
        with tarfile.open(pacote, "w:gz") as tar:
            dados = b"onnx falso"
            info = tarfile.TarInfo("model.onnx")
            info.size = len(dados)
            tar.addfile(info, io.BytesIO(dados))
        return pacote

    def test_instala_quando_sha_confere(self):
        with tempfile.TemporaryDirectory() as tmp:
            pacote = self._pacote(Path(tmp))
            manifesto = {
                "chave": "falso",
                "tamanho": pacote.stat().st_size,
                "sha256": hashlib.sha256(pacote.read_bytes()).hexdigest(),
            }
            destino = instalar_pacote(pacote, manifesto, Path(tmp) / "models")
            self.assertEqual((destino / "model.onnx").read_bytes(), b"onnx falso")
            self.assertTrue((destino / ".completo").exists())

    def test_recusa_pacote_corrompido_sem_deixar_nada(self):
        with tempfile.TemporaryDirectory() as tmp:
            pacote = self._pacote(Path(tmp))
            manifesto = {"chave": "falso", "tamanho": pacote.stat().st_size, "sha256": "0" * 64}
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                instalar_pacote(pacote, manifesto, Path(tmp) / "models")
            self.assertFalse((Path(tmp) / "models" / "falso").exists())


class GeracaoEIndiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.banco = Path(self.tmp.name) / "dados.db"
        criar_banco(self.banco)
        self.contexto = criar_contexto(Path(self.tmp.name) / "ctx")
        self.gerar = carregar_script("gerar_embeddings_dados")
        p = patch.object(valores, "modelo_ativo", return_value=MODELO_FALSO)
        p.start()
        self.addCleanup(p.stop)

    def test_gera_um_vetor_por_valor_distinto_por_coluna(self):
        resumo = self.gerar.gerar(self.banco, self.contexto, embedder_falso(), log=lambda *_: None)
        self.assertEqual(resumo["totais"], {
            "vfact_teste.campus": 3,   # "Serra; Vitória" vira Serra e Vitória; Serra não repete
            "vfact_teste.area": 2,     # vazio e NULL ficam de fora
            "vfact_teste.titulo": 3,
        })
        indice = valores.carregar_indice(self.banco)
        self.assertTrue(indice.disponivel, indice.motivo)
        self.assertEqual(len(indice), 8)
        self.assertEqual(indice.catalogo()[("vfact_teste", "campus")]["vitoria"], "Vitória")

    def test_busca_por_cosseno_acha_o_valor_certo_e_respeita_o_minimo(self):
        self.gerar.gerar(self.banco, self.contexto, embedder_falso(), log=lambda *_: None)
        indice = valores.carregar_indice(self.banco)
        consultas = embedder_falso().matriz(["cariacca", "xyzw"], pergunta=True)
        achados = indice.buscar(consultas, minimo=0.5)
        self.assertEqual(achados[0][0]["valor"], "Cariacica")
        self.assertEqual(achados[1], [])

    def test_modelo_diferente_desliga_a_busca(self):
        self.gerar.gerar(self.banco, self.contexto, embedder_falso(), log=lambda *_: None)
        outro = Modelo(chave="outro", nome="outro", dim=DIM)
        with patch.object(valores, "modelo_ativo", return_value=outro):
            indice = valores.carregar_indice(self.banco)
        self.assertFalse(indice.disponivel)
        self.assertIn("'falso'", indice.motivo)
        self.assertEqual(indice.buscar(np.ones((1, DIM)), 0.0), [[]])

    def test_banco_sem_vetores_desliga_a_busca(self):
        indice = valores.carregar_indice(self.banco)
        self.assertFalse(indice.disponivel)
        self.assertIn("sem embeddings", indice.motivo)

    def test_tabelas_de_vetores_ficam_fora_do_sql_do_llm(self):
        from agents.bi_agent.sql_security import validate_read_only_sql

        ok, erro = validate_read_only_sql("SELECT valor FROM adito_valor_embedding", {"vfact_teste"})
        self.assertFalse(ok, erro)


if __name__ == "__main__":
    unittest.main()
