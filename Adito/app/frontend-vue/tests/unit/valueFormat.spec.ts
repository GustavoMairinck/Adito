import { describe, expect, it } from 'vitest'
import { axisKind, formatValue, valueKind } from '@/common/utils/valueFormat'

describe('common/utils/valueFormat', () => {
  it('valueKind separa dinheiro, percentual e contagem pelo nome', () => {
    expect(valueKind('Investimento Total')).toBe('money')
    expect(valueKind('valor_pago')).toBe('money')
    expect(valueKind('Taxa de Conclusão')).toBe('percent')
    expect(valueKind('Total Grupos')).toBe('number')
  })

  it('axisKind só usa R$ quando todas as séries são dinheiro', () => {
    expect(axisKind(['Valor Pago', 'Custo Total'])).toBe('money')
    expect(axisKind(['Valor Pago', 'Total Grupos'])).toBe('number')
  })

  it('formatValue mostra o valor exato no tooltip e o curto no eixo', () => {
    expect(formatValue(1363864, 'money', true)).toMatch(/R\$\s?1\.363\.864,00/)
    expect(formatValue(1400000, 'money')).toBe('R$ 1,4 mi')
    expect(formatValue(9263, 'number', true)).toBe('9.263')
    expect(formatValue(71, 'number')).toBe('71')
    expect(formatValue(12.34, 'percent')).toBe('12,3%')
  })

  it('formatValue não extrai número de texto nem formata vazio ou booleano', () => {
    expect(formatValue('2024 - Sem custo', 'money')).toBe('2024 - Sem custo')
    expect(formatValue('', 'money')).toBe('')
    expect(formatValue(true, 'money')).toBe('true')
    expect(formatValue(null, 'percent')).toBe('')
    expect(formatValue('1500', 'money', true)).toMatch(/R\$\s?1\.500,00/)
  })
})
