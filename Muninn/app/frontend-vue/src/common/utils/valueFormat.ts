// Formato dos números no Meu painel. O widget salvo não guarda o formato de cada coluna,
// então o nome da coluna/série diz se o valor é dinheiro, percentual ou contagem.

export type ValueKind = 'money' | 'percent' | 'number'

const semAcento = (texto: string) => texto.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()

const MONEY_KEY = /(valor|investiment|investid|custo|gasto|pago|pagament|orcament|receita|reais|bolsa[ _]mensal)/
const PERCENT_KEY = /(percent|taxa|pct|proporcao)/

/** Tipo do valor pelo nome ("Investimento Total" → money, "Total Grupos" → number). */
export function valueKind(nome: string): ValueKind {
  const chave = semAcento(String(nome || ''))
  if (PERCENT_KEY.test(chave)) return 'percent'
  if (MONEY_KEY.test(chave)) return 'money'
  return 'number'
}

/** Um tipo só para o eixo: o das séries, se todas forem iguais; senão número comum. */
export function axisKind(nomes: string[]): ValueKind {
  const tipos = new Set(nomes.map(valueKind))
  return tipos.size === 1 ? [...tipos][0] : 'number'
}

const fmt = (valor: number, casas: number) => valor.toLocaleString('pt-BR', { maximumFractionDigits: casas })

const compacto = (valor: number) => {
  const abs = Math.abs(valor)
  if (abs >= 1_000_000) return `${fmt(valor / 1_000_000, 1)} mi`
  if (abs >= 1_000) return `${fmt(valor / 1_000, 1)} mil`
  return fmt(valor, 2)
}

/** Eixo: forma curta ("R$ 1,4 mi", "9,3 mil"). Tooltip (`exato`): valor inteiro ("R$ 1.363.864,00"). */
export function formatValue(valor: unknown, tipo: ValueKind, exato = false): string {
  // Só formata valor realmente numérico: "2024 - Sem custo" não pode virar "R$ 2.024,00".
  const num = typeof valor === 'number' ? valor : typeof valor === 'string' && valor.trim() !== '' ? Number(valor) : Number.NaN
  if (!Number.isFinite(num)) return String(valor ?? '')
  if (tipo === 'percent') return `${fmt(num, 1)}%`
  if (tipo === 'money') {
    return exato ? num.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) : `R$ ${compacto(num)}`
  }
  return exato ? fmt(num, 2) : compacto(num)
}
