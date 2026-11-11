# User Story: [US-003] Abrir o app direto, sem login

**Epic:** Porte do Oráculo-ESX para desktop
**Prioridade:** Alta
**Story Points:** -
**Sprint:** -
**Status:** Done

---

## 📖 História

**Como** usuário do app desktop
**Eu quero** abrir o app e começar a usar, sem criar conta nem digitar senha
**Para que** não depender do Acesso Cidadão nem do gateway de autenticação da versão web

### Contexto Adicional
Na web o login passava pelo Acesso Cidadão, um gateway C# e JWT. No desktop há um usuário por conta do sistema operacional. Decidido em 2026-11-03: **sem login local** e **tenant fixo**.

---

## ✅ Critérios de Aceitação

- [x] **Critério 1:** No primeiro start o backend cria um usuário local único e um tenant fixo; o app abre direto no chat.
- [x] **Critério 2:** Toda chamada à API exige o token efêmero gerado pelo Tauri no header `X-Oraculo-Token`; sem ele, a API recusa.
- [x] **Critério 3:** O backend escuta só em `127.0.0.1`, com `ALLOWED_HOSTS` limitado a `127.0.0.1`/`localhost`.
- [x] **Critério 4:** Saíram JWT, `simplejwt`, as rotas e a tela de login e o botão de sair.
- [x] **Critério 5:** `SECRET_KEY` é gerada por instalação e `DEBUG` fica desligado por padrão.

---

## 🎨 Mockups/Wireframes

N/A

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `core/local_auth.py` (novo), `core/views.py` (`GET /api/me`), `bi_agent_api/settings.py`, `bi_agent_api/urls.py`, `frontend-vue/src/modules/auth/`, `SidebarNav.vue`
- **APIs necessárias:** `GET /api/me`
- **Database changes:** O `Tenant` perde `db_schema_name`; FKs de tenant e `thread_id` continuam

### Dependências
- N/A

### Considerações de Performance
- Sem impacto relevante.

---

## 🧪 Plano de Testes

### Testes Unitários
- [x] `scripts/teste_nucleo_sqlite.py`: sem token e com token errado a API nega; com token devolve o usuário local; host fora de `127.0.0.1`/`localhost` é recusado.

### Testes de Integração
- N/A

### Testes Manuais
- [x] Abrir o app e cair direto no chat, sem tela de login.

---

## 📋 Tasks (Breakdown)

- [x] **[TASK-001]** `LocalTokenAuthentication` e usuário local
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-002]** Remover JWT, rotas e telas de login
  - Estimativa: -
  - Assignee: -
- [x] **[TASK-003]** `SECRET_KEY` por instalação e `DEBUG` falso
  - Estimativa: -
  - Assignee: -

---

## 🤖 IA Insights

### Sugestões de Implementação
N/A

### Riscos Identificados
Quem abre a conta do SO vê tudo: a proteção passa a ser a conta do sistema e a criptografia de disco (US-005).

### Alternativas Consideradas
Login local com senha (atrito sem ganho real numa máquina de um usuário) e manter vários tenants (ver Notas).

---

## 📝 Notas e Comentários

- 2026-11-03: sem login local; tenant fixo (uma linha criada no primeiro start).
- O modelo `Tenant` foi mantido (cerca de 150 referências em 30 arquivos) para preservar compatibilidade com a web e deixar um caminho barato para várias instituições: um par `app.db`/`dados.db` por pasta de perfil. Isso não foi pedido.

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
