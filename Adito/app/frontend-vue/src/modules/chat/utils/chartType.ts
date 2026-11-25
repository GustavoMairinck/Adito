import { chartKeys, isTimeKey } from '@/common/utils/chartKeys'
import type { ChartSeries } from '@/modules/chat/types'

/**
 * Tipos de gráfico que o chat oferece. São os mesmos do Meu painel (sem a tabela, que o chat
 * já mostra embaixo do gráfico), para o tipo escolhido valer igual ao fixar a resposta.
 */
export type ChatChartType = 'bar' | 'horizontal_bar' | 'line' | 'area' | 'pie'

export const CHAT_CHART_TYPES: ReadonlyArray<{ value: ChatChartType; label: string }> = [
  { value: 'bar', label: 'Barras verticais' },
  { value: 'horizontal_bar', label: 'Barras horizontais' },
  { value: 'line', label: 'Linhas' },
  { value: 'area', label: 'Área' },
  { value: 'pie', label: 'Pizza' },
]

/** Tipo que o ApexCharts entende: a barra horizontal é uma barra com `horizontal: true`. */
export function apexChartType(type: ChatChartType): 'bar' | 'line' | 'area' | 'pie' {
  return type === 'horizontal_bar' ? 'bar' : type
}

/**
 * Tipo com que o gráfico abre: série no tempo (uma só dimensão de tempo, com 3 pontos ou mais)
 * abre em linhas; o resto abre em barras verticais.
 */
export function defaultChartType(rows: Array<Record<string, any>> | null | undefined): ChatChartType {
  if (!Array.isArray(rows) || rows.length < 3) return 'bar'
  const { dimensionKeys } = chartKeys(rows)
  if (dimensionKeys.length === 1 && isTimeKey(dimensionKeys[0])) return 'line'
  return 'bar'
}

export function isChatChartType(value: unknown): value is ChatChartType {
  return CHAT_CHART_TYPES.some(type => type.value === value)
}

/**
 * Tipo com que o gráfico abre quando o usuário ainda não escolheu: o sugerido pelo agente de
 * painéis, se for um tipo válido; senão, o que o formato dos dados indica.
 */
export function initialChartType(
  suggested: unknown,
  rows: Array<Record<string, any>> | null | undefined
): ChatChartType {
  return isChatChartType(suggested) ? suggested : defaultChartType(rows)
}

/** Pizza só faz sentido com uma série de valores, todos não negativos e algum maior que zero. */
export function canUsePie(series: ChartSeries[] | null | undefined): boolean {
  if (!Array.isArray(series) || series.length !== 1) return false
  const values = series[0].data.map(value => Number(value))
  if (values.length === 0 || values.some(value => !Number.isFinite(value) || value < 0)) return false
  return values.some(value => value > 0)
}
