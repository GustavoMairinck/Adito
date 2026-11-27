# User Story: [US-EMB-05] Comparar modelos de embedding e calibrar os limites de similaridade sem LLM

**Epic:** EPIC-16 — Embeddings locais no `dados.db` e respostas mais estáveis
**GitHub Epic Issue:** -
**GitHub US Issue:** -
**Prioridade:** 🟠 Alta (slice 3)
**Story Points:** 2
**Sprint:** - (implementação direta na branch `feat/embeddings-locais`, no fork)
**Status:** Em andamento
**Behavior Change Esperado:** YES

---

## Historia

**Como** equipe do Adito
**Eu quero** comparar os modelos candidatos no `dados.db` real e calibrar o limite de similaridade com números
**Para que** escolher o modelo e o limite sem achismo e sem gastar tokens de IA

### Contexto Adicional

O modelo padrão (`minilm-l12-int8`) e o limite de 0,80 são provisórios, marcados com `shortcut:` no código.

Origem: análise de 27/11/2026 (`/mnt/project-files/embeddings/analise-fluxo-resposta-embeddings.md`) e [ADR-0009](../../../Docs/ADR/ADR-0009-embeddings-locais-no-dados-db.md).

### Pontos de Esclarecimento

- Modelo final e limite de similaridade dependem da comparação no `dados.db` real.

---

## Criterios de Aceitacao

- [x] **Criterio 1 (Script sem LLM):** `scripts/teste_busca_valores.py` gera os vetores numa cópia do banco para cada modelo (um processo por modelo) e mede acerto top 1 e top 3, falsos positivos por limite, tempo de carga e de geração, ms por consulta, memória de pico e tamanho dos vetores.
- [x] **Criterio 2 (Casos reproduzíveis):** os casos saem do próprio banco com semente fixa (erro de digitação, código escrito como texto, pedaço de título), mais termos negativos e casos manuais por `--casos`.
- [ ] **Criterio 3 (Decisão registrada):** o modelo escolhido e o limite entram em `MODELO_PADRAO` e `SIMILARIDADE_MINIMA`, e o ADR-0009 passa a Aceito.

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
- **Depende de:** US-EMB-01, US-EMB-03
- **Touch List preliminar:**
  - `Adito/scripts/teste_busca_valores.py`
  - `Adito/app/backend/nucleo/analytics_index/modelo_local.py`
  - `Adito/app/backend/nucleo/agents/bi_agent/nodes/value_resolver.py`

---

## Tasks

- [x] **[TASK-001]** Criar `teste_busca_valores.py`.
- [ ] **[TASK-002]** Rodar no `dados.db` real com `minilm-l12-int8`, `e5-small-int8` e `e5-large-int8`.
- [ ] **[TASK-003]** Escolher o modelo e o limite com o Gustavo e atualizar o código e o ADR.

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
