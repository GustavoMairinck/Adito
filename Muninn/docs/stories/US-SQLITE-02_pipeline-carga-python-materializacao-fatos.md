# User Story: [US-SQLITE-02] Pipeline de Carga Direta em Python/SQLite (`popular_banco.py`), Criação das VIEWs e Validação

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

**Como** Mantenedor do ETL do Adito  
**Eu quero** refatorar o script de carga `popular_banco.py` (e expor o comando na CLI `adito-etl`) para executar diretamente em Python via `sqlite3`, inserindo os dados nas 42 tabelas base, criando as 6 fatos como VIEWs dinâmicas e executando validações automatizadas  
**Para que** a base de dados acadêmicos `dados.db` seja gerada localmente em segundos, de forma 100% autocontida, sem dependência de Docker, PostgreSQL ou arquivos intermediários JSON.

### Contexto Adicional

O script `popular_banco.py` anteriormente executava comandos `psql` contra um container Docker. Com a eliminação do PostgreSQL e a adoção de SQLite com views dinâmicas (Opção 3, 100% OLTP), o script conecta diretamente em `sqlite3`, executa os scripts DDL `00..04`, insere os dados acadêmicos estruturados de `Adito/etl/`, e roda validações completas de integridade (`PRAGMA foreign_key_check`), varredura anti-PII e validação estrutural das 6 views.

### Pontos de Esclarecimento

Nenhum ponto pendente.

---

## Criterios de Aceitacao

- [x] **Criterio 1 (Execução Autocontida em Python):** O comando `python scripts/popular_banco.py` (e `adito-etl popular-banco`) executa diretamente via `sqlite3` sem exigir Docker, containers ativos ou utilitários externos, gerando o arquivo `Adito/app/data/dados.db` (ou no caminho configurado por `ORACULO_DATA_DIR`).
- [x] **Criterio 2 (Tempo de Execução e Volumetria):** O processo completo de carga, criação de VIEWs e validação executa em tempo inferior a 5 segundos (1.08s atingido), gerando um banco entre 2 MB e 8 MB (2.83 MB gerado).
- [x] **Criterio 3 (Regras de Vínculo e Patentes no ETL):**
  - O carregador prioriza vínculo de campus do Ifes para o pesquisador antes de aceitar instituições externas, e nunca promove agências de fomento (`FAPES`, `CNPq`) a organização de lotação.
  - Grava com sucesso patentes e softwares com patente extraídos do Lattes na tabela `patente_registro`.
  - Mapeia a situação `'Excluído'` do CNPq para a constraint de situação de grupo (`'EXCLUIDO'`).
- [x] **Criterio 4 (Definição das 6 Fatos como VIEWs Dinâmicas):** As 6 fatos analíticas (`vfact_*_resolved`) são definidas como views relacionais dinâmicas diretamente sobre as 42 tabelas base no `dados.db` (100% OLTP).
- [x] **Criterio 5 (Validação Pós-Carga Automatizada):**
  - `PRAGMA foreign_key_check` retorna 0 erros.
  - Varredura anti-PII confirma 0 ocorrências de CPFs (máscara ou regex) e e-mails pessoais.
  - Validações de sanidade estrutural confirmam: `SUM(flag_lider) > 0`, `SUM(flag_obra_unica) == COUNT(DISTINCT id_producao)` e 0 valores negativos em `tempo_participacao_dias`.
- [x] **Criterio 6 (Script de Visualização):** O script `Adito/scripts/ver_dados.py` é adaptado para consultar e exibir tabelas e views analíticas diretamente de `dados.db` via SQLite.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Pipeline interno de ETL e persistência em banco local.
- **US exige Spec governada?** Nao
- **Spec prevista:** N/A
- **US exige Contract governado?** Nao
- **Contract previsto:** N/A
- **Touch List preliminar:**
  - `Adito/scripts/popular_banco.py`
  - `Adito/scripts/ver_dados.py`
  - `Adito/etl/src/adito_etl/cli.py`
  - `Adito/etl/tests/test_popular_banco_sqlite.py`
- **Requisitos Cobertos:** `FR03`, `FR11`, `FR12`, `NFR01`, `NFR04`, `NFR05`, `NFR07`.

---

## Notas Tecnicas

### Arquitetura
- **Conexão SQLite de Escrita durante o ETL:**
  ```python
  conn = sqlite3.connect(db_path)
  conn.execute("PRAGMA foreign_keys = ON;")
  conn.execute("PRAGMA journal_mode = WAL;")
  conn.execute("PRAGMA synchronous = NORMAL;")
  ```
- **Criação das VIEWs Dinâmicas:**
  Ao término das inserções nas 42 tabelas base, o script executa `04_fatos_views.sql`, criando as 6 views analíticas dinâmicas.

---

## Plano de Testes

### Testes de Integracao / ETL
- [x] Executar carga completa em ambiente de teste limpo gerando `dados.db`.
- [x] Validar tempo de execução (< 5s).
- [x] Verificar contagens de linhas de cada uma das 42 tabelas base e das 6 fatos.
- [x] Executar `ver_dados.py` e verificar amostragem tabular correta no terminal.
- [x] Suite de testes `Adito/etl/tests/test_popular_banco_sqlite.py` passando 100%.

---

## Tasks (Breakdown)

- [x] **[TASK-001]** Refatorar `Adito/scripts/popular_banco.py` para usar `sqlite3` nativo, eliminando chamadas `psql` e Docker.
- [x] **[TASK-002]** Ajustar lógica de carga no ETL: priorizar campus Ifes no pesquisador, gravar patentes do Lattes e mapear `'EXCLUIDO'` do CNPq.
- [x] **[TASK-003]** Implementar execução de `04_fatos_views.sql` criando as 6 views analíticas dinâmicas.
- [x] **[TASK-004]** Implementar rotina de validação pós-carga (`foreign_key_check`, varredura anti-PII e sanidade de regras P1-P12).
- [x] **[TASK-005]** Atualizar `ver_dados.py` e expor comando no `adito-etl`.
- [x] **[TASK-006]** Implementar testes automatizados `test_popular_banco_sqlite.py`.
