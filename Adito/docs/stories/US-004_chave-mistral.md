# User Story: [US-004] Informar a minha própria chave da Mistral

**Epic:** Porte do Oráculo-ESX para desktop
**Prioridade:** Alta
**Story Points:** -
**Sprint:** -
**Status:** Done

---

## 📖 História

**Como** usuário do app desktop
**Eu quero** colar a minha chave da Mistral numa tela de configurações e ter ela guardada com segurança
**Para que** usar o chat sem que nenhuma chave venha embutida no instalador

### Contexto Adicional
Todos os LLMs do orquestrador e do agente BI, e os embeddings, usam Mistral; o app precisa de uma única chave. Decidido em 2026-11-03: **o usuário informa a chave**, guardada no **cofre do sistema operacional**.

---

## ✅ Critérios de Aceitação

- [x] **Critério 1:** A tela **Configurações** testa a chave na Mistral antes de salvar e mostra o motivo se falhar (inválida, sem permissão, cota).
- [x] **Critério 2:** A chave fica no cofre do SO (Secret Service no Linux, Credential Manager no Windows), nunca em arquivo ou `.env`.
- [x] **Critério 3:** O backend recebe a chave só por variável de ambiente ao subir; salvar ou apagar a chave reinicia o backend.
- [x] **Critério 4:** Sem chave, o app abre, o chat fica bloqueado com aviso e link para Configurações, e a API do chat responde 503.
- [x] **Critério 5:** `GET /api/me` informa `llm_configured`.
- [ ] **Critério 6:** Plano B para distros Linux sem Secret Service.

---

## 🎨 Mockups/Wireframes

Tela **Configurações** (`frontend-vue/src/modules/settings/views/ConfiguracoesView.vue`).

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `src-tauri/src/lib.rs` (comandos `llm_key_status`, `set_llm_key`, `clear_llm_key`), `frontend-vue/src/common/api/llmKey.ts`, `modules/settings/`, `core/views.py`, `chat/views.py`, `chat/stream_views.py`, `ChatEstrategicoView.vue`
- **APIs necessárias:** `POST /api/config/test-llm-key`; comandos Tauri `llm_key_status`, `set_llm_key`, `clear_llm_key`
- **Database changes:** Nenhuma

### Dependências
- [x] Crate `keyring` 4

### Considerações de Performance
- Sem impacto relevante.

---

## 🧪 Plano de Testes

### Testes Unitários
- N/A

### Testes de Integração
- N/A

### Testes Manuais
- [x] Salvar uma chave real no Linux pela tela Configurações.
- [ ] Ver o aviso do chat sumir e fazer uma conversa completa com a Mistral (pergunta → SQL → resposta).

---

## 📋 Tasks (Breakdown)

- [x] **[TASK-001]** Comandos de cofre no Tauri e reinício do backend
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-002]** Endpoint de teste da chave
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-003]** Tela Configurações
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-004]** Bloqueio do chat sem chave (front e API)
  - Estimativa: -
  - Assignee: -

---

## 🤖 IA Insights

### Sugestões de Implementação
N/A

### Riscos Identificados
Distros Linux mínimas podem não ter Secret Service; hoje o app só avisa que o cofre não está disponível.

### Alternativas Consideradas
N/A

---

## 📝 Notas e Comentários

- 2026-11-03: o usuário informa a chave; só a da Mistral é usada.
- 2026-11-04: implementado; o usuário salvou uma chave real no Linux. A conversa completa com a Mistral ainda não foi verificada.
- Langfuse fica desligado, a menos que as variáveis dele sejam definidas.

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
