# User Story: [US-LLM-04] Tela de Configurações multi-provedor, avisos na Base de conhecimento e testes Frontend/E2E

**Epic:** EPIC-11: Suporte Multi-Provedor de IA (BYOK)
**GitHub Epic Issue:** -
**GitHub US Issue:** -
**Prioridade:** Alta (Vertical Slice 2)
**Story Points:** 5
**Sprint:** A definir
**Status:** Done
**Behavior Change Esperado:** YES

---

## Historia

**Como** servidor ou gestor usuário do Adito,
**Eu quero** escolher meu provedor de IA na tela de Configurações, ajustar modelo ou Base URL quando necessário, ver claramente o que sai do meu computador e receber avisos claros na Base de conhecimento sobre o suporte a embeddings,
**Para que** eu configure e utilize o Adito com simplicidade, autonomia e total transparência de privacidade.

### Contexto Adicional

Origem: `Adito/docs/discovery/suporte-multi-provedor-llm.md` (`PROBLEM_READY`) e `Adito/docs/requirements/suporte-multi-provedor-llm.md` (`REQUIREMENTS_READY`).

Atualmente `ConfiguracoesView.vue` e `src/common/api/llmKey.ts` expõem apenas um campo fixo para chave Gemini e a seção de privacidade cita exclusivamente "Google Gemini". A aba **Admin → Base de conhecimento** (`AdminView.vue`) também assume que o provedor sempre gera embeddings compatíveis. Esta story conclui a entrega de ponta a ponta da funcionalidade BYOK na interface Vue 3 e na suíte de testes Vitest + Playwright mock.

**Requisitos rastreados:** `FR06`, `FR07` (UI), `FR08` (UI), `FR10` (UI), `BR02`, `BR03`, `BR04`, `BR06`, `NFR05` (Vitest + `tauriMock.ts` / E2E).

### Pontos de Esclarecimento

Nenhum ponto pendente.

---

## Criterios de Aceitacao

- [x] **Criterio 1 (Cliente IPC/RPC em `llmKey.ts` — FR06, FR09):** `src/common/api/llmKey.ts` expõe funções tipadas (sem `any`) para catálogo, status multi-provedor, teste/salvamento e remoção seletiva.
- [x] **Criterio 2 (Tela Configurações com dropdown customizado `ProviderSelect.vue` — FR06, FR10, BR02, BR03):** Seletor customizado com identidade visual do Adito para os 8 provedores com embeddings, selo **"Em uso"** (lido do núcleo via `me`) e **"Chave salva"** nos demais, campo **Modelo** editável, **Base URL** em opções avançadas para `Z.AI`/`Ollama`, campo **Chave API** (`password`, opcional apenas em loopback), ações **Testar e salvar** e **Remover**.
- [x] **Criterio 3 (Privacidade dinâmica — FR07, BR06):** Seção **"O que sai do seu computador"** dinâmica conforme o provedor selecionado, destacando **100% local** para Ollama/loopback.
- [x] **Criterio 4 (Avisos na Base de conhecimento — FR08, BR04):** `AdminView.vue` exibe banner recomendando **Wipe & Retrain** quando há vetores incompatíveis (dimensão ou provedor/modelo divergente) e mantém guarda defensiva caso `supports_embeddings === false`.
- [x] **Criterio 5 (Acessibilidade e validação redundante — Coding Standards):** Controles com `role`/`label` acessíveis e navegação por teclado no dropdown.
- [x] **Criterio 6 (Testes Vitest + `tauriMock.ts` / E2E offline — NFR05):** `llmKey.spec.ts`, `ConfiguracoesView.spec.ts`, `AdminView.spec.ts`, `tauriMock.ts` e `settings-admin.spec.ts` passando 100% offline.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 2
- **Justificativa do nivel:** Altera fluxo observável de interface crítica (Configurações + Admin), integração com comandos IPC Tauri e RPC, com testes unitários Vitest e mock de boundary E2E (`tauriMock.ts`).
- **US exige Spec governada?** Nao
- **Justificativa da Spec:** Fluxos, estados de erro e regras de UI estão documentados em `Adito/docs/requirements/suporte-multi-provedor-llm.md` (`FR06`–`FR08`, `FR10`).
- **Spec prevista:** N/A
- **US exige Contract governado?** Sim (consumo do contrato RPC + IPC Tauri)
- **Justificativa do Contract:** Consome os campos de `me`, `config.llm_providers` (`US-LLM-01`), diagnóstico de embeddings (`US-LLM-02`) e comandos Tauri (`US-LLM-03`).
- **Contract previsto:** `src/common/api/llmKey.ts` + `tests/e2e/helpers/tauriMock.ts`
- **Padrao de erro aplicavel:** Feedback de erro amigável retornado por `config.test_llm_key` e comandos Tauri
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** `npm run test:unit` (Vitest) + `npm run build` (TypeScript/Vite) + testes E2E mock (Playwright)
- **Touch List preliminar:**
  - `Adito/app/frontend-vue/src/common/api/llmKey.ts`
  - `Adito/app/frontend-vue/src/modules/settings/views/ConfiguracoesView.vue`
  - `Adito/app/frontend-vue/src/modules/admin/views/AdminView.vue`
  - `Adito/app/frontend-vue/tests/unit/llmKey.spec.ts`
  - `Adito/app/frontend-vue/tests/unit/ConfiguracoesView.spec.ts` (novo)
  - `Adito/app/frontend-vue/tests/unit/AdminView.spec.ts` (novo ou atualização se já existir)
  - `Adito/app/frontend-vue/tests/e2e/helpers/tauriMock.ts`
- **Task Issues previstas:** N/A

---

## Mockups/Wireframes

Fluxo previsto em `ConfiguracoesView.vue` (mantendo o visual atual do Adito, sem redesign):
1. **Provedor de IA** (select com os 8 presets + selo *"Chave salva"* ou *"Local — sem chave"*).
2. **Modelo** (input texto pré-preenchido com o padrão do provedor, editável).
3. **Opções avançadas / Base URL** (visível automaticamente em *"Outro (OpenAI-compatível)"* ou expansível em presets como Ollama e Z.AI).
4. **Chave API** (input `password`; mostra placeholder contextual quando já há chave salva ou aviso de opcional em servidor local).
5. Botões **Testar e salvar** (primário) e **Remover chave deste provedor** (secundário, quando houver chave salva).
6. Card **"O que sai do seu computador"** atualizado dinamicamente com o nome do provedor selecionado (ou destaque *"100% local"* para Ollama/loopback).

---

## Notas Tecnicas

### Arquitetura

- **Componentes afetados:** `src/common/api/llmKey.ts`, `src/modules/settings/views/ConfiguracoesView.vue`, `src/modules/admin/views/AdminView.vue` (e store/composable de sessão se `me` for cacheado).
- **APIs necessarias:** Comandos Tauri de `US-LLM-03` (`llm_config_status`, `test_llm_config`, `set_llm_config`, `clear_llm_key`) e RPCs `me` / `config.llm_providers` / status da Base de conhecimento (`US-LLM-01`, `US-LLM-02`).
- **Database changes:** Nenhuma.
- **Referencias do modelo de dados:** N/A
- **Erros observaveis esperados:**
  - Chave ausente em provedor remoto (bloqueio no formulário + feedback).
  - Erro de validação retornado pelo provedor (chave inválida, modelo inexistente, cota esgotada, Ollama inacessível).
  - Banner informativo na Base de conhecimento para provedor só-chat ou vetores incompatíveis.

### Dependencias

- [ ] `US-LLM-01` (catálogo RPC e campos em `me`).
- [ ] `US-LLM-02` (sinalização de suporte/compatibilidade de embeddings na Base de conhecimento).
- [ ] `US-LLM-03` (comandos Tauri multi-provedor e reuso seguro de chave salva).

### Consideracoes de Performance

- Evitar chamadas redundantes ao selecionar provedores no dropdown: preencher modelo/URL padrão instantaneamente em memória a partir do catálogo carregado uma única vez.

---

## Plano de Testes

### Testes Unitarios

- [ ] `llmKey.spec.ts`: chamadas Tauri/RPC para listar provedores, ler status, testar/salvar com chave nova vs. `use_saved_key`, remover chave por provedor e modo fallback web/dev.
- [ ] `ConfiguracoesView.spec.ts`: troca de provedor preenche modelo padrão; "Outro" exibe `Base URL`; Ollama permite salvar sem chave e exibe privacidade "100% local"; provedor com chave salva permite reativar sem redigitar; erro de validação impede salvamento e exibe mensagem em português.
- [ ] `AdminView.spec.ts`: banner de "provedor sem embeddings" exibido e "Wipe & Retrain" desabilitado para Groq/DeepSeek; banner de "reindexação recomendada" exibido quando `embeddings_mismatch = true`; ambos ocultos quando provedor suporta embeddings e base está consistente.

### Testes de Integracao

- [ ] `tests/e2e/helpers/tauriMock.ts` atualizado com estado multi-provedor em memória (`has_key_by_provider`, `provider`, `model`, `base_url`) e fluxo E2E de configuração em Playwright passando sem rede real.

### Testes de Contract

- [ ] Tipagem TypeScript (`npm run build` / `vue-tsc`) validando interfaces de payload contra `llmKey.ts` e `tauriMock.ts`.

### Testes Manuais

- [ ] Testar no app desktop a configuração de Gemini, OpenAI, Groq (sem embeddings) e Ollama local, verificando textos de privacidade e banners na aba Administração → Base de conhecimento.

### BDD / Cenarios de Comportamento

- [ ] N/A.

---

## Tasks (Breakdown)

- [ ] **[TASK-001]** Refatorar `src/common/api/llmKey.ts` com tipos e wrappers para catálogo, status multi-provedor, teste/salvamento e remoção seletiva
  - GitHub Task Issue: N/A
  - Estimativa: 2h
  - Assignee: A definir
- [ ] **[TASK-002]** Evoluir `ConfiguracoesView.vue` (seletor de provedor, modelo editável, Base URL condicional/avançada, reuso de chave salva e privacidade dinâmica)
  - GitHub Task Issue: N/A
  - Estimativa: 4h
  - Assignee: A definir
- [ ] **[TASK-003]** Adicionar banners de suporte/compatibilidade de embeddings em `AdminView.vue`
  - GitHub Task Issue: N/A
  - Estimativa: 2h
  - Assignee: A definir
- [ ] **[TASK-004]** Atualizar `llmKey.spec.ts`, criar testes Vitest para `ConfiguracoesView` e `AdminView` e atualizar `tests/e2e/helpers/tauriMock.ts`
  - GitHub Task Issue: N/A
  - Estimativa: 3h
  - Assignee: A definir

---

## IA Insights

### Sugestoes de Implementacao

- Manter um composable leve (ex.: `useLlmConfig.ts`) ou estado bem isolado em `ConfiguracoesView.vue` para separar lógica de seleção de preset, detecção de loopback e estados de loading/erro do template.
- Ao trocar o provedor no `<select>`, só sobrescrever o campo `Modelo` com o padrão do novo provedor se o usuário ainda não personalizou ou se o valor atual pertencer ao provedor anterior.
- Nota de ambiente local: lembrar de rodar `npm install` em `Adito/app/frontend-vue` antes de executar Vitest/Playwright caso `node_modules` local esteja desatualizado.

### Riscos Identificados

- Caso a store/header do app mostre banner de "chave Gemini não configurada" em outro componente compartilhado, fazer uma varredura rápida (`git grep -i gemini Adito/app/frontend-vue/src`) durante a implementação para garantir consistência de copy em toda a UI.

### Alternativas Consideradas

- Criar abas separadas por provedor na tela de Configurações: descartada por aumentar complexidade visual; um único seletor de provedor com opção avançada mantém a simplicidade do Adito.

---

## Notas e Comentarios

- Completa o **Vertical Slice 2** junto com `US-LLM-03` e fecha o `EPIC-11`.
- **Ajuste final consolidado na implementação (24/11/2026):** substituído `<select>` nativo por componente customizado `ProviderSelect.vue` com identidade visual do Adito (`IBM Plex Sans` / `IBM Plex Mono`, `--brand-primary`, modo claro/escuro) e indicador visual **"Em uso"** lido diretamente do núcleo em execução (`me`).

---

## Definition of Done Checklist

- [ ] Codigo implementado conforme criterios de aceitacao
- [ ] Decisao sobre Spec governada foi registrada
- [ ] Decisao sobre Contract governado foi registrada
- [ ] Nivel ScrumAIDev foi registrado
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
