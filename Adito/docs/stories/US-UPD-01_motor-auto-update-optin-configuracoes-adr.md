# User Story: [US-UPD-01] Motor de auto-update opt-in, proteção de chat ativo, Configurações e adenda ADR-0006

**Epic:** EPIC-13 — Atualização Automática (Opt-in) e Auto-Reload de Telas
**GitHub Epic Issue:** -
**GitHub US Issue:** -
**Prioridade:** Alta (slice 1)
**Story Points:** 5
**Sprint:** - (implementação direta na branch `feat/auto-update-reload`)
**Status:** Review
**Behavior Change Esperado:** YES

---

## Historia

**Como** usuário frequente do Adito no desktop
**Eu quero** poder ativar opcionalmente a atualização automática em Configurações para que o app verifique, baixe e aplique atualizações do executável e do banco `dados.db` em segundo plano sem interromper minhas consultas no chat
**Para que** meu aplicativo e meus dados institucionais fiquem sempre atualizados sem cliques repetitivos, mantendo o modo assistido padrão para quem não ativar a opção

### Contexto Adicional

Hoje o Adito verifica atualizações apenas uma vez na inicialização (`MainLayout.vue` → `verificar()`) e sempre aguarda clique manual no rodapé da barra lateral (`AtualizacaoDisponivel.vue`). Em `atualizacoes.ts`, `AppUpdate` expõe apenas `downloadAndInstall()`, o que no Windows (NSIS) pode encerrar o app assim que o instalador inicia. Com o estado compartilhado de streams ativos do chat (`useChatApi().isLoading`, entregue no `EPIC-12`), é possível baixar atualizações em segundo plano e aguardar o chat ficar livre antes de exibir contagem regressiva de 10 segundos ou trocar `dados.db`.

Origem: `Adito/docs/discovery/auto-update-reload.md` e `Adito/docs/requirements/auto-update-reload.md` (`FR01–FR06`, `FR08`, `FR09`, `BR01–BR06`, `NFR01–NFR04`, `A01–A03`).

### Pontos de Esclarecimento

Nenhum ponto pendente.

---

## Criterios de Aceitacao

- [x] **Criterio 1 (Preferência opt-in em Configurações):** `ConfiguracoesView.vue` exibe um controle acessível (switch/checkbox) **"Atualização automática (app e dados)"**, desligado por padrão (`false`), persistido em `localStorage` (`adito:auto_update`). Quando desligado, o comportamento assistido atual (`ADR-0006`) permanece inalterado.
- [x] **Criterio 2 (Verificação periódica e ao retornar foco):** `useAtualizacoes.ts` oferece `iniciarMonitoramento()` e `pararMonitoramento()` que verificam atualizações ao abrir o app, a cada **30 minutos** em segundo plano e ao voltar o foco/visibilidade (`visibilitychange` / `focus`) respeitando cooldown mínimo de **15 minutos**, sem execuções concorrentes e falhando silenciosamente quando offline.
- [x] **Criterio 3 (Download automático seguro do executável):** Com `autoAtualizar === true` e `app.value` disponível (não adiado nem com falha recente no ciclo), o app baixa o pacote em segundo plano via `update.download()` (com fallback para `downloadAndInstall()` em mocks legados) sem encerrar prematuramente o aplicativo.
- [x] **Criterio 4 (Proteção de chat ativo + contagem de 10s + Adiar/Agora):** Após o download concluir, a contagem regressiva de **10 segundos** só inicia quando `!useChatApi().isLoading.value`. Se um stream de chat iniciar durante a contagem, ela pausa/cancela até o chat ficar livre. `reiniciarAgora()` executa `install()` + `relaunch()` imediatamente; `adiarReinicio()` silencia a contagem daquela versão na sessão atual mantendo o botão manual disponível em `AtualizacaoDisponivel.vue` (que indica quando o update já está pronto para reiniciar).
- [x] **Criterio 5 (Prioridade executável > `dados.db` e auto-update de `dados.db`):** Quando executável e `dados.db` têm atualizações simultâneas, apenas o executável é processado. Sem update de executável pendente e com `autoAtualizar === true`, `dadosNovos` com `!precisa_chave` e `!status.desenvolvimento`, o app aguarda `!useChatApi().isLoading.value` e instala `dados.db` em segundo plano; se `precisa_chave === true`, não tenta instalar nem entra em loop.
- [x] **Criterio 6 (Sinal `dadosReloadSeq` e proteção contra loop de erro):** Toda instalação bem-sucedida de `dados.db` (manual ou automática) incrementa `dadosReloadSeq` e registra `ultimaVersaoDadosAtualizada`. Falhas no download/instalação automática de uma versão evitam novas tentativas automáticas até o próximo ciclo de 30 minutos, sem bloquear o clique manual.
- [x] **Criterio 7 (Adenda na ADR-0006 e testes unitários):** `Docs/ADR/ADR-0006-empacotamento-e-auto-update-desktop.md` documenta o modo opt-in e a separação download vs. reinício; `useAtualizacoes.spec.ts` e `ConfiguracoesView.spec.ts` cobrem os novos comportamentos com fake timers e zero regressão.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Evolução contida no frontend Vue e documentação ADR, sem alteração de protocolo IPC/RPC, banco de dados ou sidecar Rust/Python.
- **US exige Spec governada?** Nao
- **Justificativa da Spec:** Não introduz novo contrato de API nem fluxo de domínio complexo fora do composable de atualizações já documentado em Requirements e ADR-0006.
- **Spec prevista:** N/A
- **US exige Contract governado?** Nao
- **Justificativa do Contract:** Utiliza exclusivamente os comandos Tauri existentes (`dados_status`, `dados_verificar`, `dados_instalar`) e plugins oficiais (`@tauri-apps/plugin-updater`, `@tauri-apps/plugin-process`).
- **Contract previsto:** N/A
- **Padrao de erro aplicavel:** N/A
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** N/A
- **Touch List preliminar:**
  - `Adito/app/src-tauri/src/lib.rs` (registro condicional `#[cfg(not(debug_assertions))]` do `tauri_plugin_updater` em release)
  - `Adito/app/frontend-vue/src/common/api/atualizacoes.ts`
  - `Adito/app/frontend-vue/src/common/composables/useAtualizacoes.ts`
  - `Adito/app/frontend-vue/src/common/components/navigation/AtualizacaoDisponivel.vue`
  - `Adito/app/frontend-vue/src/modules/settings/views/ConfiguracoesView.vue`
  - `Docs/ADR/ADR-0006-empacotamento-e-auto-update-desktop.md`
  - `Adito/app/frontend-vue/tests/unit/useAtualizacoes.spec.ts`
  - `Adito/app/frontend-vue/tests/unit/ConfiguracoesView.spec.ts`
- **Task Issues previstas:** N/A

---

## Notas Tecnicas

### Arquitetura

- **Componentes afetados:** `atualizacoes.ts`, `useAtualizacoes.ts`, `AtualizacaoDisponivel.vue`, `ConfiguracoesView.vue`.
- **APIs necessarias:** `@tauri-apps/plugin-updater` (`check`, `download`, `install`, `downloadAndInstall`) e `@tauri-apps/plugin-process` (`relaunch`), sem novas dependências.
- **Database changes:** Nenhuma.
- **Referencias do modelo de dados:** N/A
- **Erros observaveis esperados:** Falhas de rede em verificações em segundo plano são silenciosas; falhas manuais continuam populando `erro.value`; falhas automáticas registram backoff para a versão até o próximo ciclo de 30 min.

### Dependencias

- [x] `EPIC-12` (`useChatApi().isLoading` compartilhado por conversa/rota) concluído na branch base `development`.

### Consideracoes de Performance

- Evitar verificações concorrentes (`verificacaoEmCurso`) e aplicar cooldown mínimo de 15 minutos no retorno de foco para não sobrecarregar a API pública do GitHub Releases (rate limit).
- Limpar todos os timers e event listeners em `pararMonitoramento()` e `_resetAtualizacoes()`.

---

## Plano de Testes

### Testes Unitarios

- [x] Preferência `autoAtualizar` inicia `false`, persiste no `localStorage` e é refletida no toggle de `ConfiguracoesView.vue`.
- [x] Verificação periódica (30 min) e por retorno de foco (`visibilitychange` / `focus` com cooldown de 15 min) sem chamadas duplicadas e silenciosa offline.
- [x] Download automático do executável (`download()`), espera por `!useChatApi().isLoading`, contagem de 10s, pausa se chat iniciar durante a contagem, `reiniciarAgora()` e `adiarReinicio()` (silencia versão na sessão).
- [x] Prioridade do executável sobre `dados.db` quando ambos têm atualização simultânea.
- [x] Auto-update de `dados.db` com `!precisa_chave && !desenvolvimento` quando chat livre; skip quando `precisa_chave === true`; incremento de `dadosReloadSeq` no modo manual e automático.
- [x] Backoff de erro por versão no modo automático sem bloquear clique manual.

### Testes de Integracao

- [x] Verificado na `US-UPD-02` via Playwright E2E com `tauriMock.ts`.

### Testes de Contract

- [x] N/A

### Testes Manuais

- [ ] Conferir acessibilidade e contraste do toggle em Configurações nos temas claro e escuro.

### BDD / Cenarios de Comportamento

- [x] N/A

---

## Tasks (Breakdown)

- [x] **[TASK-001]** Evoluir `atualizacoes.ts` para suportar `download()` separado de `install()` + `relaunchApp()` com fallback retrocompatível.
- [x] **[TASK-002]** Evoluir `useAtualizacoes.ts` com opt-in `localStorage`, monitoramento 30 min / foco 15 min, proteção `useChatApi().isLoading`, contagem 10s, prioridade app > dados, backoff e `dadosReloadSeq`.
- [x] **[TASK-003]** Adicionar toggle **"Atualização automática (app e dados)"** em `ConfiguracoesView.vue` e estado *"Pronto para reiniciar"* em `AtualizacaoDisponivel.vue`.
- [x] **[TASK-004]** Registrar adenda do modo opt-in em `Docs/ADR/ADR-0006-empacotamento-e-auto-update-desktop.md`.
- [x] **[TASK-005]** Ampliar testes unitários em `useAtualizacoes.spec.ts` e `ConfiguracoesView.spec.ts`.

---

## IA Insights

### Sugestoes de Implementacao

- Quando o objeto `AppUpdate` não possuir `download()`/`install()` separados (mocks antigos), diferir `downloadAndInstall()` para o momento de `aplicarApp()` (após chat livre e contagem de 10s), preservando a segurança no Windows e a compatibilidade com testes legados.

### Riscos Identificados

- Leaks de timers ou listeners `visibilitychange`/`focus` entre testes Vitest se `_resetAtualizacoes()` não chamar `pararMonitoramento()` e limpar `localStorage`/estado interno.

### Alternativas Consideradas

- Manter apenas `downloadAndInstall()` — descartada pois no Windows (NSIS) `install()` já fecha o app durante o processo, impossibilitando a contagem de 10 segundos após o download.

---

## Definition of Done Checklist

- [x] Codigo implementado conforme criterios de aceitacao
- [x] Decisao sobre Spec governada foi registrada
- [x] Decisao sobre Contract governado foi registrada
- [x] Nivel ScrumAIDev foi registrado
- [x] Spec, Contract e BDD foram atualizados quando aplicavel
- [x] Gates opcionais executados ou dispensados com justificativa
- [x] Error handling observavel segue o padrao compartilhado quando aplicavel
- [x] Code review aprovado
- [x] Testes unitarios com cobertura adequada
- [x] Testes de integracao e contract passando
- [x] Documentacao atualizada
- [x] Build/CI passando
- [ ] `Behavior change` documentado no PR
- [ ] Aprovacao do Product Owner
