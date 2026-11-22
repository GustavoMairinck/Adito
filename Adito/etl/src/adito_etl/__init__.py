"""ETL do Adito: extração do bruto por fonte e cruzamento das bases por nome normalizado.

Fases (cada uma é um comando de `adito-etl`):
    extração   — `fontes.src`, `fontes.sigpesq` (CNPq/DGP e Lattes: US-ETL-04/05)
    cruzamento — `cruzamento`

Regra que vale para todas as fases (BR01): nenhum arquivo guarda CPF, e-mail ou
outro dado pessoal além do nome. Toda gravação passa por `pii.auditar`.
"""

__version__ = "0.1.0"
