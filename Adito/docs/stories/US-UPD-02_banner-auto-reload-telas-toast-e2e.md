# User Story: [US-UPD-02] Banner de reinício, auto-reload reativo nas telas abertas, toast e testes E2E Playwright

**Epic:** EPIC-13 — Atualização Automática (Opt-in) e Auto-Reload de Telas
**GitHub Epic Issue:** -
**GitHub US Issue:** -
**Prioridade:** Alta (slice 2)
**Story Points:** 3
**Sprint:** - (implementação direta na branch `feat/auto-update-reload`)
**Status:** Review
**Behavior Change Esperado:** YES

---

## Historia

**Como** usuário do Adito acompanhando dashboards, chat ou administração
**Eu quero** ver um aviso discreto com contagem regressiva antes de o app reiniciar e ter minhas telas atualizadas automaticamente assim que o `dados.db` for trocado
**Para que** eu possa adiar um reinício se estiver apresentando algo e visualize os dados mais recentes sem precisar recarregar manualmente cada tela

### Contexto Adicional

Após a implementação do motor em `US-UPD-01`, falta conectar o ciclo de vida no `MainLayout.vue` (monitoramento contínuo, banner discreto da contagem regressiva de 10s e toast discreto de atualização de dados), fazer as telas abertas (**Dashboard**, **Meu painel**, **Contextos/Chat** e **Administração**) reagirem automaticamente a `dadosReloadSeq` sem disparar reindexação automática de embeddings (BR03), e validar todo o fluxo ponta a ponta no Playwright E2E.

Origem: `Adito/docs/discovery/auto-update-reload.md` e `Adito/docs/requirements/auto-update-reload.md` (`FR04`, `FR07`, `FR09`, `BR03`, `NFR02`, `NFR04`, `NFR05`).

### Pontos de Esclarecimento

Nenhum ponto pendente.

---

## Criterios de Aceitacao

- [x] **Criterio 1 (Ciclo de vida e banner de contagem regressiva no `MainLayout.vue`):** `MainLayout.vue` chama `iniciarMonitoramento()` em `onMounted` e `pararMonitoramento()` em `onBeforeUnmount`. Quando `segundosParaReinicio !== null`, exibe banner discreto acessível (`role="status"` / `aria-live="polite"`) informando *"Nova versão vX.Y.Z pronta — reiniciando em Ns..."* com botões **"Reiniciar agora"** e **"Adiar"**.
- [x] **Criterio 2 (Toast discreto de dados atualizados):** Quando `dados.db` é atualizado (automática ou manualmente), `MainLayout.vue` exibe um toast discreto acessível (*"Dados atualizados para a versão X"*) com botão de fechar e fechamento automático após alguns segundos.
- [x] **Criterio 3 (Auto-reload reativo nas 4 telas abertas):** Ao incrementar `dadosReloadSeq`:
  - **Dashboard** recarrega métricas/gráficos automaticamente;
  - **Meu painel** recarrega os widgets/consultas do painel automaticamente;
  - **Contextos / Chat** recarrega a lista de contextos disponíveis automaticamente;
  - **Administração** recarrega status/contextos/treinamentos automaticamente **sem nunca** chamar `admin.trainings.retrain`.
- [x] **Criterio 4 (Mock E2E e testes Playwright):** `tests/e2e/helpers/tauriMock.ts` suporta simulação de `appVerificar` (`download`/`install`/`relaunch`) e atualização de `dados.db`; `tests/e2e/atualizacoes.spec.ts` valida fluxo assistido existente + novos cenários de auto-update do executável (contagem, "Adiar", "Reiniciar agora") e auto-update/auto-reload de `dados.db` nas telas abertas.
- [x] **Criterio 5 (Zero regressão e build verde):** `npm run test:unit`, `npm run build` e `npm run test:e2e` passam 100% sem regressão nas suítes existentes.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Integração de UI reativa no frontend Vue e testes Vitest/Playwright sem novos contratos externos.
- **US exige Spec governada?** Nao
- **Justificativa da Spec:** Comportamento observável de UI coberto diretamente pelos requisitos (`FR04`, `FR07`, `FR09`) e testes automatizados.
- **Spec prevista:** N/A
- **US exige Contract governado?** Nao
- **Justificativa do Contract:** Consome exclusivamente o estado reativo de `useAtualizacoes.ts` e os RPCs já existentes das views.
- **Contract previsto:** N/A
- **Padrao de erro aplicavel:** N/A
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** N/A
- **Touch List preliminar:**
  - `Adito/app/frontend-vue/src/common/components/layout/MainLayout.vue`
  - `Adito/app/frontend-vue/src/modules/dashboard/views/DashboardView.vue`
  - `Adito/app/frontend-vue/src/modules/dashboard/views/MeuDashboardView.vue`
  - `Adito/app/frontend-vue/src/common/composables/useContextos.ts` (ou composable/view de contextos/chat correspondente)
  - `Adito/app/frontend-vue/src/modules/admin/views/AdminView.vue`
  - `Adito/app/frontend-vue/tests/unit/useAtualizacoes.spec.ts` (e/ou spec dedicado de auto-reload)
  - `Adito/app/frontend-vue/tests/e2e/helpers/tauriMock.ts`
  - `Adito/app/frontend-vue/tests/e2e/atualizacoes.spec.ts`
- **Task Issues previstas:** N/A

---

## Notas Tecnicas

### Arquitetura

- **Componentes afetados:** `MainLayout.vue`, telas de Dashboard, Meu painel, Contextos/Chat e Administração.
- **APIs necessarias:** Estado reativo `dadosReloadSeq`, `ultimaAtualizacaoDadosToast`, `segundosParaReinicio`, `reiniciarAgora`, `adiarReinicio` de `useAtualizacoes.ts`.
- **Database changes:** Nenhuma.
- **Referencias do modelo de dados:** N/A
- **Erros observaveis esperados:** Erros durante recarga silenciosa de views seguem o tratamento já existente em cada tela sem travar a interface.

### Dependencias

- [x] `US-UPD-01` concluída.

### Consideracoes de Performance

- O `watch(dadosReloadSeq)` deve reagir apenas quando `novo > 0` (sem disparar carga duplicada no `onMounted` inicial).
- Usar `watch` dentro do ciclo de vida do componente (ou limpar adequadamente) para evitar múltiplas recargas quando o usuário navega entre rotas.

---

## Plano de Testes

### Testes Unitarios

- [x] Reatividade de `dadosReloadSeq` dispara recarga nas telas/composables sem disparar `retrain` (`useContextos.spec.ts` e `AdminView.spec.ts`).
- [x] Banner de contagem e toast de dados atualizados validados via Vitest (`useAtualizacoes.spec.ts`) e Playwright E2E (`atualizacoes.spec.ts`).

### Testes de Integracao

- [x] Playwright E2E (`atualizacoes.spec.ts`): ativar opt-in em Configurações, simular atualização do executável com contagem regressiva e clicar em "Adiar" (banner fecha e botão na sidebar permanece); simular "Reiniciar agora" disparando `install` + `relaunch`.
- [x] Playwright E2E (`atualizacoes.spec.ts`): simular atualização de `dados.db` (automática e manual) e verificar toast *"Dados atualizados para a versão X"* + recarga automática dos dados no Dashboard aberto.

### Testes de Contract

- [x] N/A

### Testes Manuais

- [ ] Verificar visual do banner e do toast em temas claro e escuro e em viewport mobile/desktop.

### BDD / Cenarios de Comportamento

- [x] N/A

---

## Tasks (Breakdown)

- [x] **[TASK-001]** Conectar `iniciarMonitoramento()`/`pararMonitoramento()`, banner de contagem regressiva e toast de dados atualizados em `MainLayout.vue`.
- [x] **[TASK-002]** Adicionar `watch(dadosReloadSeq)` em Dashboard, Meu painel, Contextos/Chat e Administração (sem disparar retrain).
- [x] **[TASK-003]** Estender `tauriMock.ts` para suportar mock do updater (`check`/`download`/`install`/`relaunch`) e testes E2E em `atualizacoes.spec.ts`.
- [x] **[TASK-004]** Executar Vitest, build TypeScript/Vite e Playwright E2E garantindo 100% verde.

---

## IA Insights

### Sugestoes de Implementacao

- Incluir um gancho de teste discreto no `window.__ADITO_UPDATER_MOCK__` (ou via `tauriMock.ts` interceptando os comandos internos do `@tauri-apps/plugin-updater` e `@tauri-apps/plugin-process`) para que o Playwright teste o fluxo real de `atualizacoes.ts` sem stubs artificiais na UI.

### Riscos Identificados

- Se `watch(dadosReloadSeq)` for registrado no escopo de módulo de `useContextos.ts` fora de um componente, pode ser registrado múltiplas vezes ou vazar entre testes; registrar um watcher único (ou no componente/composable com cuidado de deduplicação).

### Alternativas Consideradas

- `window.location.reload()` ao atualizar `dados.db` — descartada porque perderia o estado da conversa aberta no chat e filtros da sessão.

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
