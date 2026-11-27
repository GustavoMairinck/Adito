# Requirements — Atualização Automática (Opt-in) e Auto-Reload de Telas no Adito

**Status:** REQUIREMENTS_READY
**Discovery de origem:** `Adito/docs/discovery/auto-update-reload.md`
**Classificacao de Processo:** NORMAL PROCESS
**Data:** 2026-11-25

## Intent Summary
Evoluir o sistema de atualizações do Adito para oferecer um modo **opt-in de atualização automática** (desligado por padrão, configurável em Configurações) capaz de verificar continuamente novas versões, baixar/instalar atualizações do executável e do `dados.db` em segundo plano sem interromper consultas em andamento no chat e recarregar automaticamente as telas abertas assim que novos dados forem instalados — preservando a cota de API BYOK do usuário e a política assistida da `ADR-0006` por padrão.

## Functional Requirements
- **FR01 (Preferência opt-in em Configurações):** Adicionar em `ConfiguracoesView.vue` um controle acessível (switch/checkbox) **"Atualização automática (app e dados)"**, **desligado por padrão** (`false`), persistido em `localStorage` (chave dedicada, ex.: `adito:auto_update`), com descrição clara explicando que o executável e o banco `dados.db` são atualizados em segundo plano quando não houver pergunta em andamento no chat.
- **FR02 (Verificação periódica e ao retornar foco):** Evoluir `useAtualizacoes.ts` (iniciado no `MainLayout.vue`) para verificar atualizações:
  1. Ao abrir o app (comportamento atual);
  2. Periodicamente em segundo plano a cada **30 minutos**;
  3. Ao retornar o foco/visibilidade da janela (`visibilitychange` / `focus`) caso tenham se passado pelo menos **15 minutos** desde a última verificação concluída.
  Nunca disparar duas verificações simultâneas e sempre falhar silenciosamente quando offline.
- **FR03 (Download automático do executável em segundo plano):** Quando `autoAtualizar` estiver ligado e `app.value` existir (e essa versão não tiver sido adiada nem falhado neste ciclo), baixar o pacote automaticamente em segundo plano via `update.download()` (ou fallback seguro se o mock só tiver `downloadAndInstall`) sem fechar o app prematuramente e sem exigir clique do usuário.
- **FR04 (Proteção de chat ativo + contagem regressiva de 10s para reinício):**
  - Após o download do executável concluir, aguardar até que nenhum stream de chat esteja ativo (`!useChatApi().isLoading.value`) antes de iniciar a contagem regressiva.
  - Com o chat livre, exibir um aviso/banner discreto (*"Nova versão vX.Y.Z pronta — reiniciando em Ns..."*, começando em **10 segundos**) com botões **"Reiniciar agora"** (executa `install()` + `relaunch()` imediatamente) e **"Adiar"** (cancela a contagem, marca aquela versão como adiada nesta sessão e mantém o botão de atualização disponível na barra lateral).
  - Se um stream de chat iniciar durante a contagem regressiva, pausar/cancelar a contagem e retomar apenas quando o chat voltar a ficar livre.
  - Ao chegar em `0s` sem adiamento, executar `install()` + `relaunch()` automaticamente.
- **FR05 (Prioridade do executável sobre `dados.db`):** Quando houver simultaneamente atualização do executável e atualização de `dados.db`, priorizar **exclusivamente o executável** primeiro (não iniciar troca automática de `dados.db` antes do reinício do app; ao reabrir na nova versão, o `dados.db` será atualizado automaticamente).
- **FR06 (Atualização automática de `dados.db` em segundo plano):** Quando `autoAtualizar` estiver ligado, não houver update de executável pendente, existir `dadosNovos.value` com `!precisa_chave` e `!status.desenvolvimento`, aguardar `!useChatApi().isLoading.value` e executar `instalarDados()` automaticamente em segundo plano. Se `precisa_chave === true`, não tentar instalar automaticamente e manter o aviso na barra lateral pedindo a nova chave.
- **FR07 (Sinal reativo `dadosReloadSeq` e auto-reload das telas abertas):** Sempre que `dados.db` for instalado com sucesso (tanto no modo automático quanto no manual), incrementar um contador reativo `dadosReloadSeq` e registrar `ultimaVersaoDadosAtualizada` em `useAtualizacoes.ts`. As telas abertas (**Dashboard**, **Meu painel**, **Contextos/Chat** e **Administração**) devem observar `dadosReloadSeq` e recarregar automaticamente seus dados/widgets/contextos sem exigir clique no ícone de atualização, exibindo também um toast discreto no `MainLayout.vue` (*"Dados atualizados para a versão X"*).
- **FR08 (Adenda documental na `ADR-0006`):** Atualizar `Docs/ADR/ADR-0006-empacotamento-e-auto-update-desktop.md` registrando o modo opt-in de atualização automática (desligado por padrão) e a separação download vs. reinício controlado.
- **FR09 (Testes automatizados e Mock E2E):** Ampliar `useAtualizacoes.spec.ts` e `ConfiguracoesView.spec.ts` no Vitest (cobrindo opt-in, polling/cooldown, prioridade app > dados, pausa durante chat ativo, contagem de 10s, Adiar/Agora, `dadosReloadSeq` e backoff em erro) e evoluir `tauriMock.ts` + `atualizacoes.spec.ts` no Playwright E2E cobrindo auto-update do executável (contagem + Adiar/Agora) e auto-update + auto-reload de `dados.db`.

## Business / Domain Rules
- **BR01 (Opt-in desligado por padrão):** Para qualquer instalação nova ou existente sem preferência salva, `autoAtualizar` deve iniciar `false`, mantendo integralmente o fluxo assistido atual da `ADR-0006`.
- **BR02 (Nunca interromper prompt em andamento):** Nenhum reinício automático do executável nem reinício automático do núcleo Python para troca de `dados.db` pode ser disparado enquanto `useChatApi().isLoading.value === true`.
- **BR03 (Sem gasto silencioso de cota BYOK):** A atualização automática nunca deve disparar `admin.trainings.retrain` nem reindexação de embeddings automaticamente; apenas recarrega status/contextos para que o aviso existente na Base de conhecimento funcione normalmente.
- **BR04 (Chave alterada exige ação humana):** Se `dadosRemoto.precisa_chave === true`, a atualização automática de `dados.db` não deve tentar instalar nem entrar em loop de erro — deve permanecer disponível no painel da barra lateral para o usuário informar a nova chave.
- **BR05 (Respeito ao adiamento na sessão):** Clicar em **"Adiar"** na contagem regressiva de uma versão `vX.Y.Z` impede que o app volte a iniciar contagem automática para aquela mesma versão na sessão atual (enquanto uma versão mais nova `vX.Y.Z+1` pode voltar a notificar).
- **BR06 (Proteção contra loop de erro):** Se o download/instalação automática de uma versão falhar (rede/disco), registrar falha para aquela versão evitando novas tentativas imediatas até o próximo ciclo de verificação (30 min), sem bloquear o botão manual.

## Non-Functional Requirements
- **NFR01 (Segurança no Windows NSIS):** Baixar o executável via `update.download()` em segundo plano antes de `update.install()` + `relaunch()`, evitando encerramento inesperado do aplicativo durante o download no Windows.
- **NFR02 (Acessibilidade):** O toggle em Configurações e o banner de contagem regressiva (`role="status"` / `aria-live="polite"`) devem ter rótulos acessíveis (`aria-label` / `<label>`), suporte a teclado e legibilidade em tema claro e escuro.
- **NFR03 (Zero novas dependências externas):** Utilizar apenas `@tauri-apps/plugin-updater`, `@tauri-apps/plugin-process`, Vue 3 e `localStorage`.
- **NFR04 (Higiene de timers e testes determinísticos):** Intervalos, timeouts e listeners (`visibilitychange`/`focus`) devem ser configuráveis/limpáveis (`iniciarMonitoramento` / `pararMonitoramento` / `_resetAtualizacoes`) para uso limpo com fake timers no Vitest e sem leaks ao desmontar.
- **NFR05 (Zero regressão nos fluxos assistidos):** Todos os testes unitários e E2E existentes (`useAtualizacoes.spec.ts`, `atualizacoes.spec.ts`, `ConfiguracoesView.spec.ts`, `dashboard.spec.ts`, `meu-dashboard.spec.ts`, `chat.spec.ts`) devem continuar passando sem quebra.

## User Scenarios

### Main flow — Auto-update do executável
1. Usuário ativa **"Atualização automática (app e dados)"** em **Configurações**.
2. Em uma verificação (ao abrir ou no ciclo de 30 min / foco), o Adito detecta `v0.2.0` disponível.
3. O app baixa o pacote em segundo plano silenciosamente (`update.download()`).
4. O usuário está no meio de uma pergunta no Chat (`isLoading === true`): o app aguarda a resposta terminar.
5. Assim que o chat fica livre, aparece o banner discreto: *"Adito v0.2.0 pronto — reiniciando em 10s..."* com **"Reiniciar agora"** e **"Adiar"**.
6. Se o usuário não adiar (ou clicar em "Reiniciar agora"), o app executa `install()` + `relaunch()`.

### Main flow — Auto-update de `dados.db` + Auto-reload das telas
1. Com atualização automática ligada, sem nova versão de executável, o Adito detecta `dados.db` versão `2026-11-26` (`precisa_chave === false`).
2. Com o chat livre, baixa, valida SHA-256/AES-256-GCM e troca `dados.db` reiniciando o núcleo Python.
3. Ao retornar `core_ready`, `dadosReloadSeq` incrementa, o **Dashboard** / **Meu painel** / **Contextos** / **Administração** recarregam automaticamente os novos dados e um toast discreto informa: *"Dados atualizados para a versão 2026-11-26"*.

### Alternative / Error / Edge cases
- **Modo automático desligado (padrão):** comportamento idêntico ao atual (aviso discreto na barra lateral); se o usuário clicar manualmente em "Atualizar os dados", `dadosReloadSeq` ainda dispara o auto-reload das telas abertas.
- **Executável + `dados.db` novos ao mesmo tempo:** baixa e prepara apenas o executável; não troca `dados.db` antes de reiniciar.
- **Usuário envia uma pergunta no Chat durante a contagem de 10s:** contagem pausa/cancela automaticamente e só reinicia quando o chat voltar a ficar livre.
- **Usuário clica em "Adiar":** contagem encerra e não volta a aparecer para aquela mesma versão na sessão; o botão na barra lateral continua permitindo clicar em "Atualizar o app" (ou "Reiniciar para atualizar") quando quiser.
- **Chave dos dados rotacionada (`precisa_chave === true`):** auto-update não tenta baixar nem falha em loop; aviso na barra lateral pede a nova chave normalmente.
- **App offline:** verificações periódicas e de foco falham silenciosamente sem exibir erro na UI.
- **Ambiente de desenvolvimento (`desenvolvimento === true`):** auto-update de `dados.db` permanece desativado.

## Business / Domain Context
O Adito roda localmente em máquinas institucionais do IFES sem servidor próprio (GitHub Releases público para app assinado em Ed25519 e `dados.db.enc` cifrado em AES-256-GCM). Usuários frequentes querem manter app e dados em dia sem cliques manuais, mas gestores em apresentações ou redes restritas precisam continuar protegidos pelo modo assistido padrão da `ADR-0006`.

## Technical Context & Constraints
- **Frontend (`Adito/app/frontend-vue/src/`):**
  - `common/api/atualizacoes.ts` (`AppUpdate` suportando `download()` + `install()` + `relaunchApp()`, mantendo `appInstalar()` compatível).
  - `common/composables/useAtualizacoes.ts` (preferência `autoAtualizar`, agendador periódico 30 min / foco 15 min, orquestração com `useChatApi().isLoading`, contagem regressiva 10s, `adiarReinicio()`, `reiniciarAgora()`, `dadosReloadSeq`, `ultimaAtualizacaoDadosToast`).
  - `common/components/navigation/AtualizacaoDisponivel.vue` (mostra estado "Pronto para reiniciar" se já baixado, mantém fluxo manual).
  - `common/components/layout/MainLayout.vue` (inicia/para monitoramento, exibe banner discreto da contagem de 10s e toast discreto de `dados.db` atualizado).
  - `modules/settings/views/ConfiguracoesView.vue` (seção/toggle **"Atualização automática (app e dados)"**).
  - `modules/dashboard/views/DashboardView.vue`, `MeuDashboardView.vue`, `common/composables/useContextos.ts`, `modules/admin/views/AdminView.vue` (watch em `dadosReloadSeq` para recarga automática).
- **Documentação:** `Docs/ADR/ADR-0006-empacotamento-e-auto-update-desktop.md`.
- **Testes:** `tests/unit/useAtualizacoes.spec.ts`, `tests/unit/ConfiguracoesView.spec.ts`, `tests/e2e/helpers/tauriMock.ts`, `tests/e2e/atualizacoes.spec.ts`.

## Quality Attributes
- **Segurança operacional:** nunca interromper consulta em andamento no chat e nunca fechar no Windows antes do usuário ver a contagem regressiva.
- **Previsibilidade:** opt-in explícito, contagem clara com botão "Adiar", sem consumo oculto de cota BYOK.
- **Testabilidade:** timers e hooks de updater 100% mockáveis no Vitest e no Playwright.

## Assumptions
- **A01:** `@tauri-apps/plugin-updater` v2 oferece `download()` e `install()` em `Update` (e nossa interface `AppUpdate` suporta ambos com fallback seguro para `downloadAndInstall()` em mocks/testes que só exponham o método antigo).
- **A02:** Em desenvolvimento (`cfg!(debug_assertions)` / `status.desenvolvimento === true`), tanto o auto-update de `dados.db` quanto o updater do executável (`tauri_plugin_updater`) ficam desativados (mantendo o `data/dados.db` do repositório e evitando que `tauri dev` tente baixar releases antigas do GitHub sobre o código local).
- **A03:** Nenhuma mudança é necessária no backend Python nem em `src-tauri/src/dados.rs`; em `src-tauri/src/lib.rs`, apenas restringe-se o registro de `tauri_plugin_updater` a builds de release (`#[cfg(not(debug_assertions))]`).

## Out of Scope
- Reindexação automática de embeddings/RAG.
- Alterações no protocolo criptográfico (`dados.rs`) ou no backend Python.
- Forçar auto-update sem possibilidade de desligar ou adiar.

## Open Questions
- *Nenhuma pergunta bloqueante aberta.*

## Key Decisions Proposed
- **KD01 (Opt-in desligado por padrão + adenda na `ADR-0006`):** Preserva 100% da política assistida para usuários em apresentações/redes lentas e mantém zero regressão nos testes existentes, entregando auto-update completo para quem ativar em Configurações.
- **KD02 (Download separado do `install` + `relaunch`):** Usar `update.download()` em segundo plano e deixar `update.install()` + `relaunch()` apenas para o fim da contagem de 10s (ou clique em "Reiniciar agora"), evitando fechamento abrupto pelo instalador NSIS no Windows.
- **KD03 (Integração direta com `useChatApi().isLoading`):** Reutilizar o estado compartilhado de streams ativos do EPIC-12 para garantir que nem `relaunch()` nem `dadosInstalar()` interrompam um prompt em andamento.
- **KD04 (Sinal reativo `dadosReloadSeq`):** Desacoplar a notificação de troca do `dados.db` das telas por meio de um contador reativo observado por Dashboard, Meu painel, Contextos e Administração (funcionando tanto no auto-update quanto na atualização manual).

## Review & Adjust

O usuario pode **aprovar, editar, adicionar, remover ou reclassificar** qualquer requisito/regra antes do gate.

- [x] Proposta completa apresentada ao usuario
- [x] Ajustes solicitados incorporados
- [x] IDs estabilizados depois da revisao
- [x] Nenhuma pergunta bloqueante aberta

### User adjustments
- Aprovado sem alterações no Checkpoint R1 (2026-11-25).

## Gate G1 — REQUIREMENTS READY

**Status:** APPROVED

**Aprovado pelo usuario:** sim
