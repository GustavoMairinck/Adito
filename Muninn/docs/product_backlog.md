# Product Backlog — Muninn

Backlog do Muninn no monorepo. As stories do porte desktop (US-001 a US-015) estão indexadas em [README.md](README.md); aqui fica o que veio depois do Discovery rev. 4.

## Epics

### EPIC-07: ETL do Muninn
Extração do bruto de SRC, SigPesq, CNPq/DGP e Lattes, cruzamento das bases por nome normalizado em `Muninn/etl/`. Origem: `docs/discovery/muninn.md` (rev. 4 e rev. 5) e `docs/requirements/muninn-etl.md` (rev. 1 e rev. 2).
- **Stories**: US-ETL-01 a US-ETL-07 (US-ETL-08 e US-ADITO-DUCKDB-01 substituídas pelo EPIC-08).

### EPIC-08: Migração da Arquitetura de Dados Acadêmicos para 100% SQLite (dados.db)
Unificação da camada relacional (42 tabelas 3FN do Modelo ASTA) e da camada analítica (6 VIEWs de fatos dinâmicas) em um único banco SQLite (`dados.db`) gerado diretamente por script Python (`sqlite3`), eliminando Docker, PostgreSQL, JSONs intermediários e DuckDB, e adaptando o backend núcleo com segurança estrita (`mode=ro`, `set_authorizer`), busca sem acentos e transpilação `sqlglot`. Origem: `docs/discovery/migracao-arquitetura-sqlite.md`, `docs/requirements/migracao-arquitetura-sqlite.md` e ADRs 0001 a 0004.
- **Stories**: US-SQLITE-01 a US-SQLITE-04.

### EPIC-09: Produtividade de Desenvolvimento & Automação Local (DevEx)
Criação de ponto de entrada único via Makefile na raiz do monorepo para unificar setup de ambientes virtuais e dependências, reconstrução do banco relacional com fatos em < 5s, inicialização do app desktop, execução consolidada das suítes de testes automatizados e resiliência de onboarding em ambientes limpos (Issues #83, #84, #87 e #88). Origem: `docs/discovery/automacao-makefiles-devex.md`, `docs/requirements/automacao-makefiles-devex.md`, `Muninn/docs/discovery/correcao-onboarding-makefile-desktop.md` e `Muninn/docs/requirements/correcao-onboarding-makefile-desktop.md`.
- **Stories**: US-DEVEX-01 a US-DEVEX-05.

### EPIC-10: Garantia de Qualidade — Testes Automatizados, Performance e Avaliação da IA (Issue #71)
Estruturação da suíte completa de qualidade do Muninn: testes unitários no frontend Vue (Vitest + Vue Test Utils), testes E2E híbridos com Playwright (mock de `__TAURI_INTERNALS__` + bridge live com `desktop_server.py`), benchmark de performance/latência do núcleo local sobre o `dados.db` real com SLOs e avaliação híbrida de acurácia da IA (SQL gabarito executada + LLM-as-a-Judge) com dataset independente. Origem: `Muninn/docs/discovery/testes-automatizados-qualidade.md` e `Muninn/docs/requirements/testes-automatizados-qualidade.md`.
- **Stories**: US-QA-01 a US-QA-04.

---

## User Stories Priorizadas

### 🗂️ EPIC-07 — ETL do Muninn (aprovado em 10/11/2026)

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

> 10/11/2026: o usuário pediu para implementar os slices 1 e 2 direto, sem sprint planning ("sem esse trem de sprint"). Status por story na própria story.
>
> Total: 34 pts. Primeiro vertical slice: US-ETL-01 + US-ETL-02 (SRC completo até o bruto, 8 pts). Segundo: US-ETL-03 + US-ETL-06 (primeiro cruzamento SRC ↔ SigPesq, 10 pts). Terceiro: US-ETL-08 (ponte PostgreSQL `unificado` → JSON para as 6 views de fatos, 5 pts). Todas Nível ScrumAIDev 1, sem Spec nem Contract governados.
