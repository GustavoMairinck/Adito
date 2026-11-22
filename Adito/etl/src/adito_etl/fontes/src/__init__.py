"""Extrator do SRC/Ifes (ações de extensão).

Copiado do SRCEtl (github.com/ifesserra-lab/src, commit d66fc746), só a parte
de extração:

    scraper     — consulta pública de ações (Playwright)        <- src_etl/etl/scraper.py
    detalhe     — página de detalhe da ação (httpx)               <- src_etl/etl/detail.py
    vinculadas  — ação-mãe -> ações filhas (fonte oficial)        <- src_etl/etl/vinculadas.py
    models      — schemas pydantic                                <- src_etl/etl/models.py
    acoes       — orquestra a parte pública (US-ETL-01)           <- src_etl/etl/pipeline.py
    participacoes — área autenticada, sem CPF/e-mail (US-ETL-02)  <- src_etl/etl/gerenciar.py
"""
