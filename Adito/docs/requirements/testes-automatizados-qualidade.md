# Requirements — Suíte de Testes Automatizados (Frontend, Performance e Acurácia da IA)

**Status:** REQUIREMENTS_READY  
**Discovery de origem:** `Adito/docs/discovery/testes-automatizados-qualidade.md` (`PROBLEM_READY`)  
**Classificacao de Processo:** NORMAL PROCESS  
**Issue Relacionada:** [#71](https://github.com/SmartIdea-ifes-serra/Adito/issues/71)

## Intent Summary
Entregar uma suíte automatizada completa e sustentável para o Adito que valide: (1) lógica e fluxos da interface Vue 3 via Vitest e Playwright (modo determinístico e modo integrado com o núcleo Python), (2) desempenho e latência do núcleo local sobre o `dados.db` real com SLOs mensuráveis e (3) acurácia das respostas da IA (Text-to-SQL + geração de texto) em duas camadas sobre um dataset gabarito independente, com integração no `Makefile`, documentação no `README.md` e relatório consolidado pronto para a Issue #71.

## Functional Requirements
- **FR01 — Testes Unitários de Frontend (Vitest + Vue Test Utils):** Configurar `vitest` com `@vue/test-utils` e ambiente DOM (`happy-dom` ou `jsdom`) em `Adito/app/frontend-vue/`, com testes cobrindo cliente IPC (`core.ts`, `llmKey.ts`), composables (`useChatHistory.ts`, `useDashboardData.ts`, `useContextos.ts`, `useToast.ts`) e utilitários (`markdown.ts`).
- **FR02 — Testes E2E de Frontend em Modo Determinístico (Playwright + Mock IPC):** Configurar `@playwright/test` em `Adito/app/frontend-vue/` com injeção de stub de `window.__TAURI_INTERNALS__` (`core_ready`, `core_call`, `core_stream`, `llm_key_status`, `Channel`) e fixtures realistas do domínio IFES, validando navegação principal, Dashboard (KPIs, gráficos, filtros), Explorar Dados (seleção de tabela, busca, ordenação, paginação), Chat Estratégico (envio, streaming, tabela, gráfico, histórico e bloqueio/erro), Meu Dashboard, Admin e Configurações.
- **FR03 — Testes E2E Integrados com Núcleo Real (Playwright Live Bridge):** Disponibilizar uma ponte HTTP local leve (usada apenas em modo teste) que conecta o stub de `__TAURI_INTERNALS__` do navegador ao processo real `desktop_server.py` (stdin/stdout) lendo `Adito/app/data/dados.db`, validando fluxos reais de leitura (Dashboard, Explorar Dados, Contextos e Status) sem precisar compilar a casca Rust/Tauri.
- **FR04 — Benchmark de Cold-Start e RPCs do Núcleo Local:** Criar script de benchmark em Python que inicia `desktop_server.py` contra o `dados.db` real, mede o tempo de boot até o evento `ready` e executa múltiplas iterações das RPCs críticas (`health`, `me`, `contextos.list`, `dashboard.kpis`, `dashboard.charts`, `dashboard.top_projects`, `explorer.tables`, `explorer.rows` com busca sem acento e ordenação), calculando `min`, `p50`, `p95`, `p99` e `max`.
- **FR05 — Benchmark Analítico nas 6 Views Fato e Concorrência STDIO:** O script de benchmark deve medir tempos de consulta analítica (agregações e filtros reais) sobre todas as 6 views fato (`vfact_extensao_acao_resolved`, `vfact_extensao_participacao_resolved`, `vfact_projeto_pesquisa_resolved`, `vfact_orientacao_bolsa_resolved`, `vfact_producao_cientifica_resolved`, `vfact_grupo_pesquisa_membro_resolved`) e executar rajada de requisições concorrentes no protocolo STDIO/RPC medindo throughput (req/s) e taxa de erro (esperado: 0%).
- **FR06 — Validação de SLOs e Relatório de Performance:** Comparar métricas coletadas contra thresholds (SLOs) configuráveis (falhando com exit code != 0 em regressão crítica, com opção `--no-fail` para modo informativo) e exportar relatório em JSON e Markdown pronto para publicação na Issue #71.
- **FR07 — Dataset Gabarito Independente de Acurácia:** Criar arquivo estruturado `eval_dataset.json` com ~20–25 casos balanceados, independentes de `Adito/app/contexts/pesquisa-extensao-ifes/examples.json`, cobrindo: consultas simples e agregadas nas 6 views fato, cruzamentos e filtros com acentos/nomes reais, perguntas fora de escopo (`out_of_scope`), tentativas de *prompt injection* (`blocked`) e perguntas acadêmicas legítimas com termos sensíveis (ex.: "orientações", "regras de edital").
- **FR08 — Camada 1 da Avaliação de Acurácia (Determinística: Execution Accuracy + Guard):** Para casos analíticos, executar a SQL gabarito e a SQL gerada pelo Adito contra o mesmo `dados.db` no momento da execução, normalizar e comparar os resultados (Execution Accuracy) e verificar conformidade de `sql_security`. Para casos de escopo/segurança, validar determinísticamente se o intent/resposta esperada de bloqueio ou fora de escopo foi acionada sem gerar SQL.
- **FR09 — Camada 2 da Avaliação de Acurácia (LLM-as-a-Judge):** Enviar ao juiz LLM (reutilizando `GEMINI_API_KEY` com suporte à variável opcional `GEMINI_JUDGE_MODEL`, fallback para `GEMINI_MODEL`) a tupla `(pergunta, resultado real da SQL gabarito, resposta em linguagem natural do Adito)` para pontuar com saída estruturada (JSON/Pydantic): fidelidade factual (zero alucinação de números), completude, ausência de vazamento de SQL/PII e justificativa curta.
- **FR10 — Telemetria de Latência LLM, Filtros e Relatório de Acurácia:** O runner de acurácia deve suportar `--sample N`, `--categoria <cat>` e `--no-judge` (rodar só Camada 1), medir a latência ponta a ponta do pipeline de IA (`p50`/`p95`/média por pergunta) e gerar relatório consolidado em JSON e Markdown com taxas de aprovação por categoria e tabela detalhada de falhas.
- **FR11 — Novos Alvos no Makefile Raiz:** Adicionar ao `Makefile` os alvos `test-front`, `test-e2e`, `test-e2e-live`, `test-perf` e `test-eval` (com suporte a passagem de `ARGS`), e incluir `test-front` no alvo `make test`.
- **FR12 — Documentação e Evidências para Issue #71:** Documentar pré-requisitos (incluindo instalação do Chromium para Playwright), comandos de execução e interpretação dos relatórios no `README.md`, além de gerar os relatórios de execução reais prontos para comentar na Issue #71.

## Business / Domain Rules
- **BR01 — Zero Data Leakage no Eval:** O `eval_dataset.json` não deve copiar verbatim as perguntas de `Adito/app/contexts/pesquisa-extensao-ifes/examples.json` (que alimentam o *few-shot* do agente), garantindo medição honesta de generalização.
- **BR02 — Gabarito Dinâmico via SQL:** Casos analíticos do dataset devem guardar a *SQL gabarito* (executada em tempo real no `dados.db`) em vez de números/textos fixos, evitando obsolescência quando o ETL atualizar os dados.
- **BR03 — Zero PII em Artefatos de Teste:** Nem fixtures do frontend, nem o `eval_dataset.json`, nem os relatórios exportados devem conter CPF, e-mail pessoal, telefone, endereço ou data de nascimento.
- **BR04 — Isolamento de Custo e Velocidade no `make test`:** O alvo padrão `make test` deve permanecer 100% local, offline, rápido e gratuito — nunca exigindo binário Chromium nem disparando chamadas à API Gemini.
- **BR05 — Separação entre Falha de Infraestrutura e Falha de Acurácia:** Erros transitórios de API (ex.: HTTP 429 / rate limit ou falha de rede no Gemini) devem ser retentados com backoff e, se persistirem, contabilizados separadamente de erros de acurácia do modelo.
- **BR06 — Aprovação Explícita de Dependências Externas:** Toda nova dependência (`vitest`, `@vue/test-utils`, `happy-dom`, `@playwright/test`) só será adicionada ao `package.json` após aprovação explícita do usuário (Regra 6 do `AGENTS.md`).

## Non-Functional Requirements
- **NFR01 — Rapidez da Suíte Padrão:** `make test-front` (Vitest) deve concluir em < 10 segundos; `make test-e2e` (Playwright mock) deve concluir em < 45 segundos em máquina local.
- **NFR02 — Determinismo Local:** `make test-front`, `make test-e2e`, `make test-e2e-live` (exceto chat LLM) e `make test-perf` devem ser 100% reproduzíveis sem acesso à internet.
- **NFR03 — Compatibilidade com Caminhos com Espaços:** Todos os novos alvos do `Makefile` e scripts de teste devem preservar aspas em caminhos (seguindo a diretriz estabelecida no PR #77).
- **NFR04 — Portabilidade de Relatórios:** Relatórios gerados por `test-perf` e `test-eval` devem ser salvos em diretório previsível (com artefatos transitórios ignorados no git se necessário, e resumo limpo em Markdown pronto para colar no GitHub).
- **NFR05 — Tolerância Semântica na Comparação de Dados:** A Camada 1 do `eval` deve comparar resultados SQL tolerando diferenças de alias de coluna, pequenas variações de ponto flutuante (`abs_tol=0.05` ou relativo `1e-3`) e ordem das linhas quando a pergunta não exigir ordenação específica.

## User Scenarios

### Main flow
1. Desenvolvedor executa `make test` no dia a dia: roda ETL, núcleo Python, STDIO/contrato e Vitest (`test-front`), tudo offline e rápido.
2. Antes de abrir PR tocando UI, desenvolvedor executa `make test-e2e` (mock rápido em Chromium) e, opcionalmente, `make test-e2e-live` para validar a integração real com o núcleo Python + `dados.db`.
3. Ao alterar SQL, views ou datastore, desenvolvedor executa `make test-perf` sobre o `dados.db` real e confere se `p95` e cold-start respeitam os SLOs.
4. Ao alterar prompts, contexto ou modelo Gemini, desenvolvedor executa `make test-eval` (ou `make test-eval ARGS="--sample 5"`), recebe relatório com Execution Accuracy, nota do LLM Judge e latência `p50`/`p95`, e cola o resumo na Issue/PR.

### Alternative / Error / Edge cases
- `dados.db` ausente ao rodar `make test-perf`, `make test-e2e-live` ou `make test-eval`: script falha com mensagem clara orientando a executar `make db` primeiro.
- `GEMINI_API_KEY` ausente ao rodar `make test-eval`: script falha imediatamente com instrução clara antes de iniciar o loop (sem stack trace críptico).
- Chromium do Playwright não instalado ao rodar `make test-e2e`: mensagem clara instruindo `cd Adito/app/frontend-vue && npx playwright install chromium`.
- Rate-limit (429) da API Gemini durante `make test-eval`: backoff exponencial breve (ex.: 2 tentativas) e marcação explícita como `infra_error` no relatório.
- Streaming interrompido ou erro 503 ("chave não configurada") no Chat: coberto explicitamente nos cenários E2E do Playwright mock.

## Business / Domain Context
- Domínio acadêmico do IFES Campus Serra: 4 fontes (SRC, SigPesq, Lattes, CNPq DGP) consolidadas em 6 views fato no SQLite (`dados.db`).
- O frontend é uma SPA Vue 3 + TypeScript + `@nuxt/ui` + ApexCharts empacotada via Tauri v2, comunicando-se exclusivamente via `@tauri-apps/api/core` (`invoke` + `Channel`).

## Technical Context & Constraints
- **Frontend:** `Adito/app/frontend-vue` (Vue 3.5, Vite 8, TypeScript 5.9, Node.js).
- **Novas `devDependencies` propostas (Regra 6):** `vitest`, `@vue/test-utils`, `happy-dom`, `@playwright/test`.
- **Backend:** `Adito/app/backend/nucleo` (Python `.venv`, LangGraph, `langchain-google-genai`, `sqlite3` read-only). Nenhuma dependência externa Python adicional necessária (usa `stdlib` + pacotes já instalados no `requirements.txt`).
- **Makefile:** `SHELL := /bin/bash`, Linux/WSL/macOS, caminhos sempre entre aspas duplas.

## Quality Attributes
- **Testability:** Abstração limpa do mock de `__TAURI_INTERNALS__` reutilizável entre todos os specs Playwright.
- **Maintainability:** Dataset gabarito em JSON declarativo fácil de expandir por qualquer membro da equipe sem alterar código do runner.
- **Observability:** Relatórios estruturados (JSON para histórico/comparação + Markdown legível para GitHub Issues/PRs).

## Assumptions
- **A01** — `Adito/app/data/dados.db` existe localmente após `make db` e contém as 6 views populadas.
- **A02** — `GEMINI_API_KEY` está configurada no `.env` do usuário quando `make test-eval` for executado.
- **A03** — A instalação do browser Chromium do Playwright é feita uma única vez no ambiente de desenvolvimento (`npx playwright install chromium` ou usando Chromium já presente no sistema).
- **A04** — Não há necessidade de alterar código de produção do backend ou frontend além de eventuais `data-testid` pontuais (somente se realmente necessários quando `getByRole`/`getByLabel` não forem suficientes, conforme `.agents/rules/coding-standards.md`).

## Out of Scope
- Automação sobre o binário desktop compilado do Tauri (`tauri-driver`).
- Workflows de CI/CD no GitHub Actions (fica para etapa posterior).
- Testes de carga distribuída multi-usuário.
- Novos provedores de LLM pagos exclusivos para o juiz.

## Open Questions
- [BLOCKING? nao] Aprovação das novas `devDependencies` de frontend (`vitest`, `@vue/test-utils`, `happy-dom`, `@playwright/test`) — será confirmada no encerramento dos Requirements / antes da implementação.

## Key Decisions Proposed
1. **Sem novas dependências Python:** tanto o benchmark (`test-perf`) quanto o avaliador de acurácia (`test-eval`) serão escritos usando apenas a stdlib + dependências já presentes em `Adito/app/backend/requirements.txt` (`langchain-google-genai`, `pydantic`, `sqlite3`).
2. **Sem alteração invasiva no código de produção do frontend:** o Playwright injeta o mock/bridge em `window.__TAURI_INTERNALS__` via `addInitScript`, testando o `core.ts` e o bundle Vue reais sem criar `if (isTest)` no código de produção.
3. **Sem `data-testid` desnecessário:** priorizar seletores acessíveis (`getByRole`, `getByLabel`, `getByPlaceholder`, `getByText`) conforme `.agents/rules/coding-standards.md`.
4. **Estrutura de arquivos proposta:**
   - `Adito/app/frontend-vue/tests/unit/` (Vitest)
   - `Adito/app/frontend-vue/tests/e2e/` (Playwright + mock IPC + bridge live)
   - `Adito/app/scripts/bench_backend.py` (Performance + SLOs)
   - `Adito/app/scripts/eval_acuracia.py` + `Adito/app/scripts/eval_dataset.json` (Acurácia híbrida)

## Review & Adjust

O usuario pode **aprovar, editar, adicionar, remover ou reclassificar** qualquer requisito/regra antes do gate.

- [x] Proposta completa apresentada ao usuario
- [x] Ajustes solicitados incorporados
- [x] IDs estabilizados depois da revisao
- [x] Nenhuma pergunta bloqueante aberta

### User adjustments
- Nenhum ajuste solicitado; requisitos e novas `devDependencies` (`vitest`, `@vue/test-utils`, `happy-dom`, `@playwright/test`) aprovados pelo usuario.

## Gate G1 — REQUIREMENTS READY

**Status:** APPROVED

**Aprovado pelo usuario:** sim
