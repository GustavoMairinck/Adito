> **Nota:** documento histórico. O projeto se chamava Adito na época; o nome atual é Muninn (ver `Docs/ADR/ADR-0005-nome-muninn.md`). O texto abaixo não foi reescrito.

# Task Breakdown: [US-SQLITE-01] Modelagem DDL em SQLite (42 Tabelas Base 3FN e 6 Fatos Analíticas v2.0)

**Data:** 18/11/2026  
**Participantes:** Equipe de Engenharia de Dados  
**Estimativa total:** 5 Story Points  
**Nivel ScrumAIDev:** 1  
**Spec governada:** N/A (documentação em `Adito/docs/specs/especificacao_ddl_unificado.md` e `Docs/Fatos/PropostaFatosV2.md`)  
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
- **Justificativa do Nivel ScrumAIDev:** Nível 1 — Definição de DDL e schema interno em SQLite sem exposição de API pública ou boundary externo.
- **Justificativa:** Refatoração de scripts DDL para dialeto SQLite nativo e criação de views relacionais.
- **Touch List aplicavel:**
  - `Adito/scripts/sql/00_schema.sql`
  - `Adito/scripts/sql/01_tipos_e_dominios.sql`
  - `Adito/scripts/sql/02_tabelas.sql`
  - `Adito/scripts/sql/03_relacionamentos_e_juncoes.sql`
  - `Adito/scripts/sql/04_fatos_views.sql`
  - `Adito/scripts/sql/99_validacao.sql`
  - `Adito/etl/tests/test_ddl_sqlite.py`
- **Runner BDD a executar:** N/A
- **Validacao de contrato a executar:** N/A
- **Teste de contrato a executar:** N/A
- **Teste de mock a executar:** N/A

---

## Checagem de Principios

Preenchido porque `Behavior change = YES`:
- [x] Esta e a abordagem mais simples que atende a User Story? Sim, migração direta para dialeto SQLite padrão sem dependências C ou compiladores externos.
- [x] A abordagem esta alinhada com `docs/definition_of_done.md` e com as regras de `AGENTS.md`? Sim.
- [x] Nenhuma dependencia externa nova esta sendo introduzida sem aprovacao? Sim, apenas `sqlite3` da biblioteca padrão do Python.
- [x] O escopo respeita a Touch List? Sim.

---

## Tasks Tecnicas

### Backend Tasks

#### [TASK-001] Adaptar DDL 00 e 01 (Tipos e Domínios Ampliados em SQLite)
- **Descricao:** Adaptar `00_schema.sql` (ativando `PRAGMA foreign_keys = ON;`) e `01_tipos_e_dominios.sql` criando tabelas de domínio com `INTEGER PRIMARY KEY AUTOINCREMENT` e incluindo domínios ampliados (`pivic`, `pibic_em`, `jtc`, `picti`, `'EXCLUIDO'`, `'ENSINO_FUNDAMENTAL'`, `'FINANCIAMENTO'`).
- **Status:** Done
- **Estimativa:** 1 hora
- **Criterios de conclusao:**
  - [x] Tabelas de domínio criadas em sintaxe SQLite
  - [x] Domínios ampliados presentes e povoados sem erros
  - [x] Sem comandos específicos de PostgreSQL (`SET search_path`, `CREATE SCHEMA`, `CREATE TYPE ... AS ENUM`)

#### [TASK-002] Adaptar DDL 02 e 03 (Tabelas Base 3FN e Junções em SQLite)
- **Descricao:** Adaptar `02_tabelas.sql` e `03_relacionamentos_e_juncoes.sql` com as 42 tabelas base, preservando chaves primárias `INTEGER PRIMARY KEY AUTOINCREMENT`, subclasses com `REFERENCES superclasse(id) ON DELETE CASCADE`, constraints para antigos ENUMs, e `patente_registro.id_instituicao_depositante` anulável.
- **Status:** Done
- **Estimativa:** 2 horas
- **Criterios de conclusao:**
  - [x] 42 tabelas estruturadas com tipagem SQLite válida
  - [x] Herança relacional íntegra
  - [x] Chave de depositante em `patente_registro` configurada como `NULLABLE`

#### [TASK-003] Criar DDL 04 (6 Fatos Analíticas como VIEWs Dinâmicas em SQLite v2.0)
- **Descricao:** Criar `Adito/scripts/sql/04_fatos_views.sql` contendo o DDL das 6 fatos analíticas (`vfact_*_resolved`) como `CREATE VIEW ... AS SELECT ...` diretamente sobre as 42 tabelas base, com as correções P1 a P12 de `Docs/Fatos/PropostaFatosV2.md`.
- **Status:** Done
- **Estimativa:** 1.5 hora
- **Criterios de conclusao:**
  - [x] 6 VIEWs criadas em sintaxe pura SQLite 3
  - [x] Todas as 12 correções de negócio (P1 a P12) implementadas
  - [x] Grão 1:1 rigorosamente preservado

---

### Testing Tasks

#### [TASK-004] Validar Integridade e Execução Completa em SQLite
- **Descricao:** Criar e rodar script de teste automatizado carregando `00`, `01`, `02`, `03` e `04` em um banco SQLite in-memory com `PRAGMA foreign_keys = ON`, verificando tabelas, views, integridade e ausência de erros.
- **Status:** Done
- **Estimativa:** 0.5 hora
- **Criterios de conclusao:**
  - [x] Script executa com retorno de código 0 (`test_ddl_sqlite.py`)
  - [x] Todas as 42 tabelas e 6 views são inspecionáveis via `sqlite_master`
  - [x] `PRAGMA foreign_key_check` limpo (0 erros)
