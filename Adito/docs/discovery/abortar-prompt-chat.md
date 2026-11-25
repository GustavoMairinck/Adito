# Discovery — Abortar Prompts em Andamento no Chat (com Execução em Segundo Plano por Conversa)

**Status:** PROBLEM_READY
**Classificacao de Processo:** NORMAL PROCESS
**Origem:** hibrido (usuario + codigo)
**Data:** 2026-11-25
**Branch:** `feat/abortar-prompt-chat`

## Intent
Permitir que o usuário do Adito interrompa a qualquer momento uma pergunta em processamento no chat (via botão **"Parar"** ou tecla **`Esc`**) e envie imediatamente um novo prompt, além de poder alternar entre conversas ou outras telas do app sem perder ou corromper o processamento em andamento.

## Problem
Hoje, ao enviar uma pergunta no chat do Adito:
1. O usuário fica bloqueado até o núcleo finalizar toda a execução do grafo LangGraph/BI Agent (que pode levar vários segundos em consultas SQL com múltiplas chamadas ao LLM ou quando o provedor está lento/com erro intermitente), sem nenhum botão ou atalho para interromper.
2. O estado de carregamento (`isLoading`) e o destino das atualizações (`updateCurrentConversation`) são globais à instância de `ChatEstrategicoView.vue`, impedindo controle independente por conversa e causando risco de perda de estado ao sair da rota de Chat ou vazamento de eventos ao trocar de conversa durante um stream.
3. Embora o protocolo STDIO (`$cancel` em `rpc/server.py`), o Tauri (`core_cancel` em `src-tauri/src/lib.rs`) e a bridge (`AbortSignal` em `common/api/core.ts`) já possuam suporte básico a cancelamento, o chat não utiliza `AbortController`, eventos atrasados podem vazar pós-abort no `core.ts`, e o `BIAgent` roda de forma síncrona em thread (`self.app.invoke(...)`), continuando a consumir chamadas à API do LLM mesmo após `task.cancel()`.

## Users / Stakeholders relevantes
- **Usuários finais do Adito (gestores, coordenadores e pesquisadores do IFES):** precisam corrigir rapidamente perguntas mal formuladas, cancelar consultas lentas e alternar entre conversas/abas sem perder produtividade ou desperdiçar cota da chave de API (BYOK).
- **Equipe de manutenção do Adito:** precisa manter o protocolo STDIO/Tauri simples, o checkpointer SQLite do LangGraph íntegro após cancelamentos e a suíte de testes (Python, Vitest, Playwright e contrato RPC) verde.

## Current Situation
- `rpc/server.py` aceita `{"method": "$cancel", "params": {"id": <rid>}}`, cancela a task `asyncio` e responde com status `499`.
- `src-tauri/src/lib.rs` expõe `core_cancel(id)` escrevendo `$cancel` no `stdin` do núcleo.
- `common/api/core.ts` aceita `signal?: AbortSignal` em `stream()`, mas `channel.onmessage` não ignora eventos que cheguem depois de `signal` abortar.
- `useChatApi.ts` mantém um único `isLoading = ref(false)` sem `AbortController` nem função `cancelStream`.
- `useChatHistory.ts` cria `conversations` e `currentConvId` dentro da instância do componente (resetando ao desmontar `ChatEstrategicoView.vue`), e `ChatEstrategicoView.vue` aplica eventos do stream sobre `updateCurrentConversation` em vez do `conversationId` de origem.
- `ChatInputArea.vue` exibe `<Loader2>` desabilitado no lugar do botão enviar durante `loading`, sem botão "Parar" nem atalho `Esc`.
- `rpc/chat.py` persiste `user_message` antes do grafo, propaga `asyncio.CancelledError`, mas `agents/bi_agent/agent.py` executa `self.app.invoke(...)` síncrono sem checagem cooperativa de cancelamento entre seus nós.

## Desired Outcome
- O usuário consegue clicar em **"Parar"** (ou pressionar **`Esc`**) enquanto uma conversa está gerando resposta, interrompendo imediatamente a geração daquela conversa e liberando o envio do próximo prompt sem perder o que já estiver digitando.
- Na tela, permanecem visíveis a pergunta do usuário e o texto parcial já recebido em streaming (se houver) com aviso discreto *"Resposta interrompida"* (sem erro vermelho), sem persistir resposta incompleta da IA no `app.db`.
- O usuário pode trocar de conversa na barra lateral, abrir "Nova conversa" ou navegar para outras abas (Dashboard, Meu Painel, Explorador, Configurações) enquanto uma conversa continua gerando em segundo plano (com indicador visual na lista de conversas), podendo inclusive enviar/parar prompts em outra conversa em paralelo.
- O núcleo Python interrompe cooperativamente as próximas etapas do `BIAgent` após `$cancel` (poupando cota de API) e mantém o checkpointer SQLite íntegro para a próxima pergunta na mesma conversa.

## Success Criteria
- Clicar em **"Parar"** ou pressionar **`Esc`** durante o streaming cancela o prompt ativo daquela conversa em < 200 ms na UI, mantém texto parcial (se houver) + indicador discreto *"Resposta interrompida"*, não grava resposta incompleta no `app.db` e libera o envio imediato de nova pergunta sem alterar o texto já digitado no campo.
- Enviar uma nova pergunta na mesma conversa imediatamente após abortar funciona sem erro e sem misturar eventos/tokens do stream cancelado.
- Alternar para outra conversa ou outra tela (Dashboard/Configurações) mantém o stream da conversa original ativo em segundo plano, atualizando apenas a conversa de origem, exibindo indicador de carregamento na sidebar e permitindo operar outra conversa em paralelo.
- Excluir uma conversa em andamento ou reiniciar o núcleo (ex.: troca de chave/provedor) cancela/encerra o stream da conversa afetada com segurança.
- No backend Python, cancelar durante a execução do `BIAgent` interrompe antes da próxima etapa LLM/SQL (comprovado por teste unitário com `cancel_event`).
- Todas as suítes automatizadas (Python `unittest`, contrato RPC, Vitest, build e Playwright E2E) passam sem regressões, com novos testes cobrindo abortar, reenvio pós-abort e execução em segundo plano.

## Scope

### IN
- **Bridge IPC (`common/api/core.ts`):** encerrar entrega de eventos no `channel.onmessage` imediatamente quando `options.signal` abortar, evitando eventos atrasados após `CanceledError`.
- **Estado compartilhado de conversas e streams por conversa (`useChatHistory.ts` / `useChatApi.ts` / `ChatEstrategicoView.vue`):**
  - Promover estado de conversas e mapa de streams ativos (`AbortController` + status de carregamento por `conversationId`) para estado compartilhado de módulo que sobrevive à troca de rotas no Vue Router.
  - Vincular atualizações de rascunho/tokens/status/resultado ao `conversationId` de origem (inclusive ao migrar `local-*` → ID real do servidor), nunca ao `currentConvId` atual.
  - Cancelar automaticamente o stream de uma conversa ao excluí-la; limpar streams ativos caso o núcleo reinicie/encerre.
- **UX do Chat (`ChatInputArea.vue`, `ChatMessageBubble.vue`, `ChatSidebar.vue`, `ChatEstrategicoView.vue`):**
  - Substituir o botão "Enviar" pelo botão **"Parar"** (ícone stop, acessível com `aria-label="Parar geração"`) enquanto a conversa atual estiver gerando + atalho **`Esc`**.
  - Campo de texto sempre livre para digitar durante o carregamento; não limpar/sobrescrever o texto ao abortar.
  - Exibir estado discreto *"Resposta interrompida"* na bolha da IA (mantendo texto parcial já recebido se houver, sem estilo de erro vermelho) e sem gravar resposta incompleta no `app.db`.
  - Exibir indicador discreto de carregamento na conversa ativa em segundo plano na `ChatSidebar`.
- **Cancelamento cooperativo no núcleo Python (`rpc/chat.py`, `agents/orchestrator/`, `agents/bi_agent/`):**
  - Propagar `cancel_event: threading.Event` da task `chat.stream` (setado no `except asyncio.CancelledError:` / `finally`) até o `BIAgent`, verificando antes de cada etapa custosa (RAG, resolvedor de valores, geração/correção SQL, execução SQL e geração de resposta).
  - Validar/garantir que abortar uma execução não corrompe o estado da `thread_id` no checkpointer SQLite do LangGraph para a pergunta seguinte.
- **Testes e Mock E2E:**
  - Suporte a `core_cancel` e stream pausável/cancelável no `tauriMock.ts`.
  - Testes unitários Python (`core/tests.py`), Vitest (`useChatApi.spec.ts`, `ChatInputArea.spec.ts` / `useChatHistory.spec.ts`) e Playwright E2E cobrindo abortar (botão + `Esc`), reenvio imediato e troca de conversa/rota durante geração.

### OUT
- Migração completa de todos os nós do `BIAgent` de síncrono para `async`/`ainvoke` para derrubar requisições HTTP já em voo no milissegundo do clique (o cancelamento cooperativo entre etapas já evita novas chamadas LLM/SQL sem reescrever todo o `bi_agent`).
- Botão "Editar e reenviar última pergunta" ou edição de histórico de mensagens anteriores.
- Persistência de respostas parciais/interrompidas no `app.db` (decisão explícita: manter apenas em memória na sessão atual, sem gravar resposta incompleta no banco).
- Fila automática de prompts pendentes (enfileirar 2ª pergunta para disparar sozinha ao terminar a 1ª).

### LATER
- Migrar nós do `BIAgent` para `ainvoke` assíncrono nativo se futuramente houver necessidade de cortar uma única chamada HTTP muito longa no meio do voo.
- Opção de botão "Tentar novamente" na bolha interrompida.

## Constraints / Feasibility
- **Protocolo STDIO + Tauri já existentes:** `$cancel` e `core_cancel` já existem e não exigem quebra de contrato RPC (`teste_contrato.py` permanece compatível).
- **Sem novas dependências externas:** tudo usa recursos nativos (`AbortController`, Vue 3 reactivity, `asyncio`, `threading.Event`, `lucide-vue-next`).
- **Threads em Python:** `asyncio.CancelledError` não interrompe código síncrono dentro de `asyncio.to_thread`; por isso o `threading.Event` cooperativo é indispensável no `BIAgent`.
- **SQLite / Checkpointer:** escritas concorrentes em `app.db` (duas conversas rodando em paralelo) continuam usando WAL/transações curtas; o `AsyncSqliteSaver` do LangGraph isola estado por `thread_id`, mas é preciso testar explicitamente cancelamento + nova pergunta na mesma `thread_id` e duas conversas concorrentes.

## Assumptions
- `[ASSUMPTION]` Como `prepare_conversation` grava `user_message` no `app.db` antes de acionar o grafo, ao recarregar o app após abortar, a pergunta do usuário permanece no histórico sem resposta da IA (sem resposta incompleta gravada).
- `[ASSUMPTION]` O atalho `Esc` só cancela a geração quando não há modal aberto na tela de chat (ex.: modal de exclusão de conversa ou de pin no dashboard têm prioridade sobre o `Esc`).
- `[ASSUMPTION]` Não há necessidade de alterar o backend Rust (`src-tauri/src/lib.rs`), pois `core_cancel` já envia `$cancel` corretamente — apenas verificar/testar se `Pending::Stream` precisa de algum ajuste de limpeza em `lib.rs` (se não precisar, mantém intacto).

## Risks
- **Vazamento de eventos atrasados entre `core_cancel` e a parada real do Python:** mitigado travando `settled = true` em `core.ts` no `onAbort` e vinculando handlers ao `streamId`/`conversationId`.
- **Corrida na migração de ID `local-*` → ID real do servidor:** se o usuário trocar de conversa antes do primeiro evento `status` trazer `conversation_id`, o mapa de streams ativos precisa migrar a chave `local-*` → `serverConversationId` atomicamente sem mudar `currentConvId` (a menos que o usuário ainda esteja olhando aquela conversa).
- **Estado parcial no checkpointer do LangGraph após `CancelledError`:** mitigado validando em teste de integração em `core/tests.py` o ciclo completo `perguntar → cancelar → perguntar de novo na mesma conversa`.
- **Estado global compartilhado em testes Vitest:** ao promover `useChatHistory` / `useChatApi` para estado compartilhado de módulo, expor helper de reset para testes unitários (`__resetChatStoreForTests` ou similar) para não vazar estado entre specs do Vitest.

## Open Questions
- *Nenhuma pergunta bloqueante aberta* — todas as decisões de UX, persistência, segundo plano e profundidade de cancelamento foram alinhadas com o usuário.

## Review & Adjust

- [x] Usuario revisou a proposta completa
- [x] Alteracoes solicitadas foram incorporadas
- [x] Decisoes relevantes foram confirmadas
- [x] Nao existem perguntas bloqueantes abertas

### User adjustments
- Proposta aprovada integralmente pelo usuário no Checkpoint D1 (2026-11-25).

## Gate G0 — PROBLEM READY

**Status:** APPROVED

**Aprovado pelo usuario:** sim
