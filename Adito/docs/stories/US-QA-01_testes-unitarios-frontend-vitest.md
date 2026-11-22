# User Story: [US-QA-01] Testes Unitários de Frontend Vue (Vitest + Vue Test Utils)

**Epic:** EPIC-10 — Garantia de Qualidade: Testes Automatizados, Performance e Avaliação da IA  
**GitHub Epic Issue:** [#71](https://github.com/SmartIdea-ifes-serra/Adito/issues/71)  
**GitHub US Issue:** [#71](https://github.com/SmartIdea-ifes-serra/Adito/issues/71)  
**Prioridade:** Alta (Slice 1)  
**Story Points:** 3  
**Sprint:** Backlog  
**Status:** Done  
**Behavior Change Esperado:** NO (infraestrutura de testes unitários de frontend; não altera lógica de negócio em produção)

---

## Historia

**Como** desenvolvedor do projeto Adito,  
**Eu quero** executar testes unitários rápidos sobre os composables, utilitários e camada de cliente IPC do frontend Vue 3 via Vitest,  
**Para que** regressões de estado, tratamento de erro, histórico de chat e formatação sejam detectadas em segundos no fluxo diário (`make test`), totalmente offline.

### Contexto Adicional
O frontend em `Adito/app/frontend-vue` (Vue 3.5, Vite 8, TypeScript 5.9) não possui nenhuma suíte de testes unitários. Módulos críticos como `src/common/api/core.ts` (protocolo RPC/Channel sobre Tauri IPC), `src/common/api/llmKey.ts`, `src/modules/chat/composables/useChatHistory.ts`, `src/modules/dashboard/composables/useDashboardData.ts` e `src/modules/chat/utils/markdown.ts` concentram lógica de estado e parsing que deve ser protegida por testes unitários determinísticos.

### Pontos de Esclarecimento
Nenhum ponto pendente (dependências `vitest`, `@vue/test-utils` e `happy-dom` aprovadas no Gate G1).

---

## Criterios de Aceitacao

- [x] **CA01 (Setup Vitest):** `vitest`, `@vue/test-utils` e `happy-dom` configurados em `Adito/app/frontend-vue/package.json` e `vitest.config.ts` com alias `@` resolvendo para `src/` e script `npm run test:unit`.
- [x] **CA02 (Camada IPC & Chave LLM):** Testes unitários cobrindo `src/common/api/core.ts` (`call`, `stream`, `$end`, `CoreError`, cancelamento via `AbortSignal`) e `src/common/api/llmKey.ts` (`keyStatus`, `testAndSaveKey`, `clearKey`), mockando apenas `@tauri-apps/api/core`.
- [x] **CA03 (Composables & Utilitários):** Testes unitários cobrindo `useChatHistory.ts`, `useDashboardData.ts`, `useContextos.ts`, `useToast.ts` e `markdown.ts`, validando fluxos principais, edge cases e ausência de PII nas fixtures.
- [x] **CA04 (Performance e Determinismo):** A suíte `make test-front` executa 100% offline em menos de 10 segundos e retorna código de saída `0` quando todos os testes passam.
- [x] **CA05 (Integração no Makefile):** Alvo `make test-front` adicionado ao `Makefile` raiz (com caminhos entre aspas duplas) e integrado ao alvo `make test` padrão sem exigir Chromium nem API Gemini.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Menor nível suficiente; entrega de infraestrutura de testes unitários locais sem alteração de contratos ou boundaries de produção.
- **US exige Spec governada?** Não
- **Justificativa da Spec:** Ferramental de qualidade local; comportamento de produto não muda.
- **Spec prevista:** N/A
- **US exige Contract governado?** Não
- **Justificativa do Contract:** Não cria nem altera contratos de API.
- **Contract previsto:** N/A
- **Padrao de erro aplicavel:** N/A
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** N/A
- **Requisitos rastreados:** `FR01`, `FR11`, `BR03`, `BR04`, `BR06`, `NFR01`, `NFR02`, `NFR03`
- **Touch List preliminar:**
  - `Adito/app/frontend-vue/package.json`
  - `Adito/app/frontend-vue/vitest.config.ts`
  - `Adito/app/frontend-vue/tests/unit/**`
  - `Makefile`
- **Task Issues previstas:** N/A

---

## Notas Tecnicas

### Arquitetura
- **Componentes afetados:** Novo diretório `Adito/app/frontend-vue/tests/unit/`.
- **APIs necessarias:** Mock de `@tauri-apps/api/core` via `vi.mock`.
- **Database changes:** Nenhuma.
- **Referencias do modelo de dados:** N/A.
- **Erros observaveis esperados:** `CoreError` (400, 404, 499 `CanceledError`, 503).

### Dependencias
- [x] Aprovação das `devDependencies`: `vitest`, `@vue/test-utils`, `happy-dom` (aprovadas no Gate G1).

### Consideracoes de Performance
- Execução completa da suíte unitária deve permanecer abaixo de 10s (`NFR01`).

---

## Plano de Testes

### Testes Unitarios
- [x] `core.spec.ts` — `call`, `stream`, tratamento de erros e `AbortSignal`.
- [x] `llmKey.spec.ts` — fluxo de validação, salvamento e limpeza da chave Gemini.
- [x] `useChatHistory.spec.ts` — criação, persistência em `localStorage`, alternância e remoção de conversas.
- [x] `useDashboardData.spec.ts` — carregamento de KPIs/gráficos, filtros e estado de erro.
- [x] `useContextos.spec.ts` e `useToast.spec.ts` — seleção de contexto e fila de notificações.
- [x] `markdown.spec.ts` — renderização e sanitização de Markdown.
- [x] `FilterBar.spec.ts` e `KPICard.spec.ts` — montagem de componentes Vue reais (`@vue/test-utils`).

### Testes Manuais
- [x] Executar `make test-front` e `make test` da raiz do repositório e validar código de saída `0` e tempo < 10s.
