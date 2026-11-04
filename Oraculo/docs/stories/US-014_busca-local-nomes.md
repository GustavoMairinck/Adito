# User Story: [US-014] Resolver nomes de pessoas sem enviá-los à nuvem

**Epic:** Porte do Oráculo-ESX para desktop
**Prioridade:** Média
**Story Points:** -
**Sprint:** -
**Status:** Backlog

---

## 📖 História

**Como** responsável pelos dados da instituição
**Eu quero** que nomes de pessoas citados na pergunta sejam encontrados por busca local
**Para que** resolver nomes sem embedá-los na Mistral

### Contexto Adicional
Decidido em 2026-11-03: campos com nomes de pessoas vão em `local_search_columns` e são resolvidos no próprio SQLite (FTS5 ou busca por prefixo). A chave já é aceita e validada no `views.json`, mas a busca não existe.

---

## ✅ Critérios de Aceitação

- [ ] **Critério 1:** Ao carregar o contexto, o app monta um índice FTS5 no `app.db` com os valores de `local_search_columns`.
- [ ] **Critério 2:** O resolvedor de valores consulta esse índice antes de montar o SQL.
- [ ] **Critério 3:** Nenhum valor de `local_search_columns` é enviado ao embedder.

---

## 🎨 Mockups/Wireframes

N/A

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `analytics_index/`, `agents/bi_agent/nodes/semantic_value_resolver.py`, `core/contexts.py`
- **APIs necessárias:** Nenhuma
- **Database changes:** Tabela FTS5 no `app.db`, reconstruída a cada carga

### Dependências
- N/A

### Considerações de Performance
- Sem impacto relevante.

---

## 🧪 Plano de Testes

### Testes Unitários
- N/A

### Testes de Integração
- N/A

### Testes Manuais
- N/A

---

## 📋 Tasks (Breakdown)

- [ ] **[TASK-001]** Índice FTS5 por contexto
  - Estimativa: -
  - Assignee: -
- [ ] **[TASK-002]** Ligar ao resolvedor de valores
  - Estimativa: -
  - Assignee: -
- [ ] **[TASK-003]** Teste sem chamada ao embedder
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

- `local_search_columns: ["vendedor"]` já está no contexto de exemplo.

Registro completo: [PORTE_DESKTOP_DECISOES.md](../PORTE_DESKTOP_DECISOES.md).

---

## ✓ Definition of Done Checklist

- [ ] Código implementado conforme critérios de aceitação
- [ ] Code review aprovado
- [ ] Testes unitários com cobertura adequada
- [ ] Testes de integração passando
- [ ] Documentação atualizada
- [ ] Build/CI passando
- [ ] Deploy em staging
- [ ] Aprovação do Product Owner
