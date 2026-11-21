import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import FilterBar from '@/modules/dashboard/components/FilterBar.vue'
import type { Filters } from '@/modules/dashboard/composables/useDashboardData'

const baseProps = {
  filtros: { ano: '', area: '', modalidade: '', status: '', projeto: '' } as Filters,
  anosDisponiveis: ['2024', '2023'],
  areasDisponiveis: ['Engenharias', 'Ciências Exatas'],
  modalidadesDisponiveis: ['PIBIC', 'PIBITI'],
  statusDisponiveis: ['BOLSISTA', 'VOLUNTARIO'],
}

function mountFilterBar(filtrosOverride: Partial<Filters> = {}) {
  return mount(FilterBar, {
    props: {
      ...baseProps,
      filtros: { ...baseProps.filtros, ...filtrosOverride },
    },
    global: {
      directives: {
        motion: {},
      },
    },
  })
}

describe('modules/dashboard/components/FilterBar.vue', () => {
  it('emite update:filtros ao selecionar ano e não exibe botão Limpar quando filtros estão vazios', async () => {
    const wrapper = mountFilterBar()
    expect(wrapper.find('button').exists()).toBe(false)

    const anoSelect = wrapper.findAll('select')[0]
    await anoSelect.setValue('2024')

    const emitted = wrapper.emitted('update:filtros')
    expect(emitted).toBeTruthy()
    expect(emitted![0][0]).toMatchObject({ ano: '2024' })
  })

  it('emite busca direta ao pressionar Enter e evita emissão redundante quando texto não muda', async () => {
    const wrapper = mountFilterBar({ projeto: 'Robótica' })
    const input = wrapper.find('input[placeholder="Projeto ou orientador..."]')

    await input.trigger('keydown.enter')
    expect(wrapper.emitted('update:filtros')).toBeFalsy()

    await input.setValue('Visão Computacional')
    await input.trigger('keydown.enter')
    expect(wrapper.emitted('update:filtros')![0][0]).toMatchObject({ projeto: 'Visão Computacional' })
  })

  it('exibe botão Limpar quando há filtro ativo e emite evento clear ao clicar', async () => {
    const wrapper = mountFilterBar({ ano: '2023' })
    const clearBtn = wrapper.find('button')
    expect(clearBtn.exists()).toBe(true)
    expect(clearBtn.text()).toContain('Limpar')

    await clearBtn.trigger('click')
    expect(wrapper.emitted('clear')).toHaveLength(1)
  })
})
