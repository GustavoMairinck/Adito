# User Story: [US-CHAT-01] Cancelamento cooperativo no núcleo Python (`BIAgent` + checkpointer) e filtro pós-abort em `core.ts`

**Epic:** EPIC-12: Cancelamento de Prompts e Streaming em Segundo Plano no Chat
**GitHub Epic Issue:** -
**GitHub US Issue:** -
**Prioridade:** Alta (Vertical Slice 1)
**Story Points:** 3
**Sprint:** -
**Status:** Done
**Behavior Change Esperado:** YES

---

## Historia

**Como** usuário do Adito com chave de API própria (BYOK)
**Eu quero** que cancelar um prompt em andamento interrompa cooperativamente as próximas etapas do agente de BI no núcleo Python sem gravar resposta incompleta nem vazar eventos atrasados pelo canal IPC
**Para que** eu não desperdice cota/créditos da minha chave de API e possa enviar imediatamente uma nova pergunta na mesma conversa sem erros no histórico ou no checkpointer.

### Contexto Adicional

O protocolo STDIO (`$cancel` em `rpc/server.py`), o Tauri (`core_cancel` em `src-tauri/src/lib.rs`) e a bridge (`AbortSignal` em `common/api/core.ts`) já existem, mas hoje:
1. Em `common/api/core.ts`, `withAbort()` rejeita com `CanceledError` quando `signal` aborta, mas `channel.onmessage` continua ativo até o `$end` chegar — permitindo vazamento de eventos atrasados (`token`, `status`, `result`, `error`) para os callbacks da UI.
2. Em `rpc/chat.py`, `task.cancel()` cancela o `orchestrator_graph.astream(...)` em pontos de `await`, mas o `BIAgent` roda de forma síncrona em thread (`self.app.invoke`), continuando a executar os nós seguintes (`query_extractor`, `semantic_value_resolver`, `sql_generator`, `sql_validator`, `sql_corrector`, `response_generator`) e consumindo cota do LLM mesmo depois do cancelamento.

### Pontos de Esclarecimento

Nenhum ponto pendente (todas as decisões de escopo foram consolidadas em `Adito/docs/discovery/abortar-prompt-chat.md` e `Adito/docs/requirements/abortar-prompt-chat.md`).

---

## Criterios de Aceitacao

- [x] **Criterio 1 (`FR04`):** Em `Adito/app/frontend-vue/src/common/api/core.ts`, ao acionar `options.signal.abort()` em `stream()`, `channel.onmessage` passa imediatamente a ignorar qualquer mensagem futura (`settled = true`), `core_cancel` é invocado no Tauri e a Promise rejeita com `CanceledError` sem entregar nenhum evento atrasado ao callback `onEvent`.
- [x] **Criterio 2 (`FR08`, `BR05`):** Ao receber `$cancel` (`asyncio.CancelledError`) em `rpc/chat.py`, um `cancel_event: threading.Event` associado àquela execução é sinalizado (`cancel_event.set()`) e propagado até o `BIAgent` (`agents/orchestrator/` → `agents/bi_agent/`), interrompendo a execução antes da próxima etapa custosa (RAG, resolvedor de valores, geração/correção SQL, execução SQL ou geração de resposta) sem disparar novas chamadas ao LLM.
- [x] **Criterio 3 (`BR01`, `A01`):** Quando `chat.stream` é cancelado via `$cancel`, `persist_assistant_response` não é chamado e nenhuma mensagem `assistant` incompleta nem `QueryExecution` órfã é gravada no `app.db` (apenas a `user_message` criada em `prepare_conversation` permanece).
- [x] **Criterio 4 (`BR04`):** Após cancelar uma pergunta em andamento em uma conversa (`thread_id`), enviar uma nova pergunta na mesma conversa executa normalmente sem erro nem corrupção de estado no `AsyncSqliteSaver` do LangGraph.
- [x] **Criterio 5 (`NFR03`, `NFR04`, `A02`):** Nenhuma dependência externa é adicionada; `scripts/teste_contrato.py` e toda a suíte `core/tests.py` (incluindo os novos testes de cancelamento cooperativo e pós-abort) passam 100% verdes.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Comportamento observável de cancelamento reutilizando integralmente o protocolo `$cancel` / `core_cancel` / status `499` já existente, sem introduzir novos endpoints, schemas ou contratos públicos.
- **US exige Spec governada?** Nao
- **Justificativa da Spec:** US nao exige Spec governada adicional; os requisitos estáveis (`FR04`, `FR08`, `BR01`, `BR04`, `BR05`, `NFR03`, `NFR04`) já estão registrados em `Adito/docs/requirements/abortar-prompt-chat.md`.
- **Spec prevista:** N/A
- **US exige Contract governado?** Nao
- **Justificativa do Contract:** US nao exige novo Contract governado porque não altera request, response, eventos ou códigos de erro do protocolo RPC (`teste_contrato.py` valida retrocompatibilidade).
- **Contract previsto:** N/A
- **Padrao de erro aplicavel:** N/A (status `499` / `CanceledError` já existentes)
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** `test-contract` (`Adito/app/scripts/teste_contrato.py`)
- **Touch List preliminar:**
  - `Adito/app/frontend-vue/src/common/api/core.ts`
  - `Adito/app/backend/nucleo/rpc/chat.py`
  - `Adito/app/backend/nucleo/agents/orchestrator/graph.py`
  - `Adito/app/backend/nucleo/agents/bi_agent/cancellation.py`
  - `Adito/app/backend/nucleo/agents/bi_agent/tool.py`
  - `Adito/app/backend/nucleo/agents/bi_agent/agent.py`
  - `Adito/app/backend/nucleo/agents/bi_agent/graph.py`
  - `Adito/app/backend/nucleo/core/tests.py`
  - `Adito/app/frontend-vue/tests/unit/core.spec.ts`
- **Task Issues previstas:** N/A

---

## Mockups/Wireframes

N/A (story de infraestrutura/backend + bridge IPC).

---

## Notas Tecnicas

### Arquitetura

- **Componentes afetados:** `core.ts`, `rpc/chat.py`, `agents/orchestrator/graph.py`, `agents/bi_agent/{tool.py,agent.py,graph.py}`.
- **APIs necessarias:** Reutiliza `chat.stream`, `$cancel` (`rpc/server.py`) e `core_cancel` (`src-tauri/src/lib.rs`).
- **Database changes:** Nenhuma alteração de schema (`app.db` e `dados.db` intactos).
- **Referencias do modelo de dados:** N/A.
- **Erros observaveis esperados:** `CanceledError` (status `499`) tratado silenciosamente pelo consumidor de stream no frontend; internamente no `BIAgent`, exceção dedicada de cancelamento cooperativo (ex.: `BIAgentCancelled`) que não é convertida em mensagem de erro ou fallback salvo no banco.

### Dependencias

- [x] Infraestrutura `$cancel` (`rpc/server.py`), `core_cancel` (`lib.rs`) e `withAbort` (`core.ts`) já presentes na branch base.

### Consideracoes de Performance

- A checagem `cancel_event.is_set()` entre nós do `BIAgent` tem custo O(1) desprezível e evita 1 a 4 chamadas HTTP extras ao provedor de LLM quando o usuário cancela no início da consulta.
- Garantir isolamento de `cancel_event` por requisição (ex.: via `ContextVar` / dicionário por `run_id` ou argumento explícito no `config`/`state`) para não cancelar uma segunda conversa rodando em paralelo!

---

## Plano de Testes

### Testes Unitarios

- [ ] Python (`core/tests.py`): `BIAgent` com `cancel_event` sinalizado durante o primeiro nó interrompe antes do segundo nó (não chama `sql_generator` / `response_generator`).
- [ ] Python (`core/tests.py`): `Server.handle({"method": "$cancel", ...})` em `chat.stream` sinaliza `cancel_event`, devolve `499` e não grava mensagem `assistant` nem `QueryExecution` no `app.db`.
- [ ] Python (`core/tests.py`): duas execuções concorrentes de `chat.stream` em conversas distintas cancelando apenas a 1ª não afetam o `cancel_event` da 2ª.
- [ ] Frontend Vitest: `stream()` em `core.ts` ao receber `signal.abort()` dispara `core_cancel`, rejeita com `CanceledError` e ignora eventos `token`/`result` enviados depois no `Channel`.

### Testes de Integracao

- [ ] Python (`core/tests.py`): fluxo `perguntar → cancelar → perguntar novamente na mesma conversa` usando `AsyncSqliteSaver` confirma checkpointer íntegro e resposta válida na 2ª pergunta.

### Testes de Contract

- [ ] Executar `python Adito/app/scripts/teste_contrato.py` garantindo 0 regressões frente a `referencia.json`.

### Testes Manuais

- [ ] Conferir em `src-tauri/src/lib.rs` se `core_cancel` seguido de resposta `499` limpa o `HashMap` `pending` sem warnings ou vazamento (rodar `cargo test`).

### BDD / Cenarios de Comportamento

- N/A (Nível ScrumAIDev 1).

---

## Tasks (Breakdown)

- [x] **[TASK-001]** Travar entrega de eventos pós-abort em `common/api/core.ts` e adicionar teste unitário Vitest
  - GitHub Task Issue: N/A
  - Estimativa: 1h
  - Assignee: -
- [x] **[TASK-002]** Propagar `cancel_event` isolado por requisição em `rpc/chat.py` → `orchestrator` → `BIAgent` sem persistir resposta incompleta
  - GitHub Task Issue: N/A
  - Estimativa: 3h
  - Assignee: -
- [x] **[TASK-003]** Adicionar testes unitários/integração em `core/tests.py` (cancelamento cooperativo, concorrência entre conversas e checkpointer pós-abort) e validar contrato RPC + Rust `cargo test`
  - GitHub Task Issue: N/A
  - Estimativa: 2h
  - Assignee: -

---

## IA Insights

### Sugestoes de Implementacao

- Como `mcp_tool_node` em `agents/orchestrator/graph.py` captura `except Exception as e:` (linha 124), atenção crítica: a exceção de cancelamento (`BIAgentCancelled` ou `asyncio.CancelledError`) precisa ser re-lançada **antes** do `except Exception`, caso contrário `mcp_tool_node` engoliria o cancelamento e devolveria `"Erro na ferramenta..."`!
- Passar o `cancel_event` por registro indexado por um `request_id`/`run_id` ou via `ContextVar` (propagado automaticamente por `asyncio.to_thread` no Python 3.10+!) evita poluir o estado serializado pelo checkpointer SQLite (`threading.Event` não é serializável por msgpack/json no `AsyncSqliteSaver`!).

### Riscos Identificados

- **Colocar `threading.Event` dentro do `MultiAgentState` do LangGraph:** quebraria a serialização do `AsyncSqliteSaver`. Deve trafegar fora do estado persistido (via `ContextVar` + `configurable` não persistido ou registro em memória por execução).
- **`except Exception` em `mcp_tool_node` engolindo o cancelamento:** precisa de `except (asyncio.CancelledError, BIAgentCancelled): raise` explícito.

### Alternativas Consideradas

- Migrar todo o `BIAgent` para `async`/`ainvoke`: descartado neste slice por ser invasivo em todos os nós/testes existentes; o cancelamento cooperativo por `threading.Event` resolve o desperdício de cota entre etapas com risco mínimo.

---

## Notas e Comentarios

- Rastreabilidade: `Adito/docs/discovery/abortar-prompt-chat.md` → `Adito/docs/requirements/abortar-prompt-chat.md` (`FR04, FR08, BR01, BR04, BR05, NFR03, NFR04, A01, A02`).

---

## Definition of Done Checklist

- [ ] Codigo implementado conforme criterios de aceitacao
- [x] Decisao sobre Spec governada foi registrada
- [x] Decisao sobre Contract governado foi registrada
- [x] Nivel ScrumAIDev foi registrado
- [ ] Spec, Contract e BDD foram atualizados quando aplicavel
- [ ] Gates opcionais executados ou dispensados com justificativa
- [ ] Error handling observavel segue o padrao compartilhado quando aplicavel
- [ ] Code review aprovado
- [ ] Testes unitarios com cobertura adequada
- [ ] Testes de integracao e contract passando
- [ ] Documentacao atualizada
- [ ] Build/CI passando
- [ ] `Behavior change` documentado no PR
- [ ] Aprovacao do Product Owner
