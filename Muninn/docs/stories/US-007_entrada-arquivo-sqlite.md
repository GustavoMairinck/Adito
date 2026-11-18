# User Story: [US-007] Trazer meus dados num arquivo SQLite pronto

**Epic:** Porte do Oráculo-ESX para desktop
**Prioridade:** Alta
**Story Points:** -
**Sprint:** -
**Status:** In Progress

---

## 📖 História

**Como** quem fornece os dados
**Eu quero** entregar um arquivo `.db` com as views prontas e o app passar a usá-lo
**Para que** não precisar de ETL nem de banco dentro do app

### Contexto Adicional
A web carregava dados por ETL (SQL Server → Postgres, dbt, pgloader). Decidido em 2026-11-03: **arquivo SQLite pronto**, que o app **copia** para a pasta de dados do usuário como `dados.db`. Importar CSV/XLSX fica para depois.

---

## ✅ Critérios de Aceitação

- [x] **Critério 1:** O app lê `dados.db` e `contexts/` da pasta de dados do usuário.
- [x] **Critério 2:** As views do `views.json` são validadas contra o `dados.db` ao carregar os contextos.
- [ ] **Critério 3:** O usuário escolhe o arquivo pela interface e o app copia com a API de backup do SQLite (hoje a cópia é manual, descrita no README).
- [ ] **Critério 4:** O app valida o arquivo (`PRAGMA quick_check`) e identifica a carga por hash.
- [ ] **Critério 5:** Ao trocar os dados, o app compara o esquema das views, reindexa e marca widgets desatualizados.

---

## 🎨 Mockups/Wireframes

N/A

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `core/datastore.py`, `core/contexts.py`, `dashboard/views.py` (`data_bootstrap`), `AdminView.vue`
- **APIs necessárias:** `POST /api/admin/data/bootstrap`
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
- [x] Copiar a demo para a pasta de dados e carregar os contextos pela Administração.

---

## 📋 Tasks (Breakdown)

- [x] **[TASK-001]** Ler `dados.db` e `contexts/` da pasta de dados
  - Estimativa: -
  - Assignee: -
- [ ] **[TASK-002]** Seleção de arquivo e cópia com `Connection.backup`
  - Estimativa: -
  - Assignee: -
- [ ] **[TASK-003]** `quick_check` e hash da carga
  - Estimativa: -
  - Assignee: -
- [ ] **[TASK-004]** Comparar esquema e reindexar ao trocar
  - Estimativa: -
  - Assignee: -

---

## 🤖 IA Insights

### Sugestões de Implementação
N/A

### Riscos Identificados
Copiar bytes de um arquivo em uso pode pegar uma escrita pela metade; por isso a cópia deve usar a API de backup.

### Alternativas Consideradas
N/A

---

## 📝 Notas e Comentários

- 2026-11-03: arquivo SQLite pronto; o app copia para a pasta de dados; só views do arquivo.
- O formato do `views.json` será validado quando os dados reais chegarem.

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
