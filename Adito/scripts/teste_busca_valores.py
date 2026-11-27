#!/usr/bin/env python3
"""Compara modelos de embedding na busca de valores do `dados.db`, sem chamar nenhuma LLM.

Para cada modelo: gera os vetores numa cópia do banco (mede o tempo), monta casos de teste a
partir dos próprios valores e mede se a busca acha o valor certo.

Casos gerados (sementes fixas, sempre os mesmos):
  - erro de digitação: uma letra a menos na palavra mais longa ("Cariacca" → "Cariacica");
  - código escrito como texto: "PESQUISA_APLICADA" → "pesquisa aplicada";
  - pedaço de título: 3 palavras do meio de títulos longos;
  - negativos: termos que não existem no banco (servem para achar o limite sem falso positivo).
Com `--casos arquivo.json` ([{"termo", "coluna", "valor"}]) entram também casos escritos à mão.

Uso (um processo por modelo, para medir memória direito):
    python3 teste_busca_valores.py caminho/dados.db --modelos minilm-l12-int8 e5-small-int8 e5-large-int8
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
NUCLEO = AQUI.parent / "app" / "backend" / "nucleo"
CONTEXTO_PADRAO = AQUI.parent / "app" / "contexts" / "pesquisa-extensao-ifes"
POR_COLUNA = 15
LIMITES = (0.70, 0.75, 0.80, 0.85, 0.90)
NEGATIVOS = [
    "futebol", "receita de bolo", "previsão do tempo", "carro elétrico", "bitcoin", "novela",
    "campeonato brasileiro", "imposto de renda", "aeroporto", "hamburguer", "academia de ginástica",
    "salário mínimo", "eleição", "praia", "cinema", "pizzaria", "show de rock", "videogame",
]


def _typo(valor: str, rnd: random.Random) -> str | None:
    palavras = valor.split()
    i = max(range(len(palavras)), key=lambda k: len(palavras[k]))
    p = palavras[i]
    if len(p) < 6:
        return None
    j = rnd.randrange(2, len(p) - 2)
    palavras[i] = p[:j] + p[j + 1:]
    return " ".join(palavras)


def casos_do_banco(indice, rnd: random.Random) -> list[dict]:
    por_coluna: dict[tuple[str, str], list[str]] = {}
    for view, coluna, valor in zip(indice.views, indice.colunas, indice.valores):
        por_coluna.setdefault((view, coluna), []).append(valor)
    casos = []
    for (view, coluna), valores in sorted(por_coluna.items()):
        for valor in rnd.sample(valores, min(POR_COLUNA, len(valores))):
            if "_" in valor and valor.upper() == valor:
                casos.append({"tipo": "código", "termo": valor.replace("_", " ").lower(), "coluna": coluna, "valor": valor})
            palavras = valor.split()
            if len(palavras) >= 6:
                k = rnd.randrange(1, len(palavras) - 3)
                casos.append({"tipo": "pedaço", "termo": " ".join(palavras[k:k + 3]), "coluna": coluna, "valor": valor})
            elif len(palavras) <= 4:
                termo = _typo(valor, rnd)
                if termo:
                    casos.append({"tipo": "digitação", "termo": termo, "coluna": coluna, "valor": valor})
    return casos


def medir(banco: Path, contexto: Path, chave: str, casos_extra: list[dict]) -> dict:
    os.environ["ADITO_EMBEDDING_MODELO"] = chave
    sys.path.insert(0, str(NUCLEO))
    sys.path.insert(0, str(AQUI))
    import numpy as np
    from analytics_index.modelo_local import EmbedderLocal
    from analytics_index.valores import carregar_indice, normalizar_texto
    from gerar_embeddings_dados import gerar

    with tempfile.TemporaryDirectory() as tmp:
        copia = Path(tmp) / "dados.db"
        shutil.copy2(banco, copia)
        embedder = EmbedderLocal()
        inicio = time.monotonic()
        embedder.embed_query("aquecimento")
        carga = time.monotonic() - inicio
        inicio = time.monotonic()
        resumo = gerar(copia, contexto, embedder, log=lambda *_: None)
        geracao = time.monotonic() - inicio
        tamanho_vetores = copia.stat().st_size - banco.stat().st_size
        indice = carregar_indice(copia)
    if not indice.disponivel:
        raise SystemExit(f"índice indisponível: {indice.motivo}")

    casos = casos_do_banco(indice, random.Random(42)) + [{"tipo": "manual", **c} for c in casos_extra]
    termos = [c["termo"] for c in casos] + NEGATIVOS
    inicio = time.monotonic()
    consultas = embedder.matriz(termos, pergunta=True)
    por_consulta_ms = (time.monotonic() - inicio) / len(termos) * 1000
    achados = indice.buscar(consultas, -1.0, 3)

    linhas = []
    for caso, hits in zip(casos, achados):
        certo = [i for i, h in enumerate(hits)
                 if h["coluna"] == caso["coluna"] and normalizar_texto(h["valor"]) == normalizar_texto(caso["valor"])]
        linhas.append({**caso, "pos": certo[0] if certo else None,
                       "sim_top": hits[0]["similaridade"] if hits else 0.0,
                       "top": hits[0]["valor"] if hits else None})
    sims_neg = [h[0]["similaridade"] if h else 0.0 for h in achados[len(casos):]]

    def taxa(pred) -> float:
        return round(sum(1 for x in linhas if pred(x)) / max(1, len(linhas)), 3)

    por_tipo = {}
    for tipo in sorted({c["tipo"] for c in casos}):
        sub = [x for x in linhas if x["tipo"] == tipo]
        por_tipo[tipo] = {"casos": len(sub),
                          "top1": round(sum(x["pos"] == 0 for x in sub) / len(sub), 3),
                          "top3": round(sum(x["pos"] is not None for x in sub) / len(sub), 3)}
    limites = {
        f"{t:.2f}": {
            "acerto_top1": taxa(lambda x, t=t: x["pos"] == 0 and x["sim_top"] >= t),
            "valor_errado": taxa(lambda x, t=t: x["pos"] != 0 and x["sim_top"] >= t),
            "falso_positivo_negativos": round(float(np.mean([s >= t for s in sims_neg])), 3),
        }
        for t in LIMITES
    }
    return {
        "modelo": chave,
        "valores": len(indice),
        "carga_s": round(carga, 1),
        "geracao_s": round(geracao, 1),
        "vetores_mb": round(tamanho_vetores / 1_048_576, 1),
        "ms_por_consulta": round(por_consulta_ms, 1),
        "memoria_pico_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024),
        "top1": taxa(lambda x: x["pos"] == 0),
        "top3": taxa(lambda x: x["pos"] is not None),
        "por_tipo": por_tipo,
        "negativos_sim_max": round(max(sims_neg), 3),
        "limites": limites,
        "erros": [x for x in linhas if x["pos"] != 0][:15],
        "total_vetores": resumo["meta"]["total"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("banco", type=Path, help="dados.db (não é alterado; o script usa uma cópia)")
    parser.add_argument("--modelos", nargs="+", default=None, help="chaves dos modelos (padrão: todos)")
    parser.add_argument("--contexto", type=Path, default=CONTEXTO_PADRAO)
    parser.add_argument("--casos", type=Path, help="JSON com casos escritos à mão")
    parser.add_argument("--saida", type=Path, help="grava o resultado completo em JSON")
    parser.add_argument("--um", help=argparse.SUPPRESS)  # processo filho: mede um modelo só
    args = parser.parse_args()
    extra = json.loads(args.casos.read_text(encoding="utf-8")) if args.casos else []

    if args.um:
        print(json.dumps(medir(args.banco, args.contexto, args.um, extra), ensure_ascii=False))
        return 0

    sys.path.insert(0, str(NUCLEO))
    from analytics_index.modelo_local import MODELOS

    resultados = []
    for chave in args.modelos or list(MODELOS):
        print(f"→ {chave}…", flush=True)
        cmd = [sys.executable, __file__, str(args.banco), "--contexto", str(args.contexto), "--um", chave]
        if args.casos:
            cmd += ["--casos", str(args.casos)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"  falhou: {proc.stderr.strip()[-400:]}")
            continue
        r = json.loads(proc.stdout.strip().splitlines()[-1])
        resultados.append(r)
        print(f"  {r['valores']} valores | top1 {r['top1']:.0%} top3 {r['top3']:.0%} | carga {r['carga_s']}s, "
              f"geração {r['geracao_s']}s, {r['ms_por_consulta']} ms/consulta, pico {r['memoria_pico_mb']} MB, "
              f"vetores {r['vetores_mb']} MB")
        for tipo, t in r["por_tipo"].items():
            print(f"    {tipo:<10} {t['casos']:>4} casos  top1 {t['top1']:.0%}  top3 {t['top3']:.0%}")
        print(f"    maior similaridade de um negativo: {r['negativos_sim_max']}")
        for limite, t in r["limites"].items():
            print(f"    limite {limite}: acerta {t['acerto_top1']:.0%}, valor errado {t['valor_errado']:.0%}, "
                  f"negativos aceitos {t['falso_positivo_negativos']:.0%}")
    if args.saida:
        args.saida.write_text(json.dumps(resultados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"✓ resultado em {args.saida}")
    return 0 if resultados else 1


if __name__ == "__main__":
    raise SystemExit(main())
