# User Story: [US-EMB-03] Valores da pergunta achados sem LLM, sinônimos do contexto e pergunta original até o SQL

**Epic:** EPIC-16 — Embeddings locais no `dados.db` e respostas mais estáveis
**GitHub Epic Issue:** -
**GitHub US Issue:** -
**Prioridade:** 🔴 Alta (slice 2)
**Story Points:** 5
**Sprint:** - (implementação direta na branch `feat/embeddings-locais`, no fork)
**Status:** Em teste no fork
**Behavior Change Esperado:** YES

---

## Historia

**Como** usuário do chat do Adito
**Eu quero** que o Adito ache os valores reais do banco citados na minha pergunta sempre do mesmo jeito, e que o SQL siga o que eu perguntei
**Para que** que a mesma pergunta não dê respostas muito diferentes nem ganhe filtros que eu não pedi

### Contexto Adicional

O resolvedor ReAct decidia sozinho se e o que buscar, e o rewriter reescrevia a pergunta. Os dois somavam chamadas de LLM e variação. O orquestrador também reescreve a pergunta como instrução.

Origem: análise de 27/11/2026 (`/mnt/project-files/embeddings/analise-fluxo-resposta-embeddings.md`) e [ADR-0009](../../../Docs/ADR/ADR-0009-embeddings-locais-no-dados-db.md).

### Pontos de Esclarecimento

- Modelo final e limite de similaridade dependem da comparação no `dados.db` real.

---

## Criterios de Aceitacao

- [x] **Criterio 1 (Resolvedor determinístico):** `value_resolver` quebra a pergunta em trechos de 1 a 4 palavras e tenta, em ordem, `sinonimos.json`, valor idêntico do catálogo e similaridade no índice local (limite `ADITO_VALOR_SIMILARIDADE_MIN`). Trechos sobrepostos ficam com o de maior similaridade.
- [x] **Criterio 2 (Sinônimos do contexto):** `contexts/pesquisa-extensao-ifes/sinonimos.json` tem só o que o `rules.md` afirma. Termos com palavra vazia na ponta ("pibic em") também casam. A lista de sugestões para a equipe validar fica fora do arquivo.
- [x] **Criterio 3 (Bloco à parte no prompt):** os valores vão num bloco "REAL VALUES FOUND IN THE DATABASE", com aspas escapadas, e a pergunta não é reescrita.
- [x] **Criterio 4 (Pergunta original até o gerador):** o orquestrador passa `pergunta_original` para a ferramenta do BI. Quando ela diverge da instrução, o gerador e o corretor recebem as duas, com a ordem de seguir a do usuário e não acrescentar filtros.
- [x] **Criterio 5 (Grafo mais curto):** extractor → value_resolver → generator → validator ↔ corrector → formatter.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Mudança interna do núcleo (e do painel admin), coberta por testes unitários sem rede nem LLM.
- **US exige Spec governada?** Nao
- **Justificativa da Spec:** A decisão de arquitetura está no ADR-0009.
- **Spec prevista:** N/A
- **US exige Contract governado?** Nao
- **Justificativa do Contract:** Só RPCs internos entre o front e o núcleo.
- **Contract previsto:** N/A
- **Padrao de erro aplicavel:** N/A
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** N/A
- **Depende de:** US-EMB-01
- **Touch List preliminar:**
  - `Adito/app/backend/nucleo/agents/bi_agent/nodes/value_resolver.py`
  - `Adito/app/backend/nucleo/agents/bi_agent/graph.py`
  - `Adito/app/backend/nucleo/agents/bi_agent/state.py`
  - `Adito/app/backend/nucleo/agents/bi_agent/nodes/sql_generator.py`
  - `Adito/app/backend/nucleo/agents/bi_agent/tool.py`
  - `Adito/app/backend/nucleo/agents/orchestrator/graph.py`
  - `Adito/app/contexts/pesquisa-extensao-ifes/sinonimos.json`

---

## Tasks

- [x] **[TASK-001]** Criar `nodes/value_resolver.py` e remover `semantic_value_resolver.py`, `question_rewriter.py` e `tools/vector_search.py`.
- [x] **[TASK-002]** Levar `pergunta_original` de `orchestrator/graph.py` até `sql_generator.py` e `sql_corrector.py`.
- [x] **[TASK-003]** Criar `sinonimos.json` e a lista de sugestões (`/mnt/project-files/embeddings/sugestoes-sinonimos.md`).
- [x] **[TASK-004]** Testes do resolvedor, dos sinônimos e da pergunta original.

---

## Definition of Done Checklist

- [x] Codigo implementado conforme criterios de aceitacao
- [x] Decisao sobre Spec governada foi registrada
- [x] Decisao sobre Contract governado foi registrada
- [x] Nivel ScrumAIDev foi registrado
- [x] Gates opcionais executados ou dispensados com justificativa
- [ ] Code review aprovado
- [x] Testes unitarios com cobertura adequada
- [x] Documentacao atualizada
- [ ] Teste conjunto no fork (Gustavo)
- [ ] `Behavior change` documentado no PR
- [ ] Aprovacao do Product Owner
