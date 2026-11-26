# Discovery — Exportação de Dados de Tabelas e Gráficos do Chat (CSV e Excel)

**Status:** PROBLEM_READY
**Classificacao de Processo:** NORMAL PROCESS
**Origem:** hibrido (usuario + codigo)
**Data:** 2026-11-26

## Intent
Permitir que usuários do Adito exportem diretamente para **CSV** e **Excel (`.xlsx`)** os dados retornados nas respostas analíticas do Chat (tabelas e gráficos), facilitando o uso dos números institucionais em relatórios, planilhas, apresentações e auditorias sem precisar copiar manualmente ou recriar consultas fora do aplicativo.

## Problem
Hoje, quando o Adito responde uma pergunta analítica no Chat com tabela ou gráfico, o usuário só consegue copiar o texto em Markdown pela área de transferência (`copyToClipboard`) ou fixar um widget no Meu painel. Não existe exportação estruturada para CSV ou planilha Excel (`.xlsx`), o que obriga gestores e pesquisadores a copiar tabelas manualmente, perder formatação numérica/acentos ou ficar limitados às 10 linhas exibidas por padrão na tela.

## Users / Stakeholders relevantes
- **Gestores e coordenadores de pesquisa/extensão (IFES):** precisam levar os dados consultados no Chat para planilhas de prestação de contas, relatórios institucionais e apresentações.
- **Pesquisadores e servidores técnicos:** analisam recortes específicos no Chat e querem continuar cruzando/filtrando os dados no Excel ou LibreOffice Calc.
- **Equipe de manutenção do Adito:** precisa manter o app desktop leve (zero novas dependências em npm/Cargo/Python), compatível com Linux (WebKitGTK) e Windows (WebView2) e seguro contra path traversal e Formula/CSV Injection.

## Current Situation
- Em `ChatMessageBubble.vue`, toda resposta analítica com tabela ou gráfico recebe `message.table` (array completo de registros retornado por `chat.stream` ou reexecutado por `chat.message_rows` ao abrir conversas do histórico) e `message.fieldFormats` (`currency`, `integer`, `decimal`, `percent`, `date`, `text`).
- Visualmente, a tabela exibe por padrão 10 linhas (`rowLimit`: `5 / 10 / 15 / all`) e o gráfico agrupa categorias pequenas em `"Outros"`.
- Abaixo da tabela/gráfico existe a barra de ações com **"Ver SQL Gerado"** e **"Fixar no Dashboard"**, sem botão de exportação.
- No desktop Linux (Tauri/WebKitGTK), downloads puramente via `<a download>` com `Blob` podem falhar silenciosamente; hoje não existe comando Rust de escrita segura em Downloads.

## Desired Outcome
Com um clique em **"Exportar"** na resposta do Chat, o usuário escolhe **CSV (`.csv`)** ou **Excel (`.xlsx`)**, recebe todos os registros de `message.table` bem formatados e prontos para abrir no Excel PT-BR / LibreOffice Calc / Google Sheets, salvos automaticamente na pasta **Downloads** do sistema operacional (sem sobrescrever arquivos existentes) com confirmação discreta por toast — mantendo zero novas dependências externas.

## Success Criteria
- Botão acessível **"Exportar"** aparece em todas as respostas analíticas do Chat com dados renderizáveis (`hasRenderableTable && !message.isScalarResult`), tanto em respostas novas quanto no histórico reaberto.
- CSV exportado abre corretamente no Excel PT-BR (UTF-8 com BOM, separador `;`, escape RFC 4180 e mitigação de Formula Injection) com 100% dos registros de `message.table`.
- Excel (`.xlsx` OOXML nativo) abre sem alertas no Excel/LibreOffice/Google Sheets com cabeçalhos em negrito, larguras ajustadas, valores numéricos reais e formatação coerente com `fieldFormats`.
- No desktop Tauri (Linux e Windows), o arquivo é salvo na pasta **Downloads** via comando Rust `exportar_arquivo` (sem sobrescrita, sem path traversal, limite de tamanho) com toast de confirmação; fora do Tauri, faz fallback para download `Blob`.
- Zero novas dependências em `package.json`, `Cargo.toml` ou `requirements.txt`; 100% dos testes Rust, Vitest e Playwright E2E verdes.

## Scope

### IN
- Botão dropdown **"Exportar"** (**Exportar CSV (.csv)** e **Exportar Excel (.xlsx)**) em `ChatMessageBubble.vue` ao lado de **"Ver SQL Gerado"** e **"Fixar no Dashboard"**, acessível via teclado (`Esc` e clique fora fecham).
- Exportação completa de todos os registros de `message.table` (ignorando `rowLimit` visual e agrupamento `"Outros"` do gráfico).
- Gerador puro em TypeScript (`common/utils/exportData.ts`) para CSV PT-BR (UTF-8 BOM, `;`, RFC 4180, proteção contra CSV/Formula Injection) e `.xlsx` OOXML nativo (ZIP + XMLs + estilos de cabeçalho e formatos numéricos de `fieldFormats`).
- Nome sanitizado de arquivo derivado do título/pergunta + timestamp (compatível com Windows e Linux).
- Comando Rust `exportar_arquivo` em `src-tauri/src/lib.rs` salvando em `app.path().download_dir()` com sanitização estrita de basename/extensão, desambiguação ` (1)`, ` (2)`, limite de tamanho e escrita atômica; API `common/api/export.ts` com fallback `Blob` fora do Tauri e toast de confirmação no Chat.
- Testes automatizados: Rust (`cargo test`), Vitest (`exportData.spec.ts` + `ChatMessageBubble.spec.ts`) e Playwright E2E (`tauriMock.ts` + `chat.spec.ts`).

### OUT
- Exportação de imagem do gráfico (PNG/SVG).
- Exportação no Meu painel (`MeuDashboardView.vue`) ou no Explorar dados (`ExplorarDadosView.vue`).
- Diálogo nativo "Salvar como…" (`tauri-plugin-dialog`) ou adição de novas bibliotecas (`xlsx`, `exceljs`, `openpyxl`).
- Exportação de respostas puramente textuais ou escalares (`isScalarResult`) sem tabela.

### LATER
- Reaproveitar o utilitário `exportData.ts` + `exportar_arquivo` em widgets do **Meu painel** e na tela **Explorar dados**.
- Eventual exportação visual do gráfico em PNG/SVG se houver demanda futura.

## Constraints / Feasibility
- **Zero novas dependências externas** (Regra 6 do `AGENTS.md` e requisito explícito do usuário).
- **Compatibilidade multiplataforma Tauri v2:** funcionar igualmente em Linux (WebKitGTK) e Windows (WebView2), além de fallback `Blob` em navegador/E2E.
- **Segurança:** proteção contra path traversal e extensões arbitrárias no comando Rust (`exportar_arquivo`) e contra CSV/Formula Injection (`=`, `+`, `-`, `@`, `\t`, `\r`) em células textuais.
- **Sem alterar backend Python:** os dados completos já chegam no frontend via `chat.stream` e `chat.message_rows`.

## Assumptions
- **[ASSUMPTION] A01:** Um arquivo `.xlsx` OOXML mínimo gerado em TypeScript puro (ZIP modo *store* com CRC32 válido + `[Content_Types].xml`, `_rels/.rels`, `xl/workbook.xml`, `xl/_rels/workbook.xml.rels`, `xl/styles.xml`, `xl/worksheets/sheet1.xml`) abre nativamente no Microsoft Excel, LibreOffice Calc e Google Sheets sem dependências externas.
- **[ASSUMPTION] A02:** `app.path().download_dir()` no Tauri v2 resolve corretamente a pasta Downloads no Linux (XDG) e Windows (`FOLDERID_Downloads`); se indisponível em algum ambiente incomum, o comando retorna erro claro ao usuário (ou fallback para `home_dir`/erro acionável).
- **[ASSUMPTION] A03:** O volume típico de linhas retornadas em `message.table` no Chat fica confortavelmente dentro de um limite de segurança no Rust (ex.: 20 MB por arquivo exportado), suficiente para dezenas de milhares de linhas.

## Risks
- **Detalhes de especificação OOXML / CRC32 no `.xlsx`:** qualquer erro de escape XML, caracteres de controle inválidos (`\x00-\x08`, `\x0B`, `\x0C`, `\x0E-\x1F`) ou header ZIP malformado faria o Excel exibir aviso de "arquivo corrompido". *Mitigação:* testes unitários validando cabeçalhos ZIP/CRC32, XML bem-formado (descompactando com `zlib`/parser ou `zipfile` no Python/Vitest) e sanitização de caracteres de controle XML 1.0.
- **Conflito de tecla `Esc` no Chat:** `ChatEstrategicoView.vue` usa `Esc` para abortar stream em andamento; ao fechar o dropdown **"Exportar"** com `Esc`, chamar `event.stopPropagation()` evita disparar o cancelamento global do chat.
- **Path traversal / caracteres proibidos no Windows:** nomes com `..`, `/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|` ou nomes reservados (`CON`, `PRN`, `AUX`, `NUL`, `COM1`..`LPT9`) precisam ser sanitizados tanto no frontend quanto no Rust.

## Open Questions
- *Nenhuma pergunta bloqueante aberta (decisões alinhadas no `/grill-me`).*

## Review & Adjust

- [x] Usuario revisou a proposta completa
- [x] Alteracoes solicitadas foram incorporadas
- [x] Decisoes relevantes foram confirmadas
- [x] Nao existem perguntas bloqueantes abertas

### User adjustments
- Aprovado sem alterações no Checkpoint D1 (2026-11-26).
- Adendo aprovado pelo usuário (2026-11-26): incluir diálogo nativo **"Salvar como..."** via `tauri-plugin-dialog = "2"` em `Cargo.toml` para permitir escolher a pasta/nome de destino no PC (mantendo zero novas dependências em npm/Python).

## Gate G0 — PROBLEM READY

**Status:** APPROVED

**Aprovado pelo usuario:** sim
