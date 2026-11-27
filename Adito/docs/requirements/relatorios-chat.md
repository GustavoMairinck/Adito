# Requirements — Relatórios a partir das respostas do chat

**Status:** REQUIREMENTS_READY
**Discovery de origem:** [`docs/discovery/relatorios-chat.md`](../discovery/relatorios-chat.md) (PROBLEM_READY em 2026-11-25)
**Classificacao de Processo:** HEAVY PROCESS
**Epic proposto:** EPIC-14

## Intent Summary
O usuário reúne respostas que já recebeu no chat em um **relatório por modelo fixo**, que aparece **como mensagem da conversa** e pode ser **exportado em PDF** com acabamento de documento institucional e a logo do Adito. Todo número sai do SQL das respostas, reexecutado sobre os dados atuais com a política do contexto, **sem nenhuma chamada ao LLM**.

## Functional Requirements

### Entrada e formulário
- **FR01** — O chat mostra um botão **"Mais" (+)** na área de entrada, com a opção **Criar relatório**. O botão só aparece quando a conversa atual tem ao menos uma resposta elegível (BR01).
- **FR02** — **Criar relatório** abre um formulário no chat ("O que você quer no relatório?") com:
  - título do relatório, editável, preenchido com o título da conversa;
  - a lista das respostas elegíveis da conversa, cada uma com caixa de seleção e título da seção (a pergunta original, editável);
  - contador "N de M" de seções marcadas;
  - botões **Cancelar** e **Gerar relatório**.
- **FR03** — No formulário, o usuário muda a ordem das seções (subir/descer); a ordem inicial é a cronológica da conversa.
- **FR04** — **Gerar relatório** fica desativado sem nenhuma seção marcada ou com título vazio; **Cancelar** fecha o formulário sem gravar nada.

### Geração e mensagem do relatório
- **FR05** — Gerar cria **uma mensagem de relatório na conversa**, gravada no `app.db`, com o título, a data e hora de geração, o contexto e a lista ordenada de seções. Cada seção guarda a referência à resposta de origem, o título, o SQL, os formatos das colunas e o tipo de gráfico.
- **FR06** — Para mostrar o relatório (ao gerar e ao reabrir a conversa), o app reexecuta o SQL de cada seção no `dados.db` com a política do contexto da conversa e preenche o modelo com os dados atuais.
- **FR07** — No chat, a mensagem de relatório mostra:
  - cabeçalho: título, data e hora de geração, contexto e versão dos dados;
  - uma seção por pergunta, na ordem escolhida, com número da seção, título, o número principal (cartão) ou o gráfico no tipo da seção, e a tabela;
  - acesso ao SQL de cada seção (como o "Ver SQL Gerado" das respostas).
- **FR08** — O gráfico de cada seção usa o tipo que a resposta de origem tinha na tela ao gerar (escolha do usuário ou sugestão do agente de painéis), entre os 5 tipos já existentes; resultado escalar vira cartão de número, sem gráfico.
- **FR09** — A tabela de cada seção mostra até 20 linhas, com a indicação "mostrando X de Y registros".
- **FR10** — Uma seção cujo SQL falha mostra um aviso no lugar do conteúdo ("Não foi possível atualizar esta seção: os dados mudaram desde a pergunta"); uma seção sem linhas mostra "Nenhum registro para esta seção". As demais seções aparecem normalmente.
- **FR11** — A mensagem de relatório tem a ação **Copiar**, que copia o relatório em texto (título, seções, números e tabelas em Markdown), no mesmo padrão do "Copiar" das respostas.

### Exportação em PDF
- **FR12** — A mensagem de relatório tem a ação **Exportar PDF**, que gera um PDF com o mesmo conteúdo, a partir dos dados mostrados no momento.
- **FR13** — O PDF abre com uma **primeira página** com o contexto, o título, a base de dados (contexto e versão dos dados), a data e hora de geração, a versão do app e o identificador do relatório.
- **FR14** — A primeira página lista o **conteúdo**: número e título de cada seção e o apêndice.
- **FR15** — Toda página do PDF tem, no canto superior esquerdo, a **logo pequena com o nome "Adito"** e, no canto superior direito, o número da página. Não há rodapé nem selo.
- **FR16** — Cada seção começa em página nova com o título numerado e mostra a tabela ("Tabela N – título") e o gráfico ("Figura N – título"), cada um com a linha "Fonte:" embaixo; resultado escalar vira "Quadro N" com o valor em destaque. Visual de documento formal: Arial, margens ABNT, tabelas no padrão IBGE (traços horizontais, sem linhas verticais).
- **FR17** — O PDF termina com o **Apêndice A – Consultas utilizadas**: o SQL de cada seção e a observação de que os números foram calculados diretamente da base, sem uso de IA.
- **FR18** — O nome sugerido do arquivo é `Relatório - <título> - <AAAA-MM-DD>.pdf`.

## Business / Domain Rules
- **BR01** — Resposta **elegível** para seção: resposta do Adito na conversa atual, com SQL e com dados (tipo `analysis`), que não seja aviso de "não encontrei" (`fallback`), conversa simples (`chat`), resposta interrompida nem outro relatório.
- **BR02** — Um relatório tem de 1 a 20 seções.
- **BR03** — O relatório **não usa LLM**: gerar, mostrar, reabrir, copiar e exportar não chamam nenhum provedor de IA e funcionam sem chave configurada.
- **BR04** — O **texto da resposta** original (escrito por LLM quando a pergunta foi feita) **não entra** no relatório; entram título, número, gráfico, tabela e SQL.
- **BR05** — Os números são sempre os **atuais**: cada exibição e cada exportação reexecuta o SQL. O relatório não grava as linhas de resultado.
- **BR06** — Um relatório gerado **não muda**: para alterar seções, títulos ou ordem, o usuário gera um novo relatório, que vira nova mensagem.
- **BR07** — A mensagem de relatório **não entra no histórico dos agentes** (checkpointer do LangGraph) e não altera o contexto das próximas perguntas.
- **BR08** — O relatório só lê dados pelo mesmo caminho do chat: views do contexto da conversa, colunas sensíveis bloqueadas, banco só leitura.
- **BR09** — Logo e identificador **identificam a origem**; o app não afirma que o PDF é à prova de edição (sem assinatura digital nesta iniciativa).
- **BR10** — O PDF sai sempre em **tema claro**, independentemente do tema do app.

## Non-Functional Requirements
- **NFR01 — Desempenho:** com o `dados.db` atual, um relatório de 10 seções aparece no chat em até 3 s depois de "Gerar relatório", e o PDF fica pronto para salvar em até 5 s.
- **NFR02 — Sem dependência nova sem aprovação:** o PDF é gerado pela impressão do webview com página de impressão própria. Se um critério de FR13–FR16 não for atingível assim no Windows ou no Linux, a alternativa (plugin do Tauri ou biblioteca) é proposta e só entra com aprovação (AGENTS.md, regra 6).
- **NFR03 — Multiplataforma:** geração, exibição e PDF funcionam no Windows (WebView2) e no Linux (WebKitGTK).
- **NFR04 — Legibilidade do PDF:** A4 retrato; gráficos e tabelas não são cortados no meio entre páginas (cabeçalho da tabela se repete quando ela continua); fontes do app embutidas; sem animações.
- **NFR05 — Compatibilidade:** conversas e mensagens existentes continuam abrindo, sincronizando e sendo copiadas como hoje; o contrato RPC só ganha métodos e campos novos.
- **NFR06 — Acessibilidade:** botão "Mais", menu, formulário e ações do relatório com rótulos acessíveis e uso por teclado.
- **NFR07 — Testabilidade:** a montagem do relatório (seleção, ordem, elegibilidade, falha de seção, conteúdo do texto copiado e da página de impressão) é testável sem LLM e sem o app desktop, com o núcleo simulado no Playwright.

## User Scenarios

### Main flow
1. O usuário faz perguntas no chat e recebe respostas com dados (por exemplo, "pagamentos por ano", "bolsas por modalidade", "projetos por campus").
2. O botão **"Mais" (+)** aparece na área de entrada; ele clica e escolhe **Criar relatório**.
3. O formulário lista as três respostas, todas marcadas; ele renomeia o título do relatório, desmarca uma seção, ajusta a ordem e clica em **Gerar relatório**.
4. Aparece na conversa uma mensagem de relatório com cabeçalho e duas seções, cada uma com gráfico e tabela.
5. Ele clica em **Exportar PDF**, confere a prévia (capa com a logo, sumário, seções, metodologia) e salva o arquivo.
6. Dias depois, reabre a conversa: o relatório continua lá, com os números recalculados e a versão dos dados atual.

### Alternative / Error / Edge cases
- **Conversa sem resposta elegível** (só conversa, só avisos, ou vazia): o botão "Mais" não aparece.
- **Resposta escalar** ("quantos projetos existem?"): a seção mostra só o cartão do número.
- **Resposta com muitas linhas:** a tabela mostra 20 e indica o total; o gráfico segue o agrupamento em "Outros" que o chat já usa.
- **SQL de uma seção falha** ao reabrir (view mudou): a seção mostra o aviso; o resto do relatório e o PDF continuam.
- **Seção sem linhas** (dados atualizados removeram os registros): a seção mostra "Nenhum registro para esta seção".
- **Usuário cancela** o formulário ou a janela de impressão: nada é gravado nem exportado.
- **Sem chave de LLM configurada:** criar, ver e exportar o relatório funcionam normalmente.
- **Resposta ainda gerando** na conversa: ela não aparece como elegível até terminar.
- **Núcleo reinicia** durante a geração: o usuário vê erro amigável e pode tentar de novo; nenhuma mensagem pela metade fica gravada.
- **Muitas seções** (20): o formulário rola, o relatório gera e o PDF pagina sem cortar figuras.
- **App em tema escuro:** o relatório no chat segue o tema; o PDF sai claro.

## Business / Domain Context
- Usuários são gestores, coordenadores e pesquisadores do Ifes que precisam apresentar números de pesquisa e extensão (bolsas, projetos, ações, produção) em reuniões e prestações de contas.
- Os dados vêm do `dados.db` publicado pela equipe (SRC, SigPesq, Lattes e CNPq DGP), com versão datada; números podem mudar entre versões.
- Os dados usados não são considerados privados, mas o app mantém a política de colunas sensíveis por contexto.

## Technical Context & Constraints
- **Núcleo Python (`rpc/chat.py`):**
  - novo método para gravar a mensagem de relatório, validando que cada seção referencia uma resposta elegível da mesma conversa e do mesmo usuário;
  - leitura das linhas pelo caminho que já existe (`chat.message_rows`/`execute_query` com a política do contexto) ou por um método por relatório;
  - a mensagem usa `chat_message` com `metadata.type = "report"`, sem gravar `QueryExecution`;
  - o checkpointer do LangGraph não é tocado, porque os agentes leem o histórico dele, não da `chat_message`.
- **Front (`modules/chat`):**
  - extrair do `ChatMessageBubble.vue` os componentes de gráfico, cartão e tabela com formatação, para reuso na resposta, no relatório e na página de impressão;
  - o histórico (`useChatHistory.ts`) passa a mapear o novo tipo de mensagem.
- **PDF:**
  - página/rota de impressão dedicada, com CSS `@page` (A4), regras de quebra de página, cabeçalho e rodapé repetidos e numeração;
  - a viabilidade de cabeçalho/rodapé e de "Página X de Y" no WebView2 e no WebKitGTK precisa de spike antes da implementação completa.
- **Identidade visual:** `public/brand/adito-light.png` e fontes de `public/fonts`.
- **Versões:** `dados_status` (Tauri) para a versão dos dados; `@tauri-apps/api/app` para a versão do app.
- **Testes:**
  - `core/tests.py` e contrato RPC (`scripts/teste_contrato.py`) para os métodos novos;
  - Vitest para a montagem do relatório e o texto copiado;
  - Playwright com `tauriMock.ts` para o fluxo completo e a página de impressão.

## Quality Attributes
- **Confiabilidade:** números vêm só do SQL; uma seção com erro não derruba as outras; nada pela metade fica gravado.
- **Rastreabilidade:** cada seção mostra o SQL; o PDF traz versão dos dados, versão do app, data e identificador.
- **Manutenibilidade:** um único conjunto de componentes de gráfico/tabela para chat, relatório e PDF.
- **Testabilidade:** fluxo inteiro coberto sem LLM, com o núcleo simulado.
- **Segurança:** mesmo caminho de leitura do chat (só leitura, views do contexto, colunas sensíveis bloqueadas); validação de que as seções pertencem à conversa e ao usuário.

## Assumptions
- **A01** — O botão "Mais" (+) fica na área de entrada do chat, à esquerda do campo, como na referência visual.
- **A02** — Só entram respostas da conversa atual (relatório com respostas de outras conversas fica para depois).
- **A03** — No chat, o relatório é mais compacto que o PDF: sem capa de página inteira e sem sumário.
- **A04** — Limite de 20 seções por relatório e de 20 linhas por tabela.
- **A05** — O identificador do relatório é o id da mensagem de relatório.
- **A06** — A exportação usa a janela de impressão do sistema ("Salvar como PDF"); o usuário escolhe a pasta nela.
- **A07** — O tipo de gráfico da seção é o da resposta no momento da geração e não muda depois (BR06).

## Out of Scope
- Texto escrito por LLM (resumo executivo, conclusões, interpretação).
- "Adicionar seção" com pergunta livre.
- "Criar apresentação" e "Pensamento profundo".
- Seções automáticas a partir do recorte (evolução no tempo, por campus, ranking).
- Exportação em Word/ODT/planilha/Markdown em arquivo.
- Assinatura digital ou verificação de autenticidade do PDF.
- Lista "Meus relatórios" fora do chat; editar ou excluir um relatório gerado.
- Compartilhamento, e-mail ou publicação.
- Mudanças no Meu painel.

## Open Questions
- [BLOCKING? nao] Nenhuma pergunta bloqueante aberta. A viabilidade de cabeçalho/rodapé e numeração na impressão do Tauri é tratada como spike (NFR02).

## Key Decisions Proposed
- **KD01** — O relatório é uma **mensagem da conversa** (`chat_message` com `metadata.type = "report"`), não uma tabela nova nem uma tela separada.
- **KD02** — O relatório guarda só a **definição** (seções, SQL, títulos, ordem, tipos de gráfico); as linhas são sempre reexecutadas (BR05).
- **KD03** — O texto original das respostas fica de fora; o relatório é 100% determinístico (BR03, BR04).
- **KD04** — PDF pela **impressão do webview** com página de impressão própria, sem dependência nova; alternativa só com aprovação depois do spike (NFR02).
- **KD05** — Os componentes de gráfico, cartão e tabela saem do `ChatMessageBubble.vue` e passam a ser compartilhados entre resposta, relatório e PDF.
- **KD06** — Relatório gerado é imutável; mudanças geram outro relatório (BR06).

## Review & Adjust

O usuario pode **aprovar, editar, adicionar, remover ou reclassificar** qualquer requisito/regra antes do gate.

- [x] Proposta completa apresentada ao usuario
- [x] Ajustes solicitados incorporados
- [x] IDs estabilizados depois da revisao
- [x] Nenhuma pergunta bloqueante aberta

### User adjustments
- 2026-11-25: proposta aprovada sem alterações.
- 2026-11-26: o usuário pediu um PDF com cara de documento formal e menos enfeite: sem capa com logo grande, sem selo "Gerado pelo Adito" e sem rodapé; logo pequena com o nome no topo de toda página; só tabelas, gráficos e títulos, sem texto corrido. FR13–FR17 e BR09 ajustados.

## Gate G1 — REQUIREMENTS READY

**Status:** APPROVED

**Aprovado pelo usuario:** sim (2026-11-25)
