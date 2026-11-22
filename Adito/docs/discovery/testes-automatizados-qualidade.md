# Discovery — Suíte de Testes Automatizados (Frontend, Performance e Acurácia da IA)

**Status:** PROBLEM_READY
**Classificacao de Processo:** NORMAL PROCESS
**Origem:** hibrido (usuario + Issue #71 + codigo)
**Issue Relacionada:** [#71](https://github.com/SmartIdea-ifes-serra/Adito/issues/71)

## Intent

Estruturar uma suíte completa e sustentável de garantia de qualidade para o ecossistema Adito (Issue #71), cobrindo testes unitários e E2E do frontend Vue, benchmark de performance/latência do núcleo local sobre o `dados.db` real e avaliação sistemática de acurácia das respostas da IA (Text-to-SQL + geração de resposta em linguagem natural).

## Problem

Embora o repositório já conte com testes unitários e de contrato para o ETL e o núcleo Python (`make test`), existem quatro lacunas críticas de qualidade:

1. O frontend Vue (`Adito/app/frontend-vue`) não possui nenhum teste automatizado (nem unitário nem E2E), deixando regressões visuais, de estado e de fluxo descobertas.
2. O frontend se comunica exclusivamente via IPC do Tauri (`@tauri-apps/api/core`, sem servidor HTTP), o que impede rodar testes E2E em navegador comum sem uma estratégia dedicada de mock/bridge.
3. Não existe um benchmark de performance estruturado sobre o `dados.db` real (6 views fato, milhares de linhas) com percentis (`p50`/`p95`/`p99`), testes de concorrência e limites de regressão (SLOs).
4. Não há um mecanismo automatizado com dataset gabarito independente para medir se o `bi_agent` gera SQL correta e se as respostas textuais são fiéis aos dados (sem alucinação, vazamento de PII ou falsos positivos no `guard`).

## Users / Stakeholders relevantes

- **Desenvolvedores do Adito:** precisam de feedback rápido, local e confiável ao alterar frontend, núcleo Python, prompts ou SQL.
- **Revisores de PR / Mantenedores:** precisam de evidências objetivas de qualidade, performance e acurácia (incluindo resultados registrados na Issue #71).
- **Usuários finais (gestores e pesquisadores do IFES):** dependem de uma interface estável, respostas rápidas e dados acadêmicos sem alucinação.

## Current Situation

- **ETL (`Adito/etl/tests`):** 69 testes `pytest`.
- **Núcleo Python (`Adito/app/backend/nucleo`):** 51 testes `unittest` + 14 testes STDIO (`teste_stdio.py`, com mediana simples em banco sintético) + 51 verificações de contrato RPC (`teste_contrato.py`).
- **Frontend Vue (`Adito/app/frontend-vue`):** 0 testes configurados (apenas `vue-tsc` no build).
- **Acurácia LLM:** validação puramente manual no chat.

## Desired Outcome

- Regressões de lógica e fluxo no frontend Vue detectadas automaticamente via **Vitest** (unitário) e **Playwright** (E2E híbrido).
- Performance local do núcleo medida de forma reproduzível sobre o `dados.db` real com SLOs claros e relatório pronto para publicação.
- Acurácia do pipeline de IA avaliada de forma objetiva em 2 camadas (execução real da SQL gabarito + LLM-as-a-Judge) sobre um dataset independente, gerando métricas claras de acerto, fidelidade e latência de LLM.
- Todos os comandos integrados ao `Makefile` raiz e documentados no `README.md`, mantendo `make test` rápido e offline.

## Success Criteria

- [ ] Testes unitários do frontend (Vitest + Vue Test Utils) rodando via `make test-front` e integrados ao `make test` rápido/offline.
- [ ] Testes E2E com Playwright cobrindo os fluxos principais de UI em modo determinístico (`make test-e2e`, via mock de `__TAURI_INTERNALS__`) e em modo integrado opcional com o núcleo Python real (`make test-e2e-live`, via bridge local).
- [ ] Benchmark local de performance (`make test-perf`) sobre o `dados.db` real medindo cold-start, percentis (`p50`/`p95`/`p99`) das RPCs críticas, queries nas 6 views fato e carga concorrente, validando SLOs e gerando relatório Markdown/JSON.
- [ ] Suite de avaliação de acurácia (`make test-eval`) com dataset gabarito balanceado (~20–25 casos independentes de `examples.json`), executando comparação determinística (Execution Accuracy + Guard) e LLM-as-a-Judge (fidelidade factual, completude, ausência de SQL/PII) + telemetria de latência do LLM, gerando relatório Markdown/JSON.
- [ ] Instruções completas de setup e execução documentadas no `README.md`.
- [ ] Resultados consolidados executados e prontos para publicação no comentário da Issue #71.

## Scope

### IN

- **Frontend Unit (Vitest + `@vue/test-utils` + `jsdom`/`happy-dom`):** testes de composables, utilitários e cliente IPC (`core.ts`, `llmKey.ts`, `useChatHistory.ts`, `useDashboardData.ts`, `markdown.ts`, etc.).
- **Frontend E2E Híbrido (`@playwright/test`):**
  - Fluxos de navegação, Dashboard (KPIs, filtros, gráficos), Explorar Dados (busca, paginação, ordenação), Chat Estratégico (streaming, tabela, gráfico, histórico), Meu Dashboard, Admin e Configurações;
  - Mock de `window.__TAURI_INTERNALS__` com fixtures determinísticas (padrão);
  - Bridge local opcional conectando o Chromium ao `desktop_server.py` real sobre `dados.db`.
- **Backend Performance Benchmark:** script dedicado em Python sobre `dados.db` real medindo cold-start, RPCs críticas (`dashboard.*`, `explorer.*`), queries nas 6 views fato e concorrência STDIO/RPC, com SLOs e relatório Markdown/JSON.
- **Avaliação Híbrida de Acurácia da IA:** dataset independente (~20–25 casos cobrindo 6 views, cruzamentos/filtros com acentos, escopo e segurança), runner Python com Camada 1 determinística (execução SQL gabarito vs gerada + guard) e Camada 2 LLM-as-a-Judge (`GEMINI_API_KEY` + opcional `GEMINI_JUDGE_MODEL`), flags `--sample`/`--categoria`, telemetria de latência LLM e relatório Markdown/JSON.
- **Integração DevEx & Docs:** novos alvos no `Makefile` (`test-front`, `test-e2e`, `test-e2e-live`, `test-perf`, `test-eval`), atualização do `make test` (incluindo `test-front`), atualização do `README.md` e geração de relatório final para a Issue #71.

### OUT

- Testes E2E dentro da janela binária compilada do Tauri/WebView nativo (WebDriver/tauri-driver).
- Configuração de pipeline CI/CD no GitHub Actions (workflow `.github/workflows/`).
- Testes de carga distribuída ou stress multi-máquina (o Adito é um aplicativo desktop local).
- Criação de novos provedores pagos de LLM apenas para o juiz (reutiliza a chave Gemini já usada pelo projeto).

### LATER

- Integração automatizada das suítes (`test-front`, `test-e2e`, `test-perf`) em pipeline CI no GitHub Actions.
- Testes visuais de regressão por screenshot (*visual regression testing*) no Playwright.
- Avaliação contínua de histórico multi-turno longo no `eval` (conversas de 5+ turnos encadeados).

## Constraints / Feasibility

- **Regra 6 (`AGENTS.md`):** exige aprovação explícita do usuário antes de adicionar novas `devDependencies` em `Adito/app/frontend-vue/package.json` (`vitest`, `@vue/test-utils`, `happy-dom` ou `jsdom`, `@playwright/test`).
- **IPC Tauri sem HTTP:** o frontend chama `invoke('core_call')` e `invoke('core_stream')` com `Channel`; o mock/bridge precisa emular fielmente o protocolo de `Channel` e os eventos `$end` usados em `src/common/api/core.ts`.
- **Cota e Custo da API Gemini:** `make test-eval` consome requisições da API Gemini e nunca deve ser disparado implicitamente pelo `make test`.
- **Ambiente Linux/WSL/macOS:** alinhado ao `Makefile` atual; Chromium do Playwright precisa ser instalado via `npx playwright install chromium` (ou reutilizar browser disponível no ambiente).

## Assumptions

- [ASSUMPTION] O arquivo `Adito/app/data/dados.db` (gerado por `make db`) está disponível localmente para rodar `make test-perf`, `make test-e2e-live` e `make test-eval`.
- [ASSUMPTION] Para rodar `make test-eval` com a camada LLM-as-a-Judge, `GEMINI_API_KEY` estará configurada no `.env` do ambiente local.
- [ASSUMPTION] `happy-dom` ou `jsdom` pode ser utilizado como ambiente DOM do Vitest sem conflitos com `@nuxt/ui` e Vue 3.5.
- [ASSUMPTION] O `eval_dataset.json` será versionado no repositório contendo apenas perguntas públicas e SQLs sobre o schema analítico do IFES (zero PII).

## Risks

- **R1 — Divergência entre fixtures do Playwright mock e contrato real do núcleo:** mitigado pelo modo `make test-e2e-live` (que valida contra o `desktop_server.py` real) e pela suíte `teste_contrato.py`.
- **R2 — Flakiness ou variação de cota/rate-limit do Gemini no `make test-eval`:** mitigado por retry com backoff leve, flag `--sample` / `--categoria` e separação clara entre falhas de infraestrutura (429/timeout) e falhas de acurácia.
- **R3 — Falso negativo na comparação determinística de SQL (aliases diferentes, arredondamento ou ordem):** mitigado por normalização semântica de resultados (comparação por linhas/valores numéricos com tolerância de ponto flutuante e ignorando nomes de colunas/aliases quando não exigidos).
- **R4 — Dependências pesadas do Playwright quebrando `make setup`:** mitigado mantendo a instalação do binário Chromium explícita (`npx playwright install chromium` ou alvo dedicado) e documentada.

## Open Questions

- [BLOCKING? nao] Confirmar aprovação explícita das novas `devDependencies` no frontend (`vitest`, `@vue/test-utils`, `happy-dom`, `@playwright/test`) na transição para implementação.

## Review & Adjust

- [x] Usuario revisou a proposta completa
- [x] Alteracoes solicitadas foram incorporadas
- [x] Decisoes relevantes foram confirmadas
- [x] Nao existem perguntas bloqueantes abertas

### User adjustments

- Nenhum ajuste solicitado; proposta aprovada integralmente pelo usuario.

## Gate G0 — PROBLEM READY

**Status:** APPROVED

**Aprovado pelo usuario:** sim
