# Task Breakdown: [US-QA-02] Testes E2E Híbridos de Frontend com Playwright (Mock IPC + Live Bridge)

**Data:** 19/11/2026  
**Estimativa total:** 5 Story Points  
**Nivel ScrumAIDev:** 1  
**Spec governada:** N/A (dispensa: suíte E2E de interface sem mudança de comportamento de produto)  
**Contract governado:** N/A  
**Behavior change:** NO  
**GitHub Parent US Issue:** [#71](https://github.com/SmartIdea-ifes-serra/Adito/issues/71)

---

## Pre-Flight de Governanca
- **US exige Spec/Contract?** Não (Nível 1, automação de testes E2E).
- **Nova dependência aprovada (Regra 6):** `@playwright/test` (aprovada pelo usuário no Gate G1).
- **Touch List:**
  - `Adito/app/frontend-vue/package.json`
  - `Adito/app/frontend-vue/playwright.config.ts`
  - `Adito/app/frontend-vue/tests/e2e/**`
  - `Adito/app/scripts/e2e_bridge.py`
  - `Makefile`

---

## Tasks Tecnicas

### [TASK-QA-02.1] Configurar `@playwright/test` e helper de stub `__TAURI_INTERNALS__`
- Instalar `@playwright/test` em `Adito/app/frontend-vue/`.
- Criar `playwright.config.ts` iniciando Vite (`webServer`) e suportando modo padrão (`mock`) e modo `live` (`E2E_MODE=live`).
- Criar `tests/e2e/helpers/tauriMock.ts` emulando fielmente `window.__TAURI_INTERNALS__` (`invoke`, `transformCallback`, `unregisterCallback`, protocolo de `Channel` com `{ index, message }`) via `page.addInitScript()`, com fixtures realistas do IFES (zero PII).

### [TASK-QA-02.2] Specs E2E determinísticas (Mock IPC — `make test-e2e`)
- `tests/e2e/navigation.spec.ts`: rotas principais (`/chat`, `/dashboard`, `/meu-dashboard`, `/explorar`, `/admin`, `/configuracoes`) e alternância de tema.
- `tests/e2e/dashboard.spec.ts`: KPIs acadêmicos ("Investimento estimado", "Projetos", "Orientadores"), tabela Top 10 projetos e aplicação de filtros.
- `tests/e2e/explorer.spec.ts`: listagem das views fato, troca de tabela, busca textual e paginação.
- `tests/e2e/chat.spec.ts`: envio de pergunta, streaming de status/resposta, renderização de tabela, histórico lateral e tratamento de erro 503 (sem chave LLM).
- `tests/e2e/settings-admin.spec.ts`: tela de Configurações (chave API) e tela de Administração (status do sistema).

### [TASK-QA-02.3] Bridge local Live (`e2e_bridge.py`) e spec integrada (`make test-e2e-live`)
- Criar `Adito/app/scripts/e2e_bridge.py` (stdlib `http.server` + subprocess `desktop_server.py` sobre `Adito/app/data/dados.db` isolado).
- Criar `tests/e2e/live-core.spec.ts` validando em Chromium leitura real de Dashboard, Explorar Dados e Contextos vindos do `dados.db`.

### [TASK-QA-02.4] Integrar `make test-e2e` e `make test-e2e-live` no Makefile e validar
- Adicionar scripts `test:e2e` e `test:e2e:live` em `package.json` e alvos `make test-e2e` / `make test-e2e-live` no `Makefile`.
- Executar ambas as suítes e validar 100% de aprovação.
