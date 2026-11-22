/**
 * Decide quais colunas de um resultado viram o eixo do gráfico (dimensões) e quais viram séries
 * (métricas). Usado pelo chat e pelo Meu painel, para os dois desenharem o mesmo gráfico.
 *
 * Regra:
 * - coluna de tempo (ano, mês, trimestre, data…) é sempre eixo, mesmo sendo número;
 * - coluna com algum valor que não é número é eixo;
 * - se nenhuma coluna for eixo, a primeira coluna vira o eixo;
 * - as outras colunas com números são as séries.
 */

const TIME_KEY = /^(ano|anos|mes|m[eê]s|dia|data|trimestre|semestre|periodo|per[ií]odo|year|month|quarter|date)$|^(ano|mes|data|trimestre|semestre|year|month)_|_(ano|mes|data|year|month)$/i

/** Número de verdade: "2024" e 12.5 sim; "2024-01-01" e "PIBIC" não. */
export function parseStrictNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value === 'boolean') return null
  const parsed = Number(String(value).trim())
  return Number.isFinite(parsed) ? parsed : null
}

export function isTimeKey(key: string): boolean {
  return TIME_KEY.test(key)
}

export function chartKeys(data: Array<Record<string, any>> | null | undefined): { dimensionKeys: string[]; metricKeys: string[] } {
  if (!Array.isArray(data) || data.length === 0) return { dimensionKeys: [], metricKeys: [] }
  const keys = Object.keys(data[0] || {})
  const hasText = (key: string) =>
    data.some(row => {
      const value = row[key]
      return value !== null && value !== undefined && value !== '' && parseStrictNumber(value) === null
    })
  const hasNumber = (key: string) => data.some(row => parseStrictNumber(row[key]) !== null)

  let dimensionKeys = keys.filter(key => isTimeKey(key) || hasText(key))
  if (dimensionKeys.length === 0 && keys.length > 1) dimensionKeys = [keys[0]]
  const metricKeys = keys.filter(key => !dimensionKeys.includes(key) && hasNumber(key))
  return { dimensionKeys, metricKeys }
}
