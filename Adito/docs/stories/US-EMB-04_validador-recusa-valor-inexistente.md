# User Story: [US-EMB-04] Validador recusa filtro com valor que não existe no dados.db

**Epic:** EPIC-16 — Embeddings locais no `dados.db` e respostas mais estáveis
**GitHub Epic Issue:** -
**GitHub US Issue:** -
**Prioridade:** 🟠 Alta (slice 2)
**Story Points:** 2
**Sprint:** - (implementação direta na branch `feat/embeddings-locais`, no fork)
**Status:** Em teste no fork
**Behavior Change Esperado:** YES

---

## Historia

**Como** usuário do chat do Adito
**Eu quero** que um SQL que filtra por um valor inventado seja corrigido antes de rodar
**Para que** não receber "nenhum resultado" por causa de um nome de campus ou programa escrito errado pela LLM

### Contexto Adicional

A LLM às vezes escreve `campus = 'Serra Campus'` ou `programa_fomento = 'PIBIC-EM'`, que não existem no banco.

Origem: análise de 27/11/2026 (`/mnt/project-files/embeddings/analise-fluxo-resposta-embeddings.md`) e [ADR-0009](../../../Docs/ADR/ADR-0009-embeddings-locais-no-dados-db.md).

### Pontos de Esclarecimento

Nenhum ponto pendente.

---

## Criterios de Aceitacao

- [x] **Criterio 1 (Conferência dos literais):** o validador acha comparações `coluna = 'x'`, `IN (...)` e `LIKE` nas colunas que estão no índice e confere contra o catálogo, sem caixa e sem acento. No `LIKE`, o padrão precisa casar com algum valor; em coluna agregada com `; `, cada parte precisa existir.
- [x] **Criterio 2 (Erro com sugestão):** valor que não existe vira erro "Filtro com valor que não existe no banco: ..." com até 3 sugestões parecidas, e o corretor recebe o erro.
- [x] **Criterio 3 (Uma vez só):** a conferência roda só na primeira validação (`correction_attempts == 0`), para não prender o corretor em laço.
- [x] **Criterio 4 (Guarda de nulos pela pergunta do usuário):** a guarda que exige tratar nulos olha `user_input`, não a instrução reescrita.

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
  - `Adito/app/backend/nucleo/agents/bi_agent/nodes/sql_validator.py`
  - `Adito/app/backend/nucleo/core/test_embeddings_locais.py`

---

## Tasks

- [x] **[TASK-001]** Criar `check_valores_inexistentes` em `sql_validator.py`.
- [x] **[TASK-002]** Testes com valor certo, valor inventado e coluna fora do índice.

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
