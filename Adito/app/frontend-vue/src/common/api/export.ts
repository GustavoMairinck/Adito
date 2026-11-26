import {
  buildCsvBytes,
  buildExportFilename,
  buildXlsxBytes,
  type ExportFormat,
  type ExportRow,
  type FieldFormatsMap,
} from '@/common/utils/exportData'

export interface ExportSaveResult {
  nome: string
  caminho: string | null
  modo: 'tauri' | 'browser'
  cancelado?: boolean
}

const MIME_BY_FORMAT: Record<ExportFormat, string> = {
  csv: 'text/csv;charset=utf-8',
  xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}

interface SaveFilePickerHandle {
  name?: string
  createWritable: () => Promise<{
    write: (data: Blob) => Promise<void>
    close: () => Promise<void>
  }>
}

type ShowSaveFilePickerFn = (options?: {
  suggestedName?: string
  types?: Array<{ description?: string; accept: Record<string, string[]> }>
}) => Promise<SaveFilePickerHandle>

function isTauriRuntime(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window
}

function getSaveFilePicker(): ShowSaveFilePickerFn | null {
  if (typeof window === 'undefined') return null
  const fn = (window as unknown as { showSaveFilePicker?: ShowSaveFilePickerFn }).showSaveFilePicker
  return typeof fn === 'function' ? fn : null
}

function downloadViaBlob(nome: string, bytes: Uint8Array, mimeType: string): ExportSaveResult {
  const copy = new Uint8Array(bytes.byteLength)
  copy.set(bytes)
  const blob = new Blob([copy], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = nome
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
  return { nome, caminho: null, modo: 'browser', cancelado: false }
}

async function saveViaBrowserPicker(
  picker: ShowSaveFilePickerFn,
  nome: string,
  bytes: Uint8Array,
  mimeType: string,
): Promise<ExportSaveResult> {
  const ext = nome.toLowerCase().endsWith('.xlsx') ? '.xlsx' : '.csv'
  const description = ext === '.xlsx' ? 'Planilha Excel' : 'CSV'
  const cleanMime = mimeType.split(';')[0] || 'application/octet-stream'
  try {
    const handle = await picker({
      suggestedName: nome,
      types: [{ description, accept: { [cleanMime]: [ext] } }],
    })
    const copy = new Uint8Array(bytes.byteLength)
    copy.set(bytes)
    const writable = await handle.createWritable()
    await writable.write(new Blob([copy], { type: mimeType }))
    await writable.close()
    return { nome: handle.name || nome, caminho: null, modo: 'browser', cancelado: false }
  } catch (err: unknown) {
    if (err && typeof err === 'object' && 'name' in err && (err as { name: string }).name === 'AbortError') {
      return { nome, caminho: null, modo: 'browser', cancelado: true }
    }
    throw err
  }
}

/**
 * Abre o diálogo nativo "Salvar como..." via comando Rust `exportar_arquivo` no Tauri,
 * ou usa `showSaveFilePicker` / fallback `<a download>` via `Blob` fora do Tauri.
 */
export async function salvarArquivoExportado(
  nome: string,
  bytes: Uint8Array,
  mimeType: string,
): Promise<ExportSaveResult> {
  if (isTauriRuntime()) {
    const { invoke } = await import('@tauri-apps/api/core')
    const res = await invoke<{ nome: string; caminho: string; cancelado?: boolean }>('exportar_arquivo', {
      nome,
      bytes: Array.from(bytes),
    })
    if (res.cancelado) {
      return { nome: res.nome || nome, caminho: null, modo: 'tauri', cancelado: true }
    }
    return { nome: res.nome, caminho: res.caminho, modo: 'tauri', cancelado: false }
  }
  const picker = getSaveFilePicker()
  if (picker) {
    return saveViaBrowserPicker(picker, nome, bytes, mimeType)
  }
  return downloadViaBlob(nome, bytes, mimeType)
}

export async function exportarTabela(
  rows: ExportRow[],
  format: ExportFormat,
  options?: { fieldFormats?: FieldFormatsMap; label?: string; sheetName?: string },
): Promise<ExportSaveResult> {
  if (!rows.length) {
    throw new Error('Não há dados disponíveis para exportar.')
  }
  const nome = buildExportFilename(format, options?.label)
  const bytes =
    format === 'xlsx'
      ? buildXlsxBytes(rows, options?.fieldFormats, options?.sheetName || 'Dados')
      : buildCsvBytes(rows, options?.fieldFormats)
  return salvarArquivoExportado(nome, bytes, MIME_BY_FORMAT[format])
}
