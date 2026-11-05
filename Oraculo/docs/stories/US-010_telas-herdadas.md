# User Story: [US-010] Tirar do app as telas que só faziam sentido na web

**Epic:** Porte do Oráculo-ESX para desktop
**Prioridade:** Baixa
**Story Points:** -
**Sprint:** -
**Status:** Done

---

## 📖 História

**Como** usuário do app desktop
**Eu quero** ver no menu só as telas que funcionam com os meus dados
**Para que** não esbarrar em telas presas ao ETL ou à demo da web

### Contexto Adicional
Decidido em 2026-11-04: **Validação de Dados** comparava OLTP com OLAP do ETL da web; no desktop não há ETL. **Explorar Dados** é uma lista fixa da view de vendas, sem contextos.

---

## ✅ Critérios de Aceitação

- [x] **Critério 1:** Validação de Dados foi removida (tela, componentes e `GET /api/admin/data-validation` e `/analytics`).
- [x] **Critério 2:** Explorar Dados saiu do menu; a rota `/explorar` e o endpoint continuam até a tela ser refeita por contexto (US-015).
- [x] **Critério 3:** O menu mostra Chat, Meu Dashboard, Administração e Configurações.

---

## 🎨 Mockups/Wireframes

N/A

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `SidebarNav.vue`, `modules/dataExplorer/`, `dashboard/views.py`, `bi_agent_api/urls.py`
- **APIs necessárias:** Removidas: `GET /api/admin/data-validation` e `GET /api/admin/data-validation/analytics`
- **Database changes:** Nenhuma

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
- [x] Conferir o menu no app aberto.

---

## 📋 Tasks (Breakdown)

- [x] **[TASK-001]** Remover Validação de Dados
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-002]** Esconder Explorar Dados do menu
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

- 2026-11-04: a validação útil no desktop é a de **Carregar Contextos**.

Registro completo: [PORTE_DESKTOP_DECISOES.md](../PORTE_DESKTOP_DECISOES.md).

---

## ✓ Definition of Done Checklist

- [x] Código implementado conforme critérios de aceitação
- [ ] Code review aprovado
- [ ] Testes unitários com cobertura adequada
- [ ] Testes de integração passando
- [x] Documentação atualizada
- [ ] Build/CI passando
- [ ] Deploy em staging
- [ ] Aprovação do Product Owner
