import { describe, expect, it } from 'vitest'
import {
  apexChartType,
  CHAT_CHART_TYPES,
  canUsePie,
  defaultChartType,
  initialChartType,
  isChatChartType,
} from '@/modules/chat/utils/chartType'

describe('modules/chat/utils/chartType', () => {
  it('oferece os mesmos tipos de gráfico do Meu painel, com rótulos', () => {
    expect(CHAT_CHART_TYPES.map(type => type.value)).toEqual(['bar', 'horizontal_bar', 'line', 'area', 'pie'])
    expect(CHAT_CHART_TYPES.map(type => type.label)).toEqual([
      'Barras verticais',
      'Barras horizontais',
      'Linhas',
      'Área',
      'Pizza',
    ])
  })

  it('apexChartType desenha a barra horizontal como barra', () => {
    expect(apexChartType('bar')).toBe('bar')
    expect(apexChartType('horizontal_bar')).toBe('bar')
    expect(apexChartType('line')).toBe('line')
    expect(apexChartType('area')).toBe('area')
    expect(apexChartType('pie')).toBe('pie')
  })

  it('defaultChartType abre série no tempo com 3 pontos ou mais em linhas', () => {
    const porAno = [
      { ano: 2022, total: 10 },
      { ano: 2023, total: 12 },
      { ano: 2024, total: 15 },
    ]
    expect(defaultChartType(porAno)).toBe('line')
    expect(defaultChartType([
      { mes: '2024-01', total: 1 },
      { mes: '2024-02', total: 2 },
      { mes: '2024-03', total: 3 },
    ])).toBe('line')
  })

  it('defaultChartType abre em barras o resto', () => {
    // Poucos pontos no tempo
    expect(defaultChartType([{ ano: 2023, total: 1 }, { ano: 2024, total: 2 }])).toBe('bar')
    // Dimensão que não é tempo
    expect(defaultChartType([
      { grande_area: 'Engenharias', total: 120 },
      { grande_area: 'Ciências Exatas', total: 116 },
      { grande_area: 'Ciências Humanas', total: 40 },
    ])).toBe('bar')
    // Tempo junto com outra dimensão
    expect(defaultChartType([
      { ano: 2023, modalidade: 'PIBIC', total: 1 },
      { ano: 2023, modalidade: 'PIBITI', total: 2 },
      { ano: 2024, modalidade: 'PIBIC', total: 3 },
    ])).toBe('bar')
    // Sem linhas
    expect(defaultChartType([])).toBe('bar')
    expect(defaultChartType(undefined)).toBe('bar')
    expect(defaultChartType(null)).toBe('bar')
  })

  it('isChatChartType aceita só os tipos do chat', () => {
    for (const type of ['bar', 'horizontal_bar', 'line', 'area', 'pie']) {
      expect(isChatChartType(type)).toBe(true)
    }
    for (const type of ['table', 'metric_card', 'donut', '', null, undefined, 1]) {
      expect(isChatChartType(type)).toBe(false)
    }
  })

  it('initialChartType usa a sugestão do agente e, sem ela, o formato dos dados', () => {
    const porAno = [
      { ano: 2022, total: 10 },
      { ano: 2023, total: 12 },
      { ano: 2024, total: 15 },
    ]
    expect(initialChartType('area', porAno)).toBe('area')
    expect(initialChartType('pie', porAno)).toBe('pie')
    expect(initialChartType(undefined, porAno)).toBe('line')
    expect(initialChartType('metric_card', porAno)).toBe('line')
    expect(initialChartType(null, [{ grande_area: 'Engenharias', total: 1 }])).toBe('bar')
  })

  it('canUsePie exige uma série só, sem negativos e com algum valor positivo', () => {
    expect(canUsePie([{ name: 'Total', data: [3, 0, 1] }])).toBe(true)
    expect(canUsePie([{ name: 'Total', data: [3, 1] }, { name: 'Valor', data: [10, 20] }])).toBe(false)
    expect(canUsePie([{ name: 'Saldo', data: [3, -1] }])).toBe(false)
    expect(canUsePie([{ name: 'Total', data: [0, 0] }])).toBe(false)
    expect(canUsePie([{ name: 'Total', data: [] }])).toBe(false)
    expect(canUsePie([])).toBe(false)
    expect(canUsePie(null)).toBe(false)
  })
})
