> **Nota:** documento histórico. O projeto se chamava Adito na época; o nome atual é Muninn (ver `Docs/ADR/ADR-0005-nome-muninn.md`). O texto abaixo não foi reescrito.

# Sprint Planning: Sprint 01 — Migração 100% SQLite e Camada Analítica em Views Dinâmicas

**Sprint:** 01  
**Data de Inicio:** 18/11/2026  
**Data de Termino:** 18/11/2026 (Concluída)  
**Capacidade planejada:** 18 Story Points (EPIC-08 completo: Slices 1 e 2)  
**Meta da Sprint (Sprint Goal):** Migrar a persistência e camada analítica de dados acadêmicos do Adito para 100% SQLite (`dados.db`), unificando 42 tabelas relacionais em 3FN e 6 views dinâmicas analíticas (v2.0, 100% OLTP), com pipeline de carga direta em Python, conexão somente-leitura com authorizer, busca sem acento resiliente e descomissionamento total de legados (Docker, Postgres, DuckDB).

---

## User Stories da Sprint

### [US-SQLITE-01] Modelagem DDL em SQLite (42 Tabelas Base 3FN e 6 Fatos Analíticas v2.0)

- **Prioridade:** 🔴 Alta (Slice 1)
- **Story Points:** 5
- **Assignee:** Equipe de Engenharia de Dados
- **Nivel ScrumAIDev:** 1
- **Status:** Completed
- **Criterios de Aceitacao:**
  - [x] **Critério 1:** Scripts DDL em `Adito/scripts/sql/01_tipos_e_dominios.sql` a `03` criam as 42 tabelas relacionais em 3FN em SQLite com `PRAGMA foreign_keys = ON` e herança referencial íntegra (`ON DELETE CASCADE`).
  - [x] **Critério 2:** Constraints e domínios incluem `'pivic'`, `'pibic_em'`, `'jtc'`, `'picti'`, `'EXCLUIDO'`, `'ENSINO_FUNDAMENTAL'` e `'FINANCIAMENTO'`; `patente_registro.id_instituicao_depositante` é definido como anulável (`NULLABLE`).
  - [x] **Critério 3:** Arquivo `Adito/scripts/sql/04_fatos_views.sql` contém a definição DDL completa em dialeto SQLite das 6 tabelas fato analíticas como views dinâmicas em conformidade com `Docs/Fatos/PropostaFatosV2.md`.
  - [x] **Critério 4:** Fatos incluem: `instituicao_vinculo`, `campus` restrito a Ifes, `qtd_autorias`, `flag_obra_unica`, `flag_patente_software`, `flag_software_sem_patente`, `flag_lider` (EXISTS + papel), `duracao_meses_efetiva` com cancelamento, `parceiros_demandantes`, `origem_registro`, `flag_projeto_completo` e subqueries anti-fan-out em extensão.
  - [x] **Critério 5:** Execução sequencial dos scripts SQL (`00..04`) roda em base SQLite limpa com zero erros, validada por teste automatizado `test_ddl_sqlite.py`.

---

### [US-SQLITE-02] Pipeline de Carga Direta em Python/SQLite (`popular_banco.py`), Criação das VIEWs e Validação

- **Prioridade:** 🔴 Alta (Slice 1)
- **Story Points:** 5
- **Assignee:** Equipe de Backend / ETL
- **Nivel ScrumAIDev:** 1
- **Status:** Completed
- **Criterios de Aceitacao:**
  - [x] **Critério 1:** `python scripts/popular_banco.py` (e `adito-etl popular-banco`) executa diretamente via `sqlite3` nativo, sem exigir Docker, `psql` ou arquivos JSON intermediários, gerando `Adito/app/data/dados.db`.
  - [x] **Critério 2:** Processo completo de criação, carga, criação de VIEWs e validação conclui em tempo < 5 segundos (1.08s realizado), gerando banco com tamanho entre 2 MB e 8 MB (2.83 MB gerado).
  - [x] **Critério 3:** Carga prioriza campus Ifes no pesquisador, grava patentes/softwares do Lattes em `patente_registro` e mapeia situação `'Excluído'` do CNPq para `'EXCLUIDO'`.
  - [x] **Critério 4:** As 6 fatos analíticas (`vfact_*_resolved`) são compiladas como views relacionais dinâmicas diretamente sobre as 42 tabelas base no `dados.db` (100% OLTP).
  - [x] **Critério 5:** Validação pós-carga automatizada confirma: 0 violações em `PRAGMA foreign_key_check`, 0 violações de PII e sanidade estrutural das métricas P1-P12.
  - [x] **Critério 6:** Script `Adito/scripts/ver_dados.py` adaptado para exibir tabelas e views analíticas diretamente do SQLite.

---

### [US-SQLITE-03] Adaptação do Backend Núcleo para SQLite (Datastore Somente-Leitura, Authorizer, Custom LIKE e Transpilação)

- **Prioridade:** 🔴 Alta (Slice 2)
- **Story Points:** 5
- **Assignee:** Equipe de Backend
- **Nivel ScrumAIDev:** 2
- **Status:** Completed
- **Criterios de Aceitacao:**
  - [x] **Critério 1:** `core/datastore.py` abre `dados.db` usando URI estrita `file:dados.db?mode=ro` e executa `PRAGMA query_only = ON`. Tentativas de escrita falham em nível de driver.
  - [x] **Critério 2:** `conn.set_authorizer` autoriza exclusivamente leitura e funções, bloqueando imediatamente comandos de modificação (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `ATTACH`) e pragmas de escrita.
  - [x] **Critério 3:** Função customizada `LIKE` registrada via `conn.create_function("like", 2, ...)` normaliza caracteres com `unicodedata.normalize('NFD')`, garantindo que filtros com ou sem acentuação retornem os mesmos registros.
  - [x] **Critério 4:** Queries recebidas pelo datastore são transpiladas automaticamente (`sqlglot.transpile(sql, read="duckdb", write="sqlite")`) quando contiverem sintaxes legadas (`ILIKE`, `::TYPE`, `EXTRACT`).
  - [x] **Critério 5:** `core/contexts.py` utiliza `PRAGMA table_info(...)` para introspecção de schema; endpoints RPC (`dashboard.py`, `explorer.py`, `admin.py`) operam com sucesso sobre o novo datastore.
  - [x] **Critério 6:** Os arquivos `views.json`, `rules.md` e `examples.json` em `Adito/app/contexts/pesquisa-extensao-ifes/` atualizados para dialeto SQLite e documentando os novos campos da especificação v2.0.

---

### [US-SQLITE-04] Descomissionamento de Legados, Atualização de Testes e Especificações Técnicas

- **Prioridade:** 🟡 Média (Slice 2)
- **Story Points:** 3
- **Assignee:** Equipe de Engenharia de Software
- **Nivel ScrumAIDev:** 1
- **Status:** Completed
- **Criterios de Aceitacao:**
  - [x] **Critério 1:** Arquivos obsoletos removidos (`docker-compose.yml`, `recriar_banco.sh`, `exportar_json.py`, `gerar_duckdb.py`, `test_exportar_json.py`, `dados.duckdb*`).
  - [x] **Critério 2:** O pacote `duckdb` removido de `Adito/app/backend/requirements.txt` e manifestos de dependência.
  - [x] **Critério 3:** Testes em `core/tests.py` (31/31), `core/test_datastore_sqlite.py` (11/11), `scripts/teste_contrato.py` (51/51) e `scripts/teste_stdio.py` (14/14) passam com 100% de sucesso sem DuckDB.
  - [x] **Critério 4:** Documentação técnica atualizada em `Adito/scripts/README.md` e `Adito/docs/specs/especificacao_ddl_unificado.md`.

---

## Definition of Done (Sprint 01 Completa)

- [x] Código DDL e Python implementado conforme critérios de aceitação
- [x] Geração do `dados.db` conclui em < 5 segundos sem Docker (1.08s realizado)
- [x] Integridade referencial com 0 violações em `PRAGMA foreign_key_check`
- [x] 0 violações de dados sensíveis na varredura anti-PII
- [x] 6 fatos analíticas ativas como views relacionais dinâmicas (100% OLTP)
- [x] Defesa em profundidade no backend: modo somente-leitura, authorizer, busca sem acento e AST policy
- [x] Arquivos obsoletos (Docker, PostgreSQL, JSON intermediário, DuckDB) removidos
- [x] 100% das 4 suítes de testes automatizados aprovadas:
  - `Adito/etl/tests`: 69/69 passed (100%)
  - `core.test_datastore_sqlite`: 11/11 passed (100%)
  - `core.tests`: 31/31 passed (100%)
  - `teste_contrato.py`: 51/51 checks passed (100%)
  - `teste_stdio.py`: 14/14 checks passed (100%)
- [x] Documentação técnica atualizada (`README.md`, `especificacao_ddl_unificado.md`, `PropostaFatosV2.md`)
- [x] Branch temática `fix/altera-arquitetura-banco` íntegra sem commits diretos em main
