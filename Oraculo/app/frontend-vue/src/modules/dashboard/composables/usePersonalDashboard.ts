import { ref } from 'vue'
import httpClient from '@/common/api/httpClient'

export interface Widget {
  id: string
  title: string
  question_original: string
  chart_type: 'bar' | 'line' | 'table' | 'metric_card' | 'horizontal_bar' | 'area' | 'pie'
  size: 'small' | 'medium' | 'large' | 'full' | string
  sort_order: 'none' | 'asc' | 'desc'
  limit_rows: number
  status: 'OK' | 'STALE' | 'BROKEN'
  last_executed_at: string
  data?: any
  grid_x?: number
  grid_y?: number
  grid_w?: number
  grid_h?: number
  mode?: string
}

export interface CreateWidgetPayload {
  title: string
  question_original: string
  sql_validated?: string
  chart_type: Widget['chart_type']
  mode?: string
  cache_ttl_hours?: number
}

function authHeaders(token?: string | null) {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function usePersonalDashboard(token?: string | null) {
  const widgets = ref<Widget[]>([])
  const widgetData = ref<Record<string, any>>({})
  const loading = ref(false)

  async function fetchWidgets() {
    loading.value = true
    try {
      const res = await httpClient.get('/api/dashboard/widgets', {
        headers: authHeaders(token),
        params: { dashboard_id: 'principal' }
      })
      const data = res.data

      if (Array.isArray(data)) {
        widgets.value = data
        // Fetch specific data for each widget in background
        data.forEach(w => refreshWidgetData(w.id))
      }
    } catch (err) {
      console.error('Failed to fetch widgets:', err)
    } finally {
      loading.value = false
    }
  }

  async function refreshWidgetData(widgetId: string) {
    try {
      const res = await httpClient.get(`/api/dashboard/widgets/${widgetId}/refresh`, {
        headers: authHeaders(token)
      })
      widgetData.value[widgetId] = res.data.data || res.data

      // Update widget status if returned
      const widget = widgets.value.find(w => w.id === widgetId)
      if (widget && res.data.widget_status) {
        widget.status = res.data.widget_status
      }
    } catch (err) {
      console.error(`Failed to refresh widget ${widgetId}:`, err)
    }
  }

  async function updateWidget(widgetId: string, updates: Partial<Widget>) {
    try {
      await httpClient.put(`/api/dashboard/widgets/${widgetId}`, updates, {
        headers: authHeaders(token)
      })
      const index = widgets.value.findIndex(w => w.id === widgetId)
      if (index !== -1) {
        widgets.value[index] = { ...widgets.value[index], ...updates }
      }
    } catch (err) {
      console.error(`Failed to update widget ${widgetId}:`, err)
      throw err
    }
  }

  async function deleteWidget(widgetId: string) {
    try {
      await httpClient.delete(`/api/dashboard/widgets/${widgetId}`, {
        headers: authHeaders(token)
      })
      widgets.value = widgets.value.filter(w => w.id !== widgetId)
      delete widgetData.value[widgetId]
    } catch (err) {
      console.error(`Failed to delete widget ${widgetId}:`, err)
      throw err
    }
  }

  async function createWidget(payload: CreateWidgetPayload) {
    const res = await httpClient.post('/api/dashboard/widgets', payload, {
      headers: authHeaders(token)
    })
    return res.data
  }

  async function updateWidgetsBulk(updatesList: Array<{ id: string; updates: Partial<Widget> }>) {
    // Implementacao basica para compilar; o ideal e enviar em batch para o backend
    for (const item of updatesList) {
      await updateWidget(item.id, item.updates)
    }
  }

  return {
    widgets,
    widgetData,
    loading,
    fetchWidgets,
    refreshWidgetData,
    updateWidget,
    deleteWidget,
    createWidget,
    updateWidgetsBulk
  }
}
