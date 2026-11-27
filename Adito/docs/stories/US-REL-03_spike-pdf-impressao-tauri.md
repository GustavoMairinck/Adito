# User Story: [US-REL-03] Spike: PDF pela impressão do Tauri

**Epic:** EPIC-14 — Relatórios a partir das respostas do chat
**Prioridade:** Alta (slice 1, em paralelo à US-REL-01)
**Story Points:** 2 (limite de tempo: 1 dia)
**Sprint:** —
**Status:** Review

**Origem:** [`docs/discovery/relatorios-chat.md`](../discovery/relatorios-chat.md) · [`docs/requirements/relatorios-chat.md`](../requirements/relatorios-chat.md)
**Requisitos:** NFR02, NFR03, NFR04; KD04 (insumo para FR12–FR18)

---

## 📖 História

**Como** equipe de manutenção do Adito
**Eu quero** confirmar se a impressão do webview gera, no Windows e no Linux, um PDF com o acabamento pedido
**Para que** a US-REL-04 siga pelo caminho sem dependência nova ou, se não der, a alternativa seja proposta e aprovada antes da implementação

### Contexto Adicional
O app não tem plugins de diálogo nem de sistema de arquivos. O caminho preferido (KD04) é uma página de impressão própria com CSS `@page` e `window.print()`, usando "Salvar como PDF" do sistema. O suporte do WebView2 (Windows) e do WebKitGTK (Linux) a cabeçalho e rodapé repetidos, numeração de páginas e quebras controladas precisa ser verificado antes.

---

## ✅ Critérios de Aceitação

- [x] **Critério 1 — Protótipo:** existe uma página de impressão de teste com capa, sumário, duas seções (gráfico do ApexCharts e tabela longa que passa de uma página) e anexo, usando a logo (`public/brand/adito-light.png`) e as fontes do app.
- [ ] **Critério 2 — Janela de impressão:** confirmado, no app desktop do Windows e do Linux, se `window.print()` abre a janela de impressão com "Salvar como PDF".
- [ ] **Critério 3 — Verificação do PDF:** para cada plataforma, registrado se o PDF salvo tem:
  - cabeçalho e rodapé repetidos em todas as páginas, exceto a capa;
  - "Página X de Y";
  - gráfico inteiro, sem corte entre páginas e sem animação pela metade;
  - cabeçalho da tabela repetido quando ela continua na página seguinte;
  - fontes do app embutidas;
  - tema claro com o app em tema escuro.
- [x] **Critério 4 — Decisão registrada:** a conclusão fica registrada (nota de decisão em `Adito/docs/` ou adenda de ADR) com o que funciona em cada plataforma e o caminho escolhido para a US-REL-04.
- [x] **Critério 5 — Alternativa:** se algum item do Critério 3 não for atingível sem dependência nova, a nota traz a alternativa proposta (plugin do Tauri ou biblioteca de PDF), com tamanho, licença e impacto no empacotamento, para aprovação do usuário (AGENTS.md, regra 6). Nenhuma dependência entra nesta story.
- [x] **Critério 6 — Sem código de produção:** o protótipo não fica no menu nem nas rotas do app; o que for aproveitável vira insumo para a US-REL-04.

---

## 🎨 Mockups/Wireframes

Estrutura do PDF descrita em FR13–FR17 dos requisitos (capa, sumário, cabeçalho/rodapé, divisões, cartões, "Figura N", tabelas, metodologia).

---

## 🔧 Notas Técnicas

### Arquitetura
- **Componentes afetados:** protótipo descartável no front (fora das rotas do app).
- **APIs necessárias:** `window.print()`; versão do app por `@tauri-apps/api/app`.
- **Database changes:** nenhuma.

### Dependências
- [ ] Acesso a uma máquina Windows e a uma Linux com o app desktop.

### Considerações de Performance
- Medir quanto tempo a janela de impressão leva para abrir com um relatório de 10 seções (meta do NFR01: até 5 s).

---

## 🧪 Plano de Testes

### Testes Unitários
- [ ] Não se aplica (spike).

### Testes de Integração
- [ ] Não se aplica (spike).

### Testes Manuais
- [ ] Gerar o PDF do protótipo no Windows e no Linux e conferir os itens do Critério 3.

---

## 📋 Tasks (Breakdown)

- [x] **[TASK-001]** Página de impressão de teste com CSS `@page`
- [ ] **[TASK-002]** Teste no Windows (WebView2)
- [ ] **[TASK-003]** Teste no Linux (WebKitGTK)
- [x] **[TASK-004]** Nota de decisão e, se preciso, proposta de dependência

---

## 🤖 IA Insights

### Sugestões de Implementação
- Margin boxes do `@page` (`@top-center`, `counter(page)`) têm suporte recente no Chromium e incerto no WebKitGTK; cabeçalho e rodapé com `position: fixed` e numeração por contador CSS são o plano B dentro do próprio webview.

### Riscos Identificados
- WebKitGTK pode não oferecer "Salvar como PDF" em todas as distribuições, ou ignorar parte do CSS de impressão.

### Alternativas Consideradas
- Gerar o PDF no núcleo Python ou no Rust com biblioteca própria: só se o webview não atender, e com aprovação.

---

## 📝 Notas e Comentários

- 2026-11-25: implementada na branch `feat/relatorios-chat`, junto com as outras stories do EPIC-14, a pedido do usuário (sem sprint planning). Nota do spike de PDF: [`docs/resultados/spike-pdf-relatorio-2026-11-25.md`](../resultados/spike-pdf-relatorio-2026-11-25.md).

---

## ✓ Definition of Done Checklist

- [ ] Critérios de aceitação verificados nas duas plataformas
- [x] Nota de decisão registrada
- [ ] Proposta de dependência apresentada, se necessária
- [ ] Aprovação do Product Owner sobre o caminho da US-REL-04
