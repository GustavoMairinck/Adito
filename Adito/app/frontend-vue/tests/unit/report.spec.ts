import { describe, expect, it } from 'vitest'
import type { ChatMessage, ChatReport } from '@/modules/chat/types'
import {
  REPORT_TABLE_LIMIT,
  SECTION_ERROR_TEXT,
  isReportEligible,
  mapReportMetadata,
  questionFor,
  reportFileName,
  reportToMarkdown,
  sectionView,
} from '@/modules/chat/utils/report'
import { formatFieldValue } from '@/modules/chat/utils/format'

const answer = (patch: Partial<ChatMessage> = {}): ChatMessage => ({
  id: 'a1',
  type: 'ai',
  text: 'Resposta',
  timestamp: '2026-11-25T10:00:00Z',
  sql: 'SELECT area, total FROM v',
  table: [{ area: 'A', total: 1 }],
  ...patch,
})

describe('modules/chat/utils/report', () => {
  it('isReportEligible aceita só análise com SQL e dados, terminada', () => {
    expect(isReportEligible(answer())).toBe(true)
    expect(isReportEligible(answer({ table: [], needsRows: true }))).toBe(true)
    expect(isReportEligible(answer({ type: 'user' }))).toBe(false)
    expect(isReportEligible(answer({ sql: undefined }))).toBe(false)
    expect(isReportEligible(answer({ table: [] }))).toBe(false)
    expect(isReportEligible(answer({ isFallback: true }))).toBe(false)
    expect(isReportEligible(answer({ isChat: true }))).toBe(false)
    expect(isReportEligible(answer({ interrupted: true }))).toBe(false)
    expect(isReportEligible(answer({ isLoading: true }))).toBe(false)
    expect(isReportEligible(answer({ report: { title: 'R', generatedAt: '', sections: [], loaded: true } }))).toBe(false)
  })

  it('questionFor acha a pergunta pelo id ou pela mensagem anterior', () => {
    const user = { id: 'u1', type: 'user' as const, text: 'Projetos por área?', timestamp: '' }
    expect(questionFor([user, answer()], answer())).toBe('Projetos por área?')
    expect(questionFor([user, answer({ userMessageId: 'u1' })], answer({ userMessageId: 'u1' }))).toBe('Projetos por área?')
  })

  it('mapReportMetadata lê a definição gravada e ignora tipo de gráfico inválido', () => {
    const report = mapReportMetadata({
      title: 'Panorama',
      contexto_nome: 'Pesquisa',
      sections: [
        { source_message_id: 'a1', title: 'Área', sql: 'SELECT 1', field_formats: { total: 'integer' }, chart_type: 'pie' },
        { source_message_id: 'a2', title: 'Ano', sql: 'SELECT 2', chart_type: 'metric_card' },
      ],
    }, '2026-11-25T14:30:00Z')
    expect(report.title).toBe('Panorama')
    expect(report.loaded).toBe(false)
    expect(report.sections.map(s => s.chartType)).toEqual(['pie', null])
    expect(report.sections[1].fieldFormats).toEqual({})
  })

  it('sectionView decide aviso, cartão ou gráfico com tabela de até 20 linhas', () => {
    const base = { sourceMessageId: 'a1', title: 'S', sql: 'x', fieldFormats: {}, chartType: null }
    expect(sectionView({ ...base }, false).kind).toBe('loading')
    expect(sectionView({ ...base, data: [], error: 'falhou' }, true)).toEqual({ kind: 'error', message: SECTION_ERROR_TEXT })
    expect(sectionView({ ...base, data: [] }, true).kind).toBe('empty')
    expect(sectionView({ ...base, data: [{ total: 236 }] }, true)).toEqual({ kind: 'scalar', label: 'total', value: '236' })

    const rows = Array.from({ length: 30 }, (_, i) => ({ campus: `Campus ${i}`, total: i + 1 }))
    const view = sectionView({ ...base, data: rows }, true)
    expect(view.kind).toBe('data')
    if (view.kind !== 'data') return
    expect(view.rows).toHaveLength(REPORT_TABLE_LIMIT)
    expect(view.total).toBe(30)
    expect(view.chartType).toBe('bar')

    // Pizza pedida com duas séries cai para barras
    const twoSeries = [{ area: 'A', total: 1, valor: 2 }, { area: 'B', total: 3, valor: 4 }]
    const pie = sectionView({ ...base, chartType: 'pie', data: twoSeries }, true)
    expect(pie.kind === 'data' && pie.chartType).toBe('bar')
    // Série no tempo abre em linhas
    const byYear = [{ ano: 2022, total: 1 }, { ano: 2023, total: 2 }, { ano: 2024, total: 3 }]
    const line = sectionView({ ...base, data: byYear }, true)
    expect(line.kind === 'data' && line.chartType).toBe('line')
  })

  it('reportToMarkdown monta o texto copiado sem texto de LLM', () => {
    const report: ChatReport = {
      title: 'Panorama',
      contextoNome: 'Pesquisa',
      generatedAt: '2026-11-25T14:30:00Z',
      loaded: true,
      sections: [
        { sourceMessageId: 'a1', title: 'Por área', sql: 'x', fieldFormats: { total: 'integer' }, chartType: null, data: [{ grande_area: 'Engenharias', total: 1200 }, { grande_area: 'Exatas', total: 80 }] },
        { sourceMessageId: 'a2', title: 'Quebrada', sql: 'y', fieldFormats: {}, chartType: null, data: [], error: 'x' },
      ],
    }
    const md = reportToMarkdown(report, '2026-11-01')
    expect(md).toContain('# Panorama')
    expect(md).toContain('Versão dos dados: 2026-11-01')
    expect(md).toContain('## 1. Por área')
    expect(md).toContain('| grande area | total |')
    expect(md).toContain('| Engenharias | 1.200 |')
    expect(md).toContain(`_${SECTION_ERROR_TEXT}_`)
  })

  it('reportFileName segue "Relatório - título - data" sem caracteres inválidos', () => {
    expect(reportFileName('Bolsas: 2024/2025', '2026-11-25T14:30:00')).toBe('Relatório - Bolsas 2024 2025 - 2026-11-25')
  })

  it('colunas de tempo não ganham separador de milhar', () => {
    expect(formatFieldValue({ ano: 'integer' }, 'ano', 2024)).toBe('2024')
    expect(formatFieldValue({}, 'ano', 2024)).toBe('2024')
    expect(formatFieldValue({ total: 'integer' }, 'total', 2024)).toBe('2.024')
  })
})
