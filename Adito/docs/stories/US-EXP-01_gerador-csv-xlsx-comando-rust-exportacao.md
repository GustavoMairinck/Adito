# User Story: [US-EXP-01] Gerador CSV/OOXML `.xlsx` (TS puro), comando Rust `exportar_arquivo` e testes unitários

**Epic:** EPIC-15 — Exportação de Dados do Chat para CSV e Excel (`.xlsx`)
**GitHub Epic Issue:** -
**GitHub US Issue:** -
**Prioridade:** Alta (slice 1)
**Story Points:** 5
**Sprint:** - (implementação direta na branch `feat/exportar-dados-csv-excel`)
**Status:** Review
**Behavior Change Esperado:** YES

---

## Historia

**Como** usuário do Adito desktop (Windows ou Linux)
**Eu quero** que os dados tabulares retornados pelo Chat sejam convertidos de forma confiável para CSV (padrão Excel PT-BR) e Excel nativo (`.xlsx`) e salvos na pasta de minha escolha pelo diálogo nativo **"Salvar como..."**
**Para que** eu possa organizar, abrir e trabalhar imediatamente os números completos em Excel, LibreOffice Calc ou Google Sheets sem perder acentos ou formatação

### Contexto Adicional

O Adito gera CSV e `.xlsx` OOXML em TypeScript puro (zero novas dependências em npm ou Python, mantendo o bundle e o PyInstaller leves). No desktop Tauri v2, downloads via `<a download>` com `Blob` podem falhar silenciosamente no Linux (WebKitGTK); sob aprovação explícita do usuário (Regra 6), foi adicionado o plugin oficial `tauri-plugin-dialog = "2"` no backend Rust para que `exportar_arquivo` abra o diálogo nativo **"Salvar como..."** pré-preenchido com `Downloads`, nome sugerido sanitizado e filtro de extensão.

Origem: `Adito/docs/discovery/exportar-dados-csv-excel.md` e `Adito/docs/requirements/exportar-dados-csv-excel.md` (`FR03–FR08`, `BR01`, `BR03–BR06`, `NFR01`, `NFR03`, `NFR04`, `A01–A03`).

### Pontos de Esclarecimento

Nenhum ponto pendente.

---

## Criterios de Aceitacao

- [x] **Criterio 1 (Gerador CSV PT-BR em TS puro):** `common/utils/exportData.ts` gera CSV em UTF-8 com BOM (`\uFEFF`), separador `;`, escape RFC 4180, datas ISO formatadas (`DD/MM/YYYY`), todos os registros de entrada preservados e mitigação de Formula/CSV Injection (`=`, `+`, `-`, `@`, `\t`, `\r` prefixados com `'` em células textuais, sem corromper números negativos reais).
- [x] **Criterio 2 (Gerador `.xlsx` OOXML nativo em TS puro):** `common/utils/exportData.ts` gera pacote ZIP válido (assinatura PK, CRC32 IEEE 802.3 exato, local headers + central directory + EOCD) com XMLs OOXML válidos (`[Content_Types].xml`, `_rels/.rels`, `xl/workbook.xml`, `xl/_rels/workbook.xml.rels`, `xl/styles.xml`, `xl/worksheets/sheet1.xml`), cabeçalhos em negrito com largura ajustada, valores numéricos reais (`t="n"`) com formatação alinhada a `fieldFormats` (`currency`, `integer`, `decimal`, `percent`, `date`, `text`), preservação de strings numéricas > 15 dígitos como texto e células `t="inlineStr"` com escape/sanitização XML 1.0 (sem apóstrofo visível).
- [x] **Criterio 3 (Nome sanitizado do arquivo):** `buildExportFilename(ext, label?)` gera nome seguro derivado do título/pergunta (ou `adito-dados`) + timestamp `YYYYMMDD-HHMMSS` + `.csv`/`.xlsx`, removendo acentos e caracteres inválidos no Windows/Linux.
- [x] **Criterio 4 (Comando Rust `exportar_arquivo` com diálogo nativo "Salvar como..."):** `src-tauri/src/lib.rs` utiliza `tauri-plugin-dialog = "2"` (aprovado pelo usuário) para abrir o diálogo nativo "Salvar como..." pré-preenchido com `Downloads`, nome sugerido validado e filtro `.csv`/`.xlsx`; valida basename/extensão/limite de 20 MB, retorna `cancelado: true` se o usuário cancelar, garante a extensão no destino escolhido e grava atomicamente via arquivo temporário + `rename`.
- [x] **Criterio 5 (API `common/api/export.ts` com fallback navegador):** Invoca `exportar_arquivo` quando em ambiente Tauri (`__TAURI_INTERNALS__`), trata cancelamento silenciosamente e fora do Tauri usa `showSaveFilePicker` quando suportado ou fallback `<a download>` com `Blob`.
- [x] **Criterio 6 (Testes unitários Rust e Vitest):** `cargo test` cobre sanitização, path traversal, extensões proibidas, limite de tamanho, garantia de extensão e gravação atômica no destino; `exportData.spec.ts` valida CSV, integridade ZIP/CRC32/XML do `.xlsx` gerado e `export.ts` (Tauri confirmado/cancelado + navegador picker/Blob).

---

## Governanca e Rastreabilidade

- **Nivel ScrumAIDev:** 1
- **Justificativa do nivel:** Utilitário puro no frontend + comando Tauri isolado de escrita em Downloads, sem mudança de banco de dados ou protocolo RPC do núcleo Python.
- **US exige Spec governada?** Nao
- **Justificativa da Spec:** Regras de formato e segurança já especificadas em `Adito/docs/requirements/exportar-dados-csv-excel.md` (`FR04–FR07`, `BR03–BR04`).
- **Spec prevista:** N/A
- **US exige Contract governado?** Nao
- **Justificativa do Contract:** Comando interno de desktop sem API externa/HTTP.
- **Contract previsto:** N/A
- **Padrao de erro aplicavel:** N/A
- **BDD previsto:** N/A
- **Gates opcionais aplicaveis:** N/A
- **Touch List preliminar:**
  - `Adito/app/src-tauri/Cargo.toml`
  - `Adito/app/src-tauri/Cargo.lock`
  - `Adito/app/src-tauri/src/lib.rs`
  - `Adito/app/frontend-vue/src/common/utils/exportData.ts`
  - `Adito/app/frontend-vue/src/common/api/export.ts`
  - `Adito/app/frontend-vue/tests/unit/exportData.spec.ts`
- **Task Issues previstas:** N/A

---

## Notas Tecnicas

### Arquitetura

- **Componentes afetados:** `src-tauri/Cargo.toml`, `src-tauri/src/lib.rs`, `common/utils/exportData.ts`, `common/api/export.ts`.
- **APIs necessarias:** `tauri::Manager::path().download_dir()` (`tauri` v2), `tauri_plugin_dialog::DialogExt` (`tauri-plugin-dialog = "2"`, aprovado pelo usuário), `@tauri-apps/api/core` (`invoke`). Zero novas dependências em npm ou Python.
- **Database changes:** Nenhuma.
- **Referencias do modelo de dados:** N/A
- **Erros observaveis esperados:** Nome/extensão inválidos, payload vazio ou > 20 MB e falha de permissão/disco no destino escolhido retornam mensagens amigáveis em português; cancelamento do diálogo retorna `cancelado: true` sem erro.

### Dependencias

- [x] Branch `feat/exportar-dados-csv-excel` atualizada com `upstream/development`.

### Consideracoes de Performance

- Gerar ZIP em modo *store* (sem compressão pesada) em array único `Uint8Array` mantém geração < 50 ms para milhares de linhas.
- Limite de 20 MB no Rust previne abuso de memória/disco no IPC.

---

## Plano de Testes

### Testes Unitarios

- [x] Rust (`cargo test`): valida basename/extensão `.csv` e `.xlsx`, rejeita `../`, `/`, `\`, extensão `.exe`, nomes reservados (`CON`, `NUL`), payload vazio e > 20 MB, garante extensão no destino escolhido e grava atomicamente via arquivo temporário + `rename`.
- [x] Vitest (`exportData.spec.ts`): valida UTF-8 BOM, separador `;`, escape RFC 4180, mitigação de Formula Injection (preservando números negativos reais), datas ISO e cabeçalhos.
- [x] Vitest (`exportData.spec.ts`): valida `.xlsx` gerado (cabeçalho PKZIP, CRC32 exato, entrada `[Content_Types].xml`, `xl/styles.xml`, `xl/worksheets/sheet1.xml`, células numéricas reais, `fieldFormats` e remoção de caracteres de controle XML 1.0).
- [x] Vitest (`exportData.spec.ts`): valida `salvarExportacao()` usando `invoke('exportar_arquivo')` no Tauri e fallback `Blob` fora do Tauri.

### Testes de Integracao

- [x] Validado ponta a ponta na `US-EXP-02` via Playwright E2E.

### Testes de Contract

- [x] N/A

### Testes Manuais

- [ ] Abrir um `.csv` e um `.xlsx` gerados no LibreOffice Calc / Excel para conferência visual.

### BDD / Cenarios de Comportamento

- [x] N/A

---

## Tasks (Breakdown)

- [x] **[TASK-001]** Implementar helpers puros + comando Tauri `exportar_arquivo` e testes `#[cfg(test)]` em `Adito/app/src-tauri/src/lib.rs`.
- [x] **[TASK-002]** Implementar `common/utils/exportData.ts` (CSV PT-BR, ZIP/CRC32 + OOXML `.xlsx` com `fieldFormats`, sanitização e `buildExportFilename`).
- [x] **[TASK-003]** Implementar `common/api/export.ts` (chamada Tauri `exportar_arquivo` + fallback `Blob`).
- [x] **[TASK-004]** Criar `tests/unit/exportData.spec.ts` cobrindo CSV, integridade estrutural OOXML/ZIP e API de salvamento.

---

## IA Insights

### Sugestoes de Implementacao

- Usar arquivo temporário único (`OpenOptions::create_new(true)`) + `sync_all()` + `fs::rename()` no mesmo diretório do destino escolhido pelo diálogo nativo, garantindo gravação atômica sem corromper arquivos existentes em caso de erro de I/O.
- Em `exportData.ts`, validar `zip` com `TextDecoder` / leitura do Central Directory nos testes Vitest para garantir que o arquivo `.xlsx` é 100% parseável (inclusive validando com `zipfile.ZipFile` do Python!).

### Riscos Identificados

- Percentuais no `fieldFormats` podem chegar do SQL tanto como `0.25` quanto como `25.0` (já que `ChatMessageBubble.vue` exibe `${fmt(numericValue)}%` diretamente sem multiplicar por 100!). Portanto, no `.xlsx` usar formato `0.00"%"` (ou preservar o número exatamente como o banco retorna + sufixo `%`) evita multiplicar `25` por 100 virando `2500%`! Excelente cuidado!

### Alternativas Consideradas

- Adicionar `openpyxl` ou `exceljs` — descartada por exigir nova dependência em PyInstaller/npm quando OOXML nativo resolve em < 250 linhas puras e sem custo de bundle.

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
