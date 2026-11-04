# User Story: [US-013] Não deixar o backend rodando quando o app morre

**Epic:** Porte do Oráculo-ESX para desktop
**Prioridade:** Média
**Story Points:** -
**Sprint:** -
**Status:** Backlog

---

## 📖 História

**Como** usuário do app desktop
**Eu quero** que o backend termine sempre que o app terminar
**Para que** não acumular processos Python presos a portas

### Contexto Adicional
Fechar a janela encerra o backend. Se o app for morto à força (sinal, gerenciador de tarefas), o processo filho fica órfão.

---

## ✅ Critérios de Aceitação

- [ ] **Critério 1:** No Linux, o backend morre junto com o app (por exemplo `PR_SET_PDEATHSIG` ou o backend vigiando o PID do pai).
- [ ] **Critério 2:** No Windows, o backend fica num Job Object que é encerrado com o app.
- [ ] **Critério 3:** Matar o app com `kill -9` não deixa processo `desktop_server.py`.

---

## 🎨 Mockups/Wireframes

N/A

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `src-tauri/src/lib.rs`, `backend/api/desktop_server.py`
- **APIs necessárias:** Nenhuma
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
- [ ] `kill -9` no app e conferir que não sobra backend, no Linux e no Windows.

---

## 📋 Tasks (Breakdown)

- [ ] **[TASK-001]** Amarrar o filho ao pai no Linux
  - Estimativa: -
  - Assignee: -
- [ ] **[TASK-002]** Job Object no Windows
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

- Hoje o README orienta `pkill -f desktop_server.py` no Linux.

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
