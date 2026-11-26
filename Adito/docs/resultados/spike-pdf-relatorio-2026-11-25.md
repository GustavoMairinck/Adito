# Spike — PDF do relatório pela impressão do webview (US-REL-03)

**Data:** 2026-11-25
**Story:** [US-REL-03](../stories/US-REL-03_spike-pdf-impressao-tauri.md) · insumo para [US-REL-04](../stories/US-REL-04_exportar-relatorio-pdf.md)
**Decisão:** seguir com a **impressão do webview** (`window.print()` + página de impressão própria), **sem dependência nova** (KD04, NFR02).

## Como ficou

> **2026-11-26:** o visual do PDF mudou a pedido do usuário (documento formal, sem capa com logo grande, sem selo e sem rodapé). Hoje o cabeçalho é só a logo pequena com o nome "Adito" (`thead` repetido), o número da página fica no canto superior direito (`@page @top-right`) e as margens seguem a ABNT (3 cm em cima e à esquerda, 2 cm embaixo e à direita). A limpeza depois da impressão também roda na volta do foco, num tempo limite e ao sair da conversa, porque o WebKitGTK nem sempre dispara `afterprint` ao cancelar. O registro abaixo é o do spike original.

- A página de impressão é o componente `ChatReportPrint.vue`, montado fora da tela (`position: fixed; left: -10000px`) só durante a exportação, para os gráficos renderizarem com largura real.
- Ao exportar, `html.adito-printing` esconde o app e mostra só a página de impressão; `document.title` vira o nome sugerido do arquivo (`Relatório - <título> - <AAAA-MM-DD>`); o evento `afterprint` desfaz tudo.
- **Capa** em página própria (`@page :first` com margem 0 e sem numeração).
- **Cabeçalho e rodapé repetidos:** `thead`/`tfoot` de uma tabela de leiaute, que Chromium e WebKit repetem em toda página.
- **"Página X de Y":** margin box `@page { @bottom-right { content: "Página " counter(page) " de " counter(pages) } }`.
- **Quebras:** cada seção começa em página nova; figura e linhas de tabela com `break-inside: avoid`; cabeçalho da tabela repetido (`thead { display: table-header-group }`).
- **Tema claro** fixo e `print-color-adjust: exact` para as faixas e cartões.

## O que foi verificado

| Item | Chromium (motor do WebView2, Windows) | WebKitGTK (Linux) |
|---|---|---|
| Página de impressão monta com gráficos | ✅ Playwright (`tests/e2e/relatorio.spec.ts`) | ⏳ conferir no app |
| PDF A4 gerado (`page.pdf`) com capa, sumário, 3 seções e metodologia (6 páginas) | ✅ | ⏳ |
| Cabeçalho e rodapé em toda página, exceto a capa | ✅ | ⏳ (`thead`/`tfoot` repetem no WebKit) |
| "Página X de Y" | ✅ | ⚠️ provável ausência: o WebKit não implementa margin boxes do `@page` |
| Gráfico inteiro, sem animação pela metade | ✅ | ⏳ |
| Fontes e logo do app | ✅ | ⏳ |
| Janela de impressão com "Salvar como PDF" | não testável no Playwright (`window.print` simulado) | ⏳ conferir no app |

O Chromium do Playwright é o mesmo motor do WebView2 do Windows; a janela de impressão real no Windows ainda precisa ser conferida numa máquina Windows.

## Se o Linux não atender

Se no WebKitGTK faltar a numeração ou a janela de impressão não abrir, as alternativas, que dependem de aprovação (AGENTS.md, regra 6), são:

1. **Numeração no próprio HTML:** paginar a página de impressão em blocos de altura A4 fixa e escrever "Página X de Y" em cada bloco, sem dependência nova (mais código, quebras menos naturais).
2. **Gerar o PDF no Rust** a partir do webview (`print` nativo do Tauri) ou com uma biblioteca de PDF no núcleo Python: dependência nova, a avaliar tamanho, licença e empacotamento.
