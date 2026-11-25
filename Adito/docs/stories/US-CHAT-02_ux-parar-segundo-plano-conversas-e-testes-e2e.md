# User Story: [US-CHAT-02] UX de "Parar" / `Esc`, segundo plano por conversa/rota e testes Frontend/E2E

**Epic:** EPIC-12: Cancelamento de Prompts e Streaming em Segundo Plano no Chat
**GitHub Epic Issue:** -
**GitHub US Issue:** -
**Prioridade:** Alta (Vertical Slice 2)
**Story Points:** 5
**Sprint:** -
**Status:** Done
**Behavior Change Esperado:** YES

---

## Historia

**Como** usuário do Adito
**Eu quero** interromper uma resposta em andamento pelo botão **"Parar"** ou tecla **`Esc`**, continuar vendo o texto parcial com um aviso discreto e poder alternar entre conversas ou abas do app sem perder gerações em segundo plano
**Para que** eu nunca fique bloqueado esperando uma resposta lenta e consiga trabalhar em paralelo com produtividade.

### Contexto Adicional

Hoje `ChatInputArea.vue` exibe um spinner desabilitado durante o envio, `useChatApi.ts` mantém um único `isLoading` global sem `AbortController`, `useChatHistory.ts` perde o estado em memória quando o usuário sai da rota de Chat, e `ChatEstrategicoView.vue` atualiza `updateCurrentConversation` em vez do `conversationId` de origem do stream. Com a base cooperativa de `US-CHAT-01`, esta story entrega toda a experiência de cancelamento e segundo plano na interface do Adito.

### Pontos de Esclarecimento

Nenhum ponto pendente (todas as decisões de UX e segundo plano foram consolidadas em `Adito/docs/discovery/abortar-prompt-chat.md` e `Adito/docs/requirements/abortar-prompt-chat.md`).

---

## Criterios de Aceitacao

- [x] **Criterio 1 (`FR01`, `BR03`, `NFR01`, `NFR02`):** Enquanto a conversa aberta estiver gerando resposta, o botão "Enviar" em `ChatInputArea.vue` é substituído pelo botão **"Parar"** habilitado (ícone `Square`, `type="button"`, `aria-label="Parar geração"`, `title="Parar geração (Esc)"`), e pressionar **`Esc`** (quando nenhum modal estiver aberto) aciona o mesmo cancelamento em `< 200 ms`.
- [x] **Criterio 2 (`FR02`):** O `<textarea>` permanece editável durante o carregamento; ao clicar em **"Parar"** ou pressionar **`Esc`**, o botão "Enviar" fica disponível imediatamente sem limpar, alterar ou sobrescrever o texto que o usuário já estiver digitando.
- [x] **Criterio 3 (`FR03`, `BR01`, `A03`):** Ao abortar, a pergunta do usuário e qualquer texto parcial já recebido em streaming permanecem visíveis na conversa com um indicador/aviso discreto *"Resposta interrompida"* (visual neutro, distinto de erro vermelho, legível em tema claro e escuro). Se ainda não houver texto gerado, exibe apenas o aviso discreto de interrupção.
- [x] **Criterio 4 (`FR05`, `FR06`, `BR02`):** O estado de conversas e o mapa de streams ativos (`AbortController` por `conversationId`) vivem em estado compartilhado de módulo, sobrevivendo à troca de conversa, clique em "Nova conversa" e navegação para outras rotas (Dashboard, Meu Painel, Explorador, Configurações). Eventos (`onToken`, `onStatus`, `onResult`, finalização) atualizam exclusivamente a conversa de origem (migrando atomicamente `local-*` → `serverConversationId` sem roubar foco), a `ChatSidebar` exibe indicador discreto nas conversas em geração e outra conversa pode enviar/parar prompts em paralelo.
- [x] **Criterio 5 (`FR07`):** Excluir uma conversa com stream em andamento cancela automaticamente seu stream antes/junto da exclusão; um reinício/queda do núcleo (`503`) limpa o estado de carregamento dos streams afetados sem travar a UI.
- [x] **Criterio 6 (`FR09`, `NFR05`):** `tauriMock.ts` suporta `core_cancel` e streams pausáveis/canceláveis; o store compartilhado oferece função explícita de reset para testes; novos testes Vitest e Playwright E2E cobrem abortar por botão e por `Esc`, preservação do texto digitado, reenvio pós-abort, indicador de segundo plano na sidebar e troca de conversa/aba durante geração.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Comportamento observável de interface Vue 3 + gerenciamento de estado cliente, sem introdução de novo boundary de API ou contrato externo.
- **US exige Spec governada?** Nao
- **Justificativa da Spec:** US nao exige Spec governada adicional; os requisitos estáveis (`FR01–FR03`, `FR05–FR07`, `FR09`, `BR01–BR03`, `NFR01–NFR03`, `NFR05`, `A03`) já constam em `Adito/docs/requirements/abortar-prompt-chat.md`.
- **Spec prevista:** N/A
- **US exige Contract governado?** Nao
- **Justificativa do Contract:** Consome exclusivamente `chat.stream`, `core_cancel` e `chat.conversations.*` já existentes.
- **Contract previsto:** N/A
- **Padrao de erro aplicavel:** N/A (`CanceledError` tratado como interrupção neutra, não erro)
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** N/A
- **Touch List preliminar:**
  - `Adito/app/frontend-vue/src/modules/chat/types.ts`
  - `Adito/app/frontend-vue/src/modules/chat/composables/useChatHistory.ts`
  - `Adito/app/frontend-vue/src/modules/chat/composables/useChatApi.ts`
  - `Adito/app/frontend-vue/src/modules/chat/views/ChatEstrategicoView.vue`
  - `Adito/app/frontend-vue/src/modules/chat/components/ChatInputArea.vue`
  - `Adito/app/frontend-vue/src/modules/chat/components/ChatMessageBubble.vue`
  - `Adito/app/frontend-vue/src/modules/chat/components/ChatSidebar.vue`
  - `Adito/app/frontend-vue/tests/e2e/helpers/tauriMock.ts`
  - `Adito/app/frontend-vue/tests/unit/{core,useChatApi,useChatHistory,ChatInputArea}.spec.ts`
  - `Adito/app/frontend-vue/tests/e2e/chat.spec.ts`
- **Task Issues previstas:** N/A

---

## Mockups/Wireframes

- **Caixa de entrada (`ChatInputArea.vue`):** quando `loading === true`, o botão `#btn-send-chat` dá lugar ao botão `#btn-stop-chat` (ícone `Square` sólido em destaque suave/escuro com `aria-label="Parar geração"`), mantendo `<textarea>` habilitado e legenda *"Enter para enviar · Shift+Enter para nova linha · Esc para parar"* (quando em geração).
- **Bolha interrompida (`ChatMessageBubble.vue`):** mantém o texto parcial renderizado (se houver) + rodapé/badge discreto em tom neutro (`text-text-muted`): *"Resposta interrompida"*.
- **Sidebar (`ChatSidebar.vue`):** exibe pequeno indicador discreto (spinner/dot animado com `title="Gerando resposta..."`) ao lado do título das conversas que estão gerando em segundo plano.

---

## Notas Tecnicas

### Arquitetura

- **Componentes afetados:** `types.ts`, `useChatHistory.ts`, `useChatApi.ts`, `ChatEstrategicoView.vue`, `ChatInputArea.vue`, `ChatMessageBubble.vue`, `ChatSidebar.vue`.
- **APIs necessarias:** `stream(..., { signal })` de `common/api/core.ts` (atualizado em `US-CHAT-01`).
- **Database changes:** Nenhuma (`interrupted?: boolean` apenas em memória).
- **Referencias do modelo de dados:** N/A.
- **Erros observaveis esperados:** `error.name === 'CanceledError'` ou `error.status === 499` não deve produzir bolha `error: true` vermelha — deve finalizar o rascunho com `isLoading: false` e `interrupted: true`.

### Dependencias

- [ ] `US-CHAT-01` concluída (filtro pós-abort em `core.ts` + cancelamento cooperativo no núcleo Python).

### Consideracoes de Performance

- Usar `reactive(new Map<string, AbortController>())` ou `ref<Record<string, AbortController>>({})` em estado de módulo para rastrear streams ativos por `conversationId`, evitando re-renderizações desnecessárias em conversas não afetadas.
- Ao voltar à tela de Chat (re-montagem de `ChatEstrategicoView.vue`), evitar sobrescrever `conversations` com `syncFromBackend()` se já houver conversas hidratadas ou streams em andamento (só hidratar na primeira inicialização ou mesclar sem perder rascunhos em andamento).

---

## Plano de Testes

### Testes Unitarios

- [ ] Vitest (`useChatApi.spec.ts`): `askQuestionStream` suporta `conversationId` independente, `cancelStream(convId)` aborta apenas a conversa alvo e retorna/sinaliza cancelamento sem marcar `error: true`, e `migrateStreamKey(oldId, newId)` transfere o `AbortController` corretamente.
- [ ] Vitest (`useChatHistory.spec.ts`): `updateConversationById` atualiza conversa inativa sem afetar `currentConvId`; `replaceConversationId` migra ID de conversa inativa sem puxar foco; helper de reset limpa o estado entre testes.
- [ ] Vitest (`ChatInputArea.spec.ts`): exibe botão **"Parar"** durante `loading`, emite `cancel` ao clicar ou pressionar `Esc`, mantém texto digitado no `<textarea>`.

### Testes de Integracao

- [ ] Playwright E2E (`chat.spec.ts` com `tauriMock.ts`):
  - Enviar pergunta → receber texto parcial → clicar em **"Parar"** → manter texto parcial + *"Resposta interrompida"* → enviar 2ª pergunta imediatamente sem erro.
  - Enviar pergunta → digitar texto novo no input enquanto carrega → pressionar **`Esc`** → abortar sem apagar texto digitado.
  - Enviar pergunta na Conversa A → trocar para Nova conversa / navegar para Dashboard e voltar ao Chat → resposta da Conversa A conclui em segundo plano sem vazar para a Conversa B.
  - Excluir conversa em geração → `core_cancel` é disparado automaticamente.

### Testes de Contract

- [ ] N/A (sem alteração de contrato RPC).

### Testes Manuais

- [ ] Testar no app Tauri desktop real com provedor BYOK: enviar consulta analítica (BI Agent), clicar em "Parar" no meio, verificar no `backend.log` que etapas seguintes foram interrompidas, e enviar outra pergunta na sequência.

### BDD / Cenarios de Comportamento

- N/A (Nível ScrumAIDev 1).

---

## Tasks (Breakdown)

- [x] **[TASK-001]** Promover `useChatHistory` e `useChatApi` para estado compartilhado de módulo com mapa de streams por `conversationId`, migração `local-*` → servidor e helper de reset para testes
  - GitHub Task Issue: N/A
  - Estimativa: 2.5h
  - Assignee: -
- [x] **[TASK-002]** Atualizar `ChatInputArea.vue`, `ChatMessageBubble.vue`, `ChatSidebar.vue`, `ChatEstrategicoView.vue` e `types.ts` (botão Parar + `Esc` respeitando modais + aviso discreto + indicador na sidebar + cancelamento na exclusão)
  - GitHub Task Issue: N/A
  - Estimativa: 2.5h
  - Assignee: -
- [x] **[TASK-003]** Atualizar `tauriMock.ts` e adicionar testes Vitest + Playwright E2E + validar `npm run build`
  - GitHub Task Issue: N/A
  - Estimativa: 2h
  - Assignee: -

---

## IA Insights

### Sugestoes de Implementacao

- Como `useChatHistory()` hoje chama `syncFromBackend()` imediatamente quando instanciado, ao promover o estado para singleton de módulo devemos garantir um flag `initialized` (resetável em testes) para que navegar `Chat → Dashboard → Chat` não dispare um `syncFromBackend()` que atropelaria o rascunho em streaming da conversa em segundo plano!
- No `ChatEstrategicoView.vue`, registrar o listener de `keydown` (`Esc`) no `onMounted` / limpar no `onUnmounted`, checando `!conversationToDelete.value && !pinModalOpen.value && isCurrentConvLoading.value`.

### Riscos Identificados

- **Sobrescrita do rascunho em andamento ao voltar para `/chat`:** mitigado guardando `hasSynced` no store compartilhado e não substituindo `conversations` quando já carregadas/com stream ativo.
- **Testes unitários existentes (`useChatHistory.spec.ts`, `useChatApi.spec.ts`) vazando estado entre si:** mitigado expondo `resetChatHistoryForTests()` / `resetChatApiForTests()` e chamando no `beforeEach` das specs.

### Alternativas Consideradas

- Usar `<KeepAlive>` no `RouterView` em vez de promover o estado dos composables: menos robusto (depende de nomes de componente e não protege o estado caso o usuário acesse diretamente/reinicialize a rota), enquanto promover o estado nos composables segue o mesmo padrão já usado em `useAuth.ts` e `useContextos.ts`.

---

## Notas e Comentarios

- Rastreabilidade: `Adito/docs/discovery/abortar-prompt-chat.md` → `Adito/docs/requirements/abortar-prompt-chat.md` (`FR01–FR03, FR05–FR07, FR09, BR01–BR03, NFR01–NFR03, NFR05, A03`).

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
