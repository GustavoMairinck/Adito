# User Story: [US-QA-02] Testes E2E Híbridos de Frontend com Playwright (Mock IPC + Live Bridge)

**Epic:** EPIC-10 — Garantia de Qualidade: Testes Automatizados, Performance e Avaliação da IA  
**GitHub Epic Issue:** [#71](https://github.com/SmartIdea-ifes-serra/Adito/issues/71)  
**GitHub US Issue:** [#71](https://github.com/SmartIdea-ifes-serra/Adito/issues/71)  
**Prioridade:** Alta (Slice 2)  
**Story Points:** 5  
**Sprint:** Backlog  
**Status:** Done  
**Behavior Change Esperado:** NO (automação E2E em navegador Chromium sem alterar lógica de produção)

---

## Historia

**Como** desenvolvedor e revisor do projeto Muninn,  
**Eu quero** executar testes E2E automatizados com Playwright cobrindo as telas e fluxos principais do frontend Vue — tanto em modo determinístico/offline quanto em modo integrado ao núcleo Python real,  
**Para que** regressões de navegação, filtros, renderização de gráficos/tabelas e streaming de chat sejam capturadas antes do merge sem precisar compilar a casca Rust/Tauri.

### Contexto Adicional
O frontend Vue comunica-se exclusivamente com o núcleo Python via IPC do Tauri (`invoke` e `Channel` em `src/common/api/core.ts`), sem servidor HTTP. Para testar a aplicação real no Chromium com Playwright sem inserir código condicional (`if (isTest)`) em produção, o setup de teste injeta um stub de `window.__TAURI_INTERNALS__` via `page.addInitScript()`. No modo padrão (`make test-e2e`), o stub devolve fixtures realistas do domínio IFES; no modo live (`make test-e2e-live`), uma ponte HTTP local encaminha os comandos para o processo real `desktop_server.py` lendo `Muninn/app/data/dados.db`.

### Pontos de Esclarecimento
Nenhum ponto pendente (dependência `@playwright/test` aprovada no Gate G1).

---

## Criterios de Aceitacao

- [x] **CA01 (Setup Playwright & Stub IPC):** `@playwright/test` configurado em `Muninn/app/frontend-vue/playwright.config.ts` com `webServer` iniciando o Vite automaticamente e helper reutilizável injetando `window.__TAURI_INTERNALS__` (`core_ready`, `core_call`, `core_stream`, `core_cancel`, `llm_key_status`, `Channel`) via `addInitScript` — sem alterar código de produção com flags de teste.
- [x] **CA02 (Fluxos E2E Determinísticos — `make test-e2e`):** Specs cobrindo com seletores acessíveis (`getByRole`, `getByLabel`, `getByPlaceholder`, `getByText`):
  - Navegação lateral entre todas as rotas principais;
  - Dashboard (renderização de KPIs acadêmicos, gráficos, top projetos e aplicação de filtros);
  - Explorar Dados (seleção de view, busca, paginação e ordenação);
  - Chat Estratégico (envio de pergunta, streaming de status/resposta, tabela de resultados, histórico lateral e tratamento de erro 503 quando chave LLM não configurada);
  - Meu Dashboard, Admin e Configurações.
- [x] **CA03 (Modo Integrado Live — `make test-e2e-live`):** Ponte HTTP local de teste em Python conectada ao processo real `desktop_server.py` sobre `Muninn/app/data/dados.db`, validando em Chromium fluxos reais de leitura (Dashboard com dados reais, Explorar Dados e Contextos), com mensagem clara caso `dados.db` não exista.
- [x] **CA04 (Rapidez, Offline e Zero PII):** `make test-e2e` executa 100% offline em menos de 45 segundos, sem PII nas fixtures e sem exigir chave Gemini.
- [x] **CA05 (Integração no Makefile):** Alvos `make test-e2e` e `make test-e2e-live` adicionados ao `Makefile` raiz (com caminhos entre aspas duplas e mensagem amigável caso o Chromium do Playwright não esteja instalado).

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Menor nível suficiente; suíte E2E de interface sem mudança de contrato de API ou regra de negócio.
- **US exige Spec governada?** Não
- **Justificativa da Spec:** Automação de testes sobre fluxos já existentes.
- **Spec prevista:** N/A
- **US exige Contract governado?** Não
- **Justificativa do Contract:** Consome o contrato RPC já documentado e validado por `teste_contrato.py`.
- **Contract previsto:** N/A
- **Padrao de erro aplicavel:** N/A
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** N/A
- **Requisitos rastreados:** `FR02`, `FR03`, `FR11`, `BR03`, `BR06`, `NFR01`, `NFR02`, `NFR03`, `A03`, `A04`
- **Touch List preliminar:**
  - `Muninn/app/frontend-vue/package.json`
  - `Muninn/app/frontend-vue/playwright.config.ts`
  - `Muninn/app/frontend-vue/tests/e2e/**`
  - `Muninn/app/scripts/e2e_bridge.py` (bridge local de teste para `test-e2e-live`)
  - `Makefile`
- **Task Issues previstas:** N/A

---

## Notas Tecnicas

### Arquitetura
- **Componentes afetados:** Novo diretório `Muninn/app/frontend-vue/tests/e2e/` e script auxiliar `Muninn/app/scripts/e2e_bridge.py`.
- **APIs necessarias:** Protocolo IPC definido em `src/common/api/core.ts` e `src/common/api/llmKey.ts`.
- **Database changes:** Nenhuma.
- **Referencias do modelo de dados:** 6 views fato no `dados.db` (somente leitura no modo live).
- **Erros observaveis esperados:** 503 (chave não configurada), 404 (tabela indisponível).

### Dependencias
- [x] Aprovação da `devDependency`: `@playwright/test` (aprovada no Gate G1).
- [x] `US-QA-01` concluída (base de testes do frontend organizada).

### Consideracoes de Performance
- `make test-e2e` deve completar em < 45s (`NFR01`).

---

## Plano de Testes

### Testes de Integracao / E2E
- [x] `navigation.spec.ts` — navegação entre rotas e renderização de layout.
- [x] `dashboard.spec.ts` — KPIs, gráficos, filtros reais e limpeza sem `pageerror`.
- [x] `explorer.spec.ts` — troca de view, busca textual e novo schema sem `pageerror`.
- [x] `chat.spec.ts` — envio de pergunta, streaming, tabela, SQL gerado, novo chat, aviso sem chave e erro 503.
- [x] `live-core.spec.ts` — integração real Chromium → Bridge → `desktop_server.py` → `dados.db` (filtros e busca reais).

### Testes Manuais
- [x] Executar `make test-e2e` e `make test-e2e-live` da raiz do repositório e validar 100% de aprovação.
