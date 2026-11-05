# User Story: [US-008] Agente BI no mesmo processo do backend

**Epic:** Porte do Oráculo-ESX para desktop
**Prioridade:** Média
**Story Points:** -
**Sprint:** -
**Status:** Done

---

## 📖 História

**Como** mantenedor do Oráculo
**Eu quero** que a ferramenta de SQL rode dentro do backend, sem servidor MCP separado
**Para que** ter um processo a menos, sem porta 8005 aberta e sem cliente MCP por requisição

### Contexto Adicional
Na web o agente BI era exposto por um servidor MCP em `0.0.0.0:8005`, sem autenticação, e cada requisição abria um cliente MCP com timeout de 30 s. Decidido em 2026-11-03: **MCP no mesmo processo**.

---

## ✅ Critérios de Aceitação

- [x] **Critério 1:** A ferramenta `bi_agent` é um `StructuredTool` local com o mesmo nome, descrição e retorno (JSON em string).
- [x] **Critério 2:** O `.ask()` síncrono roda com `asyncio.to_thread` e não bloqueia o streaming.
- [x] **Critério 3:** As ferramentas são carregadas uma vez, não por requisição.
- [x] **Critério 4:** Saíram o servidor e o cliente MCP, `fastmcp`, `mcp`, `langchain-mcp-adapters`, a porta 8005 e `ORACULO_MCP_URL`.

---

## 🎨 Mockups/Wireframes

N/A

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `agents/bi_agent/tool.py` (novo), `agents/orchestrator/router.py`, `agents/orchestrator/graph.py`, `chat/stream_views.py`, `chat/views.py`
- **APIs necessárias:** Nenhuma
- **Database changes:** Nenhuma

### Dependências
- N/A

### Considerações de Performance
- Sem impacto relevante.

---

## 🧪 Plano de Testes

### Testes Unitários
- [x] `scripts/teste_nucleo_sqlite.py`: `bi_agent` local mantém o contrato da ferramenta MCP, com modelo e embeddings falsos.

### Testes de Integração
- N/A

### Testes Manuais
- N/A

---

## 📋 Tasks (Breakdown)

- [x] **[TASK-001]** Extrair a ferramenta para `tool.py`
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-002]** Ligar o orquestrador às ferramentas locais
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-003]** Remover servidor, cliente e dependências MCP
  - Estimativa: -
  - Assignee: -

---

## 🤖 IA Insights

### Sugestões de Implementação
N/A

### Riscos Identificados
N/A

### Alternativas Consideradas
N/A

---

## 📝 Notas e Comentários

- 2026-11-03: MCP no mesmo processo; backend ASGI (`daphne`) em `127.0.0.1`.

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
