# User Story: [US-REL-01] Gerar e ver o relatório no chat

**Epic:** EPIC-14 — Relatórios a partir das respostas do chat
**Prioridade:** Alta (slice 1)
**Story Points:** 8
**Sprint:** —
**Status:** Review

**Origem:** [`docs/discovery/relatorios-chat.md`](../discovery/relatorios-chat.md) · [`docs/requirements/relatorios-chat.md`](../requirements/relatorios-chat.md)
**Requisitos:** FR01, FR02 (sem título de seção editável), FR04–FR10; BR01–BR08; NFR01 (chat), NFR05–NFR07; KD01–KD03, KD05, KD06
**Referência visual:** adaptação controlada do formulário "O que você quer no relatório?" de outra versão do Oráculo ao visual atual do Adito (sem ZIP do Figma para esta tela).

---

## 📖 História

**Como** gestor ou pesquisador que usa o chat do Adito
**Eu quero** juntar respostas que já recebi em um relatório que aparece na própria conversa
**Para que** eu tenha num só lugar os números, gráficos e tabelas da análise, atualizados com os dados atuais, sem copiar resposta por resposta

### Contexto Adicional
Cada resposta de análise já guarda o SQL, os formatos das colunas e o tipo de gráfico (`chat_message.metadata`), e o front recarrega as linhas reexecutando o SQL (`chat.message_rows`). Esta story cria o relatório como **mensagem da conversa** montada por modelo fixo, sem LLM. A ordem e os títulos editáveis das seções e o "Copiar" ficam na US-REL-02; o PDF, na US-REL-04.

---

## ✅ Critérios de Aceitação

- [x] **Critério 1 — Botão "Mais":** a área de entrada do chat mostra um botão "Mais" (+) com a opção "Criar relatório" somente quando a conversa atual tem ao menos uma resposta elegível (BR01: análise com SQL e dados; não entram `fallback`, `chat`, respostas interrompidas, respostas ainda gerando nem outros relatórios).
- [x] **Critério 2 — Formulário:** "Criar relatório" abre no chat o formulário com o título do relatório (preenchido com o título da conversa), a lista das respostas elegíveis em ordem cronológica, todas marcadas, cada uma com o título da pergunta, e o contador "N de M".
- [x] **Critério 3 — Validação:** "Gerar relatório" fica desativado com nenhuma seção marcada, com mais de 20 seções marcadas ou com título vazio; "Cancelar" fecha o formulário sem gravar nada.
- [x] **Critério 4 — Gravação:** gerar grava uma mensagem em `chat_message` com `metadata.type = "report"` contendo título, data e hora de geração, e a lista ordenada de seções (id da resposta de origem, título, SQL, `field_formats`, `chart_type`). O núcleo rejeita seções que não sejam respostas elegíveis da mesma conversa e do mesmo usuário, e não grava `QueryExecution`.
- [x] **Critério 5 — Exibição no chat:** a mensagem de relatório mostra título, data e hora, contexto e versão dos dados, e uma seção por resposta selecionada, numerada, com o cartão do número (resultado escalar) ou o gráfico no tipo da resposta de origem, a tabela com até 20 linhas e "mostrando X de Y registros", e o acesso ao SQL da seção.
- [x] **Critério 6 — Números atuais:** ao gerar e ao reabrir a conversa (inclusive depois de fechar o app), o SQL de cada seção é reexecutado com a política do contexto da conversa; as linhas não são gravadas.
- [x] **Critério 7 — Falhas por seção:** uma seção cujo SQL falha mostra "Não foi possível atualizar esta seção: os dados mudaram desde a pergunta"; uma seção sem linhas mostra "Nenhum registro para esta seção"; as demais seções aparecem normalmente.
- [x] **Critério 8 — Sem LLM:** gerar, mostrar e reabrir o relatório não chamam nenhum provedor de IA e funcionam sem chave configurada (teste com o LLM simulado que falha se for chamado).
- [x] **Critério 9 — Isolamento dos agentes:** a mensagem de relatório não entra no checkpointer do LangGraph; a próxima pergunta na mesma conversa é roteada e respondida como antes.
- [x] **Critério 10 — Compatibilidade:** conversas e mensagens existentes continuam abrindo, sincronizando e sendo copiadas como hoje; o contrato RPC só ganha métodos e campos novos.
- [x] **Critério 11 — Componentes compartilhados:** gráfico, cartão de número e tabela formatada saem do `ChatMessageBubble.vue` para componentes reutilizados pela resposta e pelo relatório, sem mudança visual nas respostas.
- [ ] **Critério 12 — Desempenho:** com o `dados.db` atual, um relatório de 10 seções aparece no chat em até 3 s depois de "Gerar relatório".
- [x] **Critério 13 — Acessibilidade:** botão "Mais", menu e formulário têm rótulos acessíveis e podem ser usados por teclado.

---

## 🎨 Mockups/Wireframes

Referência: formulário "O que você quer no relatório?" com lista de seções marcáveis e botões "Cancelar" e "Gerar relatório", aberto por um menu "+" com "Criar relatório" (print enviado pelo usuário em 2026-11-25). Nesta story não entram "Novas consultas", "Adicionar seção", "Criar apresentação" nem "Pensamento profundo".

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:**
  - Front: `ChatInputArea.vue` (botão "Mais" e menu), `ChatEstrategicoView.vue`/`ChatConversation.vue` (formulário e mensagem de relatório), `ChatMessageBubble.vue` (extração dos componentes), `useChatHistory.ts` e `types.ts` (novo tipo de mensagem).
  - Núcleo: `rpc/chat.py`.
- **APIs necessárias:**
  - novo método RPC para criar o relatório (ex.: `chat.reports.create`, com `conversation_id`, título e seções);
  - leitura das linhas pelo caminho que já existe (`chat.message_rows` da resposta de origem ou um método por relatório que reexecuta cada seção com `execute_query(sql, contexto_id)`).
- **Database changes:** nenhuma tabela nova; a mensagem usa `chat_message` com `metadata.type = "report"`.

### Dependências
- [x] Nenhuma dependência nova.
- [x] US-REL-03 (spike de PDF) pode correr em paralelo; não bloqueia esta story.

### Considerações de Performance
- Reexecutar as seções em paralelo ou em uma chamada só para evitar N idas e voltas ao núcleo.
- Gráficos sem animação longa quando o relatório tiver muitas seções.

---

## 🧪 Plano de Testes

### Testes Unitários
- [x] Python (`core/tests.py`): criar relatório válido; rejeitar seção de outra conversa, de outro usuário, `fallback`, `chat` e outro relatório; limite de 20 seções; sem `QueryExecution`; nenhuma chamada ao LLM.
- [x] Vitest: elegibilidade das respostas, contador "N de M", validação do botão "Gerar relatório", mapeamento do novo tipo em `useChatHistory`.

### Testes de Integração
- [x] Contrato RPC (`scripts/teste_contrato.py`) com o método novo; mensagens antigas inalteradas.
- [x] Playwright com `tauriMock.ts`: botão "Mais" só depois de resposta elegível, formulário, geração, seções com gráfico/cartão/tabela, seção com erro e seção vazia, relatório presente depois de reabrir a conversa.

### Testes Manuais
- [ ] No app desktop com o `dados.db` real: relatório de 3 e de 10 seções; tempo até aparecer.
- [ ] Tema escuro e claro.

---

## 📋 Tasks (Breakdown)

- [x] **[TASK-001]** Extrair gráfico, cartão e tabela do `ChatMessageBubble.vue` para componentes compartilhados
- [x] **[TASK-002]** Método RPC de criação do relatório, validação das seções e leitura das linhas
- [x] **[TASK-003]** Botão "Mais" e menu no `ChatInputArea.vue`
- [x] **[TASK-004]** Formulário do relatório (título, seleção, contador, validação)
- [x] **[TASK-005]** Mensagem de relatório no chat, histórico e reabertura
- [x] **[TASK-006]** Testes Python, contrato, Vitest e Playwright

---

## 🤖 IA Insights

### Sugestões de Implementação
- Guardar no `metadata` do relatório uma cópia do SQL, `field_formats` e `chart_type` de cada seção (e não só o id da resposta), para o relatório continuar coerente mesmo se a resposta de origem mudar de forma no futuro.

### Riscos Identificados
- O novo tipo de mensagem pode quebrar o "Copiar" ou a sincronização de conversas se o front não o tratar explicitamente.
- Seção com SQL antigo quebrado depois de mudança de views (o `chat.message_rows` já devolve 409 nesse caso).

### Alternativas Consideradas
- Tabela própria `chat_report`: descartada (KD01) para o relatório reabrir junto com a conversa sem nova sincronização.

---

## 📝 Notas e Comentários

- 2026-11-25: implementada na branch `feat/relatorios-chat`, junto com as outras stories do EPIC-14, a pedido do usuário (sem sprint planning). Nota do spike de PDF: [`docs/resultados/spike-pdf-relatorio-2026-11-25.md`](../resultados/spike-pdf-relatorio-2026-11-25.md).

- Decisões do usuário em 2026-11-25: modelo fixo sem LLM, relatório no chat, números atuais, salvo na conversa.

---

## ✓ Definition of Done Checklist

- [ ] Código implementado conforme critérios de aceitação
- [ ] Code review aprovado
- [x] Testes unitários com cobertura adequada
- [x] Testes de integração passando
- [x] Documentação atualizada
- [ ] Build/CI passando
- [ ] Deploy em staging
- [ ] Aprovação do Product Owner
