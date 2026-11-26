import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  buildCsvBytes,
  buildCsvString,
  buildExportFilename,
  buildXlsxBytes,
  neutralizeFormulaText,
} from '@/common/utils/exportData'

const invokeMock = vi.fn()
vi.mock('@tauri-apps/api/core', () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}))

import { exportarTabela } from '@/common/api/export'

/** Leitor mínimo do Central Directory PKZIP para validar integridade do .xlsx gerado nos testes. */
function parseZipEntries(bytes: Uint8Array): Map<string, string> {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  const decoder = new TextDecoder()
  // Assinatura do primeiro Local File Header ("PK\x03\x04")
  expect(view.getUint32(0, true)).toBe(0x04034b50)

  // Localiza EOCD ("PK\x05\x06") nos últimos 22 bytes (sem comentário)
  const eocdOffset = bytes.length - 22
  expect(view.getUint32(eocdOffset, true)).toBe(0x06054b50)
  const entryCount = view.getUint16(eocdOffset + 10, true)
  let cdPos = view.getUint32(eocdOffset + 16, true)

  const out = new Map<string, string>()
  for (let i = 0; i < entryCount; i++) {
    expect(view.getUint32(cdPos, true)).toBe(0x02014b50)
    const compression = view.getUint16(cdPos + 10, true)
    expect(compression).toBe(0) // store
    const size = view.getUint32(cdPos + 24, true)
    const nameLen = view.getUint16(cdPos + 28, true)
    const extraLen = view.getUint16(cdPos + 30, true)
    const commentLen = view.getUint16(cdPos + 32, true)
    const localOffset = view.getUint32(cdPos + 42, true)
    const name = decoder.decode(bytes.subarray(cdPos + 46, cdPos + 46 + nameLen))

    expect(view.getUint32(localOffset, true)).toBe(0x04034b50)
    const localNameLen = view.getUint16(localOffset + 26, true)
    const localExtraLen = view.getUint16(localOffset + 28, true)
    const dataStart = localOffset + 30 + localNameLen + localExtraLen
    const content = decoder.decode(bytes.subarray(dataStart, dataStart + size))
    out.set(name, content)

    cdPos += 46 + nameLen + extraLen + commentLen
  }
  return out
}

describe('common/utils/exportData', () => {
  afterEach(() => {
    invokeMock.mockReset()
    delete (window as unknown as Record<string, unknown>).__TAURI_INTERNALS__
    vi.restoreAllMocks()
  })

  it('gera CSV PT-BR com UTF-8 BOM, separador ";", escape RFC 4180, datas e proteção contra Formula Injection', () => {
    const rows = [
      {
        titulo_projeto: 'Robótica; "IFES"\nSerra',
        valor_bolsa: 1500.5,
        saldo: -42.5,
        codigo_cep: '00123',
        data_inicio: '2026-03-15T10:00:00Z',
        ativo: true,
        formula_maliciosa: '=CMD|"/C calc"!A0',
        outro_perigo: '+1+1',
      },
      {
        titulo_projeto: 'Extensão Comunitária',
        valor_bolsa: null,
        saldo: 0,
        codigo_cep: '29173',
        data_inicio: '2026-11-26',
        ativo: false,
        formula_maliciosa: '@SUM(A1)',
        outro_perigo: '-texto',
      },
    ]

    const csv = buildCsvString(rows, {
      valor_bolsa: 'FieldFormat.CURRENCY',
      data_inicio: 'date',
      codigo_cep: 'text',
    })

    expect(csv.startsWith('\uFEFF')).toBe(true)
    const lines = csv.slice(1).split('\r\n')
    expect(lines[0]).toBe('titulo projeto;valor bolsa;saldo;codigo cep;data inicio;ativo;formula maliciosa;outro perigo')
    // Escape RFC 4180 para ;, " e quebra de linha; números PT-BR com vírgula; fórmula neutralizada com '
    expect(csv).toContain('"Robótica; ""IFES""\nSerra";1500,50;-42,5;00123;15/03/2026;Sim;"\'=CMD|""/C calc""!A0";\'+1+1')
    expect(csv).toContain("'+1+1")
    expect(csv).toContain("'@SUM(A1)")
    expect(csv).toContain("'-texto")
    expect(csv).toContain('26/11/2026;Não')
    // Números negativos reais NÃO recebem apóstrofo
    expect(csv).toContain(';-42,5;')

    const bytes = buildCsvBytes(rows)
    // BOM UTF-8 em bytes: EF BB BF
    expect(Array.from(bytes.slice(0, 3))).toEqual([0xef, 0xbb, 0xbf])
  })

  it('neutraliza todos os prefixos de CSV/Formula Injection', () => {
    expect(neutralizeFormulaText('=1+1')).toBe("'=1+1")
    expect(neutralizeFormulaText('+2+2')).toBe("'+2+2")
    expect(neutralizeFormulaText('-cmd')).toBe("'-cmd")
    expect(neutralizeFormulaText('@SUM(A1)')).toBe("'@SUM(A1)")
    expect(neutralizeFormulaText('\tabc')).toBe("'\tabc")
    expect(neutralizeFormulaText(' =CMD|"/C calc"!A0')).toBe('\' =CMD|"/C calc"!A0')
    expect(neutralizeFormulaText('\n+2+2')).toBe("'\n+2+2")
    expect(neutralizeFormulaText('texto normal')).toBe('texto normal')
    expect(neutralizeFormulaText('  texto com espaço')).toBe('  texto com espaço')
  })

  it('gera arquivo .xlsx OOXML válido com cabeçalhos em negrito, números reais, fieldFormats e sanitização XML', () => {
    const rows = [
      {
        grande_area: 'Ciências & Engenharias <IFES>\x00',
        total_projetos: 236,
        investimento: 320000.75,
        taxa: 45.5,
        data_ref: '2026-11-26',
        formula: '=HYPERLINK("http://evil")',
      },
      {
        grande_area: 'Humanas',
        total_projetos: 48,
        investimento: -10.25,
        taxa: 12.0,
        data_ref: '2026-01-05',
        formula: null,
      },
    ]

    const xlsx = buildXlsxBytes(rows, {
      total_projetos: 'integer',
      investimento: 'currency',
      taxa: 'percent',
      data_ref: 'date',
    })

    const entries = parseZipEntries(xlsx)
    expect([...entries.keys()].sort()).toEqual([
      '[Content_Types].xml',
      '_rels/.rels',
      'xl/_rels/workbook.xml.rels',
      'xl/styles.xml',
      'xl/workbook.xml',
      'xl/worksheets/sheet1.xml',
    ])

    const sheet = entries.get('xl/worksheets/sheet1.xml')!
    // Cabeçalho com estilo s="1"
    expect(sheet).toContain('<c r="A1" s="1" t="inlineStr"><is><t xml:space="preserve">grande area</t></is></c>')
    // Escape XML e remoção de caractere de controle \x00
    expect(sheet).toContain('Ciências &amp; Engenharias &lt;IFES&gt;')
    expect(sheet).not.toContain('\x00')
    // Números reais gravados com <v> e estilos correspondentes (2=int, 4=currency, 5=percent)
    expect(sheet).toContain('<c r="B2" s="2"><v>236</v></c>')
    expect(sheet).toContain('<c r="C2" s="4"><v>320000.75</v></c>')
    expect(sheet).toContain('<c r="D2" s="5"><v>45.5</v></c>')
    expect(sheet).toContain('<c r="C3" s="4"><v>-10.25</v></c>')
    // Data formatada e inlineStr sem prefixo de apóstrofo (inlineStr nunca é avaliado como fórmula no OOXML)
    expect(sheet).toContain('26/11/2026')
    expect(sheet).toContain('<t xml:space="preserve">=HYPERLINK(&quot;http://evil&quot;)</t>')
    expect(sheet).not.toContain('&apos;=HYPERLINK')
  })

  it('preserva textos iniciados por + ou - sem apóstrofo no .xlsx e mantém números longos (>15 dígitos) como texto em CSV e .xlsx', () => {
    const id20 = '12345678901234567891'
    const chaveNfe44 = '32261112345678000195550010000001231234567890'
    const rows = [
      {
        telefone: '+55 27 3333-4444',
        placeholder: '-',
        id_longo: id20,
        chave_nfe: chaveNfe44,
        valor_str: '1500.50',
      },
    ]

    // XLSX: inlineStr sem apóstrofo extra e IDs longos preservados integralmente como texto
    const entries = parseZipEntries(buildXlsxBytes(rows, { valor_str: 'currency' }))
    const sheet = entries.get('xl/worksheets/sheet1.xml')!
    expect(sheet).toContain('<t xml:space="preserve">+55 27 3333-4444</t>')
    expect(sheet).not.toContain('&apos;+55')
    expect(sheet).toContain('<t xml:space="preserve">-</t>')
    expect(sheet).not.toContain('&apos;-</t>')
    expect(sheet).toContain(`<t xml:space="preserve">${id20}</t>`)
    expect(sheet).toContain(`<t xml:space="preserve">${chaveNfe44}</t>`)
    // String numérica normal (<= 15 dígitos) continua gravada como número real
    expect(sheet).toContain('<c r="E2" s="4"><v>1500.5</v></c>')

    // CSV: mantém proteção de Formula Injection para + / -, e preserva IDs longos sem corromper dígitos
    const csv = buildCsvString(rows, { valor_str: 'currency' })
    expect(csv).toContain("'+55 27 3333-4444")
    expect(csv).toContain("'-;")
    expect(csv).toContain(`;${id20};${chaveNfe44};1500,50`)
  })

  it('buildExportFilename sanitiza acentos, caracteres inválidos e nomes reservados do Windows', () => {
    const fixedDate = new Date(2026, 10, 26, 14, 5, 9)
    expect(buildExportFilename('xlsx', 'Quantos projetos por Grande Área? (2026)', fixedDate)).toBe(
      'adito-quantos-projetos-por-grande-area-2026-20261126-140509.xlsx'
    )
    expect(buildExportFilename('csv', 'CON', fixedDate)).toBe('adito-dados-20261126-140509.csv')
    expect(buildExportFilename('csv', '   ', fixedDate)).toBe('adito-dados-20261126-140509.csv')
  })

  it('exportarTabela usa comando Tauri exportar_arquivo (com suporte a cancelamento) e fallback navegador', async () => {
    const rows = [{ area: 'Engenharias', total: 120 }]

    // Ambiente Tauri: usuário escolhe destino e confirma
    ;(window as unknown as Record<string, unknown>).__TAURI_INTERNALS__ = {}
    invokeMock.mockResolvedValueOnce({
      nome: 'relatorio-custom.csv',
      caminho: '/home/user/Documentos/relatorio-custom.csv',
      cancelado: false,
    })

    const resTauri = await exportarTabela(rows, 'csv', { label: 'Teste' })
    expect(resTauri).toEqual({
      nome: 'relatorio-custom.csv',
      caminho: '/home/user/Documentos/relatorio-custom.csv',
      modo: 'tauri',
      cancelado: false,
    })
    expect(invokeMock).toHaveBeenCalledWith(
      'exportar_arquivo',
      expect.objectContaining({
        nome: expect.stringMatching(/^adito-teste-\d{8}-\d{6}\.csv$/),
        bytes: expect.any(Array),
      })
    )

    // Ambiente Tauri: usuário cancela o diálogo "Salvar como..."
    invokeMock.mockResolvedValueOnce({ nome: '', caminho: '', cancelado: true })
    const resCancelado = await exportarTabela(rows, 'xlsx', { label: 'Teste' })
    expect(resCancelado.cancelado).toBe(true)
    expect(resCancelado.modo).toBe('tauri')

    // Ambiente navegador com showSaveFilePicker (confirmado e cancelado)
    delete (window as unknown as Record<string, unknown>).__TAURI_INTERNALS__
    const writeSpy = vi.fn().mockResolvedValue(undefined)
    const closeSpy = vi.fn().mockResolvedValue(undefined)
    const pickerMock = vi.fn().mockResolvedValueOnce({
      name: 'escolhido.xlsx',
      createWritable: vi.fn().mockResolvedValue({ write: writeSpy, close: closeSpy }),
    })
    ;(window as unknown as Record<string, unknown>).showSaveFilePicker = pickerMock

    const resPicker = await exportarTabela(rows, 'xlsx', { label: 'Painel' })
    expect(resPicker).toEqual({ nome: 'escolhido.xlsx', caminho: null, modo: 'browser', cancelado: false })
    expect(writeSpy).toHaveBeenCalledTimes(1)
    expect(closeSpy).toHaveBeenCalledTimes(1)

    pickerMock.mockRejectedValueOnce(Object.assign(new Error('cancelado'), { name: 'AbortError' }))
    const resPickerCancel = await exportarTabela(rows, 'csv', { label: 'Painel' })
    expect(resPickerCancel.cancelado).toBe(true)

    // Ambiente navegador sem showSaveFilePicker (fallback Blob)
    delete (window as unknown as Record<string, unknown>).showSaveFilePicker
    const createUrlSpy = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock')
    const revokeSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    const resBrowser = await exportarTabela(rows, 'xlsx', { label: 'Painel' })
    expect(resBrowser.modo).toBe('browser')
    expect(resBrowser.cancelado).toBe(false)
    expect(resBrowser.nome).toMatch(/^adito-painel-\d{8}-\d{6}\.xlsx$/)
    expect(createUrlSpy).toHaveBeenCalledTimes(1)
    expect(clickSpy).toHaveBeenCalledTimes(1)
    revokeSpy.mockRestore()
  })
})
