import type { FieldFormat } from '@/modules/chat/types'
import { isTimeKey } from '@/common/utils/chartKeys'

/** Formatação de valores das respostas (tabela, cartão, eixos e tooltips), em pt-BR. */
export const fmt = (n: number, dec = 1) =>
  new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: dec }).format(n)

export const formatNumber = (value: number) => {
  if (value === undefined || value === null || Number.isNaN(value)) return '0'
  const abs = Math.abs(value)
  if (abs >= 1_000_000_000) return `${fmt(value / 1_000_000_000)}B`
  if (abs >= 1_000_000)     return `${fmt(value / 1_000_000)}M`
  if (abs >= 1_000)         return `${fmt(value / 1_000)}K`
  return fmt(value, 2)
}

export function formatDateValue(value: unknown) {
  if (value === null || value === undefined || value === '') return 'nulo'
  const text = String(value)
  const datePart = text.split('T')[0]
  if (/^\d{4}-\d{2}-\d{2}$/.test(datePart)) {
    const [year, month, day] = datePart.split('-')
    return `${day}/${month}/${year}`
  }
  return text
}

export function formatFieldValue(fieldFormats: Record<string, FieldFormat | string> | undefined, key: string | number, value: unknown) {
  if (value === null || value === undefined) return 'nulo'

  const rawFormat = fieldFormats?.[String(key)]
  const format = String(rawFormat || '').replace(/^FieldFormat\./, '').toLowerCase() as FieldFormat | ''

  if (format === 'text') return String(value)
  if (format === 'date') return formatDateValue(value)
  // Ano, mês, trimestre… são rótulos, não quantidades: "2024", nunca "2.024".
  if (format !== 'currency' && format !== 'decimal' && format !== 'percent' && isTimeKey(String(key))) return String(value)

  const numericValue = Number(value)

  if (format === 'currency') {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(numericValue)
  }
  if (format === 'integer') {
    return new Intl.NumberFormat('pt-BR', { useGrouping: true, maximumFractionDigits: 0 }).format(numericValue)
  }
  if (format === 'percent') {
    return `${new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(numericValue)}%`
  }
  if (format === 'decimal') {
    return new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(numericValue)
  }

  // Sem formato definido: tenta auto-detectar pelo valor
  if (!Number.isFinite(numericValue)) return String(value)

  // Número inteiro
  if (Number.isInteger(numericValue)) {
    return new Intl.NumberFormat('pt-BR').format(numericValue)
  }
  // Número com decimais — formata com separadores pt-BR
  return new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(numericValue)
}
