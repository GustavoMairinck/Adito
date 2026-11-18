# Task Breakdown: [US-SQLITE-03] Adaptação do Backend Núcleo para SQLite (Datastore Somente-Leitura, Authorizer, Custom LIKE e Transpilação)

**Data:** 18/11/2026  
**Participantes:** Equipe de Engenharia de Dados & Backend  
**Estimativa total:** 5 Story Points  
**Nivel ScrumAIDev:** 2  
**Spec governada:** N/A  
**Contract governado:** N/A  
**Padrao de erro:** N/A  
**BDD associado:** N/A  
**Behavior change:** YES  
**GitHub Epic Issue:** -  
**GitHub Parent US Issue:** -  
**GitHub Sprint Container:** Sprint: 01 / Sprint 01  

---

## Pre-Flight de Governanca

- **US exige Spec governada?** Nao
- **US exige Contract governado?** Nao
- **Justificativa do Nivel ScrumAIDev:** Nível 2 — Alteração da camada de acesso a dados (datastore) e contratos de introspecção consumidos por RPCs e agentes.
- **Justificativa:** Transição do driver DuckDB para SQLite nativo com authorizer e transpilação de queries.
- **Touch List aplicavel:**
  - `Adito/app/backend/nucleo/core/datastore.py`
  - `Adito/app/backend/nucleo/core/contexts.py`
  - `Adito/app/backend/nucleo/rpc/explorer.py`
  - `Adito/app/backend/nucleo/rpc/dashboard.py`
  - `Adito/app/backend/nucleo/rpc/admin.py`
  - `Adito/app/backend/nucleo/agents/bi_agent/agent.py`
  - `Adito/app/backend/nucleo/agents/bi_agent/sql_security.py`
  - `Adito/app/contexts/pesquisa-extensao-ifes/views.json`
  - `Adito/app/contexts/pesquisa-extensao-ifes/rules.md`
  - `Adito/app/contexts/pesquisa-extensao-ifes/examples.json`
- **Runner BDD a executar:** N/A
- **Validacao de contrato a executar:** N/A
- **Teste de contrato a executar:** N/A
- **Teste de mock a executar:** N/A

---

## Checagem de Principios

Preenchido porque `Behavior change = YES`:
- [x] Esta e a abordagem mais simples que atende a User Story? Sim, uso de `sqlite3` built-in, URI `mode=ro`, authorizer nativo e transpilação automática com `sqlglot`.
- [x] A abordagem esta alinhada com `docs/definition_of_done.md` e com as regras de `AGENTS.md`? Sim.
- [x] Nenhuma dependencia externa nova esta sendo introduzida sem aprovacao? Sim, `sqlglot` já existe nas dependências.
- [x] O escopo respeita a Touch List? Sim.

---

## Tasks Tecnicas

### Backend Tasks

#### [TASK-001] Adaptar `core/datastore.py` para SQLite Somente-Leitura e Authorizer
- **Descricao:** Conectar em `dados.db` via `file:dados.db?mode=ro`, aplicar `PRAGMA query_only = ON`, autorizador bloqueando DML/DDL/ATTACH e registrar custom `LIKE` com normalização NFD sem acento.
- **Status:** Completed
- **Estimativa:** 1.5 hora
- **Criterios de conclusao:**
  - [x] `connect_dados()` abre `dados.db` em modo estritamente read-only
  - [x] Authorizer bloqueia qualquer mutação
  - [x] `LIKE` opera case-insensitive e acento-insensível
  - [x] Transpilação transparente de `duckdb` para `sqlite` via `sqlglot`

#### [TASK-002] Adaptar Introspecção de Schema em `core/contexts.py`
- **Descricao:** Substituir comandos `DESCRIBE` por `PRAGMA table_info` e atualizar `BASE_SQL_RULES` para dialeto SQLite.
- **Status:** Completed
- **Estimativa:** 0.5 hora
- **Criterios de conclusao:**
  - [x] `view_columns()` introspecta colunas via `PRAGMA table_info`
  - [x] Regras base de SQL instruem o LLM em SQLite 3

#### [TASK-003] Atualizar Endpoints RPC (`dashboard.py`, `explorer.py`, `admin.py`)
- **Descricao:** Ajustar queries em `dashboard.py` (funções de data `strftime`, agregações `json_group_array`), `explorer.py` (usar `LIKE` sem acento) e `admin.py` (status de `dados.db`).
- **Status:** Completed
- **Estimativa:** 1 hora
- **Criterios de conclusao:**
  - [x] `dashboard.kpis`, `dashboard.charts`, `dashboard.top_projects` respondem com sucesso
  - [x] `explorer.tables` e `explorer.rows` funcionam sem erro
  - [x] `admin.system_status` monitora `dados.db`

#### [TASK-004] Atualizar Metadados do Contexto Acadêmico
- **Descricao:** Atualizar `views.json`, `rules.md` e `examples.json` em `Adito/app/contexts/pesquisa-extensao-ifes/` com os novos campos da v2.0 e sintaxe SQLite.
- **Status:** Completed
- **Estimativa:** 1 hora
- **Criterios de conclusao:**
  - [x] `views.json` inclui novas colunas (`qtd_autorias`, `flag_obra_unica`, etc.)
  - [x] `rules.md` e `examples.json` sem sintaxes inválidas (100% SQLite testado)

---

## Testing Tasks

#### [TASK-005] Testes de Integração e Segurança do Datastore SQLite
- **Descricao:** Criar testes automatizados validando modo somente-leitura, autorizador, custom LIKE e RPCs no núcleo.
- **Status:** Completed
- **Estimativa:** 1 hora
- **Criterios de conclusao:**
  - [x] Testes cobrem bloqueio de mutações e injeções
  - [x] Testes cobrem busca com e sem acento
  - [x] Todos os testes passam 100%
