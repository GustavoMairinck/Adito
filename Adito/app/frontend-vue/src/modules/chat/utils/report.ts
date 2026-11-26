import type { ChatMessage, ChatReport, ChatReportSection, FieldFormat } from '@/modules/chat/types'
import { canUsePie, initialChartType, isChatChartType, type ChatChartType } from '@/modules/chat/utils/chartType'
import { buildChart, isScalarResultData } from '@/modules/chat/composables/useChatApi'
import { formatFieldValue } from '@/modules/chat/utils/format'

export const REPORT_MAX_SECTIONS = 20
export const REPORT_TABLE_LIMIT = 20

/**
 * Resposta que pode virar seção (BR01): análise do Adito com SQL e dados, terminada.
 * Não entram conversa simples, aviso de "não encontrei", resposta interrompida nem outro relatório.
 */
export function isReportEligible(message: ChatMessage): boolean {
  if (message.type !== 'ai' || message.report) return false
  if (message.isLoading || message.interrupted || message.isFallback || message.isChat || message.error) return false
  if (!message.sql) return false
  return (message.table?.length ?? 0) > 0 || !!message.needsRows
}

/** Pergunta que originou a resposta (pelo id gravado ou pela mensagem do usuário logo antes). */
export function questionFor(messages: ChatMessage[], message: ChatMessage): string {
  if (message.userMessageId) {
    const user = messages.find(m => m.id === message.userMessageId)
    if (user?.text) return user.text
  }
  const index = messages.findIndex(m => m.id === message.id)
  for (let i = index - 1; i >= 0; i--) {
    if (messages[i].type === 'user') return messages[i].text
  }
  return message.text?.slice(0, 120) || 'Resposta'
}

/** Mensagem do núcleo (`metadata.type = "report"`) → relatório do front, ainda sem as linhas. */
export function mapReportMetadata(metadata: any, createdAt: string): ChatReport {
  const sections: ChatReportSection[] = (metadata?.sections || []).map((section: any) => ({
    sourceMessageId: String(section.source_message_id),
    title: String(section.title || ''),
    sql: String(section.sql || ''),
    fieldFormats: (section.field_formats || {}) as Record<string, FieldFormat>,
    chartType: isChatChartType(section.chart_type) ? section.chart_type : null,
  }))
  return {
    title: String(metadata?.title || 'Relatório'),
    contextoNome: metadata?.contexto_nome ?? null,
    generatedAt: createdAt,
    sections,
    loaded: false,
  }
}

export type SectionView =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'empty' }
  | { kind: 'scalar'; label: string; value: string }
  | { kind: 'data'; chartType: ChatChartType | null; chart: ReturnType<typeof buildChart>; rows: Array<Record<string, any>>; total: number }

export const SECTION_ERROR_TEXT = 'Não foi possível atualizar esta seção: os dados mudaram desde a pergunta.'
export const SECTION_EMPTY_TEXT = 'Nenhum registro para esta seção.'

/** O que a seção mostra: aviso, cartão de número, ou gráfico (quando houver) e tabela com até 20 linhas. */
export function sectionView(section: ChatReportSection, loaded: boolean): SectionView {
  if (!loaded || section.data === undefined) return { kind: 'loading' }
  if (section.error) return { kind: 'error', message: SECTION_ERROR_TEXT }
  const rows = section.data || []
  if (rows.length === 0) return { kind: 'empty' }
  if (isScalarResultData(rows)) {
    const [key, value] = Object.entries(rows[0])[0]
    return { kind: 'scalar', label: key.replace(/_/g, ' '), value: formatFieldValue(section.fieldFormats, key, value) }
  }
  const chart = rows.length > 1 ? buildChart(rows) : null
  let chartType: ChatChartType | null = null
  if (chart?.series?.length) {
    chartType = initialChartType(section.chartType, rows)
    if (chartType === 'pie' && !canUsePie(chart.series)) chartType = 'bar'
  }
  return { kind: 'data', chartType, chart: chartType ? chart : null, rows: rows.slice(0, REPORT_TABLE_LIMIT), total: rows.length }
}

export function formatDateTime(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

/** Nome sugerido do PDF (FR18): `Relatório - <título> - <AAAA-MM-DD>`. */
export function reportFileName(title: string, iso: string): string {
  const date = new Date(iso)
  const day = Number.isNaN(date.getTime())
    ? iso.slice(0, 10)
    : `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  const safeTitle = title.replace(/[\\/:*?"<>|]+/g, ' ').replace(/\s+/g, ' ').trim() || 'Relatório'
  return `Relatório - ${safeTitle} - ${day}`
}

function markdownTable(rows: Array<Record<string, any>>, formats: Record<string, FieldFormat>): string {
  const headers = Object.keys(rows[0] || {})
  if (!headers.length) return ''
  const head = `| ${headers.map(h => h.replace(/_/g, ' ')).join(' | ')} |`
  const divider = `| ${headers.map(() => '---').join(' | ')} |`
  const body = rows
    .map(row => `| ${headers.map(h => formatFieldValue(formats, h, row[h]).replace(/\|/g, '\\|')).join(' | ')} |`)
    .join('\n')
  return `${head}\n${divider}\n${body}`
}

/** Texto copiado do relatório (FR11): Markdown com cabeçalho, seções, números e tabelas; sem texto de LLM. */
export function reportToMarkdown(report: ChatReport, dataVersion?: string | null): string {
  const lines = [`# ${report.title}`, '']
  lines.push(`Gerado pelo Adito em ${formatDateTime(report.generatedAt)}`)
  if (report.contextoNome) lines.push(`Contexto: ${report.contextoNome}`)
  if (dataVersion) lines.push(`Versão dos dados: ${dataVersion}`)
  report.sections.forEach((section, index) => {
    lines.push('', `## ${index + 1}. ${section.title}`, '')
    const view = sectionView(section, report.loaded)
    if (view.kind === 'loading') lines.push('_Carregando…_')
    else if (view.kind === 'error') lines.push(`_${view.message}_`)
    else if (view.kind === 'empty') lines.push(`_${SECTION_EMPTY_TEXT}_`)
    else if (view.kind === 'scalar') lines.push(`**${view.label}:** ${view.value}`)
    else {
      lines.push(markdownTable(view.rows, section.fieldFormats))
      lines.push('', `_Mostrando ${view.rows.length} de ${view.total} registros._`)
    }
  })
  return lines.join('\n')
}
