# Discovery — Relatórios a partir das respostas do chat

**Status:** PROBLEM_READY
**Classificacao de Processo:** HEAVY PROCESS
**Origem:** hibrido (usuario + codigo + referencia visual de outra versao do Oraculo)
**Data:** 2026-11-25
**Branch:** `docs/relatorios-chat`
**Epic proposto:** EPIC-14

## Intent
Permitir que o usuário do Adito transforme respostas que já recebeu no chat em um **relatório** organizado em seções. O relatório aparece **no próprio chat** e pode ser **exportado em PDF** com acabamento de documento oficial: capa, divisões, elementos visuais e a logo do Adito atestando que foi gerado pelo app. O objetivo é levar a análise para fora do app (reuniões, prestação de contas, relatórios de gestão de pesquisa e extensão) sem copiar tabela por tabela.

O relatório é montado por um **modelo fixo** preenchido com os resultados do SQL das perguntas escolhidas. Nesta iniciativa **não há texto escrito por LLM**; um texto interpretativo opcional fica para depois.

## Problem
1. Hoje cada resposta do chat é isolada. Para juntar várias análises, o usuário copia o texto e as tabelas (botão "Copiar") e monta o documento à mão, fora do app, perdendo os gráficos.
2. O único jeito de reunir resultados é o **Meu painel**, que serve para acompanhamento contínuo (grade de widgets), não para um documento linear com começo, meio e fim, que possa ser exportado e entregue.
3. Um documento montado à mão não mostra **de onde vieram os números** (SQL, contexto, versão dos dados) nem que saiu do Adito, o que reduz a credibilidade e dificulta conferir e repetir a análise depois.

## Users / Stakeholders relevantes
- **Gestores e coordenadores de pesquisa e extensão do Ifes:** querem um documento pronto para apresentar ou anexar, com números confiáveis e aparência de documento institucional.
- **Pesquisadores e servidores que usam o chat:** querem reaproveitar perguntas já feitas sem refazê-las em outra ferramenta.
- **Quem recebe o PDF** (direção, comissões, órgãos de fomento): precisa identificar a origem, a data e a base dos números.
- **Equipe de manutenção do Adito:** precisa que o relatório reuse o que já existe (SQL das respostas, tipos de gráfico, política do contexto) sem novo caminho de acesso aos dados e sem aumentar o consumo de cota do LLM.

## Current Situation
- **Respostas guardam o necessário.** Cada resposta do Adito é gravada em `chat_message` com `metadata.sql`, `metadata.field_formats` (formato de cada coluna) e `metadata.chart_type` (tipo de gráfico sugerido pelo agente de painéis). As linhas **não** são gravadas: `chat.message_rows` reexecuta o SQL no `dados.db` com a política do contexto da conversa (`execute_query(sql, contexto_id)`), e o front já recarrega as linhas ao reabrir uma conversa (`needsRows`).
- **Gráficos e tabelas já existem no front.** O `ChatMessageBubble.vue` desenha os 5 tipos do Meu painel (barras, barras horizontais, linhas, área, pizza), agrupa categorias pequenas em "Outros" e formata valores por `field_formats`.
- **Ações por resposta hoje:** "Ver SQL Gerado", "Fixar no Dashboard" e "Copiar". Não há menu "Mais" nem botão "+" no `ChatInputArea.vue`.
- **Meu painel** guarda widgets (`dashboard_widget`: `sql_validated`, `chart_type`, `contexto_id`) e os reexecuta com `widgets.refresh`, um modelo próximo do que uma seção de relatório precisa.
- **Identidade visual:** a logo do Adito já está no app (`public/brand/adito-light.png` e `adito-dark.png`, usadas pelo `BrandIcon.vue`), assim como as fontes em `public/fonts`.
- **Versões para carimbar o documento:** o Tauri expõe `dados_status` com a versão instalada do `dados.db` (ex.: `2026-11-01`), e a versão do app pode ser lida pela API do Tauri já instalada (`@tauri-apps/api/app`).
- **Exportação de arquivos:** o app não tem plugins de diálogo ou de sistema de arquivos (`src-tauri/Cargo.toml` só tem updater e process). Imprimir pelo webview ("Salvar como PDF" do sistema) não exige dependência nova; salvar o arquivo direto numa pasta ou gerar o PDF fora do webview exigiria.
- **Referência visual:** outra versão do Oráculo tem um formulário "O que você quer no relatório?" com recorte, lista de seções marcáveis, "Adicionar seção" e botão "Gerar relatório", aberto por um menu "+" com "Criar relatório". No Oraculo-ESX original havia um `report_agent` em que o LLM escrevia o relatório inteiro em Markdown; o Adito removeu esse código.

## Desired Outcome
- Depois de pelo menos uma resposta com dados, o usuário encontra um botão **"Mais" (+)** com a opção **Criar relatório**.
- Ele escolhe quais perguntas da conversa entram como seções, ajusta a ordem e os títulos, e gera o relatório.
- **O relatório aparece no chat**, como uma mensagem própria da conversa: título, data, contexto e versão dos dados no topo, e uma seção por pergunta (pergunta, número principal ou gráfico no tipo escolhido, tabela), com o SQL de cada seção disponível.
- A mensagem do relatório tem o botão **Exportar PDF**. O PDF segue o mesmo conteúdo com **acabamento de documento**:
  - capa com a logo do Adito, título, contexto, data e hora de geração, versão dos dados e versão do app;
  - sumário com as seções;
  - cabeçalho e rodapé em todas as páginas, com a logo, o título e o selo "Gerado pelo Adito", e numeração de páginas;
  - divisões por seção (número da seção, faixa de destaque), cartões com o número principal, gráficos com legenda numerada ("Figura 1 — …") e tabelas com cabeçalho destacado e linhas alternadas;
  - metodologia em anexo: SQL de cada seção, contexto, versão dos dados e um identificador do relatório.
- O relatório fica **salvo na conversa**: reabrir a conversa mostra o relatório de novo, com os números recalculados sobre os dados atuais.
- Todo número e todo gráfico vêm do resultado do SQL, sem passar por LLM; o mesmo relatório gerado duas vezes sobre os mesmos dados sai igual.

## Success Criteria
- O botão "Mais" com "Criar relatório" só aparece/fica ativo quando a conversa tem ao menos uma resposta com SQL e dados.
- Um relatório com N perguntas selecionadas tem exatamente N seções, na ordem escolhida, cada uma com o mesmo número, gráfico (mesmo tipo) e tabela que o usuário viu no chat para os dados atuais.
- O relatório aparece como mensagem da conversa e continua lá ao fechar e reabrir o app, com os números recalculados e a versão dos dados atualizada.
- Gerar e exportar o relatório **não faz nenhuma chamada ao LLM** e funciona sem chave configurada (comprovado por teste).
- Os dados de cada seção passam pela mesma política do contexto do chat (só leitura, só as views do contexto, colunas sensíveis bloqueadas).
- Uma seção cujo SQL falha (por exemplo, dados mudaram) aparece com aviso claro, sem derrubar o restante do relatório nem o PDF.
- O PDF tem capa com a logo, sumário, cabeçalho e rodapé com o selo "Gerado pelo Adito" em todas as páginas, numeração de páginas e metodologia; gráficos e tabelas saem inteiros e legíveis em A4, sempre em tema claro, no Windows e no Linux.
- Suítes do Python, contrato RPC, Vitest, build e Playwright passam, com testes novos para seleção, geração, relatório salvo na conversa, falha de seção e conteúdo do PDF.

## Scope

### IN
- Botão "Mais" (+) com a opção **Criar relatório**, disponível só quando há resposta com dados na conversa.
- Formulário do relatório: título editável, lista das perguntas da conversa com dados (marcáveis, com ordem e título editável), contador "N de M".
- **Relatório como mensagem do chat**, salvo na conversa (definição: perguntas, ordem, títulos), gerado por **modelo fixo**, sem LLM.
- Reexecução do SQL de cada seção no `dados.db` com a política do contexto da conversa, ao gerar e ao reabrir a conversa.
- Tipo de gráfico de cada seção: o que estava na tela/sugerido para a resposta, com os 5 tipos já existentes.
- Tratamento de seção com erro ou sem linhas.
- **Exportar PDF** a partir da mensagem do relatório, com layout de documento: capa, sumário, cabeçalho e rodapé com logo e selo "Gerado pelo Adito", numeração de páginas, divisões por seção, cartões de destaque, legendas de figura, tabelas formatadas e metodologia em anexo.
- Testes (Python, contrato, Vitest, Playwright com o núcleo simulado).

### OUT
- Texto escrito por LLM (resumo executivo, conclusões, interpretação das seções).
- "Adicionar seção" com pergunta livre (exigiria o agente de BI, ou seja, LLM).
- "Criar apresentação" (slides) e "Pensamento profundo", que aparecem no menu da referência visual.
- Seções geradas automaticamente a partir do recorte (evolução no tempo, por campus, ranking) sem pergunta correspondente.
- Exportação em Word/ODT/planilha.
- Assinatura digital do PDF ou qualquer garantia criptográfica de autenticidade (o selo e a logo identificam a origem, mas não impedem edição do arquivo).
- Compartilhamento, envio por e-mail ou publicação do relatório.
- Mudanças no Meu painel.

### LATER
- **Texto interpretativo opcional por LLM** (resumo executivo cruzando as seções), desligado por padrão, recebendo só resultados agregados, com conferência automática de que todo número do texto existe nos dados e marcação "gerado por IA".
- Verificação de autenticidade do PDF (por exemplo, código de verificação ou hash do conteúdo no rodapé, conferível dentro do app).
- Lista "Meus relatórios" fora do chat, reunindo os relatórios de todas as conversas.
- "Adicionar seção" com pergunta livre, respondida pelo agente de BI.
- Seções sugeridas a partir do recorte (evolução no tempo, por campus, por categoria, ranking), por regra e sem LLM.
- Montar relatório a partir de widgets do Meu painel ou de perguntas de outras conversas.
- Exportação em Markdown/Word.
- "Criar apresentação".

## Constraints / Feasibility
- **Sem dependências novas sem aprovação (AGENTS.md, regra 6).** O caminho preferido é gerar o PDF pela impressão do webview (`window.print()` com uma página de impressão própria e CSS `@page`), sem dependência nova. Se o resultado não atender aos critérios (cabeçalho/rodapé em todas as páginas, numeração, gráficos inteiros) em alguma plataforma, a alternativa (plugin do Tauri ou biblioteca de PDF) será proposta e precisará de aprovação.
- **Impressão no Tauri:** WebView2 (Windows) e WebKitGTK (Linux) oferecem impressão com "Salvar como PDF", mas o comportamento de `window.print()` dentro do Tauri v2, e o suporte a numeração de páginas e cabeçalho/rodapé repetidos, precisam ser confirmados nas duas plataformas (spike na primeira story de PDF).
- **Dados pela mesma porta do chat:** reexecutar via `execute_query(sql, contexto_id)`, que já aplica `mode=ro`, authorizer e a política do contexto; não criar outro acesso ao `dados.db`.
- **Histórico guarda só SQL:** respostas e relatórios não guardam as linhas; o relatório depende da reexecução. Se os dados ou as views mudarem, uma seção pode falhar ou mostrar números diferentes dos que estavam no chat.
- **Persistência na conversa:** o relatório vira uma mensagem em `chat_message` com metadados próprios (tipo "relatório", seções com referência às respostas de origem, SQL, títulos, ordem). O histórico do chat, o `chat.conversations.list` e o contrato RPC precisam aceitar esse novo tipo sem quebrar as mensagens existentes; o checkpointer do LangGraph não deve receber o relatório como mensagem da IA.
- **Desempenho:** consultas do contexto respondem em dezenas de milissegundos no `dados.db` atual (medido no Explorar dados: até ~110 ms com busca e agrupamento em ~9,5 mil linhas); um relatório com 10 seções deve gerar em poucos segundos.
- **Reuso do front:** os componentes de gráfico e formatação estão dentro do `ChatMessageBubble.vue`; para não duplicar entre resposta, relatório no chat e PDF, eles precisam ser extraídos para componentes reutilizáveis.
- **Identidade visual:** usar a logo e as fontes que já estão no app; o PDF sai sempre em tema claro.
- **Multiplataforma:** Windows e Linux (ADR do porte desktop).

## Assumptions
- [ASSUMPTION] As seções vêm só das respostas **da conversa atual** que têm SQL e dados (não entram respostas de conversa simples, avisos de "não encontrei" nem respostas interrompidas).
- [ASSUMPTION] O botão "Mais" (+) fica na **área de entrada do chat**, como na referência visual, e só aparece quando a conversa tem ao menos uma resposta com dados.
- [ASSUMPTION] O título de cada seção é a pergunta original, editável no formulário.
- [ASSUMPTION] O **texto da resposta** original (escrito por LLM quando a pergunta foi feita) **não entra** no relatório, para não misturar texto possivelmente desatualizado com números atuais; entram número, gráfico, tabela e SQL.
- [ASSUMPTION] A tabela de cada seção mostra até 20 linhas, com a indicação do total.
- [ASSUMPTION] Resultado escalar (uma linha e uma coluna) vira um cartão de número, sem gráfico.
- [ASSUMPTION] No chat, a mensagem do relatório é mais compacta que o PDF (sem capa de página inteira nem sumário), mas com o mesmo conteúdo de seções.
- [ASSUMPTION] "Comprovar que foi gerado pelo Adito" significa identificação visual (logo, selo, data, versões e identificador do relatório), não assinatura digital.
- [ASSUMPTION] Um relatório gerado não muda depois: para mudar seções, o usuário gera um novo relatório (que vira nova mensagem).

## Risks
- **`window.print()` no Tauri** pode não abrir o diálogo, não repetir cabeçalho/rodapé ou não numerar páginas em uma das plataformas. Mitigação: spike na primeira story de PDF; plano B com dependência aprovada.
- **Gráficos do ApexCharts na impressão:** animações e tamanhos responsivos podem sair errados ou cortados entre páginas. Mitigação: desligar animações, fixar largura e evitar quebra dentro de figuras no modo de impressão.
- **Números diferentes dos do chat:** se o `dados.db` foi atualizado depois da pergunta, o relatório mostra números novos. Mitigação: carimbar a versão dos dados e a data de geração na capa, no rodapé e na metodologia.
- **SQL antigo quebrado** depois de mudança de views (já acontece em `chat.message_rows`, que devolve 409). Mitigação: seção com aviso, relatório e PDF seguem.
- **Novo tipo de mensagem no chat** pode quebrar o histórico, a sincronização de conversas, o "Copiar" ou o checkpointer. Mitigação: tipo explícito nos metadados, testes de histórico e de contrato.
- **Falsa sensação de autenticidade:** a logo e o selo não impedem que o PDF seja editado. Mitigação: deixar claro no escopo; verificação de autenticidade em LATER.
- **Escopo crescer para "relatório com IA"** antes de o modelo fixo estar estável. Mitigação: texto interpretativo explicitamente em LATER.
- **Duplicação de lógica de gráfico** entre chat, relatório, PDF e Meu painel. Mitigação: extrair componentes compartilhados.

## Open Questions
- [BLOCKING? nao] Resolvidas em 2026-11-25 (ver ajustes do usuário). Nenhuma pergunta bloqueante aberta.

## Review & Adjust

- [x] Usuario revisou a proposta completa
- [x] Alteracoes solicitadas foram incorporadas
- [x] Decisoes relevantes foram confirmadas
- [x] Nao existem perguntas bloqueantes abertas

### User adjustments
- 2026-11-25: classificação alterada pelo usuário de NORMAL PROCESS para **HEAVY PROCESS**.
- 2026-11-25: relatório por **modelo fixo** preenchido com o SQL das perguntas selecionadas; texto interpretativo por LLM fica como possibilidade futura (LATER).
- 2026-11-25 — decisão 1 (salvar): o relatório fica **salvo na conversa**, como mensagem do chat. A lista "Meus relatórios" separada foi para LATER, porque o relatório já é reaberto junto com a conversa.
- 2026-11-25 — decisão 2 (números): **atuais**, recalculados ao gerar e ao reabrir, com a versão dos dados carimbada.
- 2026-11-25 — decisão 3 (saída), alterada pelo usuário: o relatório é **escrito no chat**, com a opção de **exportar em PDF**. O PDF ganha organização e elementos visuais a mais (capa, divisões, cabeçalho e rodapé, numeração, cartões, legendas) e a **logo do Adito** atestando que o documento foi gerado por ele.
- 2026-11-26 — adendo (visual do PDF), pedido do usuário: o PDF fica com **cara de documento formal** e menos enfeite. Saem a capa com a logo grande, o selo "Gerado pelo Adito", o rodapé e o texto corrido; ficam a logo pequena com o nome "Adito" no topo de toda página, tabelas e gráficos numerados com a fonte, títulos e o apêndice com o SQL. Requisitos FR13–FR17 e BR09 ajustados.

## Gate G0 — PROBLEM READY

**Status:** APPROVED

**Aprovado pelo usuario:** sim (2026-11-25)
