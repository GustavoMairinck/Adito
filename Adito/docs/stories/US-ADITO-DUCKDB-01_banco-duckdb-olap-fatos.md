# US-ADITO-DUCKDB-01: Banco analítico DuckDB OLAP com as 6 tabelas fato e adaptação do Adito

**ID:** US-ADITO-DUCKDB-01
**Epic:** EPIC-07 — ETL e Banco Analítico do Adito
**Sprint:** Sem sprint (execução direta, 1 etapa)
**Prioridade:** 🔴 Alta
**Estimativa:** 8 Story Points
**Status:** 🔍 Review

---

## 📖 User Story

> **Como** membro da equipe de dados e usuário do Adito no Campus Serra,
> **Quero** gerar o banco analítico DuckDB OLAP (`dados.duckdb`) a partir dos 41 JSONs exportados com as 6 tabelas fato materializadas (`vfact_*_resolved`) e adaptar o backend do Adito para consultar esse banco em modo somente-leitura sob o contexto `pesquisa-extensao-ifes`,
> **Para que** o Oráculo responda às perguntas de pesquisa e extensão em alta velocidade OLAP diretamente a partir das 6 tabelas fato, sem depender de servidor PostgreSQL e respeitando as regras de segurança e LGPD.

---

## 🎯 Contexto e Justificativa

As 41 tabelas base das 6 views/fatos definidas em `Docs/Fatos/PropostaFatos.md` já foram exportadas do `oraculo_postgres_unificado` para `Adito/etl/saida/json/` (`<tabela>.json` + `manifesto.json`). Porém, o backend do Adito (`Adito/app/backend/`) ainda consulta um banco SQLite (`dados.db`) com dados fictícios (`exemplo-vendas`).

Esta story entrega em 1 etapa:
1. O script `Adito/scripts/gerar_duckdb.py` que lê `manifesto.json` + 41 JSONs, carrega as 41 tabelas em `unificado.<tabela>` e **materializa as 6 tabelas fato (`CREATE TABLE main.vfact_*_resolved AS SELECT ...`)** em formato colunar nativo no DuckDB (`Adito/app/data/dados.duckdb`).
2. A adaptação de `Adito/app/backend/` (`datastore.py`, `contexts.py`, `sql_security.py`, `agent.py`, `graph.py`, `tool.py`, `nodes/sql_validator.py`, `analytics_index/services.py` e `dashboard/views.py`) para usar **DuckDB** (`read_only=True`, dialeto `duckdb` no `sqlglot`, bloqueio de funções `read_*` e de `sensitive_columns`), mantendo `app.db` em SQLite.
3. O contexto `Adito/app/contexts/pesquisa-extensao-ifes/` (`views.json`, `rules.md`, `examples.json`) ativo e a desativação de `Adito/app/contexts/exemplo-vendas/` (`"ativo": false`).

**Rastreabilidade:**
- **Discovery:** `Adito/docs/discovery/adito.md` (rev. 5, `PROBLEM_READY`)
- **Requirements:** `Adito/docs/requirements/adito-etl.md` (`FR14`, `FR15`, `FR16`, `FR17`, `FR18`, `BR07`, `BR08`, `BR09`, `NFR07`, `NFR08`, `NFR09`)

---

## ✅ Critérios de Aceitação (Formato Gherkin)

### Cenário 1: Geração do `dados.duckdb` com as 6 tabelas fato materializadas (Caminho Feliz)
- **DADO** que os 41 arquivos `<tabela>.json` e o `manifesto.json` existem em `Adito/etl/saida/json/`
- **QUANDO** executo `python Adito/scripts/gerar_duckdb.py`
- **ENTÃO** o arquivo `Adito/app/data/dados.duckdb` é criado com as 41 tabelas em `unificado` (batendo `row_count` com o `manifesto.json`)
- **E** as 6 tabelas fato são materializadas como `TABLE` no schema `main` (e views equivalentes em `unificado`) com as contagens exatas:
  - `vfact_extensao_acao_resolved`: `207`
  - `vfact_extensao_participacao_resolved`: `6.741`
  - `vfact_projeto_pesquisa_resolved`: `236`
  - `vfact_orientacao_bolsa_resolved`: `1.203`
  - `vfact_producao_cientifica_resolved`: `1.232`
  - `vfact_grupo_pesquisa_membro_resolved`: `553`

### Cenário 2: Segurança SQL no dialeto DuckDB e proteção LGPD de colunas sensíveis
- **DADO** que o contexto `pesquisa-extensao-ifes` define as 6 tabelas fato como `allowed_tables` e declara `sensitive_columns` (`*cpf*`, `*email*`)
- **QUANDO** uma query SQL passa por `validate_read_only_sql` e `connect_dados(policy)`
- **ENTÃO** consultas `SELECT` analíticas válidas no dialeto DuckDB (`ILIKE`, `EXTRACT`, `CAST`/`::`, `COUNT(DISTINCT ...)`) sobre as 6 tabelas fato são aprovadas e executadas em modo somente-leitura
- **E** qualquer comando de escrita/sistema (`COPY`, `ATTACH`, `INSTALL`, `LOAD`, `PRAGMA`, `SET`, `CALL`), função de leitura de arquivos (`read_csv*`, `read_parquet*`, `read_json*`, `parquet_scan`), acesso às 41 tabelas base fora da whitelist ou referência a `sensitive_columns` é bloqueado com `SQLSecurityError`
- **E** a conexão DuckDB (`connect_dados`) aplica defesa em profundidade nativa no motor (`enable_external_access=False` e `lock_configuration=True`), bloqueando no banco qualquer leitura de arquivos do sistema operacional ou URLs e impedindo que o SQL reative a opção, inclusive em chamadas sem `ReadPolicy` (ex: painéis).

### Cenário 3: Ativação do contexto `pesquisa-extensao-ifes` e desativação de `exemplo-vendas`
- **DADO** que `Adito/app/contexts/pesquisa-extensao-ifes/` possui `views.json`, `rules.md` e `examples.json` e `Adito/app/contexts/exemplo-vendas/views.json` possui `"ativo": false`
- **QUANDO** `load_context_dir` / `sync_from_filesystem` é executado apontando para `dados.duckdb`
- **ENTÃO** o contexto `pesquisa-extensao-ifes` fica com `is_active = True` sem erros de validação (`errors == []`)
- **E** o contexto `exemplo-vendas` fica com `is_active = False` sem gerar erros espúrios.

---

## 🔧 Notas Técnicas e Restrições
- **Nível ScrumAIDev:** Nível 1 (sem Spec/Contract/BDD externos governados).
- **Incertezas:** Nenhuma (`0` tags `[PRECISA CLARIFICAR]`).
- **LGPD:** Nenhum nome real de pessoa da base em código, testes, `examples.json` ou documentação; `sensitive_columns` ocultas no DDL enviado à LLM e bloqueadas no validador SQL.
- **Isolamento:** `app.db` permanece em SQLite; apenas `dados.duckdb` usa DuckDB.

---

## 📋 Definition of Done (DoD)
- [x] `Adito/scripts/gerar_duckdb.py` implementado e executado gerando `Adito/app/data/dados.duckdb` com as 6 tabelas fato materializadas batendo as contagens exatas
- [x] Camada analítica de `Adito/app/backend/` adaptada para DuckDB (`datastore.py`, `contexts.py`, `sql_security.py`, `bi_agent`, `analytics_index`, `dashboard`)
- [x] Contexto `Adito/app/contexts/pesquisa-extensao-ifes/` criado (`views.json`, `rules.md`, `examples.json`) e `exemplo-vendas` desativado (`"ativo": false`)
- [x] Testes automatizados criados e passando (`pytest` / `manage.py test`)
- [x] Documentação atualizada em `Adito/scripts/README.md`
