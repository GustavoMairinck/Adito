#!/usr/bin/env python3
"""Roda a carga do Horizon (PostgreSQL) com os dados mock, sem acesso à internet.

Chama ``executar_carga`` — o mesmo núcleo do flow
``src.flows.pipelines.horizon_postgres --sem-download`` — apontando as pastas do
SigPesq, Lattes e PJ para ``dados/`` e trocando o crawler do CNPq pela leitura
dos espelhos mock. O schema informado é apagado e recriado a cada execução.

Uso:
    export HORIZON_DATABASE_URL=postgresql://horizon:horizon@localhost:5434/horizon
    python executar_etl_mock.py --etl ../Adito/Etls/Horizon/Etl --schema mock_validacao
    python executar_etl_mock.py --etl ... --schema mock_completa --com-sonda
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import time
import traceback

AQUI = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    padrao_etl = os.path.dirname(AQUI) if os.path.isdir(os.path.join(os.path.dirname(AQUI), "src", "core")) else None
    ap.add_argument("--etl", default=padrao_etl, required=padrao_etl is None,
                    help="pasta Etls/Horizon/Etl do Adito (padrão: a pasta acima deste kit)")
    ap.add_argument("--dados", default=os.path.join(AQUI, "dados"))
    ap.add_argument("--schema", default="mock_validacao")
    ap.add_argument("--resultados", default=os.path.join(AQUI, "resultados"))
    ap.add_argument("--com-sonda", action="store_true",
                    help="inclui o currículo-sonda (ano numérico), que interrompe a carga do Lattes")
    args = ap.parse_args()

    etl = os.path.abspath(args.etl)
    dados = os.path.abspath(args.dados)
    os.environ["HORIZON_MOCK_CNPQ"] = os.path.join(dados, "cnpq_espelhos")
    os.environ.setdefault("HORIZON_MODELO_SQL", os.path.join(os.path.dirname(etl), "ModeloLogicoHorizon.sql"))
    sys.path.insert(0, os.path.join(AQUI, "fake_cnpq"))
    sys.path.insert(0, etl)
    os.chdir(etl)

    from loguru import logger

    os.makedirs(args.resultados, exist_ok=True)
    nome = "completa_com_sonda" if args.com_sonda else "principal"
    log_path = os.path.join(args.resultados, f"log_etl_{nome}.txt")
    logger.remove()
    logger.add(log_path, level="INFO", mode="w")
    logger.add(sys.stderr, level="ERROR")

    import psycopg
    from src.adapters.sources.cnpq_crawler import CnpqCrawlerAdapter
    from src.core.logic.carga.pipeline import ConfiguracaoCarga, executar_carga
    from src.core.logic.carga.relatorio import RelatorioCarga

    with open(os.path.join(dados, "gabarito.json"), encoding="utf-8") as fh:
        sonda = json.load(fh)["sonda"]["arquivo"]

    # O ETL lê as planilhas de bolsistas pela data de modificação; depois de um
    # git clone/unzip essas datas podem empatar. Fixa a ordem 2024 → 2025 → 2026.
    import glob
    agora = time.time()
    bolsistas = sorted(glob.glob(os.path.join(dados, "sigpesq", "advisorships", "*", "*.xlsx")))
    for k, caminho in enumerate(bolsistas):
        os.utime(caminho, (agora - 600 + k * 60, agora - 600 + k * 60))

    pasta_lattes = tempfile.mkdtemp(prefix="lattes_mock_")
    for arquivo in os.listdir(os.path.join(dados, "lattes_json")):
        if arquivo == sonda and not args.com_sonda:
            continue
        shutil.copy(os.path.join(dados, "lattes_json", arquivo), pasta_lattes)

    config = ConfiguracaoCarga(
        pasta_sigpesq=os.path.join(dados, "sigpesq"),
        pasta_lattes=pasta_lattes,
        pasta_pj=os.path.join(dados, "pj"),
        campus=None,
        schema=args.schema,
    )
    relatorio = RelatorioCarga()
    resultado = {"execucao": nome, "schema": args.schema, "com_sonda": args.com_sonda,
                 "arquivos_lattes": len(os.listdir(pasta_lattes))}
    inicio = time.time()
    passos = []
    try:
        with psycopg.connect(os.environ["HORIZON_DATABASE_URL"], autocommit=True) as conexao:
            executar_carga(conexao, relatorio, config, adaptador_cnpq=CnpqCrawlerAdapter(),
                           registrar=lambda m: (passos.append(m), print("  >", m)))
        resultado["status"] = "concluida"
    except Exception as exc:  # a sonda deve cair aqui
        resultado["status"] = "interrompida"
        resultado["erro"] = f"{type(exc).__name__}: {exc}"
        resultado["traceback"] = traceback.format_exc()
        print(f"  ! carga interrompida: {resultado['erro']}")
    finally:
        shutil.rmtree(pasta_lattes, ignore_errors=True)
    resultado["segundos"] = round(time.time() - inicio, 1)
    resultado["passos_registrados"] = passos
    resultado["relatorio_carga"] = relatorio.resumo()
    caminho = os.path.join(args.resultados, f"execucao_{nome}.json")
    with open(caminho, "w", encoding="utf-8") as fh:
        json.dump(resultado, fh, ensure_ascii=False, indent=1, default=str)
    print(f"{nome}: {resultado['status']} em {resultado['segundos']}s — "
          f"{len(relatorio.pendencias)} pendência(s), {len(relatorio.revisoes)} revisão(ões) → {caminho}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
