/**
 * Utilitário puro (zero dependências externas) para exportar dados tabulares do Chat
 * em CSV (padrão Excel PT-BR) e Excel nativo (.xlsx OOXML).
 *
 * - CSV: UTF-8 com BOM (`\uFEFF`), separador `;`, escape RFC 4180, proteção contra
 *   CSV/Formula Injection em células textuais e números decimais com vírgula (PT-BR).
 * - XLSX: pacote PKZIP (store + CRC32 IEEE 802.3) com XMLs OOXML válidos, cabeçalho
 *   em negrito com largura ajustada, valores numéricos reais (`t="n"`) e `numFmt`
 *   alinhado a `fieldFormats` (`currency`, `integer`, `decimal`, `percent`, `date`, `text`).
 */

export type ExportFormat = 'csv' | 'xlsx'
export type ExportRow = Record<string, unknown>
export type FieldFormatsMap = Record<string, string>

type NormalizedFormat = 'currency' | 'integer' | 'decimal' | 'percent' | 'date' | 'text' | ''

const FORMULA_INJECTION_RE = /^(?:[\t\r]|[\s]*[=+\-@])/
const XML_INVALID_CONTROL_RE = /[\u0000-\u0008\u000B\u000C\u000E-\u001F\uFFFE\uFFFF]/g
const WINDOWS_RESERVED_RE = /^(con|prn|aux|nul|com[1-9]|lpt[1-9])$/i
const STRICT_NUMBER_RE = /^-?(?:0|[1-9]\d*)(?:\.\d+)?$/

const textEncoder = new TextEncoder()

function normalizeFieldFormat(key: string, fieldFormats?: FieldFormatsMap): NormalizedFormat {
  const raw = fieldFormats?.[key]
  if (!raw) return ''
  const cleaned = String(raw).replace(/^FieldFormat\./, '').toLowerCase()
  if (
    cleaned === 'currency' ||
    cleaned === 'integer' ||
    cleaned === 'decimal' ||
    cleaned === 'percent' ||
    cleaned === 'date' ||
    cleaned === 'text'
  ) {
    return cleaned
  }
  return ''
}

function collectColumns(rows: ExportRow[]): string[] {
  const seen = new Set<string>()
  const columns: string[] = []
  for (const row of rows) {
    if (!row || typeof row !== 'object') continue
    for (const key of Object.keys(row)) {
      if (!seen.has(key)) {
        seen.add(key)
        columns.push(key)
      }
    }
  }
  return columns
}

function formatHeaderLabel(key: string): string {
  return key.replace(/_/g, ' ').trim() || key
}

function formatIsoDatePtBr(value: unknown): string {
  if (value === null || value === undefined || value === '') return ''
  const text = String(value).trim()
  const datePart = text.split('T')[0]
  if (/^\d{4}-\d{2}-\d{2}$/.test(datePart)) {
    const [year, month, day] = datePart.split('-')
    return `${day}/${month}/${year}`
  }
  return text
}

const MAX_SAFE_SIGNIFICANT_DIGITS = 15

function countSignificantDigits(numericStr: string): number {
  const unsigned = numericStr.startsWith('-') ? numericStr.slice(1) : numericStr
  const digitsOnly = unsigned.replace('.', '').replace(/^0+/, '')
  return digitsOnly.length
}

/**
 * Converte valores numéricos legítimos para `number`, preservando strings com zeros à esquerda
 * (ex.: códigos/CEPs `"00123"`), identificadores/chaves longas (> 15 dígitos significativos)
 * ou colunas explicitamente declaradas como `text` ou `date`.
 */
function parseRealNumber(value: unknown, format: NormalizedFormat): number | null {
  if (value === null || value === undefined || typeof value === 'boolean') return null
  if (format === 'text' || format === 'date') return null
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null
  }
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed || !STRICT_NUMBER_RE.test(trimmed)) return null
    const normalized = trimmed.includes('.')
      ? trimmed.replace(/(\.\d*?[1-9])0+$/, '$1').replace(/\.0+$/, '')
      : trimmed
    if (countSignificantDigits(normalized) > MAX_SAFE_SIGNIFICANT_DIGITS) return null
    const parsed = Number(normalized)
    if (!Number.isFinite(parsed)) return null
    if (parsed === 0) return 0
    if (String(parsed) !== normalized) return null
    return parsed
  }
  return null
}

/** Neutraliza células de texto que começam com caracteres interpretados como fórmula por planilhas. */
export function neutralizeFormulaText(text: string): string {
  return FORMULA_INJECTION_RE.test(text) ? `'${text}` : text
}

function escapeCsvCell(raw: string): string {
  if (raw.includes(';') || raw.includes('"') || raw.includes('\n') || raw.includes('\r')) {
    return `"${raw.replace(/"/g, '""')}"`
  }
  return raw
}

function formatCsvValue(value: unknown, format: NormalizedFormat): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'boolean') return value ? 'Sim' : 'Não'
  if (format === 'date') return escapeCsvCell(neutralizeFormulaText(formatIsoDatePtBr(value)))

  const num = parseRealNumber(value, format)
  if (num !== null) {
    // Em CSV com separador `;` (Excel PT-BR), usar vírgula decimal permite soma imediata sem quebrar colunas.
    if (format === 'integer') return String(Math.round(num))
    if (format === 'currency' || format === 'decimal' || format === 'percent') {
      return num.toFixed(2).replace('.', ',')
    }
    return Number.isInteger(num) ? String(num) : String(num).replace('.', ',')
  }

  return escapeCsvCell(neutralizeFormulaText(String(value)))
}

/** Gera string CSV PT-BR com UTF-8 BOM, separador `;`, RFC 4180 e proteção contra Formula Injection. */
export function buildCsvString(rows: ExportRow[], fieldFormats?: FieldFormatsMap): string {
  const columns = collectColumns(rows)
  if (columns.length === 0) return '\uFEFF'

  const headerLine = columns
    .map((col) => escapeCsvCell(neutralizeFormulaText(formatHeaderLabel(col))))
    .join(';')

  const dataLines = rows.map((row) =>
    columns
      .map((col) => formatCsvValue(row?.[col], normalizeFieldFormat(col, fieldFormats)))
      .join(';')
  )

  return `\uFEFF${[headerLine, ...dataLines].join('\r\n')}\r\n`
}

export function buildCsvBytes(rows: ExportRow[], fieldFormats?: FieldFormatsMap): Uint8Array {
  return textEncoder.encode(buildCsvString(rows, fieldFormats))
}

/** Gera nome sanitizado seguro para Linux e Windows: `adito-<slug>-YYYYMMDD-HHMMSS.<ext>`. */
export function buildExportFilename(
  ext: ExportFormat,
  label?: string,
  now: Date = new Date(),
): string {
  const rawSlug = (label || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48)
    .replace(/-+$/g, '')

  const slug = !rawSlug || WINDOWS_RESERVED_RE.test(rawSlug) ? 'dados' : rawSlug
  const pad = (n: number) => String(n).padStart(2, '0')
  const stamp =
    `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}` +
    `-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`

  return `adito-${slug}-${stamp}.${ext}`
}

// ── Gerador OOXML (.xlsx) + PKZIP (store + CRC32 IEEE 802.3) ─────────────────

const CRC32_TABLE = (() => {
  const table = new Uint32Array(256)
  for (let i = 0; i < 256; i++) {
    let c = i
    for (let k = 0; k < 8; k++) {
      c = (c & 1) !== 0 ? 0xedb88320 ^ (c >>> 1) : c >>> 1
    }
    table[i] = c >>> 0
  }
  return table
})()

function crc32(bytes: Uint8Array): number {
  let crc = 0xffffffff
  for (let i = 0; i < bytes.length; i++) {
    crc = CRC32_TABLE[(crc ^ bytes[i]) & 0xff] ^ (crc >>> 8)
  }
  return (crc ^ 0xffffffff) >>> 0
}

function escapeXml(value: string): string {
  return value
    .replace(XML_INVALID_CONTROL_RE, '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;')
}

function colIndexToLetters(index: number): string {
  let n = index + 1
  let result = ''
  while (n > 0) {
    const rem = (n - 1) % 26
    result = String.fromCharCode(65 + rem) + result
    n = Math.floor((n - 1) / 26)
  }
  return result
}

function sanitizeSheetName(name?: string): string {
  const cleaned = (name || 'Dados')
    .replace(XML_INVALID_CONTROL_RE, '')
    .replace(/[\\/?*[\]:]/g, ' ')
    .trim()
    .slice(0, 31)
  return cleaned || 'Dados'
}

interface ZipEntry {
  name: string
  data: Uint8Array
}

function buildZipStore(entries: ZipEntry[]): Uint8Array {
  const localParts: Uint8Array[] = []
  const centralParts: Uint8Array[] = []
  let offset = 0

  for (const entry of entries) {
    const nameBytes = textEncoder.encode(entry.name)
    const data = entry.data
    const checksum = crc32(data)

    // Local File Header (30 bytes + nome)
    const localHeader = new Uint8Array(30 + nameBytes.length)
    const lv = new DataView(localHeader.buffer)
    lv.setUint32(0, 0x04034b50, true) // signature
    lv.setUint16(4, 20, true) // version needed (2.0)
    lv.setUint16(6, 0x0800, true) // UTF-8 filename flag
    lv.setUint16(8, 0, true) // compression: store (0)
    lv.setUint16(10, 0, true) // mod time
    lv.setUint16(12, 0x5421, true) // mod date (2022-01-01)
    lv.setUint32(14, checksum, true)
    lv.setUint32(18, data.length, true)
    lv.setUint32(22, data.length, true)
    lv.setUint16(26, nameBytes.length, true)
    lv.setUint16(28, 0, true) // extra length
    localHeader.set(nameBytes, 30)

    localParts.push(localHeader, data)

    // Central Directory Header (46 bytes + nome)
    const centralHeader = new Uint8Array(46 + nameBytes.length)
    const cv = new DataView(centralHeader.buffer)
    cv.setUint32(0, 0x02014b50, true) // signature
    cv.setUint16(4, 20, true) // version made by
    cv.setUint16(6, 20, true) // version needed
    cv.setUint16(8, 0x0800, true) // UTF-8 flag
    cv.setUint16(10, 0, true) // compression: store
    cv.setUint16(12, 0, true) // mod time
    cv.setUint16(14, 0x5421, true) // mod date
    cv.setUint32(16, checksum, true)
    cv.setUint32(20, data.length, true)
    cv.setUint32(24, data.length, true)
    cv.setUint16(28, nameBytes.length, true)
    cv.setUint16(30, 0, true) // extra
    cv.setUint16(32, 0, true) // comment
    cv.setUint16(34, 0, true) // disk start
    cv.setUint16(36, 0, true) // internal attrs
    cv.setUint32(38, 0, true) // external attrs
    cv.setUint32(42, offset, true) // relative offset of local header
    centralHeader.set(nameBytes, 46)

    centralParts.push(centralHeader)
    offset += localHeader.length + data.length
  }

  const centralSize = centralParts.reduce((acc, part) => acc + part.length, 0)
  const eocd = new Uint8Array(22)
  const ev = new DataView(eocd.buffer)
  ev.setUint32(0, 0x06054b50, true) // EOCD signature
  ev.setUint16(4, 0, true) // disk number
  ev.setUint16(6, 0, true) // central dir disk
  ev.setUint16(8, entries.length, true)
  ev.setUint16(10, entries.length, true)
  ev.setUint32(12, centralSize, true)
  ev.setUint32(16, offset, true)
  ev.setUint16(20, 0, true) // comment length

  const totalSize = offset + centralSize + eocd.length
  const out = new Uint8Array(totalSize)
  let pos = 0
  for (const part of localParts) {
    out.set(part, pos)
    pos += part.length
  }
  for (const part of centralParts) {
    out.set(part, pos)
    pos += part.length
  }
  out.set(eocd, pos)
  return out
}

// Índices em xl/styles.xml -> cellXfs:
// 0: padrão | 1: cabeçalho negrito | 2: inteiro (#,##0) | 3: decimal (#,##0.00)
// 4: moeda BRL ("R$ "#,##0.00) | 5: percentual (0.00"%")
function styleIndexForNumber(num: number, format: NormalizedFormat): number {
  if (format === 'currency') return 4
  if (format === 'percent') return 5
  if (format === 'integer') return 2
  if (format === 'decimal') return 3
  return Number.isInteger(num) ? 2 : 3
}

function buildStylesXml(): string {
  return (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' +
    '<numFmts count="4">' +
    '<numFmt numFmtId="164" formatCode="#,##0"/>' +
    '<numFmt numFmtId="165" formatCode="#,##0.00"/>' +
    '<numFmt numFmtId="166" formatCode="&quot;R$ &quot;#,##0.00"/>' +
    '<numFmt numFmtId="167" formatCode="0.00&quot;%&quot;"/>' +
    '</numFmts>' +
    '<fonts count="2">' +
    '<font><sz val="11"/><name val="Calibri"/></font>' +
    '<font><b/><sz val="11"/><color rgb="FF1E3A2A"/><name val="Calibri"/></font>' +
    '</fonts>' +
    '<fills count="3">' +
    '<fill><patternFill patternType="none"/></fill>' +
    '<fill><patternFill patternType="gray125"/></fill>' +
    '<fill><patternFill patternType="solid"><fgColor rgb="FFE8F3EC"/><bgColor indexed="64"/></patternFill></fill>' +
    '</fills>' +
    '<borders count="2">' +
    '<border><left/><right/><top/><bottom/><diagonal/></border>' +
    '<border><left/><right/><top/><bottom style="thin"><color rgb="FFC2D9CA"/></bottom><diagonal/></border>' +
    '</borders>' +
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>' +
    '<cellXfs count="6">' +
    '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>' +
    '<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/>' +
    '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>' +
    '<xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>' +
    '<xf numFmtId="166" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>' +
    '<xf numFmtId="167" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>' +
    '</cellXfs>' +
    '</styleSheet>'
  )
}

function buildWorksheetXml(rows: ExportRow[], fieldFormats?: FieldFormatsMap): string {
  const columns = collectColumns(rows)
  const formats = columns.map((col) => normalizeFieldFormat(col, fieldFormats))
  const headers = columns.map((col) => formatHeaderLabel(col))
  const widths = headers.map((h) => Math.max(10, Math.min(48, h.length + 4)))

  const rowXmls: string[] = []

  // Linha 1: Cabeçalhos em negrito (t="inlineStr" nunca é avaliado como fórmula no OOXML)
  if (columns.length > 0) {
    const headerCells = headers.map((label, c) => {
      const ref = `${colIndexToLetters(c)}1`
      const safe = escapeXml(label)
      return `<c r="${ref}" s="1" t="inlineStr"><is><t xml:space="preserve">${safe}</t></is></c>`
    })
    rowXmls.push(`<row r="1">${headerCells.join('')}</row>`)
  }

  // Linhas de dados (2..N)
  for (let r = 0; r < rows.length; r++) {
    const row = rows[r]
    const rowNum = r + 2
    const cells: string[] = []

    for (let c = 0; c < columns.length; c++) {
      const col = columns[c]
      const format = formats[c]
      const raw = row?.[col]
      if (raw === null || raw === undefined) continue

      const ref = `${colIndexToLetters(c)}${rowNum}`
      if (typeof raw === 'boolean') {
        const text = raw ? 'Sim' : 'Não'
        widths[c] = Math.max(widths[c], Math.min(48, text.length + 3))
        cells.push(`<c r="${ref}" t="inlineStr"><is><t>${text}</t></is></c>`)
        continue
      }

      if (format === 'date') {
        const text = formatIsoDatePtBr(raw)
        widths[c] = Math.max(widths[c], Math.min(48, text.length + 3))
        cells.push(`<c r="${ref}" t="inlineStr"><is><t xml:space="preserve">${escapeXml(text)}</t></is></c>`)
        continue
      }

      const num = parseRealNumber(raw, format)
      if (num !== null) {
        const styleIdx = styleIndexForNumber(num, format)
        const displayLen = String(num).length + (format === 'currency' ? 6 : 3)
        widths[c] = Math.max(widths[c], Math.min(48, displayLen))
        cells.push(`<c r="${ref}" s="${styleIdx}"><v>${num}</v></c>`)
        continue
      }

      const text = String(raw)
      widths[c] = Math.max(widths[c], Math.min(48, text.length + 3))
      cells.push(`<c r="${ref}" t="inlineStr"><is><t xml:space="preserve">${escapeXml(text)}</t></is></c>`)
    }

    rowXmls.push(`<row r="${rowNum}">${cells.join('')}</row>`)
  }

  const colsXml =
    columns.length > 0
      ? `<cols>${widths
          .map((w, i) => `<col min="${i + 1}" max="${i + 1}" width="${w}" customWidth="1"/>`)
          .join('')}</cols>`
      : ''

  return (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' +
    colsXml +
    `<sheetData>${rowXmls.join('')}</sheetData>` +
    '</worksheet>'
  )
}

/** Gera bytes de um arquivo `.xlsx` OOXML válido compatível com Excel, LibreOffice e Google Sheets. */
export function buildXlsxBytes(
  rows: ExportRow[],
  fieldFormats?: FieldFormatsMap,
  sheetName = 'Dados',
): Uint8Array {
  const safeSheet = escapeXml(sanitizeSheetName(sheetName))

  const contentTypesXml =
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
    '<Default Extension="xml" ContentType="application/xml"/>' +
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' +
    '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' +
    '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>' +
    '</Types>'

  const relsXml =
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>' +
    '</Relationships>'

  const workbookXml =
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" ' +
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">' +
    `<sheets><sheet name="${safeSheet}" sheetId="1" r:id="rId1"/></sheets>` +
    '</workbook>'

  const workbookRelsXml =
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>' +
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' +
    '</Relationships>'

  return buildZipStore([
    { name: '[Content_Types].xml', data: textEncoder.encode(contentTypesXml) },
    { name: '_rels/.rels', data: textEncoder.encode(relsXml) },
    { name: 'xl/workbook.xml', data: textEncoder.encode(workbookXml) },
    { name: 'xl/_rels/workbook.xml.rels', data: textEncoder.encode(workbookRelsXml) },
    { name: 'xl/styles.xml', data: textEncoder.encode(buildStylesXml()) },
    { name: 'xl/worksheets/sheet1.xml', data: textEncoder.encode(buildWorksheetXml(rows, fieldFormats)) },
  ])
}
