# Task Breakdown: [US-QA-01] Testes Unitários de Frontend Vue (Vitest + Vue Test Utils)

**Data:** 19/11/2026  
**Estimativa total:** 3 Story Points  
**Nivel ScrumAIDev:** 1  
**Spec governada:** N/A (dispensa: ferramental local de testes sem mudança de comportamento de produto)  
**Contract governado:** N/A  
**Behavior change:** NO  
**GitHub Parent US Issue:** [#71](https://github.com/SmartIdea-ifes-serra/Adito/issues/71)

---

## Pre-Flight de Governanca
- **US exige Spec/Contract?** Não (Nível 1, tooling de qualidade local).
- **Novas dependências aprovadas (Regra 6):** `vitest`, `@vue/test-utils`, `happy-dom` (aprovadas pelo usuário no Gate G1).
- **Touch List:**
  - `Adito/app/frontend-vue/package.json`
  - `Adito/app/frontend-vue/vitest.config.ts`
  - `Adito/app/frontend-vue/tests/unit/**`
  - `Makefile`

---

## Tasks Tecnicas

### [TASK-QA-01.1] Configurar Vitest + Vue Test Utils + happy-dom
- Instalar `vitest`, `@vue/test-utils` e `happy-dom` como `devDependencies` em `Adito/app/frontend-vue/`.
- Criar `Adito/app/frontend-vue/vitest.config.ts` com alias `@` -> `src/`, ambiente `happy-dom` e `include: ['tests/unit/**/*.spec.ts']`.
- Adicionar script `test:unit` em `package.json`.

### [TASK-QA-01.2] Testes unitários da camada IPC (`core.ts` e `llmKey.ts`)
- Criar `tests/unit/core.spec.ts` cobrindo `coreReady`, `call`, `CoreError`, cancelamento via `AbortSignal` (`CanceledError` + `core_cancel`), `stream` com `Channel`, eventos intermediários e `$end` (sucesso e erro).
- Criar `tests/unit/llmKey.spec.ts` cobrindo `keyStatus`, `testAndSaveKey` (chave válida, inválida, erro 400 com corpo `{ok, reason}`) e `clearKey`.

### [TASK-QA-01.3] Testes unitários de composables e utilitários
- Criar `tests/unit/markdown.spec.ts` (escape XSS, headings, listas `ul`/`ol`, `hr`, bold/italic/code inline).
- Criar `tests/unit/useChatApi.spec.ts` (`buildChart`, `isScalarResultData`, `checkHealth`, `askQuestionStream`).
- Criar `tests/unit/useChatHistory.spec.ts` (conversa inicial, limpeza de storage legado, `syncFromBackend`, `loadRows` sucesso/erro, `createConversation`).
- Criar `tests/unit/useDashboardData.spec.ts` (`fetchData`, filtros em `sessionStorage`, `toggleFilter`, cancelamento de requisições anteriores).
- Criar `tests/unit/useContextos.spec.ts` e `tests/unit/useToast.spec.ts`.

### [TASK-QA-01.4] Integrar `make test-front` no Makefile e validar
- Adicionar `test-front` ao `Makefile` raiz (com aspas nos caminhos) e incluí-lo no alvo `make test`.
- Executar `make test-front` e `make test`, confirmando tempo < 10s e 100% de aprovação.
