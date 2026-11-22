import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import KPICard from '@/modules/dashboard/components/KPICard.vue'

describe('modules/dashboard/components/KPICard.vue', () => {
  it('renderiza título, valor, subtítulo e tendência positiva/negativa corretamente', () => {
    const positive = mount(KPICard, {
      props: {
        title: 'Investimento estimado',
        value: 'R$ 320.000,00',
        subtitle: 'Soma de todos os projetos',
        trend: { value: '+12%', positive: true },
      },
      global: { directives: { motion: {} } },
    })

    expect(positive.text()).toContain('Investimento estimado')
    expect(positive.text()).toContain('R$ 320.000,00')
    expect(positive.text()).toContain('Soma de todos os projetos')
    expect(positive.text()).toContain('↑ +12%')

    const negative = mount(KPICard, {
      props: {
        title: 'Projetos',
        value: 0,
        trend: { value: '-5%', positive: false },
      },
      global: { directives: { motion: {} } },
    })

    expect(negative.text()).toContain('0')
    expect(negative.text()).toContain('↓ -5%')
  })
})
