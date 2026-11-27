# Product Backlog — Adito

Backlog do Adito no monorepo. As stories do porte desktop (US-001 a US-015) estão indexadas em [README.md](README.md); aqui fica o que veio depois do Discovery rev. 4.

## Epics

### EPIC-07: ETL do Adito
Extração do bruto de SRC, SigPesq, CNPq/DGP e Lattes, cruzamento das bases por nome normalizado em `Adito/etl/`. Origem: `docs/discovery/adito.md` (rev. 4 e rev. 5) e `docs/requirements/adito-etl.md` (rev. 1 e rev. 2).
- **Stories**: US-ETL-01 a US-ETL-07 (US-ETL-08 e US-ADITO-DUCKDB-01 substituídas pelo EPIC-08).

### EPIC-08: Migração da Arquitetura de Dados Acadêmicos para 100% SQLite (dados.db)
Unificação da camada relacional (42 tabelas 3FN do Modelo ASTA) e da camada analítica (6 VIEWs de fatos dinâmicas) em um único banco SQLite (`dados.db`) gerado diretamente por script Python (`sqlite3`), eliminando Docker, PostgreSQL, JSONs intermediários e DuckDB, e adaptando o backend núcleo com segurança estrita (`mode=ro`, `set_authorizer`), busca sem acentos e transpilação `sqlglot`. Origem: `docs/discovery/migracao-arquitetura-sqlite.md`, `docs/requirements/migracao-arquitetura-sqlite.md` e ADRs 0001 a 0004.
- **Stories**: US-SQLITE-01 a US-SQLITE-04.

### EPIC-09: Produtividade de Desenvolvimento & Automação Local (DevEx)
Criação de ponto de entrada único via Makefile na raiz do monorepo para unificar setup de ambientes virtuais e dependências, reconstrução do banco relacional com fatos em < 5s, inicialização do app desktop, execução consolidada das suítes de testes automatizados e resiliência de onboarding em ambientes limpos (Issues #83, #84, #87 e #88). Origem: `docs/discovery/automacao-makefiles-devex.md`, `docs/requirements/automacao-makefiles-devex.md`, `Adito/docs/discovery/correcao-onboarding-makefile-desktop.md` e `Adito/docs/requirements/correcao-onboarding-makefile-desktop.md`.
- **Stories**: US-DEVEX-01 a US-DEVEX-05.

### EPIC-10: Garantia de Qualidade — Testes Automatizados, Performance e Avaliação da IA (Issue #71)
Estruturação da suíte completa de qualidade do Adito: testes unitários no frontend Vue (Vitest + Vue Test Utils), testes E2E híbridos com Playwright (mock de `__TAURI_INTERNALS__` + bridge live com `desktop_server.py`), benchmark de performance/latência do núcleo local sobre o `dados.db` real com SLOs e avaliação híbrida de acurácia da IA (SQL gabarito executada + LLM-as-a-Judge) com dataset independente. Origem: `Adito/docs/discovery/testes-automatizados-qualidade.md` e `Adito/docs/requirements/testes-automatizados-qualidade.md`.
- **Stories**: US-QA-01 a US-QA-04.

### EPIC-11: Suporte Multi-Provedor de IA (BYOK)
Habilitação de múltiplos provedores de IA com suporte completo a Chat + Embeddings no Adito (Gemini, OpenAI, OpenRouter, Mistral AI, Z.AI/GLM, Together AI, Fireworks AI e Ollama local) usando apenas `langchain-openai` como nova dependência, com proteção de dimensão vetorial, fallback defensivo, cofre do SO isolado por provedor com retrocompatibilidade v0.1.0, empacotamento PyInstaller, dropdown customizado com indicador "Em uso" e avisos na Base de conhecimento. Origem: `Adito/docs/discovery/suporte-multi-provedor-llm.md` e `Adito/docs/requirements/suporte-multi-provedor-llm.md`.
- **Stories**: US-LLM-01 a US-LLM-04.

### EPIC-12: Cancelamento de Prompts e Streaming em Segundo Plano no Chat
Capacidade de abortar respostas em andamento no chat do Adito via botão **"Parar"** ou tecla **`Esc`** sem perder o texto já digitado nem gravar respostas incompletas no `app.db`, com execução em segundo plano independente por conversa/rota, indicador de carregamento na sidebar, filtro pós-abort no IPC (`core.ts`) e cancelamento cooperativo no `BIAgent` para economizar cota de API BYOK. Origem: `Adito/docs/discovery/abortar-prompt-chat.md` e `Adito/docs/requirements/abortar-prompt-chat.md`.
- **Stories**: US-CHAT-01 e US-CHAT-02.

### EPIC-13: Atualização Automática (Opt-in) e Auto-Reload de Telas
Evolução do sistema de distribuição desktop (`ADR-0006`/`ADR-0007`) com opção opt-in em Configurações (desligada por padrão) para verificação periódica/foco, download em segundo plano do executável com proteção de chat ativo e contagem regressiva de 10s (com "Reiniciar agora" e "Adiar"), auto-update de `dados.db` priorizando o executável e sinal reativo `dadosReloadSeq` para recarga automática de Dashboard, Meu painel, Contextos/Chat e Administração com toast discreto, sem reindexação automática de embeddings. Origem: `Adito/docs/discovery/auto-update-reload.md` e `Adito/docs/requirements/auto-update-reload.md`.
- **Stories**: US-UPD-01 e US-UPD-02.

### EPIC-14: Relatórios a partir das respostas do chat
Relatório montado por **modelo fixo**, sem LLM, a partir de respostas já recebidas no chat: botão **"Mais" (+)** → **Criar relatório**, seleção das perguntas da conversa como seções, relatório gravado como **mensagem da conversa** com os números recalculados sobre os dados atuais, e **exportação em PDF** com visual de documento formal: logo pequena com o nome "Adito" e número da página no topo, primeira página com os dados do relatório e o conteúdo, uma página por seção com Tabela N e Figura N (ou Quadro N) e a fonte, e o Apêndice A com o SQL (ajustado em 2026-11-26). Texto interpretativo por LLM fica para depois. Origem: `Adito/docs/discovery/relatorios-chat.md` e `Adito/docs/requirements/relatorios-chat.md` (HEAVY PROCESS).
- **Stories**: US-REL-01 a US-REL-04.

### EPIC-15: Exportação de Dados do Chat para CSV e Excel (`.xlsx`)
Exportação direta dos dados completos retornados em tabelas e gráficos das respostas do Chat para **CSV** (padrão Excel PT-BR: UTF-8 BOM, separador `;`, proteção contra Formula Injection) e **Excel nativo (`.xlsx` OOXML)** em TypeScript puro (zero novas dependências em npm/Python), com comando Rust `exportar_arquivo` usando o plugin oficial `tauri-plugin-dialog = "2"` (aprovado pelo usuário) para abrir o diálogo nativo **"Salvar como..."** do SO com gravação atômica, fallback `showSaveFilePicker`/`Blob` no navegador/E2E e botão dropdown acessível **"Exportar"** com toast de confirmação. Origem: `Adito/docs/discovery/exportar-dados-csv-excel.md` e `Adito/docs/requirements/exportar-dados-csv-excel.md`.
- **Stories**: US-EXP-01 e US-EXP-02.

---

## User Stories Priorizadas

### 🗂️ EPIC-07 — ETL do Adito (aprovado em 10/11/2026)

| ID | Título | Epic | Estimativa (pts) | Prioridade | Depende de | Requisitos | Status |
|----|--------|------|------------------|------------|------------|------------|--------|
| [US-ETL-01](stories/US-ETL-01_base-etl-acoes-src.md) | Base do `etl/` e extrator de ações do SRC | EPIC-07 | 3 | 🔴 Alta (slice 1) | — | FR01, FR07–09, BR06, NFR03, NFR05 | 🔍 Review |
| [US-ETL-02](stories/US-ETL-02_participacoes-src-sem-pii.md) | Participações do SRC sem CPF nem e-mail | EPIC-07 | 5 | 🔴 Alta (slice 1) | 01 | FR02, FR03, BR01, NFR02, NFR04, NFR06 | 🔄 In Progress |
| [US-ETL-03](stories/US-ETL-03_extrator-sigpesq.md) | Extrator do SigPesq | EPIC-07 | 5 | 🟠 Alta (slice 2) | 01 | FR04, BR01, A01, A04 | 🔄 In Progress |
| [US-ETL-06](stories/US-ETL-06_cruzamento-pessoas-por-nome.md) | Cruzamento de pessoas por nome normalizado | EPIC-07 | 5 | 🟠 Alta (slice 2) | 02 + 1 fonte | FR10, FR11, FR13, BR02, BR03, BR05, NFR06 | 🔍 Review |
| [US-ETL-04](stories/US-ETL-04_extrator-cnpq-dgp.md) | Extrator do CNPq/DGP | EPIC-07 | 3 | 🟡 Média | 03 | FR05, BR04 | Backlog |
| [US-ETL-05](stories/US-ETL-05_extrator-lattes.md) | Extrator do Lattes | EPIC-07 | 5 | 🟡 Média | 01 | FR06, A02, A05 | Backlog |
| [US-ETL-07](stories/US-ETL-07_ligacoes-grupo-orientacao.md) | Ligações de grupo e de orientação | EPIC-07 | 3 | 🟡 Média | 03, 04, 05, 06 | FR12 | Backlog |

---

### 🗂️ EPIC-08 — Migração para 100% SQLite (dados.db) (Concluído em 18/11/2026)

| ID | Título | Epic | Estimativa (pts) | Prioridade | Depende de | Requisitos | Status |
|----|--------|------|------------------|------------|------------|------------|--------|
| [US-SQLITE-01](stories/US-SQLITE-01_ddl-sqlite-tabelas-core-fatos-v2.md) | Modelagem DDL em SQLite (42 Tabelas Base 3FN e 6 Fatos v2.0) | EPIC-08 | 5 | 🔴 Alta (slice 1) | — | FR01, FR02, FR04–FR10, BR01–BR08 | ✅ Concluída |
| [US-SQLITE-02](stories/US-SQLITE-02_pipeline-carga-python-materializacao-fatos.md) | Pipeline de Carga Direta em Python/SQLite (`popular_banco.py`) e Validações | EPIC-08 | 5 | 🔴 Alta (slice 1) | US-SQLITE-01 | FR03, FR11, FR12, NFR01, NFR04, NFR07 | ✅ Concluída |
| [US-SQLITE-03](stories/US-SQLITE-03_backend-nucleo-datastore-sqlite-authorizer.md) | Adaptação do Backend Núcleo para SQLite (Datastore RO, Authorizer, LIKE, sqlglot) | EPIC-08 | 5 | 🟠 Alta (slice 2) | US-SQLITE-02 | FR13–FR18, NFR02, NFR03 | ✅ Concluída |
| [US-SQLITE-04](stories/US-SQLITE-04_descomissionamento-legados-testes-specs.md) | Descomissionamento de Legados, Atualização de Testes e Especificações | EPIC-08 | 3 | 🟡 Média (slice 2) | US-SQLITE-02, 03 | FR19, NFR05, NFR06 | ✅ Concluída |

> Total EPIC-08: 18 pts (100% Concluído em 18/11/2026).  
> - **Vertical Slice 1 (10 pts):** `US-SQLITE-01` + `US-SQLITE-02` (Geração e validação do banco `dados.db` 100% funcional em SQLite). Concluído.  
> - **Vertical Slice 2 (8 pts):** `US-SQLITE-03` + `US-SQLITE-04` (Integração segura com backend núcleo, agente de BI resiliente e expurgo de legados). Concluído.  

---

### 🗂️ EPIC-09 — Produtividade de Desenvolvimento & Automação Local (DevEx) (atualizado em 20/11/2026)

| ID | Título | Epic | Estimativa (pts) | Prioridade | Depende de | Requisitos | Status |
|----|--------|------|------------------|------------|------------|------------|--------|
| [US-DEVEX-01](stories/US-DEVEX-01_automacao-comandos-makefile-unico.md) | Automação de Comandos do Desenvolvedor via Makefile Único | EPIC-09 | 3 | 🔴 Alta | — | FR01–FR09, BR01–BR04, NFR01–NFR03 | ✅ Concluída |
| [US-DEVEX-02](stories/US-DEVEX-02_geracao-automatica-lattes-csv.md) | Geração automática e segura de `entradas/lattes.csv` no `make etl-lattes` (Issue #83) | EPIC-09 | 2 | 🔴 Alta (slice 2) | — | FR01, FR02, FR09, BR01–BR03, NFR01, NFR04–NFR05, A01 | ✅ Concluída |
| [US-DEVEX-03](stories/US-DEVEX-03_guarda-cargo-e-checagens-modulares.md) | Guarda de Rust (`cargo`) e validações modulares de pré-requisitos (Issue #84) | EPIC-09 | 2 | 🔴 Alta (slice 2) | — | FR03, FR04, FR09, BR04, NFR01–NFR02, NFR04–NFR05 | ✅ Concluída |
| [US-DEVEX-04](stories/US-DEVEX-04_compatibilidade-snap-e-wayland-desktop.md) | Compatibilidade de `rodar_desktop.sh` com VS Code Snap e GNOME Wayland (Issue #87) | EPIC-09 | 2 | 🔴 Alta (slice 2) | US-DEVEX-03 | FR05, FR09, BR05, NFR01–NFR02, NFR05, A04 | ✅ Concluída |
| [US-DEVEX-05](stories/US-DEVEX-05_fluxo-all-guarda-brutos-e-check-etl-env.md) | Fluxo condicional em `make all`, guarda de `brutos/`, aviso de `.env` e `check-etl-env` granular (Issue #88) | EPIC-09 | 3 | 🟠 Alta (slice 3) | US-DEVEX-02, US-DEVEX-03 | FR06–FR09, BR01–BR03, BR06, NFR01–NFR05, A02–A03 | ✅ Concluída |

> Total EPIC-09: 12 pts (100% Concluído em 20/11/2026 — Issues #83, #84, #87 e #88).  
> - **Vertical Slice 1 (3 pts):** `US-DEVEX-01` (Makefile raiz, testes operacionais e README). Concluído.  
> - **Vertical Slice 2 (6 pts):** `US-DEVEX-02` + `US-DEVEX-03` + `US-DEVEX-04` (desbloqueio de `etl-lattes` e inicialização do desktop `rodar_desktop.sh`). Concluído.  
> - **Vertical Slice 3 (3 pts):** `US-DEVEX-05` (fluxo condicional `make all`, guarda de `brutos/`, aviso no `setup-etl` e `check-etl-env` granular). Concluído.

---

### 🗂️ EPIC-10 — Garantia de Qualidade: Testes Automatizados, Performance e Avaliação da IA (aprovado em 19/11/2026 — Issue #71)

| ID | Título | Epic | Estimativa (pts) | Prioridade | Depende de | Requisitos | Status |
|----|--------|------|------------------|------------|------------|------------|--------|
| [US-QA-01](stories/US-QA-01_testes-unitarios-frontend-vitest.md) | Testes Unitários de Frontend Vue (Vitest + Vue Test Utils) | EPIC-10 | 3 | 🔴 Alta (slice 1) | — | FR01, FR11, BR03, BR04, BR06, NFR01–NFR03 | ✅ Concluída |
| [US-QA-03](stories/US-QA-03_benchmark-performance-nucleo-local.md) | Benchmark de Performance e Latência do Núcleo Local (`dados.db`) | EPIC-10 | 3 | 🔴 Alta (slice 1) | — | FR04–FR06, FR11, BR04, NFR02–NFR04, A01 | ✅ Concluída |
| [US-QA-02](stories/US-QA-02_testes-e2e-hibridos-playwright.md) | Testes E2E Híbridos de Frontend com Playwright (Mock IPC + Live Bridge) | EPIC-10 | 5 | 🟠 Alta (slice 2) | US-QA-01 | FR02, FR03, FR11, BR03, BR06, NFR01–NFR03, A03–A04 | ✅ Concluída |
| [US-QA-04](stories/US-QA-04_avaliacao-acuracia-ia-llm-judge.md) | Avaliação Híbrida de Acurácia da IA & Consolidação Issue #71 | EPIC-10 | 5 | 🟠 Alta (slice 2) | US-QA-02, US-QA-03 | FR07–FR12, BR01–BR05, NFR03–NFR05, A01–A02 | ✅ Concluída |

> Total EPIC-10: 16 pts (100% Concluído em 19/11/2026).  
> - **Vertical Slice 1 (6 pts):** `US-QA-01` + `US-QA-03` (Testes unitários Vitest no frontend + Benchmark determinístico de performance do backend sobre `dados.db`). Concluído.  
> - **Vertical Slice 2 (10 pts):** `US-QA-02` + `US-QA-04` (Playwright E2E híbrido + Avaliação híbrida de acurácia com LLM Judge + Docs e evidências da Issue #71). Concluído.

---

### 🗂️ EPIC-11 — Suporte Multi-Provedor de IA (BYOK) (Concluído em 24/11/2026)

| ID | Título | Epic | Estimativa (pts) | Prioridade | Depende de | Requisitos | Status |
|----|--------|------|------------------|------------|------------|------------|--------|
| [US-LLM-01](stories/US-LLM-01_catalogo-provedores-fabrica-validacao-rpc.md) | Catálogo de provedores, fábrica multi-provedor e validação RPC | EPIC-11 | 5 | 🔴 Alta (slice 1) | — | FR01, FR02, FR04, FR07, FR09, FR10, BR01, BR02, BR06, NFR01, NFR03–NFR06, A01, A02, A04 | ✅ Concluída |
| [US-LLM-02](stories/US-LLM-02_embeddings-hibridos-protecao-dimensao-fallback.md) | Embeddings híbridos, proteção de dimensão vetorial e fallback textual automático | EPIC-11 | 5 | 🔴 Alta (slice 1) | US-LLM-01 | FR05, FR07, FR08, BR04, BR05, NFR04, NFR05, A02 | ✅ Concluída |
| [US-LLM-03](stories/US-LLM-03_cofre-so-por-provedor-retrocompatibilidade-pyinstaller.md) | Cofre do SO por provedor, persistência local, retrocompatibilidade v0.1.0 e PyInstaller | EPIC-11 | 5 | 🟠 Alta (slice 2) | US-LLM-01 | FR03, FR10, BR01–BR03, BR06, NFR02, NFR05, A03 | ✅ Concluída |
| [US-LLM-04](stories/US-LLM-04_configuracoes-multi-provedor-avisos-base-testes-ui.md) | Tela de Configurações multi-provedor, avisos na Base de conhecimento e testes Frontend/E2E | EPIC-11 | 5 | 🟠 Alta (slice 2) | US-LLM-01, US-LLM-02, US-LLM-03 | FR06–FR08, FR10, BR02–BR04, BR06, NFR05 | ✅ Concluída |

> Total EPIC-11: 20 pts (100% Concluído em 24/11/2026 na branch `feat/multi-provedor-llm`).  
> - **Vertical Slice 1 (10 pts):** `US-LLM-01` + `US-LLM-02` (Núcleo multi-provedor com `langchain-openai`, validação RPC, contrato executável, embeddings híbridos, proteção de dimensão e fallback textual). Concluído.  
> - **Vertical Slice 2 (10 pts):** `US-LLM-03` + `US-LLM-04` (Cofre do SO por provedor no Tauri, retrocompatibilidade v0.1.0, empacotamento PyInstaller, tela Configurações multi-provedor, avisos na Base de conhecimento e testes Rust + Vitest + Playwright mock). Concluído.

---

### 🗂️ EPIC-12 — Cancelamento de Prompts e Streaming em Segundo Plano no Chat (Concluído em 25/11/2026)

| ID | Título | Epic | Estimativa (pts) | Prioridade | Depende de | Requisitos | Status |
|----|--------|------|------------------|------------|------------|------------|--------|
| [US-CHAT-01](stories/US-CHAT-01_cancelamento-cooperativo-nucleo-e-ipc.md) | Cancelamento cooperativo no núcleo Python (`BIAgent` + checkpointer) e filtro pós-abort em `core.ts` | EPIC-12 | 3 | 🔴 Alta (slice 1) | — | FR04, FR08, BR01, BR04, BR05, NFR03, NFR04, A01, A02 | ✅ Concluída |
| [US-CHAT-02](stories/US-CHAT-02_ux-parar-segundo-plano-conversas-e-testes-e2e.md) | UX de "Parar" / `Esc`, segundo plano por conversa/rota e testes Frontend/E2E | EPIC-12 | 5 | 🔴 Alta (slice 2) | US-CHAT-01 | FR01–FR03, FR05–FR07, FR09, BR01–BR03, NFR01–NFR03, NFR05, A03 | ✅ Concluída |

> Total EPIC-12: 8 pts (100% Concluído em 25/11/2026 na branch `feat/abortar-prompt-chat`, Nível ScrumAIDev 1).  
> - **Vertical Slice 1 (3 pts):** `US-CHAT-01` (filtro pós-abort no `Channel` em `core.ts` + `cancel_event` cooperativo no `BIAgent` + integridade do checkpointer). Concluído.  
> - **Vertical Slice 2 (5 pts):** `US-CHAT-02` (estado compartilhado por conversa/rota, botão "Parar" + `Esc`, aviso discreto *"Resposta interrompida"*, indicador na sidebar, `tauriMock.ts`, Vitest e Playwright E2E). Concluído.

---

### 🗂️ EPIC-13 — Atualização Automática (Opt-in) e Auto-Reload de Telas (Aprovado em 25/11/2026)

| ID | Título | Epic | Estimativa (pts) | Prioridade | Depende de | Requisitos | Status |
|----|--------|------|------------------|------------|------------|------------|--------|
| [US-UPD-01](stories/US-UPD-01_motor-auto-update-optin-configuracoes-adr.md) | Motor de auto-update opt-in, proteção de chat ativo, Configurações e adenda ADR-0006 | EPIC-13 | 5 | 🔴 Alta (slice 1) | — | FR01–FR06, FR08, FR09 (unit), BR01–BR06, NFR01–NFR04, A01–A03 | 🔍 Review |
| [US-UPD-02](stories/US-UPD-02_banner-auto-reload-telas-toast-e2e.md) | Banner de reinício, auto-reload reativo nas telas abertas, toast e testes E2E Playwright | EPIC-13 | 3 | 🔴 Alta (slice 2) | US-UPD-01 | FR04 (UI), FR07, FR09 (unit + E2E), BR03, NFR02, NFR04, NFR05 | 🔍 Review |

> Total EPIC-13: 8 pts (Nível ScrumAIDev 1, branch `feat/auto-update-reload`).  
> - **Vertical Slice 1 (5 pts):** `US-UPD-01` (separação `download()`/`install()`, preferência opt-in em Configurações, monitoramento 30 min / foco 15 min, proteção `useChatApi().isLoading`, contagem 10s, prioridade app > dados, backoff, `dadosReloadSeq`, adenda `ADR-0006` e Vitest).  
> - **Vertical Slice 2 (3 pts):** `US-UPD-02` (banner discreto de reinício + toast no `MainLayout.vue`, auto-reload reativo nas 4 telas abertas sem retrain automático e Playwright E2E em `atualizacoes.spec.ts`).

---

### 🗂️ EPIC-14 — Relatórios a partir das respostas do chat (Aprovado em 25/11/2026)

| ID | Título | Epic | Estimativa (pts) | Prioridade | Depende de | Requisitos | Status |
|----|--------|------|------------------|------------|------------|------------|--------|
| [US-REL-01](stories/US-REL-01_gerar-e-ver-relatorio-no-chat.md) | Gerar e ver o relatório no chat | EPIC-14 | 8 | 🔴 Alta (slice 1) | — | FR01, FR02 (sem título de seção editável), FR04–FR10, BR01–BR08, NFR01 (chat), NFR05–NFR07 | 🔍 Review |
| [US-REL-03](stories/US-REL-03_spike-pdf-impressao-tauri.md) | Spike: PDF pela impressão do Tauri | EPIC-14 | 2 | 🔴 Alta (slice 1, em paralelo) | — | NFR02–NFR04 (insumo para FR12–FR18) | 🔍 Review |
| [US-REL-02](stories/US-REL-02_organizar-secoes-e-copiar-relatorio.md) | Organizar as seções e copiar o relatório | EPIC-14 | 3 | 🔴 Alta (slice 2) | US-REL-01 | FR02 (título de seção editável), FR03, FR11, BR04, BR06, NFR06, NFR07 | 🔍 Review |
| [US-REL-04](stories/US-REL-04_exportar-relatorio-pdf.md) | Exportar o relatório em PDF com acabamento | EPIC-14 | 5 | 🔴 Alta (slice 3) | US-REL-01, US-REL-03 | FR12–FR18, BR03, BR09, BR10, NFR01 (PDF), NFR02–NFR04, NFR07 | 🔍 Review |

> Total EPIC-14: 18 pts (Nível ScrumAIDev 1, branch `feat/relatorios-chat`).
> 25/11/2026: o usuário pediu para implementar o épico inteiro direto, sem sprint planning. Spike do PDF: `docs/resultados/spike-pdf-relatorio-2026-11-25.md` (Chromium verificado; WebKitGTK e janela de impressão do Windows a conferir no app).
> - **Vertical Slice 1 (10 pts):** `US-REL-01` (botão "Mais", formulário, relatório como mensagem da conversa com números atuais, componentes de gráfico/cartão/tabela compartilhados) com `US-REL-03` em paralelo (spike da impressão no Windows e no Linux).
> - **Vertical Slice 2 (3 pts):** `US-REL-02` (ordem e títulos das seções, "Copiar" em Markdown).
> - **Vertical Slice 3 (5 pts):** `US-REL-04` (PDF com visual de documento formal: abertura, tabelas, figuras e quadros numerados com a fonte e apêndice com o SQL), pelo caminho decidido no spike.

---

### 🗂️ EPIC-15 — Exportação de Dados do Chat para CSV e Excel (`.xlsx`) (Aprovado em 26/11/2026)

| ID | Título | Epic | Estimativa (pts) | Prioridade | Depende de | Requisitos | Status |
|----|--------|------|------------------|------------|------------|------------|--------|
| [US-EXP-01](stories/US-EXP-01_gerador-csv-xlsx-comando-rust-exportacao.md) | Gerador CSV/OOXML `.xlsx` (TS puro), comando Rust `exportar_arquivo` e testes unitários | EPIC-15 | 5 | 🔴 Alta (slice 1) | — | FR03–FR07 (núcleo/API), FR08 (Rust + unit), BR01, BR03–BR06, NFR01, NFR03, NFR04, A01–A03 | 🔍 Review |
| [US-EXP-02](stories/US-EXP-02_ui-exportar-chat-toast-testes-e2e.md) | Botão dropdown "Exportar" no Chat, toast de feedback e testes Vitest + Playwright E2E | EPIC-15 | 3 | 🔴 Alta (slice 2) | US-EXP-01 | FR01–FR03, FR07 (UI/toast), FR08 (component + E2E), BR01, BR02, NFR02, NFR05 | 🔍 Review |

> Total EPIC-15: 8 pts (Nível ScrumAIDev 1, branch `feat/exportar-dados-csv-excel`).  
> - **Vertical Slice 1 (5 pts):** `US-EXP-01` (gerador CSV PT-BR + OOXML `.xlsx` em TS puro sem dependências npm/Python, comando Rust `exportar_arquivo` com diálogo nativo "Salvar como..." via `tauri-plugin-dialog = "2"` + fallback navegador, testes Rust e Vitest).  
> - **Vertical Slice 2 (3 pts):** `US-EXP-02` (botão dropdown acessível **"Exportar"** teleportado no Chat, toast de confirmação/erro com cancelamento silencioso e testes Vitest + Playwright E2E).

> 10/11/2026: o usuário pediu para implementar os slices 1 e 2 direto, sem sprint planning ("sem esse trem de sprint"). Status por story na própria story.
>
> Total: 34 pts. Primeiro vertical slice: US-ETL-01 + US-ETL-02 (SRC completo até o bruto, 8 pts). Segundo: US-ETL-03 + US-ETL-06 (primeiro cruzamento SRC ↔ SigPesq, 10 pts). Terceiro: US-ETL-08 (ponte PostgreSQL `unificado` → JSON para as 6 views de fatos, 5 pts). Todas Nível ScrumAIDev 1, sem Spec nem Contract governados.
