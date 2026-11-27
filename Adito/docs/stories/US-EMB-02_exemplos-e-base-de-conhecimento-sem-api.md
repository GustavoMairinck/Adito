# User Story: [US-EMB-02] Exemplos e Base de conhecimento sem embeddings por API

**Epic:** EPIC-16 — Embeddings locais no `dados.db` e respostas mais estáveis
**GitHub Epic Issue:** -
**GitHub US Issue:** -
**Prioridade:** 🔴 Alta (slice 1)
**Story Points:** 3
**Sprint:** - (implementação direta na branch `feat/embeddings-locais`, no fork)
**Status:** Em teste no fork
**Behavior Change Esperado:** YES

---

## Historia

**Como** usuário do chat do Adito
**Eu quero** que os exemplos SQL mais parecidos com a minha pergunta sejam escolhidos na minha máquina
**Para que** que a escolha não gaste a cota do provedor de IA nem dependa de qual provedor estou usando

### Contexto Adicional

O extractor buscava DDL, regras e exemplos por similaridade, mas o `system_prompt` já levava DDL e regras inteiros. A configuração de embedding por provedor deixa de existir.

Origem: análise de 27/11/2026 (`/mnt/project-files/embeddings/analise-fluxo-resposta-embeddings.md`) e [ADR-0009](../../../Docs/ADR/ADR-0009-embeddings-locais-no-dados-db.md).

### Pontos de Esclarecimento

Nenhum ponto pendente.

---

## Criterios de Aceitacao

- [x] **Criterio 1 (Só exemplos passam por busca):** o extractor embeda a pergunta de cada exemplo do `examples.json` e dos itens manuais com o modelo local (cache em memória) e escolhe de 2 a 4 pela margem relativa ao melhor.
- [x] **Criterio 2 (Manuais entram inteiros):** esquema e regras postos à mão no painel entram como texto (cortados), sem busca.
- [x] **Criterio 3 (Sem modelo, sem travar):** se o modelo ainda não estiver pronto, entram os 8 primeiros exemplos.
- [x] **Criterio 4 (Base de conhecimento sem chave):** `admin.bootstrap`, criar treinamento e Wipe & Retrain funcionam sem chave de IA.
- [x] **Criterio 5 (Sai o código de API):** saem o embedder por API, a sincronização de `analytics_text_embedding`, o diagnóstico de dimensão divergente e os campos de embedding do catálogo de provedores e da tela de Configurações.
- [x] **Criterio 6 (Painel mostra a busca local):** `admin.system_status.embeddings` traz modelo, se está pronto, se os vetores do `dados.db` estão disponíveis e o motivo, e o painel avisa quando a busca semântica está desligada.

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
  - `Adito/app/backend/nucleo/agents/bi_agent/nodes/query_extractor.py`
  - `Adito/app/backend/nucleo/core/contexts.py`
  - `Adito/app/backend/nucleo/rpc/admin.py`
  - `Adito/app/backend/nucleo/agents/providers.py`
  - `Adito/app/frontend-vue/src/modules/admin/views/AdminView.vue`
  - `Adito/app/frontend-vue/src/modules/settings/views/ConfiguracoesView.vue`

---

## Tasks

- [x] **[TASK-001]** Reescrever `query_extractor.py`.
- [x] **[TASK-002]** Refazer `index_contexto` e os RPCs de treinamento sem embeddings.
- [x] **[TASK-003]** Remover `analytics_index/services.py`, `embedder.py`, `config.py` e `core/vectors.py`.
- [x] **[TASK-004]** Ajustar `AdminView.vue`, `ConfiguracoesView.vue`, `llmKey.ts` e os testes unitários e e2e.

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
