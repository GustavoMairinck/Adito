> **Nota:** documento histórico. O projeto se chamava Adito (e, antes, Oraculo-ESX) na época; o nome atual é Muninn (ver `Docs/ADR/ADR-0005-nome-muninn.md`). O texto abaixo não foi reescrito.

# User Story: [US-009] Testar o app com a demonstração de vendas

**Epic:** Porte do Oráculo-ESX para desktop
**Prioridade:** Média
**Story Points:** -
**Sprint:** -
**Status:** Removida

> **Removida no PR #65** (commit `593775f`, mesclado em 2026-11-19): a demonstração de vendas herdada do Oráculo-ESX saiu do Muninn, que passou a ter só o contexto `pesquisa-extensao-ifes`. Depois, a migração da versão 2 do `app.db` apagou o contexto `exemplo-vendas` que restava em instalações antigas, e o núcleo passou a mover cópias dessa pasta para `contexts.removidos/`.

---

## 📖 História

**Como** quem está conhecendo ou testando o Oráculo
**Eu quero** carregar uma base de exemplo com um comando
**Para que** ver o chat e os dashboards funcionando antes de ter os dados reais

### Contexto Adicional
O Oráculo web vinha com uma demo de vendas no Postgres. A pedido do usuário em 2026-11-04, o desktop usa os **mesmos dados de vendas**, agora em SQLite.

---

## ✅ Critérios de Aceitação

- [x] **Critério 1:** `scripts/gerar_dados_demo.py <dados.db>` gera 1.200 vendas (2023 a 2026) com a view `vfactvendasresolved`.
- [x] **Critério 2:** A demo inclui `v_receita_produto`, uma view sobre view.
- [x] **Critério 3:** `contexts/exemplo-vendas/` traz as regras originais e os 68 exemplos originais, todos executáveis na demo.

---

## 🎨 Mockups/Wireframes

N/A

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `scripts/gerar_dados_demo.py` (novo), `contexts/exemplo-vendas/`, `backend/training/ddl/schema.sql`, `mudanças/mudanca/02` e `03`
- **APIs necessárias:** Nenhuma
- **Database changes:** Nenhuma (gera um `dados.db` à parte)

### Dependências
- N/A

### Considerações de Performance
- Sem impacto relevante.

---

## 🧪 Plano de Testes

### Testes Unitários
- [x] `scripts/teste_nucleo_sqlite.py`: os 68 exemplos rodam na demo com a política do contexto.

### Testes de Integração
- N/A

### Testes Manuais
- N/A

---

## 📋 Tasks (Breakdown)

- [x] **[TASK-001]** Script que monta o `dados.db` a partir do schema e dos INSERTs originais
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-002]** Contexto de exemplo com regras e exemplos originais
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-003]** Trocar o exemplo com `INTERVAL` do Postgres por `date('now', '-3 months')`
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

- 2026-11-04: as regras antigas citavam `vfact_vendas_resolved`; corrigido para `vfactvendasresolved`.

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
