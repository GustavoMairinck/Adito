"""Extrator do SigPesq (US-ETL-03).

    download   — baixa os relatórios XLSX pela `sigpesq-agent`          <- horizon_etl adapters/sources/sigpesq/adapter.py
    converter  — XLSX -> JSON só com as colunas permitidas, XLSX apagado
    colunas    — listas de colunas permitidas por relatório (BR01)

Origem: horizon_etl (github.com/ifesserra-lab/horizon_etl), sem Infisical,
banco, Prefect ou loaders.
"""
