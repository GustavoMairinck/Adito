# User Story: [US-SQLITE-04] Descomissionamento de Legados, Atualização de Testes e Especificações Técnicas

**Epic:** EPIC-08: Migração da Arquitetura de Dados Acadêmicos para 100% SQLite (dados.db)  
**GitHub Epic Issue:** -  
**GitHub US Issue:** -  
**Prioridade:** Média (Slice 2)  
**Story Points:** 3  
**Sprint:** Sprint 01  
**Status:** Completed  
**Behavior Change Esperado:** NO  

---

## Historia

**Como** Engenheiro de Software do projeto Adito  
**Eu quero** remover definitivamente os arquivos obsoletos do PostgreSQL, Docker e DuckDB, expurgar a dependência do DuckDB, atualizar os testes automatizados para validação estrutural e documentar as especificações técnicas  
**Para que** a base de código do monorepo fique totalmente limpa de débitos técnicos legados e os testes executem com 100% de sucesso sem exigir Docker ou DuckDB.

### Contexto Adicional

Com a entrega da carga direta em SQLite (`US-SQLITE-01`, `02`) e o consumo pelo backend núcleo (`US-SQLITE-03`), a infraestrutura legada que sustentava PostgreSQL, Docker Compose, scripts shell de recriação de banco e exportação de JSON intermediário deve ser expurgada. Além disso, a suite de testes automatizados (`core/tests.py`, `teste_contrato.py`, `teste_stdio.py`) precisa ser atualizada para validar a integridade estrutural sobre `dados.db` sem travas rígidas de contagens fixas, e a especificação `Adito/docs/specs/especificacao_ddl_unificado.md` deve refletir formalmente a arquitetura final.

### Pontos de Esclarecimento

Nenhum ponto pendente.

---

## Criterios de Aceitacao

- [x] **Criterio 1 (Remoção de Arquivos Obsoletos):** São excluídos do repositório:
  - `Adito/scripts/docker-compose.yml`
  - `Adito/scripts/recriar_banco.sh`
  - `Adito/scripts/exportar_json.py`
  - `Adito/scripts/gerar_duckdb.py`
  - `Adito/etl/tests/test_exportar_json.py`
  - Arquivos temporários gerados em `saida/json/` e arquivos `dados.duckdb*`.
- [x] **Criterio 2 (Expurgo de Dependências):** O pacote `duckdb` é removido de `Adito/app/backend/requirements.txt` e de quaisquer outros manifestos de dependência do backend.
- [x] **Criterio 3 (Suite de Testes Automatizados 100% Aprovada):** Os testes em `core/tests.py`, `scripts/teste_contrato.py` e `scripts/teste_stdio.py` executam diretamente sobre `dados.db` e passam com 100% de sucesso sem travas fixas rígidas de contagens de linhas e sem a biblioteca `duckdb` instalada no ambiente.
- [x] **Criterio 4 (Atualização de Especificação DDL):** A documentação técnica `Adito/docs/specs/especificacao_ddl_unificado.md` é atualizada para documentar o modelo final em SQLite (42 tabelas relacionais em 3FN + 6 fatos como VIEWs dinâmicas da especificação v2.0).

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Limpeza e documentação interna sem novo boundary.
- **US exige Spec governada?** Nao
- **Spec prevista:** N/A (atualização documental em `Adito/docs/specs/especificacao_ddl_unificado.md`)
- **US exige Contract governado?** Nao
- **Contract previsto:** N/A
- **Touch List preliminar:**
  - `Adito/scripts/docker-compose.yml` (remoção)
  - `Adito/scripts/recriar_banco.sh` (remoção)
  - `Adito/scripts/exportar_json.py` (remoção)
  - `Adito/scripts/gerar_duckdb.py` (remoção)
  - `Adito/etl/tests/test_exportar_json.py` (remoção)
  - `Adito/app/backend/requirements.txt`
  - `Adito/app/backend/nucleo/core/tests.py`
  - `Adito/scripts/teste_contrato.py`
  - `Adito/scripts/teste_stdio.py`
  - `Adito/docs/specs/especificacao_ddl_unificado.md`
- **Requisitos Cobertos:** `FR19`, `NFR05`, `NFR06`.

---

## Plano de Testes

### Testes de Regressão e Validação Final
- [ ] Desinstalar `duckdb` do virtualenv e rodar `python -m unittest core.tests` no núcleo.
- [ ] Executar `python scripts/teste_contrato.py` e `python scripts/teste_stdio.py` validando payload RPC.
- [ ] Verificar que `git status` não apresenta referências a arquivos legados de docker ou duckdb.

---

## Tasks (Breakdown)

- [ ] **[TASK-001]** Remover arquivos legados do PostgreSQL, Docker, JSON e DuckDB.
- [ ] **[TASK-002]** Remover `duckdb` de `Adito/app/backend/requirements.txt`.
- [ ] **[TASK-003]** Refatorar `core/tests.py`, `teste_contrato.py` e `teste_stdio.py` para validação sobre SQLite.
- [ ] **[TASK-004]** Atualizar `Adito/docs/specs/especificacao_ddl_unificado.md`.

---

## Definition of Done Checklist

- [ ] Arquivos obsoletos removidos do monorepo
- [ ] Dependência do DuckDB expurgada
- [ ] Testes automatizados passando sem DuckDB
- [ ] Especificação técnica atualizada
- [ ] Code review aprovado
- [ ] Rastreabilidade para requisitos `FR19, NFR05, NFR06` confirmada
