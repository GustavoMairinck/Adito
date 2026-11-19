import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { mount } from '@vue/test-utils'

const callMock = vi.fn()

vi.mock('@/common/api/core', () => ({
  call: (...args: unknown[]) => callMock(...args),
}))

import { useDashboardData } from '@/modules/dashboard/composables/useDashboardData'

function mountDashboardComposable() {
  let exposed!: ReturnType<typeof useDashboardData>
  const Comp = defineComponent({
    setup() {
      exposed = useDashboardData()
      return () => null
    },
  })
  const wrapper = mount(Comp)
  return { wrapper, ...exposed }
}

describe('modules/dashboard/composables/useDashboardData', () => {
  beforeEach(() => {
    callMock.mockReset()
    sessionStorage.clear()
  })

  it('fetchData consulta KPIs, top_projects e charts enviando apenas filtros preenchidos', async () => {
    callMock.mockImplementation(async (method: string) => {
      if (method === 'dashboard.kpis') return { total_investido: 'R$ 100.000,00', projetos_ativos: 42 }
      if (method === 'dashboard.top_projects') return [{ nome: 'Projeto Alfa', valor: 50000 }]
      if (method === 'dashboard.charts') return { por_ano: [{ ano: 2024, total: 50000 }], mensal: [], ano_vigente: 2026 }
      return null
    })

    const { filtros, kpis, projects, charts, loading, updateFilters, wrapper } = mountDashboardComposable()

    updateFilters({ ano: '2024', area: 'Engenharias' })
    await vi.waitFor(() => expect(loading.value).toBe(false))

    expect(filtros.ano).toBe('2024')
    expect(JSON.parse(sessionStorage.getItem('dashboard_filtros') || '{}')).toMatchObject({
      ano: '2024',
      area: 'Engenharias',
    })
    expect(callMock).toHaveBeenCalledWith(
      'dashboard.kpis',
      { ano: '2024', area: 'Engenharias' },
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
    expect(kpis.value.projetos_ativos).toBe(42)
    expect(projects.value).toHaveLength(1)
    expect(charts.value.por_ano).toHaveLength(1)
    wrapper.unmount()
  })

  it('toggleFilter aplica e limpa o filtro alternadamente', async () => {
    callMock.mockResolvedValue({})
    const { filtros, toggleFilter, wrapper } = mountDashboardComposable()

    toggleFilter('ano', 2024)
    expect(filtros.ano).toBe('2024')

    toggleFilter('ano', 2024)
    expect(filtros.ano).toBe('')
    wrapper.unmount()
  })

  it('restaura filtros salvos previamente no sessionStorage', () => {
    sessionStorage.setItem(
      'dashboard_filtros',
      JSON.stringify({ ano: '2025', area: '', modalidade: 'PIBIC', status: '', projeto: '' }),
    )
    const { filtros, wrapper } = mountDashboardComposable()
    expect(filtros.ano).toBe('2025')
    expect(filtros.modalidade).toBe('PIBIC')
    wrapper.unmount()
  })
})
