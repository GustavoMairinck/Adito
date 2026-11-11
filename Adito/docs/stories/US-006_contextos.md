# User Story: [US-006] Trabalhar com vários contextos de dados

**Epic:** Porte do Oráculo-ESX para desktop
**Prioridade:** Alta
**Story Points:** -
**Sprint:** -
**Status:** Done

---

## 📖 História

**Como** quem prepara os dados para o Oráculo
**Eu quero** agrupar views, regras e exemplos em contextos e escolher o contexto de cada conversa
**Para que** que o agente só some coisas compatíveis e use as regras certas de cada assunto

### Contexto Adicional
A web tinha uma view fixa (`vfactvendasresolved`) espalhada em vários arquivos. O app desktop não depende de nenhuma fonte de dados específica. Decidido em 2026-11-03: **modelo `Contexto` novo**, com o tenant fixo, e **só views do arquivo** (o app não cria views).

---

## ✅ Critérios de Aceitação

- [x] **Critério 1:** Cada contexto é uma pasta `contexts/<slug>/` com `views.json` (views, `sensitive_columns`, `embed_columns`, `local_search_columns`, `llm_row_limit`), `rules.md` e `examples.json`.
- [x] **Critério 2:** A carga valida o contexto: views existem no `dados.db`, colunas declaradas existem, nenhuma coluna é sensível e embedada ao mesmo tempo.
- [x] **Critério 3:** O prompt, o RAG, o índice de valores e a política de leitura saem do contexto.
- [x] **Critério 4:** A conversa nova pede o contexto (ou usa o único ativo) e ele fica fixo na conversa; o widget fixado herda o contexto.
- [x] **Critério 5:** Views de views funcionam; só as views expostas entram no `views.json`.
- [x] **Critério 6:** **Administração → Carregar Contextos** recarrega os contextos da pasta de dados e, com chave configurada, gera os embeddings.

---

## 🎨 Mockups/Wireframes

Seletor de contexto no chat (`ContextoSelector.vue`) e botão **Carregar Contextos** em Administração.

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `core/models.py` (`Contexto`), `core/contexts.py`, comando `load_context`, `analytics_index/`, `knowledge/`, `chat/`, `dashboard/`, `ContextoSelector.vue`, `useContextos.ts`, `AdminView.vue`
- **APIs necessárias:** `GET /api/contextos`; `POST /api/admin/data/bootstrap`
- **Database changes:** Modelo `Contexto` com FK em conversa, widget, RAG, auditoria e índice de valores

### Dependências
- N/A

### Considerações de Performance
- Sem impacto relevante.

---

## 🧪 Plano de Testes

### Testes Unitários
- [x] `scripts/teste_nucleo_sqlite.py`: carga e validação de contexto, política por contexto, RAG filtrado por contexto, conversa nova exige contexto.

### Testes de Integração
- N/A

### Testes Manuais
- N/A

---

## 📋 Tasks (Breakdown)

- [x] **[TASK-001]** Modelo `Contexto` e migrations
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-002]** Carga e validação de pasta de contexto
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-003]** Prompt, RAG e política por contexto
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-004]** Seletor no chat e contexto no widget
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-005]** Botão Carregar Contextos
  - Estimativa: -
  - Assignee: -

---

## 🤖 IA Insights

### Sugestões de Implementação
N/A

### Riscos Identificados
Cada contexto exige regras e exemplos mantidos e testados. Perguntas que cruzam contextos precisam de uma view de junção feita por quem fornece os dados.

### Alternativas Consideradas
Reusar linhas de `Tenant` como contextos (mais barato, mas mistura organização com assunto e prende o usuário a um tenant).

---

## 📝 Notas e Comentários

- 2026-11-03: modelo `Contexto` novo; um contexto por grupo de views de mesma granularidade; só views do arquivo.
- Views de views testadas em SQLite 3.46.1 com três níveis.
- Filtros por contexto (`filters.json`) e busca local de nomes ficaram para US-015 e US-014.

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
