# Requirements — Exportação de Dados de Tabelas e Gráficos do Chat (CSV e Excel)

**Status:** REQUIREMENTS_READY
**Discovery de origem:** `Adito/docs/discovery/exportar-dados-csv-excel.md`
**Classificacao de Processo:** NORMAL PROCESS
**Data:** 2026-11-26

## Intent Summary
Capacitar o usuário do Adito a exportar diretamente para **CSV (padrão Excel PT-BR)** e **Excel (`.xlsx` OOXML nativo)** todos os registros retornados em tabelas e gráficos nas respostas analíticas do Chat, abrindo o diálogo nativo **"Salvar como..."** do sistema operacional no app Tauri via `tauri-plugin-dialog` (pré-preenchido com Downloads, nome sugerido e filtro de extensão, com fallback `showSaveFilePicker`/`Blob` no navegador/E2E) e zero novas dependências externas em npm ou Python.

## Functional Requirements
- **FR01 (Botão dropdown "Exportar" em `ChatMessageBubble.vue`):** Sempre que uma resposta do assistente possuir dados tabulares/gráficos renderizáveis (`hasRenderableTable && !message.isScalarResult`, tanto em respostas recém-geradas quanto em conversas reabertas do histórico via `chat.message_rows`), exibir um botão acessível **"Exportar"** na barra de ações ao lado de **"Ver SQL Gerado"** e **"Fixar no Dashboard"** (ou em barra dedicada caso `hasRenderableTable` sem `message.sql`), abrindo um menu com as opções **"Exportar CSV (.csv)"** e **"Exportar Excel (.xlsx)"**.
- **FR02 (Fechamento e acessibilidade do menu):** O menu dropdown **"Exportar"** deve suportar `aria-haspopup="menu"`, `aria-expanded`, `role="menu"` / `role="menuitem"`, navegação por teclado, fechamento ao clicar fora e fechamento ao pressionar `Esc` (usando `event.stopPropagation()` para não acionar o cancelamento global de stream do chat).
- **FR03 (Exportação integral dos registros):** Ao exportar CSV ou Excel, utilizar **sempre todos os registros de `message.table`**, ignorando o limite visual de exibição da tabela (`rowLimit`: `5 / 10 / 15`) e o agrupamento `"Outros"` do gráfico.
- **FR04 (Gerador CSV PT-BR em TypeScript puro — `common/utils/exportData.ts`):**
  - Gerar CSV codificado em UTF-8 **com BOM (`\uFEFF`)** e separador `;`.
  - Cabeçalhos legíveis (preservando os nomes das colunas com `_` → espaço ou cabeçalho consistente com a tabela) e escape RFC 4180 (células contendo `;`, `"`, `\n` ou `\r` envoltas em aspas duplas com `"` duplicada).
  - Formatar datas ISO (`YYYY-MM-DD`) e respeitar tipos numéricos/textuais de `fieldFormats`, mantendo separador decimal adequado ou texto limpo compatível com Excel PT-BR.
  - Aplicar proteção contra Formula/CSV Injection prefixando células textuais iniciadas por `=`, `+`, `-`, `@`, `\t`, `\r` com apóstrofo (`'`).
- **FR05 (Gerador `.xlsx` OOXML nativo em TypeScript puro — `common/utils/exportData.ts`):**
  - Gerar arquivo `.xlsx` válido (pacote ZIP com CRC32 válido contendo `[Content_Types].xml`, `_rels/.rels`, `xl/workbook.xml`, `xl/_rels/workbook.xml.rels`, `xl/styles.xml` e `xl/worksheets/sheet1.xml`), abrível no Microsoft Excel, LibreOffice Calc e Google Sheets sem alertas.
  - Cabeçalhos em negrito com preenchimento discreto e largura de coluna calculada automaticamente pelo conteúdo (com limites mínimo e máximo).
  - Valores numéricos gravados como células numéricas reais (`t="n"` / `<v>`) para permitir fórmulas/somas no Excel, com `numFmt` alinhado a `message.fieldFormats` (`currency` em `R$`, `integer`, `decimal`, `percent` — convertendo percentual para fração quando apropriado ou formato seguro — e `date`).
  - Células de texto com escape XML completo, remoção de caracteres de controle inválidos em XML 1.0 (`\x00-\x08`, `\x0B`, `\x0C`, `\x0E-\x1F`) e armazenadas como `t="inlineStr"` (que nunca são avaliadas como fórmula no OOXML, preservando textos como `+55 27 3333-4444` e `-` sem apóstrofo visível). Strings numéricas com mais de 15 dígitos significativos (ex.: IDs longos ou chaves) são preservadas como texto em CSV e `.xlsx` para evitar perda de precisão IEEE-754.
- **FR06 (Nome sugerido sanitizado do arquivo):** Gerar nome legível a partir do título/pergunta associada (ou prefixo padrão `adito-dados`) + timestamp `YYYYMMDD-HHMMSS` + extensão (`.csv` ou `.xlsx`), normalizando acentos, removendo caracteres inválidos no Windows/Linux (`/\:*?"<>|`) e respeitando tamanho máximo seguro.
- **FR07 (Comando Rust `exportar_arquivo` com diálogo nativo "Salvar como..." + API `common/api/export.ts` + Toast de feedback):**
  - Registrar plugin oficial `tauri-plugin-dialog = "2"` no Rust (aprovado pelo usuário; sem novas dependências em npm/Python) e comando Tauri `exportar_arquivo(nome: String, bytes: Vec<u8>) -> Result<ExportResultado, String>` em `Adito/app/src-tauri/src/lib.rs`.
  - Sanitizar/validar estritamente o nome sugerido (rejeitar path traversal, subdiretórios, nomes vazios, nomes reservados do Windows e extensões diferentes de `.csv` e `.xlsx`), impor limite máximo de tamanho (20 MB), abrir o diálogo nativo **"Salvar como..."** apontando inicialmente para `Downloads` com filtro `.csv`/`.xlsx`, garantir a extensão no destino escolhido e gravar atomicamente (arquivo temporário + `rename`). Caso o usuário cancele o diálogo, retornar `cancelado: true` sem gravar arquivo nem exibir erro.
  - Em `common/api/export.ts`, chamar `invoke('exportar_arquivo', ...)` quando `window.__TAURI_INTERNALS__` estiver presente e usar `showSaveFilePicker` (quando suportado) ou fallback `<a download>` via `Blob` fora do Tauri.
  - Exibir toast discreto no Chat (`ChatEstrategicoView.vue` via `useToast`) confirmando pasta e arquivo salvo (ex.: *"Arquivo salvo em Documentos: adito-dados-....xlsx"*) ou erro claro em caso de falha; não exibir toast quando cancelado pelo usuário.
- **FR08 (Testes automatizados):**
  - **Rust (`cargo test`):** sanitização de nomes, bloqueio de path traversal/extensões proibidas/nomes reservados/payload vazio ou acima do limite, garantia de extensão e gravação atômica no destino em diretório temporário.
  - **Vitest (`exportData.spec.ts` + `ChatMessageBubble.spec.ts`):** geração CSV (BOM, `;`, RFC 4180, Formula Injection inclusive com espaço inicial), integridade do `.xlsx` (assinatura ZIP `PK`, descompactação/leitura dos XMLs OOXML, tipos numéricos e `fieldFormats`, sanitização XML 1.0), exportação de todas as linhas ignorando `rowLimit`/`Outros`, `export.ts` (Tauri confirmado/cancelado + navegador picker/Blob) e interação do botão/menu **"Exportar"**.
  - **Playwright E2E (`tauriMock.ts` + `chat.spec.ts`):** mock de `exportar_arquivo` validando clique em **"Exportar" → CSV / Excel (.xlsx)**, visibilidade do menu na viewport, envio do payload completo, exibição do toast com pasta/arquivo e cenário de cancelamento do diálogo sem toast nem erro, sem quebrar nenhum dos testes existentes.

## Business / Domain Rules
- **BR01 (Completude dos dados exportados):** A exportação deve incluir 100% das linhas presentes em `message.table`, independentemente do limite visual selecionado (`5 / 10 / 15`) ou do agrupamento `"Outros"` no gráfico.
- **BR02 (Visibilidade condicional):** O botão **"Exportar"** só aparece em mensagens do assistente com tabela renderizável não-escalar (`hasRenderableTable && !message.isScalarResult`); respostas conversacionais, de erro/fallback ou escalares simples não exibem o botão.
- **BR03 (Segurança contra CSV/Formula Injection):** Qualquer valor textual que inicie com `=`, `+`, `-`, `@`, `\t` ou `\r` deve ser neutralizado com prefixo `'` (exceto números reais gravados como tipo numérico).
- **BR04 (Segurança de escrita no sistema de arquivos):** O comando `exportar_arquivo` valida nome sugerido e payload (limite de 20 MB, somente `.csv` ou `.xlsx`) e grava exclusivamente no caminho escolhido explicitamente pelo usuário no diálogo nativo **"Salvar como..."** do sistema operacional (o frontend nunca envia caminhos arbitrários).
- **BR05 (Dependências mínimas aprovadas):** Geração CSV/OOXML em TypeScript puro (zero novas dependências em npm ou Python); apenas o plugin oficial `tauri-plugin-dialog = "2"` adicionado em `Cargo.toml` sob aprovação explícita do usuário (Regra 6) para o seletor nativo do SO.
- **BR06 (Não alterar dados sensíveis nem backend Python):** A exportação utiliza exclusivamente os dados já filtrados pela `ReadPolicy` e `visible_columns` do núcleo, sem expor colunas sensíveis e sem necessidade de alterar o backend Python.

## Non-Functional Requirements
- **NFR01 (Compatibilidade desktop Linux + Windows):** Salvamento confiável tanto no WebKitGTK (Linux) quanto no WebView2 (Windows) via comando Rust `exportar_arquivo`, além de fallback `Blob` no navegador.
- **NFR02 (Acessibilidade e temas):** Botão e menu dropdown acessíveis por teclado (`Enter`/`Space`/`Esc`), atributos ARIA corretos e contraste adequado em temas claro e escuro.
- **NFR03 (Desempenho):** Geração de CSV e `.xlsx` para milhares de linhas no cliente em < 300 ms, sem travar a interface (evitar travamento duplo de clique durante salvamento com estado de busy).
- **NFR04 (Integridade OOXML):** O `.xlsx` gerado deve ser um arquivo ZIP válido (CRC32 IEEE 802.3 exato, local file headers + central directory + EOCD) com XML 1.0 válido.
- **NFR05 (Zero regressão):** Todas as suítes existentes (`cargo test`, Vitest `95/95`, `vue-tsc + vite build` e Playwright E2E `30/30`) devem continuar passando 100%.

## User Scenarios

### Main flow — Exportar dados do Chat para Excel (`.xlsx`) ou CSV
1. Usuário envia uma pergunta analítica no Chat (ou abre uma conversa do histórico) que retorna uma tabela/gráfico com 35 registros (exibindo 10 por padrão na tela).
2. Clica no botão **"Exportar"** ao lado de **"Fixar no Dashboard"**.
3. Seleciona **"Exportar Excel (.xlsx)"** (ou **"Exportar CSV (.csv)"**).
4. O Adito gera o arquivo com todos os 35 registros, abre a janela nativa **"Salvar como..."** (apontando inicialmente para `Downloads` com o nome sugerido e filtro `.xlsx`/`.csv`), grava atomicamente no destino escolhido e exibe um toast discreto: *"Arquivo salvo em Documentos: adito-...xlsx"*.

### Alternative / Error / Edge cases
- **Menu aberto + tecla `Esc`:** fecha apenas o menu **"Exportar"** (devolvendo foco ao botão) sem cancelar nenhum stream em andamento no chat.
- **Usuário clica em "Cancelar" na janela "Salvar como...":** o Rust retorna `cancelado: true`, nenhum arquivo é gravado e nenhum toast de erro é exibido.
- **Célula contendo fórmula maliciosa (`=CMD|...`, `" =1+1"`, `+1+1` em campo texto):** neutralizada com prefixo `'` no CSV e armazenada como string segura no `.xlsx`.
- **Números negativos reais (ex.: `-42.5`):** exportados como número real `-42.5` no `.xlsx` e sem corromper valores numéricos legítimos no CSV.
- **Ambiente fora do Tauri (navegador web / preview):** usa `showSaveFilePicker` quando suportado (com tratamento de `AbortError`) ou fallback `<a download>` com `Blob`, exibindo toast *"Arquivo salvo: adito-...csv"*.
- **Falha ao gravar no destino escolhido (ex.: disco cheio / arquivo aberto / permissão negada):** remove o temporário e exibe toast de erro amigável sem quebrar a conversa.

## Business / Domain Context
Gestores e pesquisadores do IFES utilizam o Chat Estratégico do Adito para consultar indicadores acadêmicos (pesquisa, extensão, bolsas, produção científica e grupos CNPq) e precisam levar os resultados completos para planilhas institucionais (Excel / LibreOffice Calc) com acentos e números prontos para análise.

## Technical Context & Constraints
- **Rust (`Adito/app/src-tauri/src/lib.rs`):** novo comando `exportar_arquivo` (e helpers puros de sanitização/desambiguação/escrita testáveis em `#[cfg(test)]`) registrado no `tauri::generate_handler![]`.
- **Frontend (`Adito/app/frontend-vue/src/`):**
  - `common/utils/exportData.ts`: geração de CSV PT-BR, gerador ZIP (CRC32 + store) + OOXML `.xlsx` nativo com `styles.xml` para `fieldFormats`, e geração de nome sanitizado.
  - `common/api/export.ts`: integração com `invoke('exportar_arquivo', ...)` no Tauri e fallback `Blob` fora do Tauri.
  - `modules/chat/components/ChatMessageBubble.vue`: botão dropdown **"Exportar"** emitindo evento ou executando exportação com callback de feedback.
  - `modules/chat/components/ChatConversation.vue` e `modules/chat/views/ChatEstrategicoView.vue`: propagação do feedback para o `showToast` já existente no Chat (e contexto do título da pergunta para o nome do arquivo).
- **Testes:** `src-tauri/src/lib.rs` (`cargo test`), `tests/unit/exportData.spec.ts`, `tests/unit/ChatMessageBubble.spec.ts`, `tests/e2e/helpers/tauriMock.ts`, `tests/e2e/chat.spec.ts`.

## Quality Attributes
- **Segurança:** validação rigorosa no boundary Rust (somente Downloads, somente `.csv`/`.xlsx`, sem path traversal, limite de 20 MB) e mitigação de Formula/CSV Injection.
- **Portabilidade:** compatível com Excel PT-BR, LibreOffice Calc e Google Sheets em Linux e Windows.
- **Manutenibilidade:** utilitário puro e desacoplado (`exportData.ts`), pronto para ser reutilizado futuramente no Meu painel e Explorar dados.

## Assumptions
- **A01:** OOXML `.xlsx` gerado via ZIP modo *store* (sem compressão DEFLATE, CRC32 IEEE 802.3 válido) é 100% conforme a especificação PKZIP/OOXML e aceito por Excel, LibreOffice Calc e Google Sheets.
- **A02:** `app.path().download_dir()` resolve corretamente em Linux e Windows no Tauri v2.
- **A03:** Limite de 20 MB no comando Rust atende amplamente todas as consultas do Chat.

## Out of Scope
- Exportação de imagem do gráfico (PNG/SVG).
- Exportação nas telas Meu painel e Explorar dados.
- Dependências externas de geração de planilha (`xlsx`, `exceljs`, `openpyxl`).

## Open Questions
- *Nenhuma pergunta bloqueante aberta.*

## Key Decisions Proposed
- **KD01 (OOXML `.xlsx` + CSV em TypeScript puro):** Zero novas dependências em npm/Python, geração instantânea em memória a partir de `message.table` + `message.fieldFormats`, sem alterar o PyInstaller nem o backend Python.
- **KD02 (Comando Rust `exportar_arquivo` com `tauri-plugin-dialog` + fallback web):** Abre o diálogo nativo "Salvar como..." em Linux/Windows/macOS sem expor escrita livre de arquivos ao frontend; aprovado pelo usuário em 2026-11-26 após revisão inicial.
- **KD03 (CSV padrão Excel PT-BR + proteção contra Formula Injection):** UTF-8 com BOM (`\uFEFF`) e `;` garante abertura imediata com acentos e colunas no Excel brasileiro; células textuais iniciadas por `=`, `+`, `-`, `@`, `\t`, `\r` são neutralizadas.
- **KD04 (Exportação integral sempre):** Exportar todos os registros de `message.table` (ignorando `rowLimit` visual e `"Outros"`) evita confusão de usuários achando que o banco só tem 10 linhas.

## Review & Adjust

O usuario pode **aprovar, editar, adicionar, remover ou reclassificar** qualquer requisito/regra antes do gate.

- [x] Proposta completa apresentada ao usuario
- [x] Ajustes solicitados incorporados
- [x] IDs estabilizados depois da revisao
- [x] Nenhuma pergunta bloqueante aberta

### User adjustments
- Aprovado sem alterações no Checkpoint R1 (2026-11-26).
- Adendo aprovado pelo usuário (2026-11-26): adicionar `tauri-plugin-dialog = "2"` em `Cargo.toml` para permitir escolher a pasta/nome de destino pelo diálogo nativo **"Salvar como..."** do SO.

## Gate G1 — REQUIREMENTS READY

**Status:** APPROVED

**Aprovado pelo usuario:** sim
