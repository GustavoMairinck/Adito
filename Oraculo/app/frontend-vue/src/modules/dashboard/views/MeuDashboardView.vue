<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  AlertCircle,
  AlertTriangle,
  AreaChart,
  BarChart2,
  BarChartHorizontal,
  CheckCircle2,
  GripVertical,
  LayoutGrid,
  Loader2,
  Lock,
  PanelBottom,
  PanelLeft,
  PanelRight,
  PanelTop,
  Pencil,
  PieChart,
  RefreshCw,
  Table,
  Trash2,
  TrendingUp,
  X,
  Minimize2
} from 'lucide-vue-next'
import VueApexCharts from 'vue3-apexcharts'
import type { ApexOptions } from 'apexcharts'

import ConfirmModal from '@/common/components/feedback/ConfirmModal.vue'
import { usePersonalDashboard, type Widget } from '@/modules/dashboard/composables/usePersonalDashboard'
import WidgetTable from '@/modules/dashboard/components/WidgetTable.vue'
import { GridLayout, GridItem } from 'grid-layout-plus'

const {
  widgets,
  widgetData,
  loading,
  fetchWidgets,
  refreshWidgetData,
  updateWidget,
  updateWidgetsBulk,
  deleteWidget
} = usePersonalDashboard()

// --- Grid Size Helpers ---

type GridDimensions = {
  w: number
  h: number
}

const MIN_W_METRIC = 4
const MIN_H_METRIC = 6
const MIN_W_TABLE = 6
const MIN_H_TABLE = 8
const MIN_W_CHART = 6
const MIN_H_CHART = 12

const getMinDimensions = (chartType: string, size?: string) => {
  if (chartType === 'metric_card') return { minW: MIN_W_METRIC, minH: MIN_H_METRIC }
  if (chartType === 'table') return size === 'small'
    ? { minW: 5, minH: MIN_H_CHART }
    : { minW: MIN_W_TABLE, minH: MIN_H_TABLE }
  if (size === 'small') return { minW: 5, minH: MIN_H_CHART }
  return { minW: MIN_W_CHART, minH: MIN_H_CHART }
}

const clampGridDimensions = (dims: GridDimensions, chartType: string, size?: string): GridDimensions => {
  const mins = getMinDimensions(chartType, size)
  return {
    w: Math.max(mins.minW, Math.min(12, dims.w)),
    h: Math.max(mins.minH, dims.h)
  }
}

const getNamedGridDimensions = (size: string, chartType: string): GridDimensions => {
  const isMetric = chartType === 'metric_card'

  if (size === 'small') {
    return { w: isMetric ? 4 : 5, h: isMetric ? 7 : 12 }
  }

  if (size === 'medium') {
    return { w: isMetric ? 5 : 6, h: isMetric ? 7 : 12 }
  }

  if (size === 'large') {
    return { w: isMetric ? 6 : 9, h: isMetric ? 8 : 14 }
  }

  if (size === 'full') {
    return { w: 12, h: isMetric ? 10 : 16 }
  }

  return { w: isMetric ? 5 : 6, h: isMetric ? 7 : 12 }
}

const parseCustomGridDimensions = (size: string, chartType: string): GridDimensions | null => {
  if (!size?.includes?.(':')) return null

  const [rawW, rawH] = size.split(':').map((value: string) => Number.parseInt(value, 10))
  if (!Number.isFinite(rawW) || !Number.isFinite(rawH)) return null

  if (rawW <= 12 && rawH <= 40) {
    return clampGridDimensions({ w: rawW, h: rawH }, chartType, size)
  }

  return clampGridDimensions(
    {
      w: Math.round(rawW / 100),
      h: Math.round((rawH + 10) / 40)
    },
    chartType,
    size
  )
}

const getGridDimensionsFromSize = (size: string, chartType: string) => {
  return clampGridDimensions(
    parseCustomGridDimensions(size, chartType) || getNamedGridDimensions(size, chartType),
    chartType,
    size
  )
}

const getWidgetGridDimensions = (widget: Widget): GridDimensions => {
  if ((widget.grid_w ?? 0) > 0 && (widget.grid_h ?? 0) > 0) {
    return clampGridDimensions({ w: widget.grid_w ?? 0, h: widget.grid_h ?? 0 }, widget.chart_type, widget.size)
  }

  return getGridDimensionsFromSize(widget.size || 'medium', widget.chart_type)
}

const buildLayoutItem = (
  widget: Widget,
  overrides: Partial<{ x: number; y: number; w: number; h: number }> = {}
) => {
  const mins = getMinDimensions(widget.chart_type, widget.size)
  const widgetDims = getWidgetGridDimensions(widget)
  const dims = clampGridDimensions(
    {
      w: overrides.w ?? widgetDims.w,
      h: overrides.h ?? widgetDims.h
    },
    widget.chart_type,
    widget.size
  )

  return {
    x: overrides.x ?? (widget.grid_x !== undefined ? widget.grid_x : 0),
    y: overrides.y ?? (widget.grid_y !== undefined ? widget.grid_y : 0),
    w: dims.w,
    h: dims.h,
    i: widget.id,
    minW: mins.minW,
    minH: mins.minH,
    widget
  }
}

const buildAutoLayout = (items: Widget[]) => {
  let currentX = 0
  let currentY = 0
  let currentRowHeight = 0

  return items.map((widget: Widget) => {
    const dims = getWidgetGridDimensions(widget)

    if (currentX + dims.w > 12) {
      currentX = 0
      currentY += currentRowHeight
      currentRowHeight = 0
    }

    const item = buildLayoutItem(widget, {
      x: currentX,
      y: currentY,
      w: dims.w,
      h: dims.h
    })

    currentX += item.w
    currentRowHeight = Math.max(currentRowHeight, item.h)
    return item
  })
}

const layoutItemsOverlap = (
  first: { x: number; y: number; w: number; h: number },
  second: { x: number; y: number; w: number; h: number }
) => {
  return (
    first.x < second.x + second.w &&
    first.x + first.w > second.x &&
    first.y < second.y + second.h &&
    first.y + first.h > second.y
  )
}

const normalizeResolvedLayout = (items: Widget[]) => {
  const placedItems: any[] = []

  const widgetsByPosition = [...items].sort((a: Widget, b: Widget) => {
    const yDiff = (a.grid_y ?? 0) - (b.grid_y ?? 0)
    if (yDiff !== 0) return yDiff
    const xDiff = (a.grid_x ?? 0) - (b.grid_x ?? 0)
    if (xDiff !== 0) return xDiff
    return 0
  })

  for (const widget of widgetsByPosition) {
    const widgetDims = getWidgetGridDimensions(widget)
    const nextItem = buildLayoutItem(widget, {
      x: Math.max(0, Math.min(12 - widgetDims.w, widget.grid_x ?? 0)),
      y: Math.max(0, widget.grid_y ?? 0),
      w: widgetDims.w,
      h: widgetDims.h
    })

    let hasCollision = true
    while (hasCollision) {
      const conflictingItem = placedItems.find((placedItem: any) => layoutItemsOverlap(nextItem, placedItem))
      if (!conflictingItem) {
        hasCollision = false
      } else {
        nextItem.y = conflictingItem.y + conflictingItem.h
      }
    }

    placedItems.push(nextItem)
  }

  return placedItems
}

// --- Widget Order Persistence ---

const sortWidgetsBySavedOrder = (fetchedWidgets: Widget[]) => {
  const savedOrderRaw = localStorage.getItem('dashboard_widget_order')
  if (!savedOrderRaw) return fetchedWidgets

  try {
    const orderIds = JSON.parse(savedOrderRaw) as string[]
    return [...fetchedWidgets].sort((a: Widget, b: Widget) => {
      const indexA = orderIds.indexOf(a.id)
      const indexB = orderIds.indexOf(b.id)

      if (indexA === -1 && indexB === -1) return 0
      if (indexA === -1) return 1
      if (indexB === -1) return -1
      return indexA - indexB
    })
  } catch {
    return fetchedWidgets
  }
}

const loadDash = async () => {
  await fetchWidgets()
  const hasGridPositions = widgets.value.some((w: Widget) => w.grid_x || w.grid_y)
  if (!hasGridPositions) {
    widgets.value = sortWidgetsBySavedOrder(widgets.value)
  }
}

// --- Layout State ---

const layout = ref<any[]>([])
const isEditingLayout = ref(false)
const originalLayout = ref<Widget[]>([])

watch(widgets, (newWidgets: Widget[]) => {
  if (!isEditingLayout.value) {
    const needsAutoLayout = newWidgets.length > 1 && newWidgets.every((w: Widget) => !w.grid_x && !w.grid_y)

    if (needsAutoLayout) {
      layout.value = buildAutoLayout(newWidgets)
    } else {
      layout.value = normalizeResolvedLayout(newWidgets)
    }
  }
}, { immediate: true, deep: true })

const onLayoutUpdated = (newLayout: any[]) => {
  newLayout.forEach((item: any) => {
    const w = widgets.value.find((widget: Widget) => widget.id === item.i)
    if (w) {
      w.grid_x = item.x
      w.grid_y = item.y
      w.grid_w = item.w
      w.grid_h = item.h
    }
  })
}

onMounted(loadDash)

// --- Delete Modal ---

const deleteModal = ref<{ isOpen: boolean; widgetId: string | null }>({ isOpen: false, widgetId: null })

// --- Edit Mode ---

const toggleEditMode = async () => {
  if (isEditingLayout.value) {
    isEditingLayout.value = false
    showToast('Layout travado e salvo com sucesso!', 'success')

    // Persist dimensions and positions
    const updates = widgets.value.map((w: Widget) => {
      const sizeStr = `${w.grid_w}:${w.grid_h}`
      return {
        id: w.id,
        updates: {
          grid_x: w.grid_x,
          grid_y: w.grid_y,
          grid_w: w.grid_w,
          grid_h: w.grid_h,
          size: sizeStr
        }
      }
    })

    const orderIds = widgets.value.map((w: Widget) => w.id)
    localStorage.setItem('dashboard_widget_order', JSON.stringify(orderIds))

    try {
      await updateWidgetsBulk(updates)
    } catch (e) {
       showToast('Falha ao sincronizar layout no servidor', 'error')
    }
  } else {
    // Entering Edit Mode
    originalLayout.value = JSON.parse(JSON.stringify(widgets.value))
    isEditingLayout.value = true
    showToast('Modo organizacao habilitado.', 'success')
  }
}

const cancelEdit = () => {
  if (!isEditingLayout.value) return
  widgets.value = JSON.parse(JSON.stringify(originalLayout.value))
  isEditingLayout.value = false

  layout.value = widgets.value.map((w: Widget) => buildLayoutItem(w))

  showToast('Alteracoes de layout canceladas.', 'error')
}

// --- Layout Presets ---

const applyLayoutPreset = async (preset: string) => {
  if (widgets.value.length === 0) return

  const descriptions: Record<string, string> = {
    metrics_top: 'Metricas e KPIs foram movidos para o topo do painel.',
    charts_top: 'Graficos visuais agora estao em destaque no topo.',
    metrics_left: 'Metricas a esquerda e graficos a direita.',
    metrics_right: 'Graficos a esquerda e metricas a direita.',
    tables_top: 'Tabelas de dados brutos movidas para a area principal.'
  }

  const metrics = widgets.value.filter((w: Widget) => w.chart_type === 'metric_card')
  const charts = widgets.value.filter((w: Widget) => ['bar', 'line', 'horizontal_bar', 'area', 'pie'].includes(w.chart_type))
  const tables = widgets.value.filter((w: Widget) => w.chart_type === 'table')
  const others = widgets.value.filter((w: Widget) => !['metric_card', 'bar', 'line', 'horizontal_bar', 'area', 'pie', 'table'].includes(w.chart_type))

  let orderedList: Widget[] = []

  if (preset === 'metrics_top') {
    orderedList = [...metrics, ...charts, ...tables, ...others]
  } else if (preset === 'charts_top') {
    orderedList = [...charts, ...tables, ...metrics, ...others]
  } else if (preset === 'metrics_left') {
    orderedList = [...metrics, ...charts, ...tables, ...others]
  } else if (preset === 'metrics_right') {
    orderedList = [...charts, ...tables, ...metrics, ...others]
  } else if (preset === 'tables_top') {
    orderedList = [...tables, ...charts, ...metrics, ...others]
  }

  const getPresetDimensions = (widget: Widget): GridDimensions => {
    if (widget.chart_type === 'table') return getGridDimensionsFromSize('medium', 'table')
    if (widget.chart_type === 'metric_card') return getGridDimensionsFromSize('medium', 'metric_card')
    return getGridDimensionsFromSize('medium', widget.chart_type)
  }

  let newOrder: Widget[] = []

  if (preset === 'metrics_left' || preset === 'metrics_right') {
    const metricColumnWidth = 4
    const contentColumnWidth = 12 - metricColumnWidth
    const metricColumnX = preset === 'metrics_left' ? 0 : contentColumnWidth
    const contentColumnX = preset === 'metrics_left' ? metricColumnWidth : 0
    let metricY = 0
    let contentY = 0

    newOrder = orderedList.map((widget: Widget) => {
      const isMetric = widget.chart_type === 'metric_card'
      const defaultDims = getPresetDimensions(widget)
      const grid_w = isMetric ? metricColumnWidth : contentColumnWidth
      const grid_h = isMetric ? defaultDims.h : Math.max(defaultDims.h, 12)
      const grid_x = isMetric ? metricColumnX : contentColumnX
      const grid_y = isMetric ? metricY : contentY

      if (isMetric) {
        metricY += grid_h
      } else {
        contentY += grid_h
      }

      return {
        ...widget,
        grid_x,
        grid_y,
        grid_w,
        grid_h,
        size: `${grid_w}:${grid_h}`
      }
    })
  } else {
    const orderedWidgets = orderedList.map((widget: Widget) => {
      const dims = getPresetDimensions(widget)
      return {
        ...widget,
        grid_w: dims.w,
        grid_h: dims.h,
        size: `${dims.w}:${dims.h}`
      }
    })

    const presetLayout = buildAutoLayout(orderedWidgets)
    newOrder = presetLayout.map((item: any) => ({
      ...item.widget,
      grid_x: item.x,
      grid_y: item.y,
      grid_w: item.w,
      grid_h: item.h,
      size: `${item.w}:${item.h}`
    }))
  }

  if (!isEditingLayout.value) {
    originalLayout.value = JSON.parse(JSON.stringify(widgets.value))
    isEditingLayout.value = true
  }

  widgets.value = newOrder

  layout.value = newOrder.map((w: Widget) => buildLayoutItem(w))

  const orderIds = newOrder.map((w: Widget) => w.id)
  localStorage.setItem('dashboard_widget_order', JSON.stringify(orderIds))

  const updates = newOrder.map((w: Widget) => ({
    id: w.id,
    updates: {
      grid_x: w.grid_x,
      grid_y: w.grid_y,
      grid_w: w.grid_w,
      grid_h: w.grid_h,
      size: w.size
    }
  }))
  try {
    await updateWidgetsBulk(updates)
  } catch (e) {
    console.error('Erro ao salvar tamanhos do preset', e)
  }

  const msg = descriptions[preset] || 'Padrao aplicado temporariamente.'
  showToast(`${msg} Clique em Travar para salvar.`, 'success')
}

// --- Toast ---

const toast = ref<{ type: 'success' | 'error'; message: string } | null>(null)
const isSyncingAll = ref(false)
const syncingWidgetIds = ref<string[]>([])

const showToast = (message: string, type: 'success' | 'error') => {
  toast.value = { message, type }
  window.setTimeout(() => {
    if (toast.value?.message === message) toast.value = null
  }, 3500)
}

// --- Sync / Refresh ---

const handleSyncAll = async () => {
  if (isSyncingAll.value) return
  isSyncingAll.value = true
  try {
    syncingWidgetIds.value = widgets.value.map((widget: Widget) => widget.id)
    await loadDash()
    showToast('Dados atualizados com o banco.', 'success')
  } catch {
    showToast('Falha ao sincronizar os widgets.', 'error')
  } finally {
    window.setTimeout(() => {
      isSyncingAll.value = false
      syncingWidgetIds.value = []
    }, 350)
  }
}

const handleForceRefresh = async (widgetId: string) => {
  try {
    if (!syncingWidgetIds.value.includes(widgetId)) {
      syncingWidgetIds.value = [...syncingWidgetIds.value, widgetId]
    }
    widgetData.value[widgetId] = null
    await refreshWidgetData(widgetId)
    showToast('Widget atualizado com sucesso.', 'success')
  } catch {
    showToast('Erro ao forcar sincronizacao do widget.', 'error')
  } finally {
    syncingWidgetIds.value = syncingWidgetIds.value.filter((id: string) => id !== widgetId)
  }
}

// --- Widget Update / Delete ---

const handleUpdateType = async (widgetId: string, newType: Widget['chart_type']) => {
  const widget = widgets.value.find((w: Widget) => w.id === widgetId)
  let updates: Partial<Widget> = { chart_type: newType }

  if (widget && newType === 'pie' && !canUsePieChart(widget)) {
    showToast('Grafico de pizza so pode ser usado quando existe uma unica serie de valores.', 'error')
    return
  }

  if (widget) {
    widget.chart_type = newType
    const dims = getWidgetGridDimensions(widget)
    widget.grid_w = dims.w
    widget.grid_h = dims.h
    updates = {
      ...updates,
      grid_w: dims.w,
      grid_h: dims.h,
      size: `${dims.w}:${dims.h}`
    }
  }
  try {
    await updateWidget(widgetId, updates)
    showToast('Visual do widget atualizado.', 'success')
  } catch {
    showToast('Falha ao atualizar visual.', 'error')
  }
}

const handleUpdateWidget = async (widgetId: string, updates: Partial<Widget>) => {
  if (updates.size) {
    const widget = widgets.value.find((w: Widget) => w.id === widgetId)
    if (widget) {
      const dims = getGridDimensionsFromSize(updates.size, widget.chart_type)
      updates.grid_w = dims.w
      updates.grid_h = dims.h

      const layoutItem = layout.value.find((item: any) => item.i === widgetId)
      if (layoutItem) {
        layoutItem.w = dims.w
        layoutItem.h = dims.h
      }
    }
  }
  try {
    await updateWidget(widgetId, updates)
  } catch {
    showToast('Falha ao atualizar widget.', 'error')
  }
}

const requestDelete = (widgetId: string) => {
  deleteModal.value = { isOpen: true, widgetId }
}

const confirmDelete = async () => {
  const widgetId = deleteModal.value.widgetId
  if (!widgetId) return
  try {
    await deleteWidget(widgetId)
    showToast('Analise removida do painel.', 'success')
  } catch {
    showToast('Falha ao excluir.', 'error')
  } finally {
    deleteModal.value = { isOpen: false, widgetId: null }
  }
}

// --- Theme ---

const isDark = ref(false)
let themeObserver: MutationObserver | null = null

onMounted(() => {
  if (typeof document !== 'undefined') {
    isDark.value = document.documentElement.classList.contains('dark')
    themeObserver = new MutationObserver(() => {
      isDark.value = document.documentElement.classList.contains('dark')
    })
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
  }
})

onBeforeUnmount(() => {
  themeObserver?.disconnect()
})

// --- Chart Data Processing ---

const expandedWidgets = ref<Record<string, boolean>>({})

type DashboardChartPoint = {
  x: string
  values: Record<string, number>
  total: number
}

type DashboardChartSeries = {
  name: string
  data: number[]
}

type DashboardChartModel = {
  categories: string[]
  series: DashboardChartSeries[]
  dimensionLabel: string
}

const parseNumericValue = (value: unknown) => {
  const parsed = Number.parseFloat(String(value ?? ''))
  return Number.isFinite(parsed) ? parsed : null
}

const normalizeSeriesLabel = (value: string) => {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (char: string) => char.toUpperCase())
}

const getChartDimensionKey = (data: Array<Record<string, any>>) => {
  if (!Array.isArray(data) || data.length === 0) return null

  const keys = Object.keys(data[0] || {})
  const nonNumericKey = keys.find((key: string) =>
    data.some((row: Record<string, any>) => {
      const value = row[key]
      if (value === null || value === undefined || value === '') return false
      return parseNumericValue(value) === null
    })
  )

  return nonNumericKey || keys[0] || null
}

const getChartMetricKeys = (data: Array<Record<string, any>>) => {
  if (!Array.isArray(data) || data.length === 0) return []
  const keys = Object.keys(data[0] || {})
  const dimensionKey = getChartDimensionKey(data)

  return keys.filter((key: string) => {
    if (key === dimensionKey) return false
    return data.some((row: Record<string, any>) => parseNumericValue(row[key]) !== null)
  })
}

const getBaseChartPoints = (widget: Widget): DashboardChartPoint[] => {
  const data = widgetData.value[widget.id]
  if (!Array.isArray(data)) return []

  const dimensionKey = getChartDimensionKey(data)
  const metricKeys = getChartMetricKeys(data)

  return data.map((row: Record<string, any>, index: number) => {
    const values = Object.fromEntries(
      metricKeys.map((key: string) => [key, parseNumericValue(row[key]) ?? 0])
    )

    return {
      x: String((dimensionKey ? row[dimensionKey] : null) || `Item ${index}`),
      values,
      total: Object.values(values).reduce((sum: number, current: number) => sum + current, 0)
    }
  })
}

const hasOthersOption = (widget: Widget) => {
  const points = getBaseChartPoints(widget)
  if (points.length <= 1) return false

  // Se a quantidade de elementos for menor ou igual ao limite configurado (se limit_rows > 0), não precisa agrupar.
  const limit = widget.limit_rows && widget.limit_rows > 0 ? widget.limit_rows : Infinity
  if (points.length <= limit) return false

  const maxTotal = Math.max(...points.map((point: DashboardChartPoint) => point.total))
  if (maxTotal <= 0) return false

  const threshold = maxTotal * 0.05
  const smallCount = points.filter((point: DashboardChartPoint) => point.total > 0 && point.total < threshold).length
  const zeroCount = points.filter((point: DashboardChartPoint) => point.total === 0).length
  return smallCount >= 1 || zeroCount > 0
}

const getChartModel = (widget: Widget): DashboardChartModel => {
  const metricKeys = getChartMetricKeys(widgetData.value[widget.id] || [])
  let points = getBaseChartPoints(widget)

  if (widget.sort_order === 'asc') points = points.sort((a: DashboardChartPoint, b: DashboardChartPoint) => a.total - b.total)
  if (widget.sort_order === 'desc') points = points.sort((a: DashboardChartPoint, b: DashboardChartPoint) => b.total - a.total)

  if (hasOthersOption(widget) && !expandedWidgets.value[widget.id]) {
    const maxTotal = Math.max(...points.map((point: DashboardChartPoint) => point.total))
    const threshold = maxTotal * 0.05
    const largeItems = points.filter((point: DashboardChartPoint) => point.total >= threshold)
    const smallItems = points.filter((point: DashboardChartPoint) => point.total < threshold)

    if (smallItems.length > 0 && largeItems.length > 0) {
      const groupedValues = Object.fromEntries(metricKeys.map((key: string) => [key, 0]))

      for (const item of smallItems) {
        for (const key of metricKeys) {
          groupedValues[key] = (groupedValues[key] || 0) + (item.values[key] || 0)
        }
      }

      points = [
        ...largeItems,
        {
          x: 'Outros',
          values: groupedValues,
          total: Object.values(groupedValues).reduce((sum: number, current: number) => sum + current, 0)
        }
      ]
    }
  }

  if (widget.limit_rows && widget.limit_rows > 0) {
    points = points.slice(0, widget.limit_rows)
  }

  return {
    categories: points.map((point: DashboardChartPoint) => point.x),
    series: metricKeys.map((key: string) => ({
      name: normalizeSeriesLabel(key),
      data: points.map((point: DashboardChartPoint) => point.values[key] || 0)
    })),
    dimensionLabel: normalizeSeriesLabel(getChartDimensionKey(widgetData.value[widget.id] || []) || 'Categoria')
  }
}

const displayedChartHasOthersBar = (widget: Widget) => {
  return getChartModel(widget).categories.includes('Outros')
}

const formatAxisCurrency = (value: any) => {
  const num = Number.parseFloat(String(value || 0))
  if (Number.isNaN(num)) return value
  if (Math.abs(num) >= 1_000_000) return `R$ ${(num / 1_000_000).toFixed(1)}M`
  if (Math.abs(num) >= 1_000) return `R$ ${(num / 1_000).toFixed(0)}K`
  return `R$ ${num.toFixed(0)}`
}

const truncateLabel = (value: string, limit = 18) => {
  if (!value) return ''
  return value.length > limit ? `${value.slice(0, limit)}...` : value
}

const getChartDensitySettings = (widget: Widget, categoryCount: number) => {
  const dims = getWidgetGridDimensions(widget)
  const chartIsWide = dims.w >= 8
  const chartIsTall = dims.h >= 12
  const fontSize = categoryCount > 35 ? '8px' : categoryCount > 20 ? '9px' : '10px'
  const rotate = categoryCount > 25 ? -60 : categoryCount > 12 ? -50 : -35
  const labelLimit = categoryCount > 35 ? 10 : categoryCount > 20 ? 14 : 20
  const maxHeight = chartIsTall ? 140 : 120

  return {
    chartIsWide,
    chartIsTall,
    fontSize,
    rotate,
    labelLimit,
    maxHeight
  }
}

const isChartable = (widgetId: string) => {
  const data = widgetData.value[widgetId]
  if (!Array.isArray(data) || data.length === 0) return false
  const firstRow = data[0]
  const values = Object.values(firstRow)
  if (values.length < 2) return false

  // Verifica especificamente se a segunda coluna tem dados numéricos válidos
  // (getParsedData usa a segunda coluna como o valor 'y')
  return getChartMetricKeys(data).length > 0
}

const canUsePieChart = (widget: Widget) => {
  if (!isChartable(widget.id)) return false
  return getChartModel(widget).series.length === 1
}

const canSwitchVisualization = (widget: Widget) => {
  if (widget.chart_type === 'metric_card') return false
  return isChartable(widget.id)
}

const getProcessedData = (widget: Widget) => {
  const data = widgetData.value[widget.id]
  if (!Array.isArray(data)) return []

  let processed = [...data]

  if (widget.sort_order && widget.sort_order !== 'none') {
    processed.sort((a: Record<string, any>, b: Record<string, any>) => {
      const valA = Number.parseFloat(String(Object.values(a)[1] || 0)) || 0
      const valB = Number.parseFloat(String(Object.values(b)[1] || 0)) || 0
      return widget.sort_order === 'asc' ? valA - valB : valB - valA
    })
  }

  if (widget.limit_rows && widget.limit_rows > 0) {
    processed = processed.slice(0, widget.limit_rows)
  }

  return processed
}

// --- Tooltip Builder ---

const buildChartTooltip = (
  dimensionLabel: string,
  label: string,
  rows: Array<{ name: string; value: number; color: string }>
) => {
  const bg = isDark.value ? '#161d27' : '#ffffff'
  const border = isDark.value ? 'rgba(99,143,255,0.12)' : 'rgba(30,63,189,0.10)'
  const text = isDark.value ? '#e8edf5' : '#0f1923'
  const muted = isDark.value ? '#9baabf' : '#4a5568'
  const content = rows.map((row: any) => `
      <div class="flex items-center justify-between gap-4 mt-1.5">
        <div class="flex items-center gap-1.5">
          <span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:${row.color};flex-shrink:0;"></span>
          <span style="color:${muted};" class="text-xs font-medium">${row.name}</span>
        </div>
        <span class="font-bold text-sm" style="color:${row.color}">${formatAxisCurrency(row.value)}</span>
      </div>
    `).join('')
  return `
    <div style="background:${bg}; border:1px solid ${border}; color:${text}; box-shadow:rgba(0,0,0,0.12) 0px 6px 16px; min-width:200px; padding:12px 16px; border-radius:10px;">
      <div style="color:${muted}; font-size:11px; font-weight:500; margin-bottom:4px;">${dimensionLabel}</div>
      <div style="font-weight:600; font-size:13px; line-height:1.3; margin-bottom:8px; padding-bottom:8px; border-bottom:1px solid ${border};">${label}</div>
      ${content}
    </div>
  `
}

// --- Chart Options ---

const getChartOptions = (widget: Widget): ApexOptions => {
  const chartType = widget.chart_type
  const model = getChartModel(widget)
  const categories = model.categories
  const seriesColors = ['#2248d4', '#2e7d32', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16']

  // === PIZZA: config completamente separada ===
  if (chartType === 'pie') {
    return {
      chart: {
        type: 'pie' as any,
        toolbar: { show: false },
        fontFamily: 'IBM Plex Sans, system-ui, sans-serif',
        background: 'transparent',
        animations: { enabled: true, speed: 400 },
        events: {
          dataPointSelection: (_event: any, _chartContext: any, config?: any) => {
            const label = categories[config?.dataPointIndex ?? -1]
            if (label === 'Outros') {
              expandedWidgets.value[widget.id] = true
            }
          }
        }
      },
      labels: categories,
      dataLabels: { enabled: true },
      tooltip: {
        theme: isDark.value ? 'dark' : 'light',
        custom: ({ series, seriesIndex, w }: any) => {
          const label = w.globals.labels[seriesIndex]
          const val = series[seriesIndex]
          const sliceColor = w.globals.colors[seriesIndex]
          return buildChartTooltip(model.dimensionLabel, label, [{ name: 'Valor', value: val, color: sliceColor }])
        }
      },
      stroke: { width: 2 },
      colors: seriesColors,
      legend: { show: false }
    }
  }

  // === BAR VERTICAL, BAR HORIZONTAL, LINE, AREA ===
  const isLine = chartType === 'line'
  const isArea = chartType === 'area'
  const isHorizontalBar = chartType === 'horizontal_bar'
  const { chartIsWide, fontSize, rotate, labelLimit, maxHeight } = getChartDensitySettings(widget, categories.length)

  // ApexCharts type: area, line, ou bar
  let apexType: string = 'bar'
  if (isLine) apexType = 'line'
  if (isArea) apexType = 'area'

  return {
    chart: {
      type: apexType as any,
      toolbar: { show: false },
      fontFamily: 'IBM Plex Sans, system-ui, sans-serif',
      background: 'transparent',
      animations: { enabled: true, speed: 400 },
      events: {
        dataPointSelection: (_event: any, _chartContext: any, config?: any) => {
          const label = categories[config?.dataPointIndex ?? -1]
          if (label === 'Outros') {
            expandedWidgets.value[widget.id] = true
          }
        },
        click: (_event: any, _chartContext: any, config?: any) => {
          if (config && config.dataPointIndex !== undefined && config.dataPointIndex !== -1) {
            const label = categories[config.dataPointIndex]
            if (label === 'Outros') {
              expandedWidgets.value[widget.id] = true
            }
          }
        },
        xAxisLabelClick: (_event: any, _chartContext: any, config?: any) => {
          if (config && config.labelIndex !== undefined) {
            const label = categories[config.labelIndex]
            if (label === 'Outros') {
              expandedWidgets.value[widget.id] = true
            }
          }
        }
      }
    },
    dataLabels: { enabled: false },
    grid: {
      borderColor: isDark.value ? 'rgba(99,143,255,0.08)' : 'rgba(30,63,189,0.08)',
      strokeDashArray: 3
    },
    xaxis: {
      categories,
      tooltip: { enabled: false },
      title: {
        text: isHorizontalBar ? 'Valor' : model.dimensionLabel,
        offsetY: isHorizontalBar ? 0 : 12,
        style: {
          fontSize: '11px',
          fontWeight: 600,
          color: isDark.value ? '#9baabf' : '#4a5568'
        }
      },
      labels: {
        show: true,
        rotate: isHorizontalBar ? 0 : rotate,
        rotateAlways: !isHorizontalBar,
        hideOverlappingLabels: false,
        trim: true,
        maxHeight,
        style: {
          fontSize: isHorizontalBar ? '10px' : fontSize,
          fontWeight: 600,
          colors: isDark.value ? '#9baabf' : '#4a5568'
        },
        formatter: (value: any) => isHorizontalBar ? formatAxisCurrency(value) : truncateLabel(String(value), labelLimit)
      },
      axisBorder: { show: false },
      axisTicks: { show: true }
    },
    yaxis: {
      title: {
        text: isHorizontalBar ? model.dimensionLabel : 'Valor',
        style: {
          fontSize: '11px',
          fontWeight: 600,
          color: isDark.value ? '#9baabf' : '#4a5568'
        }
      },
      labels: {
        show: true,
        style: {
          fontSize: '11px',
          fontWeight: 600,
          colors: isDark.value ? '#9baabf' : '#4a5568'
        },
        formatter: (value: any) => isHorizontalBar ? truncateLabel(String(value), 25) : formatAxisCurrency(value)
      }
    },
    tooltip: {
      theme: isDark.value ? 'dark' : 'light',
      shared: true,
      intersect: false,
      custom: ({ series, dataPointIndex }: any) => {
        const label = categories[dataPointIndex]
        const rows = model.series.map((serie: any, index: number) => ({
          name: serie.name,
          value: series[index]?.[dataPointIndex] ?? 0,
          color: seriesColors[index % seriesColors.length]
        }))
        return buildChartTooltip(model.dimensionLabel, label, rows)
      }
    },
    stroke: {
      curve: 'smooth',
      width: (isLine || isArea) ? 3 : 0
    },
    fill: {
      type: isArea ? 'gradient' : 'solid',
      gradient: isArea ? { shadeIntensity: 1, opacityFrom: 0.7, opacityTo: 0.3, stops: [0, 90, 100] } : undefined
    },
    markers: {
      size: (isLine || isArea) ? 4 : 0,
      hover: { size: 6 }
    },
    plotOptions: {
      bar: {
        horizontal: isHorizontalBar,
        borderRadius: 8,
        borderRadiusApplication: 'end',
        columnWidth: chartIsWide ? '76%' : '68%',
        barHeight: '70%'
      }
    },
    colors: seriesColors,
    legend: {
      show: model.series.length > 1,
      position: 'top',
      horizontalAlign: 'left',
      fontSize: '12px',
      labels: {
        colors: isDark.value ? '#9baabf' : '#4a5568'
      }
    }
  }
}

const getChartSeries = (widget: Widget) => {
  const model = getChartModel(widget)
  // Pizza: series eh array flat de numeros
  if (widget.chart_type === 'pie') return model.series[0]?.data || []
  return model.series
}

// Computes a reliable pixel height for ApexCharts based on grid item dimensions.
// height="100%" is unreliable inside flex containers; pixel values always work.
const getChartPixelHeight = (item: any): number => {
  const rowHeight = 30
  const marginY = 10
  const totalGridHeight = item.h * rowHeight + Math.max(0, item.h - 1) * marginY
  // Reserve space for the drag-handle header (~75px), footer controls (~100px), and margins/paddings (~35px)
  const reserved = 210
  return Math.max(totalGridHeight - reserved, 190)
}
</script>

<template>
  <div class="p-4 md:p-8 min-h-screen">
    <transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0 translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 translate-y-2"
    >
      <div
        v-if="toast"
        :class="[
          'fixed right-4 bottom-4 z-[70] max-w-sm rounded-2xl px-4 py-3 shadow-2xl border flex items-start gap-3',
          toast.type === 'success'
            ? 'bg-emerald-50 border-emerald-200 text-emerald-800 dark:bg-emerald-500/10 dark:border-emerald-500/20 dark:text-emerald-300'
            : 'bg-red-50 border-red-200 text-red-800 dark:bg-red-500/10 dark:border-red-500/20 dark:text-red-300'
        ]"
      >
        <CheckCircle2 v-if="toast.type === 'success'" class="w-5 h-5 mt-0.5 shrink-0" />
        <AlertCircle v-else class="w-5 h-5 mt-0.5 shrink-0" />
        <span class="text-sm font-medium">{{ toast.message }}</span>
      </div>
    </transition>

    <!-- Header Section -->
    <div class="mb-8 flex flex-col items-start justify-between gap-6 border-b border-border-subtle pb-8 dark:border-white/5 sm:flex-row sm:items-center">
      <div>
        <h1 class="text-3xl font-semibold tracking-[-0.04em] text-primary dark:text-white md:text-4xl">
          Meu Dashboard Pessoal
        </h1>
        <p class="mt-3 max-w-lg text-sm font-medium leading-relaxed text-text-secondary dark:text-gray-400 md:text-base">
          Análises estratégicas fixadas a partir do <span class="text-accent font-bold">Chat</span> para acompanhamento em tempo real.
        </p>

        <!-- Presets de Layout -->
        <div class="mt-4 flex flex-wrap items-center gap-2">
          <span class="text-[10px] font-bold text-gray-400 uppercase tracking-wider mr-1">Padrões de Layout:</span>
          <button @click="applyLayoutPreset('metrics_top')" class="rounded-lg border border-border-subtle bg-surface p-2 text-text-secondary shadow-sm transition-colors hover:border-accent/40 hover:bg-surface-elevated/50 hover:text-accent dark:bg-slate-800" title="1. Métricas/KPIs no Topo">
            <PanelTop class="w-4 h-4" />
          </button>
          <button @click="applyLayoutPreset('charts_top')" class="rounded-lg border border-border-subtle bg-surface p-2 text-text-secondary shadow-sm transition-colors hover:border-accent/40 hover:bg-surface-elevated/50 hover:text-accent dark:bg-slate-800" title="2. Gráficos Visuais no Topo">
            <PanelBottom class="w-4 h-4" />
          </button>
          <button @click="applyLayoutPreset('metrics_left')" class="rounded-lg border border-border-subtle bg-surface p-2 text-text-secondary shadow-sm transition-colors hover:border-accent/40 hover:bg-surface-elevated/50 hover:text-accent dark:bg-slate-800" title="3. Consolidar Métricas à Esquerda">
            <PanelLeft class="w-4 h-4" />
          </button>
          <button @click="applyLayoutPreset('metrics_right')" class="rounded-lg border border-border-subtle bg-surface p-2 text-text-secondary shadow-sm transition-colors hover:border-accent/40 hover:bg-surface-elevated/50 hover:text-accent dark:bg-slate-800" title="4. Consolidar Métricas à Direita">
            <PanelRight class="w-4 h-4" />
          </button>
          <button @click="applyLayoutPreset('tables_top')" class="rounded-lg border border-border-subtle bg-surface p-2 text-text-secondary shadow-sm transition-colors hover:border-accent/40 hover:bg-surface-elevated/50 hover:text-accent dark:bg-slate-800" title="5. Destaque para Tabelas de Dados">
            <LayoutGrid class="w-4 h-4" />
          </button>
        </div>
      </div>

      <div class="flex w-full flex-col gap-4 sm:w-auto sm:flex-row">
        <button
          v-if="isEditingLayout"
          @click="cancelEdit"
          class="btn-secondary flex items-center gap-2 border-red-200 px-5 py-3.5 text-sm text-red-600 hover:border-red-300 hover:bg-red-50 dark:border-red-900/40 dark:text-red-300 dark:hover:bg-red-500/10"
        >
          <X class="w-4 h-4" />
          <span class="hidden sm:inline">Cancelar</span>
        </button>

        <button
          @click="toggleEditMode"
          :class="[
            'flex w-full items-center justify-center gap-2.5 rounded-md px-7 py-3.5 text-sm font-medium transition-colors sm:w-auto',
            isEditingLayout
              ? 'border border-[#2e7d32]/80 bg-[#2e7d32] text-white hover:bg-[#256329] dark:border-[#2e7d32]/50 dark:bg-[#2e7d32] dark:hover:bg-[#1b5e20]'
              : 'btn-secondary bg-surface dark:bg-slate-800'
          ]"
        >
          <Pencil v-if="!isEditingLayout" class="w-4 h-4" />
          <Lock v-else class="w-4 h-4" />
          <span>{{ isEditingLayout ? 'Travar Layout' : 'Editar Layout' }}</span>
        </button>

        <button
          :disabled="isSyncingAll"
          @click="handleSyncAll"
          class="btn-primary flex w-full items-center justify-center gap-2.5 overflow-hidden px-6 py-3.5 text-sm sm:w-auto sm:justify-start"
        >
          <RefreshCw
            class="w-4 h-4"
            :class="{ 'animate-spin': isSyncingAll }"
          />
          <span>{{ isSyncingAll ? 'Sincronizando...' : 'Sincronizar Tudo' }}</span>
        </button>
      </div>
    </div>

    <div v-if="loading && widgets.length === 0" class="flex justify-center p-12">
      <Loader2 class="h-8 w-8 animate-spin text-accent" />
    </div>

    <div v-else-if="widgets.length === 0" class="premium-card border-dashed p-12 text-center">
      <BarChart2 class="w-12 h-12 text-gray-400 mx-auto mb-3" />
      <h3 class="text-lg font-medium text-gray-700 dark:text-gray-200">Nenhum Card Fixado</h3>
      <p class="text-gray-500 text-sm mt-1">Pergunte algo no Chat Estrategico e clique em "Fixar no Dashboard".</p>
    </div>

    <GridLayout
      v-else
      v-model:layout="layout"
      :col-num="12"
      :row-height="30"
      :is-draggable="isEditingLayout"
      :is-resizable="isEditingLayout"
      :vertical-compact="true"
      :margin="[10, 10]"
      :use-css-transforms="true"
      @layout-updated="onLayoutUpdated"
    >
      <GridItem
        v-for="item in layout"
        :key="item.i"
        :x="item.x"
        :y="item.y"
        :w="item.w"
        :h="item.h"
        :i="item.i"
        :min-w="item.minW"
        :min-h="item.minH"
        class="premium-card relative flex flex-col overflow-hidden"
        :class="[
          syncingWidgetIds.includes(item.widget.id) ? 'ring-1 ring-accent/25 shadow-elevated' : ''
        ]"
      >
        <div
          v-if="syncingWidgetIds.includes(item.widget.id)"
          class="absolute inset-0 pointer-events-none z-10 animate-[shimmer_1.2s_linear_infinite] bg-gradient-to-r from-transparent via-accent/8 to-transparent"
        />

        <!-- Header -->
        <div :class="['group/header flex shrink-0 items-start justify-between border-b border-border-subtle bg-surface/40 p-5 dark:border-white/5', isEditingLayout ? 'cursor-move' : '']">
          <div class="pr-4 overflow-hidden flex-1 flex items-start gap-2">
            <div v-if="isEditingLayout" class="mt-1 opacity-40 hover:opacity-100 transition-opacity">
              <GripVertical class="h-4 w-4 text-text-muted" />
            </div>
            <div class="overflow-hidden">
              <h3 class="mb-1.5 flex items-center gap-2 text-base font-semibold leading-tight text-primary dark:text-white md:text-lg">
                <span class="truncate">{{ item.widget.title }}</span>
                <CheckCircle2 v-if="item.widget.status === 'OK'" class="w-4 h-4 text-green-500 shrink-0" title="Sincronizado" />
                <RefreshCw v-if="item.widget.status === 'STALE'" class="w-4 h-4 text-amber-500 shrink-0" title="Frio (No Cache)" />
                <AlertTriangle v-if="item.widget.status === 'BROKEN'" class="w-4 h-4 text-red-500 shrink-0" title="Schema ou SQL quebrado" />
              </h3>
              <div class="flex items-center gap-1.5 opacity-60">
                <span class="rounded-md border border-border-subtle bg-surface-elevated px-1.5 py-0.5 leading-none text-[9px] font-semibold uppercase tracking-[0.16em] text-text-muted">AI Insight</span>
                <p class="text-[10px] text-gray-500 dark:text-gray-400 truncate font-semibold italic flex-1" :title="item.widget.question_original">
                  "{{ item.widget.question_original }}"
                </p>
              </div>
            </div>
          </div>

          <div class="flex gap-1">
            <button
              class="rounded-md border border-transparent bg-surface-elevated p-1.5 text-text-muted transition-colors hover:border-accent/20 hover:text-accent dark:bg-white/5 dark:hover:text-white"
              title="Atualizar Dados"
              @click="handleForceRefresh(item.widget.id)"
            >
              <RefreshCw :class="['h-3.5 w-3.5', syncingWidgetIds.includes(item.widget.id) ? 'animate-spin text-accent' : '']" />
            </button>
            <button
              class="rounded-md border border-transparent bg-surface-elevated p-1.5 text-text-muted transition-colors hover:border-red-200 hover:bg-red-50 hover:text-red-500 dark:bg-white/5 dark:hover:bg-red-500/10"
              title="Excluir Painel"
              @click="requestDelete(item.widget.id)"
            >
              <Trash2 class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        <!-- Widget Content -->
        <div class="relative flex min-h-0 flex-1 flex-col justify-center overflow-hidden bg-surface px-2 py-4 dark:bg-slate-950/20">
          <div v-if="!widgetData[item.widget.id]" class="flex items-center justify-center h-full w-full min-h-[150px]">
            <Loader2 class="w-5 h-5 animate-spin text-gray-400" />
          </div>

          <div
            v-else-if="item.widget.chart_type === 'metric_card'"
            class="flex flex-col items-center justify-center p-6 h-full w-full"
          >
            <p class="eyebrow mb-2">Metrica</p>
            <h3 class="text-3xl font-semibold tracking-tight text-primary dark:text-white md:text-4xl">
              {{ Object.values(widgetData[item.widget.id][0])[0] }}
            </h3>
          </div>

          <WidgetTable
            v-else-if="item.widget.chart_type === 'table'"
            :data="getProcessedData(item.widget)"
            class="w-full h-full overflow-auto"
          />

          <div v-else class="w-full h-full flex flex-col min-h-[150px]">
            <div v-if="displayedChartHasOthersBar(item.widget) && !expandedWidgets[item.widget.id]" class="px-4 mb-2 flex flex-col sm:flex-row items-start sm:items-center justify-between text-xs shrink-0 bg-surface-elevated/30 py-2 rounded-lg border border-border-subtle/50 gap-2">
              <span class="text-text-muted font-medium flex items-center gap-2">
                <span class="text-base leading-none">&#128161;</span>
                <span class="truncate">Categorias pequenas agrupadas. Clique na coluna ou na palavra <strong>'Outros'</strong> abaixo para expandir.</span>
              </span>
            </div>

            <div
              v-if="expandedWidgets[item.widget.id] && hasOthersOption(item.widget)"
              class="px-4 mb-2 flex justify-end text-xs shrink-0"
            >
              <button
                type="button"
                class="px-3 py-1.5 bg-accent/10 text-accent hover:bg-accent hover:text-white rounded-lg font-bold transition-all flex items-center gap-1.5 border border-accent/20 hover:border-accent shadow-sm shrink-0"
                @click="expandedWidgets[item.widget.id] = false"
              >
                <Minimize2 class="w-4 h-4" />
                Reagrupar 'Outros'
              </button>
            </div>

            <VueApexCharts
              :key="`${item.widget.id}-${item.widget.chart_type}-${item.widget.limit_rows}-${item.widget.sort_order}-${isDark ? 'dark' : 'light'}-${item.w}-${item.h}`"
              width="100%"
              :height="getChartPixelHeight(item)"
              :options="getChartOptions(item.widget)"
              :series="getChartSeries(item.widget)"
              class="w-full"
            />
          </div>
        </div>

        <!-- Footer Controls -->
        <div class="flex shrink-0 flex-col gap-3 border-t border-border-subtle bg-surface/70 p-3 text-xs text-text-secondary dark:border-white/5 dark:bg-slate-900/40">
          <div class="flex justify-between items-center w-full">
            <span class="font-medium opacity-60" title="Ultima Execucao">
              Visto: {{ new Date(item.widget.last_executed_at).toLocaleTimeString('pt-BR') }}
            </span>
            <div v-if="canSwitchVisualization(item.widget)" class="flex items-center gap-1 rounded-lg bg-surface-elevated/45 p-1 dark:bg-white/5">
              <button
                :class="['rounded-md p-1.5 transition-all', item.widget.chart_type === 'bar' ? 'border border-border-subtle bg-surface text-primary shadow-premium dark:bg-slate-700 dark:text-white' : 'text-text-secondary hover:bg-surface/60 hover:text-primary dark:hover:text-white']"
                title="Barras Verticais"
                @click="handleUpdateType(item.widget.id, 'bar')"
              >
                <BarChart2 class="w-3.5 h-3.5" />
              </button>
              <button
                :class="['rounded-md p-1.5 transition-all', item.widget.chart_type === 'horizontal_bar' ? 'border border-border-subtle bg-surface text-primary shadow-premium dark:bg-slate-700 dark:text-white' : 'text-text-secondary hover:bg-surface/60 hover:text-primary dark:hover:text-white']"
                title="Barras Horizontais"
                @click="handleUpdateType(item.widget.id, 'horizontal_bar')"
              >
                <BarChartHorizontal class="w-3.5 h-3.5" />
              </button>
              <button
                :class="['rounded-md p-1.5 transition-all', item.widget.chart_type === 'line' ? 'border border-border-subtle bg-surface text-primary shadow-premium dark:bg-slate-700 dark:text-white' : 'text-text-secondary hover:bg-surface/60 hover:text-primary dark:hover:text-white']"
                title="Linhas"
                @click="handleUpdateType(item.widget.id, 'line')"
              >
                <TrendingUp class="w-3.5 h-3.5" />
              </button>
              <button
                :class="['rounded-md p-1.5 transition-all', item.widget.chart_type === 'area' ? 'border border-border-subtle bg-surface text-primary shadow-premium dark:bg-slate-700 dark:text-white' : 'text-text-secondary hover:bg-surface/60 hover:text-primary dark:hover:text-white']"
                title="Área"
                @click="handleUpdateType(item.widget.id, 'area')"
              >
                <AreaChart class="w-3.5 h-3.5" />
              </button>
              <button
                v-if="canUsePieChart(item.widget)"
                :class="['rounded-md p-1.5 transition-all', item.widget.chart_type === 'pie' ? 'border border-border-subtle bg-surface text-primary shadow-premium dark:bg-slate-700 dark:text-white' : 'text-text-secondary hover:bg-surface/60 hover:text-primary dark:hover:text-white']"
                title="Pizza"
                @click="handleUpdateType(item.widget.id, 'pie')"
              >
                <PieChart class="w-3.5 h-3.5" />
              </button>
              <button
                :class="['rounded-md p-1.5 transition-all', item.widget.chart_type === 'table' ? 'border border-border-subtle bg-surface text-primary shadow-premium dark:bg-slate-700 dark:text-white' : 'text-text-secondary hover:bg-surface/60 hover:text-primary dark:hover:text-white']"
                title="Tabela"
                @click="handleUpdateType(item.widget.id, 'table')"
              >
                <Table class="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          <div class="flex w-full items-center justify-between gap-2 border-t border-border-subtle pt-1 dark:border-gray-800">
            <div class="flex w-full flex-wrap gap-2">
              <select
                :value="item.widget.size || 'medium'"
                class="rounded-md border border-border-subtle bg-surface px-1.5 py-1 text-gray-600 outline-none transition-colors hover:border-accent/40 dark:border-gray-700 dark:bg-[#1a1a1a] dark:text-gray-300"
                title="Tamanho do Card"
                @change="handleUpdateWidget(item.widget.id, { size: ($event.target as HTMLSelectElement).value as Widget['size'] })"
              >
                <option value="small">Pequeno</option>
                <option value="medium">Padrao</option>
                <option value="large">Largo</option>
                <option value="full">Tela Cheia</option>
                <option v-if="item.widget.size?.includes?.(':') " :value="item.widget.size">Tamanho Custom</option>
              </select>

              <template v-if="item.widget.chart_type !== 'metric_card' && (item.widget.chart_type === 'table' || isChartable(item.widget.id))">
                <select
                  :value="item.widget.sort_order || 'none'"
                  class="rounded-md border border-border-subtle bg-surface px-1.5 py-1 text-gray-600 outline-none transition-colors hover:border-accent/40 dark:border-gray-700 dark:bg-[#1a1a1a] dark:text-gray-300"
                  title="Ordenacao dos Dados"
                  @change="handleUpdateWidget(item.widget.id, { sort_order: ($event.target as HTMLSelectElement).value as Widget['sort_order'] })"
                >
                  <option value="none">Original</option>
                  <option value="desc">Maior p/ Menor</option>
                  <option value="asc">Menor p/ Maior</option>
                </select>
                <select
                  :value="item.widget.limit_rows || 0"
                  class="rounded-md border border-border-subtle bg-surface px-1.5 py-1 text-gray-600 outline-none transition-colors hover:border-accent/40 dark:border-gray-700 dark:bg-[#1a1a1a] dark:text-gray-300"
                  title="Recorte (Top N)"
                  @change="handleUpdateWidget(item.widget.id, { limit_rows: parseInt(($event.target as HTMLSelectElement).value) })"
                >
                  <option :value="0">Todas Linhas</option>
                  <option :value="5">Top 5</option>
                  <option :value="10">Top 10</option>
                  <option :value="15">Top 15</option>
                </select>
              </template>
            </div>
          </div>
        </div>
      </GridItem>
    </GridLayout>

    <ConfirmModal
      :is-open="deleteModal.isOpen"
      title="Remover do Painel"
      message="Tem certeza que deseja excluir esta analise de seu dashboard? Esta acao nao pode ser desfeita."
      confirm-text="Remover"
      cancel-text="Cancelar"
      @close="deleteModal = { isOpen: false, widgetId: null }"
      @confirm="confirmDelete"
    />
  </div>
</template>

<style scoped>
@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

:deep(.custom-scrollbar::-webkit-scrollbar) {
  width: 5px;
  height: 5px;
}

:deep(.custom-scrollbar::-webkit-scrollbar-track) {
  background: transparent;
}

:deep(.custom-scrollbar::-webkit-scrollbar-thumb) {
  background: rgba(155, 155, 155, 0.2);
  border-radius: 10px;
}

:deep(.custom-scrollbar::-webkit-scrollbar-thumb:hover) {
  background: rgba(155, 155, 155, 0.4);
}

.dark :deep(.custom-scrollbar::-webkit-scrollbar-thumb) {
  background: rgba(255, 255, 255, 0.1);
}

.dark :deep(.custom-scrollbar::-webkit-scrollbar-thumb:hover) {
  background: rgba(255, 255, 255, 0.2);
}

:deep(.custom-scrollbar::-webkit-scrollbar-corner) {
  background: transparent;
}
</style>
