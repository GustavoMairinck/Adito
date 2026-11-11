"""Linha de comando `adito-etl`.

    adito-etl src-acoes [--campus Serra] [--max N]
    adito-etl src-participacoes [--processo P ...] [--workers N]
    adito-etl sigpesq
    adito-etl sigpesq-converter --de PASTA_COM_XLSX
    adito-etl cnpq [--unidade Serra] [--max N] [--refazer]
    adito-etl lattes [--lista entradas/lattes.csv] [--max N] [--workers N]
    adito-etl lattes-converter --de PASTA_COM_JSON_DO_SCRIPTLATTES
    adito-etl cruzar
    adito-etl verificar-pii

Saída: 0 = ok; 1 = terminou com falhas em unidades (listadas); 2 = erro que
impediu a execução (credencial, login, bruto ausente, dado pessoal encontrado).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .comum import CredencialAusente, Execucao, base_dir, trabalho_dir
from .pii import PIIEncontrada, varrer


def _log(prefixo: str):
    return lambda m: print(f"[{prefixo}] {m}", file=sys.stderr)


def _resumo(exe: Execucao) -> int:
    contagens = ", ".join(f"{k}={v}" for k, v in sorted(exe.contagens.items()))
    print(f"{exe.fonte}/{exe.etapa}: {contagens or 'nada gravado'}")
    for a in exe.avisos:
        print(f"  aviso: {a}")
    if exe.falhas:
        print(f"  {len(exe.falhas)} falha(s):")
        for f in exe.falhas:
            print(f"    - {f['unidade']}: {f['erro']}")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="adito-etl", description="ETL do Adito (extração e cruzamento).")
    sub = ap.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("src-acoes", help="Ações do SRC pela consulta pública (US-ETL-01)")
    p.add_argument("--campus", default="Serra")
    p.add_argument("--max", type=int, default=None, help="Limite de ações (teste)")
    p.add_argument("--no-headless", action="store_true")

    p = sub.add_parser("src-participacoes", help="Público-alvo e equipe do SRC, sem CPF/e-mail (US-ETL-02)")
    p.add_argument("--processo", nargs="+", default=None, help="Processos (padrão: _index.json)")
    p.add_argument("--workers", type=int, default=1, help="Abas na mesma sessão")
    p.add_argument("--no-headless", action="store_true")

    p = sub.add_parser("sigpesq", help="Baixa e converte os relatórios do SigPesq (US-ETL-03)")
    p.add_argument("--no-headless", action="store_true")

    p = sub.add_parser("sigpesq-converter", help="Converte XLSX do SigPesq já baixados (não apaga a origem)")
    p.add_argument("--de", required=True, type=Path, help="Pasta com research_group/, research_projects/, advisorships/")

    p = sub.add_parser("cnpq", help="Espelho DGP/CNPq dos grupos do SigPesq (US-ETL-04)")
    p.add_argument("--unidade", default=None, help="Só grupos desta unidade do SigPesq (ex.: Serra)")
    p.add_argument("--max", type=int, default=None, help="Limite de grupos (teste)")
    p.add_argument("--refazer", action="store_true", help="Baixa de novo grupos já gravados")

    p = sub.add_parser("lattes", help="Currículos Lattes da lista entradas/lattes.csv (US-ETL-05)")
    p.add_argument("--lista", type=Path, default=None, help="CSV nome,lattes_id (padrão: entradas/lattes.csv)")
    p.add_argument("--max", type=int, default=None, help="Limite de currículos (teste)")
    p.add_argument("--workers", type=int, default=3, help="Downloads em paralelo")

    p = sub.add_parser("lattes-converter", help="Converte JSON do scriptLattes já gerados (não apaga a origem)")
    p.add_argument("--de", required=True, type=Path, help="Pasta com os JSON do scriptLattes")

    sub.add_parser("cruzar", help="Liga pessoas entre as fontes pelo nome (US-ETL-06)")
    sub.add_parser("verificar-pii", help="Confere que brutos/ e trabalho/ não têm CPF nem e-mail")

    args = ap.parse_args(argv)
    try:
        if args.comando == "src-acoes":
            from .fontes.src.acoes import extrair_acoes
            return _resumo(extrair_acoes(args.campus, headless=not args.no_headless,
                                         max_acoes=args.max, log=_log("src-acoes")))
        if args.comando == "src-participacoes":
            from .fontes.src.participacoes import extrair_participacoes
            return _resumo(extrair_participacoes(args.processo, headless=not args.no_headless,
                                                 workers=args.workers,
                                                 log=_log("src-participacoes")))
        if args.comando == "sigpesq":
            from .fontes.sigpesq.download import extrair_sigpesq
            return _resumo(extrair_sigpesq(headless=not args.no_headless, log=_log("sigpesq")))
        if args.comando == "sigpesq-converter":
            from .fontes.sigpesq.converter import converter
            return _resumo(converter(args.de))
        if args.comando == "cnpq":
            from .fontes.cnpq.grupos import extrair_cnpq
            return _resumo(extrair_cnpq(unidade=args.unidade, max_grupos=args.max,
                                        refazer=args.refazer, log=_log("cnpq")))
        if args.comando == "lattes":
            from .fontes.lattes.download import extrair_lattes
            return _resumo(extrair_lattes(args.lista, workers=args.workers, max_cv=args.max,
                                          log=_log("lattes")))
        if args.comando == "lattes-converter":
            from .fontes.lattes.converter import converter as converter_lattes
            return _resumo(converter_lattes(args.de))
        if args.comando == "cruzar":
            from .cruzamento.cruzar import cruzar
            rel = cruzar(log=_log("cruzar"))
            print(f"pessoas: {rel['pessoas_total']} | ligadas em 2+ fontes: "
                  f"{rel['ligadas_em_mais_de_uma_fonte']} | por grafia diferente: "
                  f"{rel['ligadas_por_variante']} | ambíguos: {len(rel['ambiguos'])} | "
                  f"nomes não plausíveis: {len(rel['nomes_implausiveis'])}")
            print(f"relatório: {trabalho_dir() / 'relatorio_cruzamento.md'}")
            return 0
        if args.comando == "verificar-pii":
            problemas = varrer(base_dir() / "brutos", trabalho_dir())
            for pr in problemas:
                print(f"PII: {pr}")
            print("ok: nenhum CPF/e-mail encontrado" if not problemas else f"{len(problemas)} arquivo(s) com PII")
            return 2 if problemas else 0
    except (CredencialAusente, FileNotFoundError, PIIEncontrada) as e:
        print(f"erro: {e}", file=sys.stderr)
        return 2
    except RuntimeError as e:  # login recusado, download, biblioteca ausente
        print(f"erro: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
