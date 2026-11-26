> **Nota:** documento histórico. O projeto se chamava Adito (e, antes, Oraculo-ESX) na época; depois o nome passou a Adito e voltou a Adito (ver `Docs/ADR/ADR-0008-volta-ao-nome-adito.md`). O texto abaixo não foi reescrito.

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
>
> **2026-11-25:** a tela Explorar dados voltou, a pedido do usuário, porque os dados usados não são privados. Voltou exatamente como era antes da remoção (`explorer.tables` e `explorer.rows`, lendo as views do contexto escolhido). Os filtros por contexto (`filters.json`) continuam pendentes nesta história.

---

## ✅ Critérios de Aceitação

- [ ] **Critério 1:** Cada contexto pode declarar filtros num `filters.json` validado na carga.
- [ ] **Critério 2:** Filtros globais do dashboard valem só para widgets cujo contexto declara o filtro.
- [x] **Critério 3:** Explorar Dados volta ao menu, lendo as views do contexto escolhido. Feito em 2026-11-25 (a tela tinha saído em 2026-11-19). Ler os filtros do contexto depende do Critério 1.

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
- [x] **[TASK-003]** Refazer Explorar Dados (removida em 2026-11-19, de volta em 2026-11-25)
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

- Ligada à US-010. Em 2026-11-19 a tela Explorar dados foi removida; em 2026-11-25 voltou como era.

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
