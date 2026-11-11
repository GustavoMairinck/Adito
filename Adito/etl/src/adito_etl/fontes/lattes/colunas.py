"""O que fica do currículo Lattes no bruto (BR01, revisto pelo usuário em 2026-11-11).

Levantado dos 126 JSON que o `scriptLattes` gerou no horizon_etl (`data/lattes_json`).

- Seções do currículo: todas as de produção e atuação acadêmica ficam
  (são públicas no Lattes). Seção nova que aparecer é descartada e avisada.
- `informacoes_pessoais`: ficam id, nome, nomes de citação, rótulo, período,
  bolsa de produtividade, data de atualização, URL, resumo e endereço
  profissional. `sexo` sai: o usuário aprovou trazê-lo, mas o Lattes público não
  mostra mais o sexo e o scriptLattes preenche "Masculino" por padrão
  (`parserLattes.py`), então o valor é falso para todos (conferido em 2026-11-11). Do endereço profissional saem telefone, fax e ramal
  (`converter.sem_contato`); e-mails são mascarados como em todo texto.
- Todos os textos passam por `pii.sanitizar` (o resumo às vezes traz e-mail).
"""

from __future__ import annotations

SECOES = frozenset({
    "informacoes_pessoais", "formacao_academica", "atuacao_profissional",
    "projetos_pesquisa", "projetos_extensao", "projetos_desenvolvimento",
    "areas_de_atuacao", "idiomas", "premios_titulos", "linhas_de_pesquisa",
    "producao_bibliografica", "producao_tecnica", "patentes_registros",
    "producao_artistica", "orientacoes", "eventos", "bancas", "estatisticas",
})

# Campos conhecidos que saem sem aviso.
DESCARTADOS_CONHECIDOS = frozenset({"sexo"})

INFORMACOES_PESSOAIS = frozenset({
    "id_lattes", "nome_completo", "nome_citacoes", "rotulo", "periodo",
    "bolsa_produtividade", "atualizacao_cv", "url", "texto_resumo", "endereco_profissional",
})
