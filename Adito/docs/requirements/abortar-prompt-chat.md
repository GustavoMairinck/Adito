# Requirements — Abortar Prompts em Andamento no Chat (com Execução em Segundo Plano por Conversa)

**Status:** REQUIREMENTS_READY
**Discovery de origem:** `Adito/docs/discovery/abortar-prompt-chat.md`
**Classificacao de Processo:** NORMAL PROCESS
**Data:** 2026-11-25

## Intent Summary
Entregar ao usuário controle imediato para interromper respostas em andamento no chat do Adito (botão **"Parar"** ou tecla **`Esc`**) sem perder texto digitado nem corromper o histórico, permitindo também alternar livremente entre conversas e telas do app enquanto gerações continuam em segundo plano na conversa de origem e garantindo parada cooperativa no agente de BI para economizar cota de API.

## Functional Requirements
- **FR01 (Botão "Parar" e atalho `Esc`):** Enquanto a conversa aberta estiver gerando uma resposta, o botão "Enviar" em `ChatInputArea.vue` deve ser substituído por um botão **"Parar"** habilitado (ícone de stop, `aria-label="Parar geração"`), e pressionar **`Esc`** (quando nenhum modal estiver aberto) deve disparar o mesmo cancelamento da conversa aberta.
- **FR02 (Input livre e reenvio imediato):** O campo de texto permanece editável durante o carregamento; ao abortar, o envio de uma nova pergunta na conversa deve ser liberado imediatamente sem apagar, alterar ou sobrescrever qualquer texto que o usuário já esteja digitando.
- **FR03 (Estado visual de resposta interrompida):** Ao abortar uma geração, a UI deve manter visíveis na conversa a pergunta do usuário e qualquer texto parcial já recebido em streaming, acompanhados de um aviso discreto (*"Resposta interrompida"*, sem estilo de erro vermelho). Se ainda não houver texto gerado, deve exibir apenas o aviso discreto de interrupção.
- **FR04 (Filtro de eventos pós-abort no IPC bridge):** Em `common/api/core.ts`, ao acionar `options.signal.abort()`, a função `stream()` deve enviar `core_cancel` para o Tauri, encerrar imediatamente o recebimento no `channel.onmessage` (`settled = true`) e rejeitar com `CanceledError`, impedindo que eventos atrasados (`token`, `status`, `result`, `error`) cheguem aos callbacks.
- **FR05 (Isolamento de stream por conversa e migração de ID):** O controle de carregamento e `AbortController` deve ser indexado por `conversationId` (nunca por uma única flag global `isLoading`), vinculando `onToken`, `onStatus`, `onResult` e finalização exclusivamente à conversa de origem — migrando atomicamente a chave do stream quando uma conversa nova (`local-*`) receber seu `conversation_id` real do servidor.
- **FR06 (Execução em segundo plano entre conversas e rotas):** Promover o estado de conversas e streams ativos para estado compartilhado de módulo (sobrevivendo à desmontagem de `ChatEstrategicoView.vue` ao navegar para Dashboard, Meu Painel, Explorador ou Configurações). Trocar de conversa ou abrir "Nova conversa" não cancela o stream da conversa anterior; a `ChatSidebar` deve exibir indicador discreto de carregamento nas conversas em processamento, e o usuário pode enviar/cancelar prompts em outra conversa em paralelo.
- **FR07 (Cancelamento automático em exclusão de conversa e reinício do núcleo):** Excluir uma conversa que esteja com stream ativo deve abortar o stream dela antes/junto da exclusão; um reinício ou queda do núcleo (status `503`) deve limpar os streams ativos afetados sem deixar a UI travada em carregamento.
- **FR08 (Cancelamento cooperativo no núcleo Python e `BIAgent`):** Ao receber `$cancel` (`asyncio.CancelledError`) em `rpc/chat.py`, o núcleo deve sinalizar um `cancel_event: threading.Event` propagado ao `BIAgent` (via estado/contexto da execução), interrompendo antes da próxima etapa custosa (extrator RAG, resolvedor de valores, gerador SQL, corretor SQL, execução SQL e gerador de resposta) e sem persistir resposta incompleta no `app.db`.
- **FR09 (Suporte a cancelamento no Mock E2E e cobertura de testes):** Atualizar `tauriMock.ts` para suportar `core_cancel` e streams controláveis, adicionar testes unitários Python (`core/tests.py`), testes unitários frontend (Vitest) e cenários Playwright E2E cobrindo abortar (botão + `Esc`), reenvio pós-abort e troca de conversa/rota em segundo plano.

## Business / Domain Rules
- **BR01 (Sem resposta incompleta no `app.db`):** Uma geração abortada pelo usuário nunca deve chamar `persist_assistant_response` nem gravar mensagem `assistant` incompleta ou `QueryExecution` órfã no banco `app.db`.
- **BR02 (Isolamento entre conversas):** Eventos de streaming de uma conversa nunca podem ser renderizados ou gravados em outra conversa, mesmo quando o usuário troca de conversa antes do primeiro evento `status` retornar o ID do servidor.
- **BR03 (Prioridade de modais para `Esc`):** Pressionar `Esc` só aciona o cancelamento da geração quando não há modal aberto sobre o chat (ex.: `ConfirmModal` de exclusão ou `DashboardPinDialog`).
- **BR04 (Integridade do checkpointer pós-cancelamento):** Abortar uma pergunta não pode corromper o `thread_id` no `AsyncSqliteSaver` do LangGraph; a pergunta seguinte na mesma conversa deve executar normalmente.
- **BR05 (Preservação de cota de API BYOK):** Após `$cancel`, o `BIAgent` não deve iniciar novas chamadas ao provedor de LLM nem novas queries SQL para a requisição cancelada.

## Non-Functional Requirements
- **NFR01 (Responsividade da UI ao cancelar):** O feedback visual de interrupção e a liberação do botão "Enviar" devem ocorrer em `< 200 ms` após o clique em **"Parar"** ou tecla **`Esc`**, sem esperar o término de uma requisição HTTP em andamento no backend.
- **NFR02 (Acessibilidade):** O botão **"Parar"** deve ter `type="button"`, `aria-label="Parar geração"` e `title="Parar geração (Esc)"`; o aviso de *"Resposta interrompida"* deve ser legível em tema claro e escuro.
- **NFR03 (Zero novas dependências externas):** Implementação exclusivamente com recursos já presentes no repositório (`AbortController`, Vue 3, `lucide-vue-next`, `asyncio`, `threading.Event`).
- **NFR04 (Compatibilidade de contrato RPC):** O contrato existente em `scripts/teste_contrato.py` e `referencia.json` deve permanecer 100% compatível sem quebra de assinatura.
- **NFR05 (Isolamento em testes unitários):** O estado compartilhado do chat no frontend deve oferecer função explícita de reset para testes (Vitest), evitando vazamento de estado entre casos de teste.

## User Scenarios

### Main flow
1. Usuário envia uma pergunta no chat; o botão "Enviar" muda para **"Parar"** (ícone stop) e a bolha da IA exibe o status de processamento (e tokens parciais, quando conversacional).
2. Antes de concluir, o usuário clica em **"Parar"** (ou pressiona **`Esc`**).
3. Em `< 200 ms`, a UI interrompe o stream, mantém a pergunta e qualquer texto parcial recebido com o aviso discreto *"Resposta interrompida"*, e volta o botão para "Enviar".
4. O usuário envia imediatamente uma nova pergunta na mesma conversa; o backend processa normalmente e devolve a nova resposta sem misturar eventos antigos.

### Alternative / Error / Edge cases
- **Abortar antes do primeiro token (ex.: durante `Roteando pergunta...` ou `Consultando dados...`):** a bolha de rascunho deixa de girar e mostra apenas o aviso discreto *"Resposta interrompida"*, sem texto vazio quebrado nem estilo de erro vermelho.
- **Usuário digitando o próximo prompt enquanto carrega:** clicar em **"Parar"** (ou `Esc`) libera o botão "Enviar" preservando exatamente o que o usuário já digitou no `<textarea>`.
- **Trocar de conversa ou abrir "Nova conversa" durante a geração:** a conversa A continua gerando em segundo plano (com indicador discreto na `ChatSidebar`), o usuário vê a conversa B sem spinner e pode enviar/abortar um prompt na conversa B em paralelo.
- **Migração `local-*` → ID real em segundo plano:** o usuário envia na conversa nova `local-123` e muda imediatamente para outra conversa antes do primeiro `status`; quando o `status` chega com `conversation_id = "42"`, apenas a conversa `local-123` é migrada para `"42"` e continua recebendo os eventos, sem puxar o foco do usuário.
- **Navegar para outra aba (Dashboard / Configurações) e voltar ao Chat:** o stream continua em segundo plano; ao voltar para o Chat, a conversa exibe o andamento atual ou a resposta já concluída.
- **Excluir conversa enquanto ela gera:** ao confirmar exclusão no modal, o stream daquela conversa é abortado imediatamente e a conversa é removida.
- **Cancelamento durante `BIAgent` multi-etapas:** `$cancel` ativa `cancel_event`; se o `BIAgent` estava no `query_extractor` ou `sql_generator`, ao terminar a chamada síncrona corrente ele detecta `cancel_event.is_set()` e aborta antes de disparar o próximo nó/chamada ao LLM, não gravando nada no `app.db`.
- **Reinicio do núcleo (troca de chave/provedor) durante geração:** a falha `503` encerra o stream de forma limpa e remove o estado de carregamento.

## Business / Domain Context
O Adito usa BYOK (chave de API do próprio usuário em provedores como Gemini, OpenAI, Mistral, etc.), onde consultas analíticas no `BIAgent` disparam múltiplas chamadas sequenciais ao LLM. Permitir abortar rapidamente protege tanto a experiência de uso quanto a cota/custo da chave do usuário, enquanto a execução em segundo plano por conversa aproxima a experiência dos chats modernos sem bloquear o trabalho em outras conversas ou no Dashboard.

## Technical Context & Constraints
- **Frontend (`Adito/app/frontend-vue/`):**
  - `src/common/api/core.ts` (`stream`, `withAbort`, `core_cancel`).
  - `src/modules/chat/composables/useChatHistory.ts` e `useChatApi.ts` (promoção para estado compartilhado + mapa de streams por `conversationId` + helper de reset para testes).
  - `src/modules/chat/views/ChatEstrategicoView.vue`, `components/ChatInputArea.vue`, `components/ChatMessageBubble.vue`, `components/ChatSidebar.vue`, `types.ts`.
  - `tests/e2e/helpers/tauriMock.ts` e specs Vitest / Playwright.
- **Backend Python (`Adito/app/backend/nucleo/`):**
  - `rpc/server.py` (`$cancel` já implementado — validar/testar).
  - `rpc/chat.py` (`chat_stream`, criação e disparo de `cancel_event`, tratamento de `CancelledError` sem persistir resposta parcial).
  - `agents/orchestrator/graph.py` e `agents/bi_agent/` (`tool.py`, `agent.py`, `graph.py` / nós) com checagem cooperativa de `cancel_event` (ex.: `ContextVar` ou parâmetro propagado ao `BIAgent` + `CancelledError` dedicada / `BIAgentCancelled`).
- **Desktop Rust (`Adito/app/src-tauri/src/lib.rs`):**
  - `core_cancel` já implementado; apenas verificar se `Pending::Stream` responde/limpa adequadamente quando o Python envia `499`.

## Quality Attributes
- **Confiabilidade:** nenhuma corrida de estado entre conversas concorrentes ou streams cancelados.
- **Usabilidade / Acessibilidade:** botão claro, atalho `Esc` previsível e não-destrutivo para o texto digitado.
- **Testabilidade:** estado compartilhado resetável em Vitest, mock determinístico no Playwright e `cancel_event` testável sem rede no `unittest` Python.

## Assumptions
- **A01:** Como `prepare_conversation` grava `user_message` no `app.db` antes de invocar o grafo, ao reabrir o app após um abortar a pergunta do usuário permanece no histórico sem resposta da IA (sem gravar resposta incompleta).
- **A02:** `src-tauri/src/lib.rs` já implementa `core_cancel` corretamente e só será alterado se os testes revelarem alguma borda pendente no ciclo `core_cancel` → `499`.
- **A03:** O estado de resposta interrompida (`interrupted?: boolean` em `ChatMessage`) vive apenas em memória na sessão atual (não exige migração de schema no `app.db`).

## Out of Scope
- Reescrever todos os nós do `BIAgent` para chamadas HTTP assíncronas (`ainvoke`) para derrubar requisição HTTP já em voo.
- Persistir respostas parciais/interrompidas no `app.db`.
- Editar/reenviar perguntas antigas do histórico ou enfileirar automaticamente prompts pendentes.

## Open Questions
- *Nenhuma pergunta bloqueante aberta.*

## Key Decisions Proposed
- **KD01 (Cancelamento cooperativo via `threading.Event`):** Em vez de reescrever todo o `BIAgent` para `async`, propagar um `cancel_event` verificado antes de cada nó custoso do grafo do `BIAgent` (parando imediatamente entre etapas e evitando novas chamadas ao LLM/SQL).
- **KD02 (Estado de chat compartilhado no módulo com mapa por `conversationId`):** Promover `conversations`, `currentConvId` e o controle de streams (`AbortController` por conversa) para estado de módulo em `useChatHistory` / `useChatApi`, garantindo continuidade ao trocar de conversa ou de aba e isolamento por `conversationId` de origem (com reset explícito para testes Vitest).
- **KD03 (Interrupção efêmera na UI, sem poluir `app.db`):** Representar a interrupção com `interrupted: true` na `ChatMessage` em memória (com estilo neutro/discreto, não erro vermelho) e não chamar `persist_assistant_response` quando `CancelledError` ocorrer.

## Review & Adjust

O usuario pode **aprovar, editar, adicionar, remover ou reclassificar** qualquer requisito/regra antes do gate.

- [x] Proposta completa apresentada ao usuario
- [x] Ajustes solicitados incorporados
- [x] IDs estabilizados depois da revisao
- [x] Nenhuma pergunta bloqueante aberta

### User adjustments
- Proposta aprovada integralmente pelo usuário no Checkpoint R1 (2026-11-25).

## Gate G1 — REQUIREMENTS READY

**Status:** APPROVED

**Aprovado pelo usuario:** sim
