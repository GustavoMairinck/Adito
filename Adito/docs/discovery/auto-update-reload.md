# Discovery — Atualização Automática (Opt-in) e Auto-Reload de Telas no Adito

**Status:** PROBLEM_READY
**Classificacao de Processo:** NORMAL PROCESS
**Origem:** hibrido (usuario + codigo)
**Data:** 2026-11-25
**Branch:** `feat/auto-update-reload`

## Intent
Permitir que usuários do Adito que desejem manter o aplicativo e a base de dados sempre atualizados sem cliques manuais possam ativar a **atualização automática (opt-in)** em Configurações — baixando novas versões do executável e do `dados.db` em segundo plano com segurança (sem interromper perguntas em andamento no chat) e recarregando automaticamente as telas abertas (Dashboard, Meu painel, Contextos/Chat e Administração) assim que os dados novos estiverem prontos.

## Problem
Hoje o mecanismo de distribuição do Adito (`useAtualizacoes.ts`, `AtualizacaoDisponivel.vue`, `atualizacoes.ts`) apresenta quatro limitações operacionais:
1. A verificação de novas versões ocorre **uma única vez** ao abrir o aplicativo; quem mantém o Adito aberto por horas/dias não descobre novas publicações até fechar e reabrir.
2. Sempre exige múltiplos cliques manuais no rodapé da barra lateral ("Atualização disponível" → "Atualizar o app" e, separadamente, "Atualizar os dados"), mesmo quando o usuário preferiria que o app se mantivesse atualizado sozinho.
3. Após atualizar o `dados.db` (mesmo no fluxo manual atual), as telas já abertas (**Dashboard**, **Meu painel**, **Contextos/Chat** e **Administração**) não recarregam automaticamente os novos dados — obrigando o usuário a clicar no ícone de atualização (`RefreshCw`) ou trocar de aba.
4. Não há proteção explícita ligando o reinício do app/núcleo ao estado de streams ativos no chat (`useChatApi.isLoading`), o que poderia interromper uma resposta em geração caso uma atualização automática reiniciasse no momento errado.

## Users / Stakeholders relevantes
- **Usuários finais do Adito (gestores, coordenadores e pesquisadores do IFES):** querem ter sempre a versão e os dados acadêmicos mais recentes sem lembrar de clicar em atualizações manuais, mas sem ter uma reunião ou consulta no chat interrompida de surpresa.
- **Equipe de manutenção do Adito:** quer acelerar a adoção de correções e cargas de `dados.db` mantendo a política conservadora da `ADR-0006` (modo assistido por padrão) e evitando consumo indevido de cota de API BYOK (sem reindexação automática de embeddings).

## Current Situation
- `MainLayout.vue` chama `useAtualizacoes().verificar()` uma única vez no `onMounted`.
- `useAtualizacoes.ts` verifica `dadosVerificar()` e `appVerificar()` (`tauri-plugin-updater`) e expõe `temAtualizacao` para `AtualizacaoDisponivel.vue`.
- `appInstalar()` faz `downloadAndInstall()` seguido imediatamente de `relaunch()` (sem separação de etapa de download vs. reinício controlado e sem contagem regressiva/adiamento).
- `dadosInstalar()` baixa/troca `dados.db`, reinicia o núcleo Python no Rust (`dados.rs` / `lib.rs`) e espera `coreReady()`, mas não notifica as telas abertas para recarregarem seus dados.
- `ADR-0006` documenta apenas o modo assistido manual.

## Desired Outcome
- Usuários podem ligar (em **Configurações**, desligado por padrão) **"Atualização automática (app e dados)"** para receber atualizações sem cliques manuais.
- O Adito verifica silenciosamente novas versões ao abrir, a cada **30 minutos** e ao retornar foco para a janela (cooldown de **15 minutos**).
- Com o modo automático ligado:
  - Se houver **nova versão do executável**, baixa e prepara em segundo plano (priorizando o executável sobre `dados.db` quando ambos existem), aguarda o chat ficar livre (`!useChatApi.isLoading`), exibe contagem regressiva discreta de **10 segundos** (*"Nova versão vX.Y.Z pronta — reiniciando em 10s..."* com **"Reiniciar agora"** e **"Adiar"**) e reinicia automaticamente ao zerar.
  - Se não houver update de executável pendente e houver **`dados.db` novo** com chave válida no cofre (`!precisa_chave` e `!desenvolvimento`), aguarda o chat ficar livre e instala `dados.db` em segundo plano.
- Sempre que `dados.db` for atualizado (no modo automático **ou** manual), um sinal reativo compartilhado (`dadosReloadSeq`) dispara o recarregamento automático de **Dashboard**, **Meu painel**, **Contextos/Chat** e **Administração**, exibindo um toast discreto (*"Dados atualizados para a versão X"*).
- Embeddings/RAG **nunca** são reindexados automaticamente (preservando a cota BYOK do usuário).

## Success Criteria
- A opção **"Atualização automática (app e dados)"** existe em `ConfiguracoesView.vue`, inicia **desligada por padrão** (preservando 100% do comportamento assistido da `ADR-0006`) e persiste em `localStorage`.
- Com o modo automático ligado, novas versões do executável são baixadas em segundo plano, aguardam streams ativos do chat terminarem, mostram contagem de 10s com "Reiniciar agora" / "Adiar" e executam `relaunch()` ao zerar (e "Adiar" cancela o reinício automático daquela versão).
- Quando executável e `dados.db` têm atualização simultânea, o executável é priorizado primeiro.
- Com o modo automático ligado e apenas `dados.db` novo (com chave válida no cofre e fora de desenvolvimento), o banco é atualizado automaticamente quando o chat estiver livre, incrementando `dadosReloadSeq`, recarregando automaticamente Dashboard / Meu painel / Contextos / Administração e exibindo toast discreto.
- No modo manual, atualizar `dados.db` também dispara o auto-reload das telas abertas via `dadosReloadSeq`.
- Verificação periódica (30 min) e por foco/visibilidade (cooldown 15 min) não cria chamadas concorrentes nem exibe erro quando offline.
- Adenda registrada na `Docs/ADR/ADR-0006-empacotamento-e-auto-update-desktop.md` e todas as suítes (Vitest, build, Playwright E2E, Python e Rust) passam verdes.

## Scope

### IN
- **Preferência opt-in em `ConfiguracoesView.vue` + `useAtualizacoes.ts`:** toggle **"Atualização automática (app e dados)"** (default `false`), persistido em `localStorage`.
- **Agendador de verificação em `useAtualizacoes.ts` + `MainLayout.vue`:** checagem no startup + intervalo de 30 min + `visibilitychange`/`focus` com cooldown de 15 min, sem concorrência e silencioso quando offline.
- **Fluxo automático de executável (`atualizacoes.ts` + `useAtualizacoes.ts` + banner discreto):** separar download/instalação (`downloadAndInstall`) de `relaunch()` para poder aguardar `!useChatApi.isLoading` e exibir a contagem regressiva de 10s com **"Reiniciar agora"** e **"Adiar"** (priorizando executável quando houver app + dados novos juntos).
- **Fluxo automático de `dados.db` + sinal `dadosReloadSeq`:** atualização silenciosa quando `!precisa_chave && !desenvolvimento && !app && !isChatLoading`; incremento de `dadosReloadSeq` (tanto no modo automático quanto manual) observado por `DashboardView.vue`, `MeuDashboardView.vue`, `useContextos.ts` / `ChatEstrategicoView.vue` e `AdminView.vue`, com toast discreto de confirmação.
- **Governança:** adenda na `Docs/ADR/ADR-0006-empacotamento-e-auto-update-desktop.md` documentando o modo opt-in.
- **Testes:** novos testes Vitest (`useAtualizacoes.spec.ts`, `ConfiguracoesView.spec.ts`), suporte no `tauriMock.ts` para mock de atualização do app e testes Playwright E2E em `atualizacoes.spec.ts`.

### OUT
- Reindexação automática de embeddings/RAG (evita consumo silencioso de cota BYOK do usuário).
- Alterações no formato criptográfico do `dados.db.enc` ou no protocolo de assinatura Ed25519 do `tauri-plugin-updater`.
- Alterações no backend Python (`rpc/` ou `agents/`) — `dados_instalar` no Tauri já reinicia o núcleo Python com `ensure_schema()` + `sync_default_contexts()`.
- Auto-update forçado/sem opção de adiar durante uso ativo.

### LATER
- Botão manual "Verificar atualizações agora" em Configurações com feedback de "Você já está na última versão".
- Histórico/changelog detalhado de notas de versão no painel de atualizações.

## Constraints / Feasibility
- **`tauri-plugin-updater` v2 (`Update`):** o método `downloadAndInstall()` instala o pacote deixando o app pronto para `relaunch()` (no Windows NSIS, atenção: verificar o comportamento do instalador NSIS quando `downloadAndInstall` é chamado vs. `download()` + `install()`, pois no Windows `install()` já fecha o app ao rodar o instalador NSIS! **Ponto técnico crucial:** usar `update.download()` em segundo plano e só chamar `update.install()` + `relaunch()` quando o chat estiver livre e a contagem de 10s zerar ou o usuário clicar em "Reiniciar agora"!).
- **Compatibilidade com `ADR-0006` e testes existentes:** manter opt-in desligado por padrão preserva o contrato dos testes existentes (`atualizacoes.spec.ts`, `useAtualizacoes.spec.ts`).
- **Zero novas dependências externas:** tudo implementado com APIs já presentes (`@tauri-apps/plugin-updater`, `@tauri-apps/plugin-process`, Vue 3 reactivity, `localStorage`).

## Assumptions
- `[ASSUMPTION]` No `@tauri-apps/plugin-updater` v2, o objeto `Update` expõe `download()` e `install()` separadamente (além de `downloadAndInstall()`), permitindo baixar ~100 MB em segundo plano sem fechar o app no Windows e só disparar `install()` + `relaunch()` ao fim da contagem de 10s (com fallback para `downloadAndInstall()` em mocks que só forneçam esse método).
- `[ASSUMPTION]` Em desenvolvimento (`status.desenvolvimento === true`, usando `data/dados.db` do repositório), o auto-update de `dados.db` continua desativado exatamente como hoje.
- `[ASSUMPTION]` O toast discreto pós-atualização automática de `dados.db` pode ser exibido no `MainLayout.vue` (visível em qualquer tela aberta).

## Risks
- **Windows NSIS encerrando o app durante `downloadAndInstall()`:** mitigado usando `download()` em segundo plano e chamando `install()` + `relaunch()` apenas no momento do reinício (após chat livre + contagem de 10s).
- **Loop infinito de retry em falha de rede/disco durante auto-update:** mitigado registrando falha por versão (`versaoFalhou` / backoff até o próximo ciclo de 30 min) para nunca entrar em loop quente de downloads.
- **Troca de `dados.db` derrubando um chat em andamento (`503`):** mitigado observando `useChatApi().isLoading` e aguardando ficar `false` antes de chamar `dadosInstalar()` (e rechecando antes do disparo).
- **Timers/listeners vazando em testes Vitest:** mitigado com `pararMonitoramento()` e limpeza completa em `_resetAtualizacoes()`.

## Open Questions
- *Nenhuma pergunta bloqueante aberta* — todas as decisões de escopo, opt-in, ordem de prioridade, proteção de chat e frequência foram alinhadas.

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
