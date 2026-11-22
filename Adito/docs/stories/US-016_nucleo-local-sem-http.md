> **Nota:** documento histórico. O projeto se chamava Adito (e, antes, Oraculo-ESX) na época; depois o nome passou a Adito e voltou a Adito (ver `Docs/ADR/ADR-0008-volta-ao-nome-adito.md`). O texto abaixo não foi reescrito.

# User Story: [US-016] Núcleo local sem servidor HTTP

**Epic:** Porte do Oráculo-ESX para desktop
**Prioridade:** Alta
**Story Points:** -
**Sprint:** -
**Status:** In Review

---

## 📖 História

**Como** usuário do Adito no desktop
**Eu quero** que o app rode só na minha máquina, sem servidor web por trás
**Para que** nada fique escutando na rede, o app abra mais rápido e não sobrem processos presos

### Contexto Adicional
O porte de 2026-11-03 manteve o backend Django servido pelo daphne em `127.0.0.1`, com token efêmero (US-001, US-003, US-008). O Adito é um app desktop, então essa camada web não deveria existir. Decidido em 2026-11-17: o Python continua (o agente depende de LangGraph, sqlglot e langchain), mas como processo filho que fala com o Tauri por stdin/stdout. O Django sai por inteiro.

---

## ✅ Critérios de Aceitação

- [x] **Critério 1:** Sem Django, DRF, daphne, CORS, whitenoise, porta ou token; `ss -ltnp` não mostra porta do Adito.
- [x] **Critério 2:** Todas as chamadas que as telas fazem devolvem o mesmo status e o mesmo JSON de antes (`scripts/teste_contrato.py`, 51 chamadas, referência gravada no Django).
- [x] **Critério 3:** O streaming do chat mantém os eventos `status`, `token`, `result` e `error`.
- [x] **Critério 4:** O `app.db` de uma instalação anterior abre sem migração de dados (conversas, mensagens e widgets preservados).
- [x] **Critério 5:** Matar o app com `kill -9` encerra o núcleo (resolve a US-013).
- [x] **Critério 6:** Abrir o app não fica mais lento (medido: ~1,0 s antes, ~0,5–0,7 s depois).
- [ ] **Critério 7:** Verificação manual tela por tela no app (chat com chave real, dashboards, Explorar, Administração, Configurações).
- [ ] **Critério 8:** Mesmo fluxo verificado no Windows.

---

## 🎨 Mockups/Wireframes

N/A

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** `src-tauri/src/lib.rs`, `backend/nucleo/rpc/` (novo), `backend/nucleo/core/db.py`, `core/records.py`, `core/schema.py`, `core/schema.sql`, `core/cli.py` (novos), `frontend-vue/src/common/api/core.ts` (novo) e as telas que chamavam a API.
- **APIs necessárias:** comandos Tauri `core_ready`, `core_call`, `core_stream`, `core_cancel`.
- **Database changes:** nenhuma no esquema; `PRAGMA user_version = 1` marca o esquema herdado.

### Dependências
- Saem: `django`, `djangorestframework`, `django-cors-headers`, `daphne`, `whitenoise`, `python-jose`, `bcrypt`, `axios`, `uuid` (Rust).
- Entram no Rust: `serde_json` e `tokio` (`sync`), já presentes na árvore do Tauri.

### Considerações de Performance
- Sem `django.setup()`/`migrate` a cada abertura nem polling de `/health`.
- Grafo do orquestrador e checkpointer abertos uma vez por processo.
- Widgets e histórico reexecutam SQL sem instanciar o LLM.
- `dados.duckdb` aberto uma vez por processo, com um cursor por chamada (~12 ms a menos por consulta). Reabre quando o arquivo muda e solta o arquivo após 60 s sem uso (`ADITO_DUCKDB_IDLE_CLOSE_S`).

---

## 🧪 Plano de Testes

### Testes Unitários
- [x] `backend/nucleo/core/tests.py` (`unittest`): segurança do SQL, contextos, Explorar e persistência no `app.db`.

### Testes de Integração
- [x] `scripts/teste_contrato.py`: contrato das 51 chamadas contra a referência gravada no Django.
- [x] `scripts/teste_stdio.py`: processo real, pronto, concorrência, erros, cancelamento, fim do stdin.

### Testes Manuais
- [x] App Tauri aberto com pasta de dados isolada: o front chamou `me`, `chat.conversations.list`, `health` e `contextos.list` pelo núcleo.
- [ ] Roteiro completo das telas (ver [NUCLEO_LOCAL_SEM_HTTP.md](../NUCLEO_LOCAL_SEM_HTTP.md)).

---

## 📋 Tasks (Breakdown)

- [x] **[TASK-001]** Gravar a referência de contrato com o Django
- [x] **[TASK-002]** Persistência sem ORM com o mesmo esquema
- [x] **[TASK-003]** Métodos RPC e servidor stdin/stdout
- [x] **[TASK-004]** Ponte no Rust e cliente no front
- [x] **[TASK-005]** Remover Django, dependências web e sobras de Docker
- [x] **[TASK-006]** Documentar ([NUCLEO_LOCAL_SEM_HTTP.md](../NUCLEO_LOCAL_SEM_HTTP.md))

---

## 📝 Notas e Comentários

- 2026-11-17: substitui a decisão "backend ASGI (daphne) em `127.0.0.1` com token" de 2026-11-03.

Registro completo: [NUCLEO_LOCAL_SEM_HTTP.md](../NUCLEO_LOCAL_SEM_HTTP.md).

---

## ✓ Definition of Done Checklist

- [x] Código implementado conforme critérios de aceitação
- [ ] Code review aprovado
- [x] Testes unitários com cobertura adequada
- [x] Testes de integração passando
- [x] Documentação atualizada
- [ ] Build/CI passando
- [ ] Deploy em staging
- [ ] Aprovação do Product Owner
