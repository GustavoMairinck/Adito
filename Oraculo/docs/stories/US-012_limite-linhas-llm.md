# User Story: [US-012] Respeitar o limite de linhas do contexto no envio ao LLM

**Epic:** Porte do Oráculo-ESX para desktop
**Prioridade:** Média
**Story Points:** -
**Sprint:** -
**Status:** Backlog

---

## 📖 História

**Como** responsável pelos dados da instituição
**Eu quero** definir por contexto quantas linhas de resultado podem ir ao LLM
**Para que** ajustar o envio ao tipo de dado de cada contexto, inclusive não enviar nenhuma linha

### Contexto Adicional
Decidido em 2026-11-03: padrão de 20 linhas, sobrescrito por `llm_row_limit` no `views.json`. Hoje `core/contexts.py` tem `row_limit_for`, mas ninguém o chama: a prévia de `agents/bi_agent/tool.py` está fixa em `PREVIEW_ROWS = 5`.

---

## ✅ Critérios de Aceitação

- [ ] **Critério 1:** A prévia enviada ao LLM usa `row_limit_for(contexto)`, com padrão 20.
- [ ] **Critério 2:** `llm_row_limit: 0` não envia nenhuma linha (modo só agregados por contexto).
- [ ] **Critério 3:** Teste cobre os limites 0, padrão e valor do contexto.

---

## 🎨 Mockups/Wireframes

N/A

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `agents/bi_agent/tool.py`, `core/contexts.py`
- **APIs necessárias:** Nenhuma
- **Database changes:** Nenhuma

### Dependências
- N/A

### Considerações de Performance
- Sem impacto relevante.

---

## 🧪 Plano de Testes

### Testes Unitários
- [ ] Prévia com 0, 20 e o valor do contexto.

### Testes de Integração
- N/A

### Testes Manuais
- N/A

---

## 📋 Tasks (Breakdown)

- [ ] **[TASK-001]** Trocar `PREVIEW_ROWS` por `row_limit_for`
  - Estimativa: -
  - Assignee: -
- [ ] **[TASK-002]** Teste no `teste_nucleo_sqlite.py`
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

- Achado em 2026-11-04 durante a revisão da US-005.

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
