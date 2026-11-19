> **Nota:** documento histórico. O projeto se chamava Adito (e, antes, Oraculo-ESX) na época; o nome atual é Muninn (ver `Docs/ADR/ADR-0005-nome-muninn.md`). O texto abaixo não foi reescrito.

# User Story: [US-015] Filtros do dashboard por contexto

**Epic:** Porte do Oráculo-ESX para desktop
**Prioridade:** Baixa
**Story Points:** -
**Sprint:** -
**Status:** Backlog

---

## 📖 História

**Como** gestor que usa o dashboard
**Eu quero** filtros que sigam o contexto dos meus dados
**Para que** não ficar preso a uma view fixa

### Contexto Adicional
Os métodos fixos do painel (`dashboard.kpis`, `dashboard.charts`, `dashboard.top_projects`) consultam uma view fixa, hoje `vfact_orientacao_bolsa_resolved` (antes era a view da demonstração de vendas, removida). A proposta é um `filters.json` por contexto.

> **2026-11-19:** a tela Explorar dados saiu do produto, a pedido do usuário. Esta história passa a tratar só dos filtros do dashboard.

---

## ✅ Critérios de Aceitação

- [ ] **Critério 1:** Cada contexto pode declarar filtros num `filters.json` validado na carga.
- [ ] **Critério 2:** Filtros globais do dashboard valem só para widgets cujo contexto declara o filtro.
- ~~**Critério 3:** Explorar Dados volta ao menu, lendo as views e filtros do contexto escolhido.~~ Fora do escopo desde 2026-11-19 (tela removida).

---

## 🎨 Mockups/Wireframes

N/A

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `dashboard/views.py`, `modules/dataExplorer/`, `modules/dashboard/`, `core/contexts.py`
- **APIs necessárias:** Endpoints de KPIs, gráficos e listagem por contexto
- **Database changes:** Nenhuma prevista

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

- [ ] **[TASK-001]** Formato e validação do `filters.json`
  - Estimativa: -
  - Assignee: -
- [ ] **[TASK-002]** Endpoints por contexto
  - Estimativa: -
  - Assignee: -
- ~~**[TASK-003]** Refazer Explorar Dados~~ (tela removida em 2026-11-19)
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

- Ligada à US-010. Em 2026-11-19 a tela Explorar dados foi removida de vez.

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
