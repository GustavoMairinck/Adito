# Task Breakdown: [US-SQLITE-04] Descomissionamento de Legados, Atualização de Testes e Especificações Técnicas

**Data:** 18/11/2026  
**Participantes:** Equipe de Engenharia de Dados & Backend  
**Estimativa total:** 3 Story Points  
**Nivel ScrumAIDev:** 1  
**Spec governada:** N/A  
**Contract governado:** N/A  
**Padrao de erro:** N/A  
**BDD associado:** N/A  
**Behavior change:** NO  
**GitHub Epic Issue:** -  
**GitHub Parent US Issue:** -  
**GitHub Sprint Container:** Sprint: 01 / Sprint 01  

---

## Pre-Flight de Governanca

- **US exige Spec governada?** Nao
- **US exige Contract governado?** Nao
- **Justificativa do Nivel ScrumAIDev:** Nível 1 — Tarefa interna de limpeza de arquivos legados, atualização de testes e documentação.
- **Justificativa:** Remoção de arquivos legados do PostgreSQL, Docker, DuckDB e adequação da suite de testes para SQLite nativo.
- **Touch List aplicavel:**
  - `Adito/scripts/docker-compose.yml` (remoção)
  - `Adito/scripts/recriar_banco.sh` (remoção)
  - `Adito/scripts/exportar_json.py` (remoção)
  - `Adito/scripts/gerar_duckdb.py` (remoção)
  - `Adito/etl/tests/test_exportar_json.py` (remoção)
  - `Adito/app/backend/requirements.txt`
  - `Adito/app/backend/nucleo/core/tests.py`
  - `Adito/app/scripts/teste_contrato.py`
  - `Adito/app/scripts/teste_stdio.py`
  - `Adito/scripts/README.md`
  - `Adito/docs/specs/especificacao_ddl_unificado.md`
- **Runner BDD a executar:** N/A
- **Validacao de contrato a executar:** N/A
- **Teste de contrato a executar:** N/A
- **Teste de mock a executar:** N/A

---

## Tasks Tecnicas

### Cleanup Tasks

#### [TASK-001] Remover Arquivos Legados (PostgreSQL, Docker, JSON, DuckDB)
- **Descricao:** Excluir scripts e manifestos que não fazem mais parte da arquitetura SQLite unificada.
- **Status:** Completed
- **Estimativa:** 0.5 hora
- **Criterios de conclusao:**
  - [x] Removido `Adito/scripts/docker-compose.yml`
  - [x] Removido `Adito/scripts/recriar_banco.sh`
  - [x] Removido `Adito/scripts/exportar_json.py`
  - [x] Removido `Adito/scripts/gerar_duckdb.py`
  - [x] Removido `Adito/etl/tests/test_exportar_json.py`
  - [x] Removido `Adito/app/data/dados.duckdb` (e arquivos wal/tmp)

#### [TASK-002] Remover Dependência do DuckDB dos Manifestos
- **Descricao:** Remover `duckdb` de `Adito/app/backend/requirements.txt` ou outros manifestos de dependências do backend.
- **Status:** Completed
- **Estimativa:** 0.5 hora
- **Criterios de conclusao:**
  - [x] `duckdb` removido de manifestos de dependência (`Adito/app/backend/requirements.txt`)
  - [x] Aplicação executa sem exigir `duckdb`

---

### Testing & Refactoring Tasks

#### [TASK-003] Adaptar `core/tests.py`, `teste_contrato.py` e `teste_stdio.py`
- **Descricao:** Refatorar a suite de testes automatizados do núcleo (`core/tests.py`) para validar `dados.db` SQLite sintético e real, sem depender de `gerar_duckdb` ou da biblioteca `duckdb`.
- **Status:** Completed
- **Estimativa:** 1 hora
- **Criterios de conclusao:**
  - [x] `core/tests.py` roda sem `duckdb` e passa 100% (31/31 testes aprovados)
  - [x] `teste_contrato.py` (51/51 chamadas aprovadas) e `teste_stdio.py` (14/14 checks aprovados) adaptados para SQLite
  - [x] 100% dos testes aprovados

---

### Documentation Tasks

#### [TASK-004] Atualizar Documentação Técnica e READMEs
- **Descricao:** Atualizar `Adito/scripts/README.md` e `Adito/docs/specs/especificacao_ddl_unificado.md` registrando o modelo 100% SQLite e as 6 views analíticas dinâmicas v2.0.
- **Status:** Completed
- **Estimativa:** 1 hora
- **Criterios de conclusao:**
  - [x] `Adito/scripts/README.md` reflete o comando único `python popular_banco.py`
  - [x] `especificacao_ddl_unificado.md` documenta a arquitetura SQLite nativa
