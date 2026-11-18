# User Story: [US-SQLITE-01] Modelagem DDL em SQLite (42 Tabelas Base 3FN e 6 Fatos Analíticas v2.0)

**Epic:** EPIC-08: Migração da Arquitetura de Dados Acadêmicos para 100% SQLite (dados.db)  
**GitHub Epic Issue:** -  
**GitHub US Issue:** -  
**Prioridade:** Alta (Slice 1)  
**Story Points:** 5  
**Sprint:** Sprint 01  
**Status:** Completed  
**Behavior Change Esperado:** YES  

---

## Historia

**Como** Engenheiro de Dados do Adito  
**Eu quero** definir os scripts DDL em dialeto SQLite nativo para as 42 tabelas relacionais em 3FN e para as 6 tabelas fato analíticas em arquivo dedicado `04_fatos_views.sql`  
**Para que** a estrutura relacional do banco seja estritamente fiel ao Modelo ASTA e as 6 fatos incorporem todas as correções de negócio (P1 a P12 de `PropostaFatosV2.md`) sem sintaxes proprietárias do PostgreSQL/DuckDB.

### Contexto Adicional

O DDL legada era segmentada para PostgreSQL com tipos específicos (`VARCHAR`, `TIMESTAMP WITH TIME ZONE`, `BIGINT`, `ENUM`, `BOOLEAN`). Na migração para 100% SQLite (`dados.db`), scripts DDL limpos definem as 42 tabelas do `ModeloClassesUnificado.asta` consumidas pelas fatos, com integridade referencial (`FOREIGN KEY`), constraints e domínios ampliados para evitar nulos. Além disso, as 6 fatos analíticas foram consolidadas em `Adito/scripts/sql/04_fatos_views.sql` como VIEWS dinâmicas com sintaxe SQLite 3 pura.

### Pontos de Esclarecimento

Nenhum ponto pendente. As especificações SQL das 6 fatos e o mapeamento dos domínios estão formalizados em `Docs/Fatos/PropostaFatosV2.md` e `Docs/Fatos/DocumentoSolucionalFatos.md`.

---

## Criterios de Aceitacao

- [x] **Criterio 1 (DDL 3FN SQLite):** Os scripts DDL em `Adito/scripts/sql/01_tipos_e_dominios.sql` a `03_relacionamentos_e_juncoes.sql` criam com sucesso as 42 tabelas relacionais em 3FN com chaves primárias, chaves estrangeiras com `ON DELETE CASCADE` nas subclasses e integridade referencial ativa.
- [x] **Criterio 2 (Domínios Completos e Depositante Nullable):** As constraints e tabelas de domínio incluem `'pivic'`, `'pibic_em'`, `'jtc'`, `'picti'` (em `programa`), `'EXCLUIDO'` (em `situacao_grupo`), `'ENSINO_FUNDAMENTAL'` (em `nivel_treinamento`) e `'FINANCIAMENTO'` (em `tipo_apoio_financiamento`). O campo `patente_registro.id_instituicao_depositante` é definido como anulável (`NULLABLE`).
- [x] **Criterio 3 (DDL Fatos v2.0):** O arquivo `Adito/scripts/sql/04_fatos_views.sql` contém a definição DDL completa em dialeto SQLite das 6 tabelas fato analíticas como views relacionais dinâmicas em conformidade estrita com a Seção 4 do `Docs/Fatos/PropostaFatosV2.md`.
- [x] **Criterio 4 (Correções P1 a P12 nas Fatos):**
  - `vfact_producao_cientifica_resolved` inclui `instituicao_vinculo`, `campus` restrito ao Ifes, `qtd_autorias`, `flag_obra_unica`, `flag_patente_software` e `flag_software_sem_patente`.
  - `vfact_grupo_pesquisa_membro_resolved` calcula `flag_lider` via `EXISTS` em `lideranca_grupo_pesquisa` OU menção em papel, e `tempo_participacao_dias` via `julianday()` protegido.
  - `vfact_orientacao_bolsa_resolved` calcula `duracao_meses_efetiva` e `investimento_total_estimado` com corte na data de cancelamento, e expõe `investimento_previsto_original`.
  - `vfact_projeto_pesquisa_resolved` expõe `parceiros_demandantes`, `origem_registro` e `flag_projeto_completo`.
  - Fatos de extensão pré-agregam `acao_campus` e `fomento_acao` via subqueries com `GROUP_CONCAT` para blindar contra *fan-out*.
- [x] **Criterio 5 (Execução Sem Erros):** Todos os scripts SQL executam sequencialmente (`00` → `01` → `02` → `03` → `04` → `99`) em uma base SQLite vazia sem nenhum erro de sintaxe ou violação de constraints, coberto por teste automatizado `test_ddl_sqlite.py`.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Definição interna de schema relacional e analítico SQLite sem exposição de boundary HTTP externo.
- **US exige Spec governada?** Nao
- **Justificativa da Spec:** A especificação técnica de referência é o DDL unificado já versionado em `Adito/docs/specs/especificacao_ddl_unificado.md` e a especificação `Docs/Fatos/PropostaFatosV2.md`.
- **Spec prevista:** N/A
- **US exige Contract governado?** Nao
- **Justificativa do Contract:** Mudança interna de persistência e schema de banco de dados.
- **Contract previsto:** N/A
- **Padrao de erro aplicavel:** N/A
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** N/A
- **Touch List preliminar:**
  - `Adito/scripts/sql/00_schema.sql`
  - `Adito/scripts/sql/01_tipos_e_dominios.sql`
  - `Adito/scripts/sql/02_tabelas.sql`
  - `Adito/scripts/sql/03_relacionamentos_e_juncoes.sql`
  - `Adito/scripts/sql/04_fatos_views.sql`
  - `Adito/scripts/sql/99_validacao.sql`
  - `Adito/etl/tests/test_ddl_sqlite.py`
- **Requisitos Cobertos:** `FR01`, `FR02`, `FR04`, `FR05`, `FR06`, `FR07`, `FR08`, `FR09`, `FR10`, `BR01..BR08`, `NFR04`, `NFR06`.

---

## Notas Tecnicas

### Arquitetura
- **Dialeto SQL:** SQLite 3 compatível.
- **Conversão de Tipos:** `SERIAL` / `BIGSERIAL` → `INTEGER PRIMARY KEY AUTOINCREMENT`; `VARCHAR` / `TEXT` → `TEXT`; `TIMESTAMP` / `DATE` → `TEXT` (ISO-8601); `NUMERIC` / `DECIMAL` → `REAL`; `BOOLEAN` → `INTEGER`.
- **Datas e Agregações:** `strftime('%Y', col)`, `julianday()`, `GROUP_CONCAT()`, `COALESCE()`.

### Dependencias
- Nenhuma dependência externa.

### Consideracoes de Performance
- Os DDLs das tabelas base e fatos preveem índices nas chaves de junção (`id_origem`, chaves estrangeiras) para performance analítica instantânea.

---

## Plano de Testes

### Testes Unitarios / Script de Teste
- [x] Executar script de validação de DDL via Python `sqlite3.connect(':memory:')`:
  - Carregar `00`, `01`, `02`, `03` e `04`;
  - Verificar criação de todas as 42 tabelas base e 6 fatos;
  - Testar integridade de chaves estrangeiras (`PRAGMA foreign_key_check`);
  - Testar compilação das 6 views com `test_ddl_sqlite.py`.

---

## Tasks (Breakdown)

- [x] **[TASK-001]** Converter e segmentar DDLs das 42 tabelas base em `Adito/scripts/sql/` para sintaxe SQLite, com constraints e domínios ampliados.
- [x] **[TASK-002]** Ajustar `patente_registro.id_instituicao_depositante` para permitir nulos no DDL.
- [x] **[TASK-003]** Criar `Adito/scripts/sql/04_fatos_views.sql` contendo o DDL SQLite das 6 fatos analíticas com as correções P1 a P12 de `PropostaFatosV2.md`.
- [x] **[TASK-004]** Validar sintaxe completa em banco SQLite in-memory com `PRAGMA foreign_keys = ON` via pytest.
