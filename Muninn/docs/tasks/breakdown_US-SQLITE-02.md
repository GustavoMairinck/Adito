# Task Breakdown: [US-SQLITE-02] Pipeline de Carga Direta em Python/SQLite (`popular_banco.py`), Criação das VIEWs e Validação

**Data:** 18/11/2026  
**Participantes:** Equipe de Engenharia de Dados  
**Estimativa total:** 5 Story Points  
**Nivel ScrumAIDev:** 1  
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
- **Justificativa do Nivel ScrumAIDev:** Nível 1 — Pipeline interno de ETL em Python/SQLite sem exposição de boundary HTTP externo.
- **Justificativa:** Refatoração de script de carga para escrita direta no SQLite com validações internas.
- **Touch List aplicavel:**
  - `Adito/scripts/popular_banco.py`
  - `Adito/scripts/ver_dados.py`
  - `Adito/etl/src/adito_etl/cli.py`
  - `Adito/etl/tests/test_popular_banco_sqlite.py`
- **Runner BDD a executar:** N/A
- **Validacao de contrato a executar:** N/A
- **Teste de contrato a executar:** N/A
- **Teste de mock a executar:** N/A

---

## Checagem de Principios

Preenchido porque `Behavior change = YES`:
- [x] Esta e a abordagem mais simples que atende a User Story? Sim, eliminação completa do PostgreSQL/Docker no ETL, gravando direto no SQLite via biblioteca padrão `sqlite3`.
- [x] A abordagem esta alinhada com `docs/definition_of_done.md` e com as regras de `AGENTS.md`? Sim.
- [x] Nenhuma dependencia externa nova esta sendo introduzida sem aprovacao? Sim, apenas utilitários built-in do Python.
- [x] O escopo respeita a Touch List? Sim.

---

## Tasks Tecnicas

### Backend Tasks

#### [TASK-001] Refatorar `popular_banco.py` para SQLite 3 Nativo
- **Descricao:** Refatorar `Adito/scripts/popular_banco.py` para inicializar a base `dados.db` a partir dos DDLs `00..04` e inserir dados em transação atômica via `sqlite3`, eliminando `psql` e Docker.
- **Status:** Done
- **Estimativa:** 1.5 hora
- **Criterios de conclusao:**
  - [x] Sem chamadas ao `psql` ou `docker compose`
  - [x] Base SQLite `dados.db` inicializada e populada em menos de 5 segundos
  - [x] Compatibilidade de tipos booleanos e literais SQLite

#### [TASK-002] Aplicar Correções de Negócio no ETL (P1, P3, P5)
- **Descricao:** Priorizar campus Ifes no pesquisador e descartar agências de fomento como lotação (P1); mapear 'Excluído' do CNPq para `'EXCLUIDO'` (P3); gravar patentes e softwares com patente do Lattes em `patente_registro` (P5).
- **Status:** Done
- **Estimativa:** 1.5 hora
- **Criterios de conclusao:**
  - [x] P1: Campus Ifes prioritário e zero agências de fomento como lotação
  - [x] P3: Situação de grupo excluído mapeada corretamente
  - [x] P5: Patentes gravadas em `patente_registro` com depositante anulável

#### [TASK-003] Compilação das 6 VIEWs Analíticas Dinâmicas
- **Descricao:** Garantir execução de `04_fatos_views.sql` e verificação de que as 6 views analíticas acessam dados em tempo real sem duplicação física.
- **Status:** Done
- **Estimativa:** 0.5 hora
- **Criterios de conclusao:**
  - [x] 6 views compiladas e retornando registros válidos
  - [x] Padrão 100% OLTP mantido

#### [TASK-004] Implementar Rotina de Validação Pós-Carga
- **Descricao:** Implementar verificações automáticas no script: `PRAGMA foreign_key_check`, varredura anti-PII de CPFs e e-mails, validação de regras estruturais (`SUM(flag_lider) > 0`, `SUM(flag_obra_unica) == COUNT(DISTINCT id_producao)`, dias de participação não negativos).
- **Status:** Done
- **Estimativa:** 1 hora
- **Criterios de conclusao:**
  - [x] `PRAGMA foreign_key_check` limpo (0 erros)
  - [x] Zero CPFs e emails pessoais inseridos
  - [x] Relatório JSON gravado com contagens e sanidade

#### [TASK-005] Adaptar `ver_dados.py` e Expor CLI `popular-banco`
- **Descricao:** Adaptar `Adito/scripts/ver_dados.py` para inspecionar `dados.db` via SQLite; adicionar o comando `popular-banco` em `Adito/etl/src/adito_etl/cli.py`.
- **Status:** Done
- **Estimativa:** 0.5 hora
- **Criterios de conclusao:**
  - [x] `ver_dados.py` roda sem dependência de DuckDB
  - [x] `adito-etl popular-banco` executa com sucesso

---

### Testing Tasks

#### [TASK-006] Testes Automatizados de Integração do Pipeline de Carga
- **Descricao:** Implementar teste automatizado `Adito/etl/tests/test_popular_banco_sqlite.py` testando a geração completa do banco temporário e validando sanidade das 6 views.
- **Status:** Done
- **Estimativa:** 0.5 hora
- **Criterios de conclusao:**
  - [x] Teste passa 100% via `pytest`
  - [x] Validação de integridade e regras de negócio cobertas
