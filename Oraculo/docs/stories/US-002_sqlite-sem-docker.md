# User Story: [US-002] Guardar tudo em SQLite, sem Postgres nem Redis

**Epic:** Porte do Oráculo-ESX para desktop
**Prioridade:** Alta
**Story Points:** -
**Sprint:** -
**Status:** Done

---

## 📖 História

**Como** usuário do app desktop
**Eu quero** que o app guarde seus dados em arquivos locais, sem instalar banco de dados
**Para que** instalar e usar o Oráculo sem Docker, Postgres ou Redis

### Contexto Adicional
Na web, o Postgres fazia três papéis (metadados Django, vetores pgvector e dados analíticos por schema) e o Redis era só o checkpointer do LangGraph. O volume esperado é pequeno (cerca de 50 mil registros). Decidido em 2026-11-03: **SQLite para tudo**, Redis removido, e **dois arquivos separados**.

---

## ✅ Critérios de Aceitação

- [x] **Critério 1:** `app.db` guarda Django, conversas, dashboards, contextos, checkpoints do LangGraph e embeddings.
- [x] **Critério 2:** `dados.db` guarda os dados do usuário e é aberto **só para leitura** (`mode=ro`, `PRAGMA query_only=ON`); o app nunca escreve nele.
- [x] **Critério 3:** Vetores ficam como BLOB float32 e a busca é feita com numpy (sem pgvector).
- [x] **Critério 4:** O checkpointer do LangGraph usa `AsyncSqliteSaver` no lugar do Redis.
- [x] **Critério 5:** O SQL gerado e o SQL cru do dashboard usam o dialeto SQLite.
- [x] **Critério 6:** `app.db` usa WAL e `busy_timeout` para evitar `database is locked`.

---

## 🎨 Mockups/Wireframes

N/A

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `core/datastore.py`, `core/vectors.py`, `bi_agent_api/settings.py`, `agents/orchestrator/graph.py`, `agents/bi_agent/agent.py`, `agents/bi_agent/sql_security.py`, `dashboard/views.py`
- **APIs necessárias:** Nenhuma nova
- **Database changes:** Migrations regeneradas para SQLite; `VectorField` trocado por `EmbeddingField` (BLOB); `db_schema_name` removido do `Tenant`

### Dependências
- [x] `langgraph-checkpoint-sqlite`
- [x] Saem `psycopg2-binary`, `pgvector` e `redis`

### Considerações de Performance
- Na ordem de 50 mil linhas o SQLite responde em milissegundos. Plano B só para leitura: DuckDB com `ATTACH`.

---

## 🧪 Plano de Testes

### Testes Unitários
- [x] `scripts/teste_nucleo_sqlite.py`: conexão do `dados.db` é só leitura; `execute_query` devolve todas as linhas; busca de valores por embedding; `get_graph` compila com `AsyncSqliteSaver` e as tabelas de checkpoint ficam no `app.db`.

### Testes de Integração
- N/A

### Testes Manuais
- N/A

---

## 📋 Tasks (Breakdown)

- [x] **[TASK-001]** Apontar o Django para o `app.db` (WAL, `IMMEDIATE`)
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-002]** Conexão só leitura do `dados.db`
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-003]** Vetores em BLOB com busca numpy
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-004]** Checkpointer SQLite
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-005]** Reescrever SQL cru do dashboard e prompts para SQLite
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-006]** Remover Redis e schema por tenant
  - Estimativa: -
  - Assignee: -

---

## 🤖 IA Insights

### Sugestões de Implementação
N/A

### Riscos Identificados
Escrita concorrente no `app.db` (streaming, checkpointer e ORM) pode gerar `database is locked`; WAL com `busy_timeout` resolveu nos testes.

### Alternativas Consideradas
Postgres embutido (exige pgvector compilado por sistema, sem binário oficial para Windows) e Docker Postgres (inviável para usuário final).

---

## 📝 Notas e Comentários

- 2026-11-03: SQLite para tudo; Redis removido; `app.db` e `dados.db` separados.
- Cache de consultas, se existir, guarda pergunta → SQL, nunca linhas.

Registro completo: [PORTE_DESKTOP_DECISOES.md](../PORTE_DESKTOP_DECISOES.md).

---

## ✓ Definition of Done Checklist

- [x] Código implementado conforme critérios de aceitação
- [ ] Code review aprovado
- [x] Testes unitários com cobertura adequada
- [ ] Testes de integração passando
- [x] Documentação atualizada
- [ ] Build/CI passando
- [ ] Deploy em staging
- [ ] Aprovação do Product Owner
