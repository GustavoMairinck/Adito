# User Story: [US-EXP-02] Botão dropdown "Exportar" no Chat, toast de feedback e testes Vitest + Playwright E2E

**Epic:** EPIC-15 — Exportação de Dados do Chat para CSV e Excel (`.xlsx`)
**GitHub Epic Issue:** -
**GitHub US Issue:** -
**Prioridade:** Alta (slice 2)
**Story Points:** 3
**Sprint:** - (implementação direta na branch `feat/exportar-dados-csv-excel`)
**Status:** Review
**Behavior Change Esperado:** YES

---

## Historia

**Como** usuário analisando tabelas ou gráficos gerados pelo Chat Estratégico do Adito
**Eu quero** clicar em um botão **"Exportar"** discreto na resposta e escolher entre **CSV** e **Excel (`.xlsx`)** recebendo confirmação imediata por toast
**Para que** eu consiga baixar todos os registros da consulta com praticidade sem sair do chat nem interromper outras conversas

### Contexto Adicional

Após a implementação do gerador CSV/OOXML e do comando Rust `exportar_arquivo` na `US-EXP-01`, esta story integra o botão dropdown **"Exportar"** em `ChatMessageBubble.vue`, conecta o feedback via `showToast` em `ChatEstrategicoView.vue` (passando o contexto da pergunta para nomear o arquivo) e valida toda a experiência com testes Vitest e Playwright E2E.

Origem: `Adito/docs/discovery/exportar-dados-csv-excel.md` e `Adito/docs/requirements/exportar-dados-csv-excel.md` (`FR01–FR03`, `FR07`, `FR08`, `BR01`, `BR02`, `NFR02`, `NFR05`).

### Pontos de Esclarecimento

Nenhum ponto pendente.

---

## Criterios de Aceitacao

- [x] **Criterio 1 (Botão dropdown "Exportar" em `ChatMessageBubble.vue`):** Exibe o botão **"Exportar"** ao lado de **"Ver SQL Gerado"** e **"Fixar no Dashboard"** sempre que `hasRenderableTable && !message.isScalarResult` (em respostas novas e no histórico reaberto). Não aparece em mensagens textuais puras, fallback/erro ou resultados escalares simples.
- [x] **Criterio 2 (Acessibilidade e tecla `Esc`):** O botão e o menu seguem ARIA (`aria-haspopup="menu"`, `aria-expanded`, `role="menu"`, `role="menuitem"`), fecham ao clicar fora ou ao pressionar `Esc` (com `stopPropagation()` para não cancelar stream ativo do chat) e funcionam em tema claro e escuro.
- [x] **Criterio 3 (Exportação integral ignorando limite visual e `"Outros"`):** Clicar em **"Exportar CSV (.csv)"** ou **"Exportar Excel (.xlsx)"** gera e salva o arquivo com **todos** os registros de `message.table`, mesmo quando `rowLimit` estiver em `5/10/15` ou o gráfico estiver agrupando categorias pequenas em `"Outros"`.
- [x] **Criterio 4 (Feedback por toast no Chat):** Ao concluir o salvamento, exibe toast discreto no `ChatEstrategicoView.vue` indicando pasta e arquivo salvo (*"Arquivo salvo em <Pasta>: ..."* no Tauri ou *"Arquivo salvo: ..."* no fallback web), toast de erro amigável caso falhe, e nenhum toast se o usuário cancelar o diálogo "Salvar como...".
- [x] **Criterio 5 (Testes Vitest + Playwright E2E + Zero regressão):** `ChatMessageBubble.spec.ts` testa visibilidade condicional, abertura/fechamento do menu teleportado (`Esc`, clique fora) e exportação integral; `tauriMock.ts` suporta `exportar_arquivo` (confirmado e cancelado) e `chat.spec.ts` valida o fluxo completo CSV/Excel, visibilidade do menu na viewport e cancelamento no Playwright, com 100% dos testes existentes passando.

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Integração de UI no módulo Chat + testes Vitest e Playwright E2E.
- **US exige Spec governada?** Nao
- **Justificativa da Spec:** Comportamento observável de UI coberto diretamente por `Requirements` e testes de componente/E2E.
- **Spec prevista:** N/A
- **US exige Contract governado?** Nao
- **Justificativa do Contract:** Consome apenas a API interna `common/api/export.ts`.
- **Contract previsto:** N/A
- **Padrao de erro aplicavel:** N/A
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** N/A
- **Touch List preliminar:**
  - `Adito/app/frontend-vue/src/modules/chat/components/ChatMessageBubble.vue`
  - `Adito/app/frontend-vue/src/modules/chat/components/ChatConversation.vue`
  - `Adito/app/frontend-vue/src/modules/chat/views/ChatEstrategicoView.vue`
  - `Adito/app/frontend-vue/tests/unit/ChatMessageBubble.spec.ts`
  - `Adito/app/frontend-vue/tests/e2e/helpers/tauriMock.ts`
  - `Adito/app/frontend-vue/tests/e2e/chat.spec.ts`
- **Task Issues previstas:** N/A

---

## Notas Tecnicas

### Arquitetura

- **Componentes afetados:** `ChatMessageBubble.vue`, `ChatConversation.vue`, `ChatEstrategicoView.vue`.
- **APIs necessarias:** `exportarTabela()` de `common/api/export.ts` e `showToast` de `useToast.ts`.
- **Database changes:** Nenhuma.
- **Referencias do modelo de dados:** N/A
- **Erros observaveis esperados:** Falhas ao salvar disparam `showToast(mensagem, 'error')` sem perder o histórico da conversa.

### Dependencias

- [x] `US-EXP-01` concluída.

### Consideracoes de Performance

- Estado `exporting` desabilita cliques duplicados enquanto o arquivo é gerado/gravado.

---

## Plano de Testes

### Testes Unitarios

- [x] `ChatMessageBubble.spec.ts`: botão **"Exportar"** aparece apenas quando `hasRenderableTable && !isScalarResult`, não aparece em resposta textual ou escalar.
- [x] `ChatMessageBubble.spec.ts`: abre menu dropdown, fecha com `Esc` chamando `stopPropagation()` e com clique fora.
- [x] `ChatMessageBubble.spec.ts`: seleciona CSV e Excel exportando todas as linhas de `message.table` (ex.: 20 linhas mesmo com `rowLimit = 10`).

### Testes de Integracao

- [x] Playwright E2E (`chat.spec.ts`): envia pergunta no chat, abre **"Exportar"**, clica em **"Exportar CSV (.csv)"** e **"Exportar Excel (.xlsx)"**, valida payload enviado ao comando `exportar_arquivo` no `tauriMock.ts` e confirma toast de sucesso sem `pageerror`.

### Testes de Contract

- [x] N/A

### Testes Manuais

- [ ] Conferir aparência do botão e dropdown em temas claro e escuro no app desktop.

### BDD / Cenarios de Comportamento

- [x] N/A

---

## Tasks (Breakdown)

- [x] **[TASK-001]** Adicionar botão dropdown **"Exportar"** (CSV / Excel `.xlsx`) com acessibilidade e proteção de `Esc` em `ChatMessageBubble.vue`.
- [x] **[TASK-002]** Conectar evento de exportação e toast de feedback em `ChatConversation.vue` e `ChatEstrategicoView.vue`.
- [x] **[TASK-003]** Criar `tests/unit/ChatMessageBubble.spec.ts` e ampliar `tests/e2e/helpers/tauriMock.ts` + `tests/e2e/chat.spec.ts`.
- [x] **[TASK-004]** Executar `cargo test`, `npm run test:unit`, `npm run build` e `npm run test:e2e`.

---

## IA Insights

### Sugestoes de Implementacao

- Em `ChatMessageBubble.vue`, renderizar a barra de ações com `v-if="message.sql || hasRenderableTable"` para que o botão **"Exportar"** apareça mesmo em cenários onde `message.table` existe sem `message.sql`.

### Riscos Identificados

- `ChatEstrategicoView.vue` escuta `keydown` (`Escape`) em `window`; usar `@keydown.escape.stop` no menu e também registrar um listener `document` em captura ou checar se o menu estava aberto garante que `Esc` nunca aborte uma resposta em geração só por fechar o menu.

### Alternativas Consideradas

- Exportação via modal separado — descartada por adicionar fricção desnecessária para uma ação de 2 cliques.

---

## Definition of Done Checklist

- [x] Codigo implementado conforme criterios de aceitacao
- [x] Decisao sobre Spec governada foi registrada
- [x] Decisao sobre Contract governado foi registrada
- [x] Nivel ScrumAIDev foi registrado
- [x] Spec, Contract e BDD foram atualizados quando aplicavel
- [x] Gates opcionais executados ou dispensados com justificativa
- [x] Error handling observavel segue o padrao compartilhado quando aplicavel
- [ ] Code review aprovado
- [x] Testes unitarios com cobertura adequada
- [x] Testes de integracao e contract passando
- [x] Documentacao atualizada
- [x] Build/CI passando
- [ ] `Behavior change` documentado no PR
- [ ] Aprovacao do Product Owner
