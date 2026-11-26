# User Story: [US-REL-04] Exportar o relatório em PDF com acabamento

**Epic:** EPIC-14 — Relatórios a partir das respostas do chat
**Prioridade:** Alta (slice 3)
**Story Points:** 5
**Sprint:** —
**Status:** Review

**Origem:** [`docs/discovery/relatorios-chat.md`](../discovery/relatorios-chat.md) · [`docs/requirements/relatorios-chat.md`](../requirements/relatorios-chat.md)
**Requisitos:** FR12–FR18; BR03, BR09, BR10; NFR01 (PDF), NFR02–NFR04, NFR07; KD04

---

## 📖 História

**Como** gestor que precisa apresentar ou anexar uma análise
**Eu quero** exportar o relatório do chat em PDF com aparência de documento institucional e a logo do Adito
**Para que** quem recebe o arquivo reconheça a origem, a data e a base dos números e confie no documento

### Contexto Adicional
O relatório já existe no chat (US-REL-01) e o caminho de geração do PDF foi decidido no spike (US-REL-03). O PDF tem o mesmo conteúdo do chat, com organização e elementos visuais a mais, e sai sempre em tema claro.

---

## ✅ Critérios de Aceitação

- [x] **Critério 1 — Ação:** a mensagem de relatório tem "Exportar PDF", que gera o PDF a partir dos dados mostrados no momento, sem chamar nenhum provedor de IA.
- [x] **Critério 2 — Primeira página:** contexto, título, base de dados com a versão, data e hora de geração, versão do app e identificador do relatório (id da mensagem).
- [x] **Critério 3 — Conteúdo:** a primeira página lista o número e o título de cada seção e o apêndice.
- [x] **Critério 4 — Cabeçalho:** toda página tem a logo pequena com o nome "Adito" no canto superior esquerdo e o número da página no canto superior direito; sem rodapé e sem selo.
- [x] **Critério 5 — Seções:** cada seção começa em página nova com o título numerado, a "Tabela N – título" e a "Figura N – título" no tipo da seção, cada uma com a linha "Fonte:"; resultado escalar vira "Quadro N"; seções com erro ou sem linhas mostram o mesmo aviso do chat. Arial, margens ABNT e tabelas no padrão IBGE.
- [x] **Critério 6 — Apêndice:** o PDF termina com o "Apêndice A – Consultas utilizadas", com o SQL de cada seção e a frase de que os números foram calculados diretamente da base, sem uso de IA.
- [x] **Critério 7 — Layout:** A4 retrato; gráficos e tabelas não são cortados no meio; o cabeçalho da tabela se repete quando ela continua; fontes do app embutidas; sem animações; tema claro mesmo com o app no tema escuro.
- [x] **Critério 8 — Nome do arquivo:** o nome sugerido é `Relatório - <título> - <AAAA-MM-DD>.pdf`.
- [ ] **Critério 9 — Plataformas e tempo:** funciona no Windows e no Linux; com 10 seções, o PDF fica pronto para salvar em até 5 s.
- [x] **Critério 10 — Cancelamento:** cancelar a janela de impressão (ou de salvar) não grava nem altera nada.
- [x] **Critério 11 — Sem dependência não aprovada:** o caminho usado é o decidido na US-REL-03; nenhuma dependência entra sem aprovação registrada.

---

## 🎨 Mockups/Wireframes

Estrutura definida em FR13–FR17; protótipo da US-REL-03 como base visual.

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** página/rota de impressão do relatório, ação "Exportar PDF" na mensagem de relatório, componentes de gráfico, cartão e tabela compartilhados (US-REL-01) em modo de impressão.
- **APIs necessárias:** `window.print()` (ou a alternativa aprovada no spike); `dados_status` para a versão dos dados; `@tauri-apps/api/app` para a versão do app.
- **Database changes:** nenhuma.

### Dependências
- [x] US-REL-01
- [x] US-REL-03 (decisão do caminho do PDF)

### Considerações de Performance
- Renderizar os gráficos sem animação e com largura fixa antes de abrir a impressão.

---

## 🧪 Plano de Testes

### Testes Unitários
- [x] Vitest: montagem da página de impressão (abertura, conteúdo, numeração das seções, tabelas, figuras e quadros, apêndice com o SQL, nome do arquivo, seções com aviso).

### Testes de Integração
- [x] Playwright com `tauriMock.ts`: abrir a página de impressão de um relatório e conferir a abertura, as seções, "Tabela N", "Figura N", o apêndice e o tema claro; gerar o PDF pelo Chromium do Playwright e conferir número de páginas e textos; liberar o botão quando a impressão fecha sem `afterprint` ou a conversa muda.

### Testes Manuais
- [ ] Exportar no Windows e no Linux um relatório de 3 e de 10 seções e conferir os critérios 2 a 8.

---

## 📋 Tasks (Breakdown)

- [x] **[TASK-001]** Página de impressão do relatório (a partir do protótipo do spike)
- [x] **[TASK-002]** Primeira página, lista do conteúdo, cabeçalho com a logo pequena e número da página
- [x] **[TASK-003]** Seções com Tabela N, Figura N e Quadro N, cada uma com a fonte, no modo de impressão
- [x] **[TASK-004]** Apêndice A com o SQL de cada seção
- [x] **[TASK-005]** Ação "Exportar PDF" e nome do arquivo
- [ ] **[TASK-006]** Testes Vitest e Playwright; verificação manual nas duas plataformas

---

## 🤖 IA Insights

### Sugestões de Implementação
- Montar a página de impressão a partir dos mesmos dados já carregados na mensagem de relatório, para não reexecutar o SQL de novo ao exportar.

### Riscos Identificados
- Diferenças de renderização entre WebView2 e WebKitGTK (fontes, quebras de página).
- A logo pode ser lida como garantia de autenticidade; o PDF não é assinado (BR09).

### Alternativas Consideradas
- Verificação de autenticidade (código ou hash no rodapé): fica para depois (LATER do Discovery).

---

## 📝 Notas e Comentários

- 2026-11-25: implementada na branch `feat/relatorios-chat`, junto com as outras stories do EPIC-14, a pedido do usuário (sem sprint planning). Nota do spike de PDF: [`docs/resultados/spike-pdf-relatorio-2026-11-25.md`](../resultados/spike-pdf-relatorio-2026-11-25.md).
- 2026-11-26: visual refeito a pedido do usuário (documento formal, sem capa com logo grande, sem selo e sem rodapé; só tabelas, gráficos e títulos). Critérios 2 a 6 ajustados.

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
