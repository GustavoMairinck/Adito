import { ref, reactive, onUnmounted } from 'vue'
import { call } from '@/common/api/core'

export interface Filters {
  ano: string
  area: string
  modalidade: string
  status: string
  projeto: string
}

const FILTROS_KEY = 'dashboard_filtros'
const FILTROS_VAZIOS: Filters = { ano: '', area: '', modalidade: '', status: '', projeto: '' }

function loadSavedFilters(): Filters {
  try {
    const raw = sessionStorage.getItem(FILTROS_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return { ...FILTROS_VAZIOS }
}

export function useDashboardData() {
  const filtros = reactive<Filters>(loadSavedFilters())
  const kpis = ref<any>(null)
  const projects = ref<any[]>([])
  const charts = ref<any>({
    por_ano: [],
    mensal: [],
    ano_vigente: new Date().getFullYear(),
    anos_disponiveis: [],
    areas_disponiveis: [],
    modalidades_disponiveis: [],
    statuses_disponiveis: []
  })
  const loading = ref(false)

  let abortController: AbortController | null = null

  async function fetchData() {
    if (abortController) abortController.abort()
    abortController = new AbortController()

    loading.value = true

    const params: Record<string, string> = {}
    Object.entries(filtros).forEach(([key, value]) => {
      if (value) params[key] = value
    })
    const signal = abortController.signal

    try {
      const [kpiRes, projRes, chartRes] = await Promise.all([
        call('dashboard.kpis', params, { signal }),
        call('dashboard.top_projects', params, { signal }),
        call('dashboard.charts', params, { signal })
      ])

      kpis.value = kpiRes
      projects.value = projRes
      charts.value = chartRes
    } catch (err: any) {
      if (err.name !== 'CanceledError' && err.message !== 'canceled') {
        console.error('Dashboard fetch error:', err)
      }
    } finally {
      loading.value = false
    }
  }

  function updateFilters(newFilters: Partial<Filters>) {
    Object.assign(filtros, newFilters)
    sessionStorage.setItem(FILTROS_KEY, JSON.stringify(filtros))
    fetchData()
  }

  function toggleFilter(key: keyof Filters, value: any) {
    const valStr = String(value)
    const newValue = filtros[key] === valStr ? '' : valStr
    updateFilters({ [key]: newValue })
  }

  onUnmounted(() => {
    if (abortController) abortController.abort()
  })

  return {
    filtros,
    kpis,
    projects,
    charts,
    loading,
    fetchData,
    updateFilters,
    toggleFilter
  }
}
