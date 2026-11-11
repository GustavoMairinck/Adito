<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import VueApexCharts from 'vue3-apexcharts'
import { ArrowLeftRight, Code, Database, Lightbulb, Pin, Copy, Check, Minimize2 } from 'lucide-vue-next'
import brandIcon from '@/common/assets/brand-icon.png'
import type { ApexOptions } from 'apexcharts'
import type { ChatMessage, FieldFormat } from '@/modules/chat/types'
import { renderMarkdown } from '@/modules/chat/utils/markdown'

const props = defineProps<{
  message: ChatMessage
}>()

const emit = defineEmits<{
  (e: 'toggle-sql', id: string): void
  (e: 'pin', message: ChatMessage): void
  (e: 'suggest', question: string): void
}>()

const hasRenderableTable = computed(() => {
  return !!(props.message.table && props.message.table.length > 0 && Object.values(props.message.table[0])[0] !== 'null')
})

const isDark = ref(false)
const rowLimit = ref<number | 'all'>(10)
const rowLimitOptions: Array<number | 'all'> = [5, 10, 15, 'all']
const isCopied = ref(false)
const isSqlCopied = ref(false)
let observer: MutationObserver | null = null

const bubbleRef = ref<HTMLElement | null>(null)
const isVisible = ref(false)
let scrollObserver: IntersectionObserver | null = null


const copyToClipboard = async () => {
  if (isCopied.value || !props.message.text) return
  
  let content = props.message.text
  
  // Adicionar interpretação se houver
  if (props.message.explanation) {
    content += `\n\nInterpretação: ${props.message.explanation}`
  }

  // Adicionar resultado escalar se houver
  if (props.message.isScalarResult && props.message.table?.[0]) {
    const [key, value] = Object.entries(props.message.table[0])[0]
    content += `\n\nResultado: ${formatTableValue(key, value)}`
  }

  // Adicionar dados da tabela se houver
  if (hasRenderableTable.value && !props.message.isScalarResult && props.message.table?.length) {
    const table = props.message.table
    const headers = Object.keys(table[0])
    const headerRow = `| ${headers.join(' | ')} |`
    const divider = `| ${headers.map(() => '---').join(' | ')} |`
    const rows = table
      .map(r => `| ${Object.entries(r).map(([key, value]) => formatTableValue(key, value)).join(' | ')} |`)
      .join('\n')
    content += `\n\nDados:\n${headerRow}\n${divider}\n${rows}`
  }

  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(content)
    } else {
      const textArea = document.createElement('textarea')
      textArea.value = content
      textArea.style.position = 'absolute'
      textArea.style.left = '-999999px'
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      textArea.remove()
    }
    isCopied.value = true
    setTimeout(() => {
      isCopied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy text:', err)
  }
}

const copySqlToClipboard = async () => {
  if (isSqlCopied.value || !props.message.sql) return
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(props.message.sql)
    } else {
      const textArea = document.createElement('textarea')
      textArea.value = props.message.sql
      textArea.style.position = 'absolute'
      textArea.style.left = '-999999px'
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      textArea.remove()
    }
    isSqlCopied.value = true
    setTimeout(() => {
      isSqlCopied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy SQL:', err)
  }
}

const fmt = (n: number, dec = 1) =>
  new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: dec }).format(n)

const formatNumber = (value: number) => {
  if (value === undefined || value === null || Number.isNaN(value)) return '0'
  const abs = Math.abs(value)
  if (abs >= 1_000_000_000) return `${fmt(value / 1_000_000_000)}B`
  if (abs >= 1_000_000)     return `${fmt(value / 1_000_000)}M`
  if (abs >= 1_000)         return `${fmt(value / 1_000)}K`
  return fmt(value, 2)
}

function formatDateValue(value: unknown) {
  if (value === null || value === undefined || value === '') return 'nulo'
  const text = String(value)
  const datePart = text.split('T')[0]
  if (/^\d{4}-\d{2}-\d{2}$/.test(datePart)) {
    const [year, month, day] = datePart.split('-')
    return `${day}/${month}/${year}`
  }
  return text
}

function formatTableValue(key: string | number, value: unknown) {
  if (value === null || value === undefined) return 'nulo'

  const rawFormat = props.message.fieldFormats?.[String(key)]
  const format = String(rawFormat || '').replace(/^FieldFormat\./, '').toLowerCase() as FieldFormat | ''

  if (format === 'text') return String(value)
  if (format === 'date') return formatDateValue(value)

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

const renderedText = computed(() => renderMarkdown(props.message.text || ''))

const tableRowCount = computed(() => props.message.table?.length || 0)

const displayedRowLimit = computed(() => {
  return rowLimit.value === 'all' ? tableRowCount.value : rowLimit.value
})

const displayedRows = computed(() => {
  return (props.message.table || []).slice(0, displayedRowLimit.value)
})

const showOriginalChart = ref(false)
const isChartAxisSwapped = ref(false)

const toggleChartAxes = () => {
  isChartAxisSwapped.value = !isChartAxisSwapped.value
}

const chartOrientationKey = computed(() => (isChartAxisSwapped.value ? 'horizontal' : 'vertical'))

const hasOthersOption = computed(() => {
  if (!props.message.chart) return false
  const chartData = props.message.chart
  if (!chartData.series || chartData.series.length === 0) return false
  
  // Garantir que todos os valores sejam convertidos para números reais (NaN ou undefined viram 0)
  const data = chartData.series[0].data.map(v => {
    const n = Number.parseFloat(String(v))
    return Number.isNaN(n) ? 0 : n
  })

  if (data.length <= 1) return false

  // Se a quantidade de dados for menor ou igual à quantidade limitadora (5, 10, 15 ou todos), não precisa agrupar
  const limit = typeof rowLimit.value === 'number' ? rowLimit.value : Infinity
  if (data.length <= limit) return false
  
  const maxVal = Math.max(...data)
  if (maxVal <= 0) return false
  
  // Considera "pequeno" o que for menor que 5% do valor máximo
  const threshold = maxVal * 0.05
  const smallCount = data.filter(v => v > 0 && v < threshold).length
  
  // Para agrupar, vamos exigir que haja pelo menos 2 categorias pequenas 
  // (se houver apenas 1, não faz muito sentido agrupá-la em 'Outros')
  // Nota: Se preferir agrupar mesmo sendo 1, podemos mudar para >= 1. O ideal para "Outros" é > 1.
  return smallCount >= 1 || data.filter(v => v === 0).length > 0
})

const displayedChart = computed(() => {
  if (!props.message.chart) return null

  const original = props.message.chart
  if (showOriginalChart.value || !hasOthersOption.value) {
    return {
      categories: original.categories.slice(0, displayedRowLimit.value),
      series: original.series.map(series => ({
        ...series,
        data: series.data.slice(0, displayedRowLimit.value)
      }))
    }
  }

  // Agrupar pequenos em "Outros"
  const categories = original.categories
  const seriesList = original.series

  // Somar totais por categoria para suportar multi-series de forma robusta
  const categoryTotals = categories.map((_, i) => {
    return seriesList.reduce((sum, series) => {
      const val = Number.parseFloat(String(series.data[i]))
      return sum + (Number.isNaN(val) ? 0 : val)
    }, 0)
  })

  const maxTotal = Math.max(...categoryTotals)
  const threshold = maxTotal * 0.05

  const largeIndices: number[] = []
  const smallIndices: number[] = []

  categoryTotals.forEach((val, i) => {
    if (val >= threshold) {
      largeIndices.push(i)
    } else {
      smallIndices.push(i)
    }
  })

  if (smallIndices.length === 0 || largeIndices.length === 0) {
    return {
      categories: categories.slice(0, displayedRowLimit.value),
      series: seriesList.map(series => ({
        ...series,
        data: series.data.slice(0, displayedRowLimit.value)
      }))
    }
  }

  const newCategories = largeIndices.map(i => categories[i])
  newCategories.push('Outros')

  const newSeries = seriesList.map(series => {
    const newData = largeIndices.map(i => {
      const val = Number.parseFloat(String(series.data[i]))
      return Number.isNaN(val) ? 0 : val
    })
    const smallSum = smallIndices.reduce((sum, i) => {
      const val = Number.parseFloat(String(series.data[i]))
      return sum + (Number.isNaN(val) ? 0 : val)
    }, 0)
    newData.push(smallSum)
    return {
      ...series,
      data: newData
    }
  })

  return {
    categories: newCategories.slice(0, displayedRowLimit.value),
    series: newSeries.map(series => ({
      ...series,
      data: series.data.slice(0, displayedRowLimit.value)
    }))
  }
})

const displayedChartHasOthersBar = computed(() => {
  return displayedChart.value?.categories.includes('Outros') ?? false
})

onMounted(() => {
  if (typeof document !== 'undefined') {
    isDark.value = document.documentElement.classList.contains('dark')
    observer = new MutationObserver(() => {
      isDark.value = document.documentElement.classList.contains('dark')
    })
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })

    // Setup scroll reveal animation observer
    scrollObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          isVisible.value = entry.isIntersecting
        })
      },
      {
        rootMargin: '0px',
        threshold: 0
      }
    )
    if (bubbleRef.value) {
      scrollObserver.observe(bubbleRef.value)
    }
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
  scrollObserver?.disconnect()
})
const chartOptions = computed<ApexOptions>(() => {
  const categories = displayedChart.value?.categories || []
  const isHorizontal = isChartAxisSwapped.value
  const seriesCount = displayedChart.value?.series.length || 0

  return {
    chart: {
      type: 'bar',
      toolbar: { show: false },
      background: 'transparent',
      animations: {
        enabled: true,
        easing: 'easeinout',
        speed: 700
      },
      events: {
        dataPointSelection: (_event: any, _chartContext: any, config?: any) => {
          const label = config?.w?.globals?.labels?.[config.dataPointIndex]
          if (label === 'Outros') {
            showOriginalChart.value = true
          }
        },
        click: (_event: any, _chartContext: any, config?: any) => {
          if (config && config.dataPointIndex !== undefined && config.dataPointIndex !== -1) {
            const label = config?.w?.globals?.labels?.[config.dataPointIndex]
            if (label === 'Outros') {
              showOriginalChart.value = true
            }
          }
        },
        xAxisLabelClick: (_event: any, _chartContext: any, config?: any) => {
          if (config && config.labelIndex !== undefined) {
            const label = config?.w?.globals?.labels?.[config.labelIndex] || config?.config?.xaxis?.categories?.[config.labelIndex]
            if (label === 'Outros') {
              showOriginalChart.value = true
            }
          }
        }
      }
    },
    dataLabels: { enabled: false },
    grid: {
      borderColor: isDark.value ? 'rgba(99,143,255,0.08)' : 'rgba(30,63,189,0.08)',
      strokeDashArray: 3,
      xaxis: { lines: { show: false } }
    },
    xaxis: isHorizontal
      ? {
          categories,
          labels: {
            show: true,
            formatter: (value: number) => formatNumber(Number(value)),
            style: {
              fontSize: '11px',
              fontWeight: 600,
              colors: isDark.value ? '#9baabf' : '#4a5568'
            }
          },
          axisBorder: { show: false },
          axisTicks: { show: false }
        }
      : {
          categories,
          labels: {
            show: categories.length <= 50,
            rotate: -45,
            rotateAlways: categories.length > 8,
            hideOverlappingLabels: true,
            trim: true,
            maxHeight: 100,
            style: {
              fontSize: '10px',
              fontWeight: 600,
              colors: isDark.value ? '#9baabf' : '#4a5568'
            }
          },
          axisBorder: { show: false },
          axisTicks: { show: categories.length <= 50 }
        },
    yaxis: isHorizontal
      ? {
          labels: {
            formatter: (value: unknown) => String(value ?? ''),
            style: {
              fontSize: '10px',
              fontWeight: 600,
              colors: isDark.value ? '#9baabf' : '#4a5568'
            }
          }
        }
      : {
          labels: {
            formatter: (value: number) => formatNumber(value),
            style: {
              fontSize: '11px',
              fontWeight: 600,
              colors: isDark.value ? '#9baabf' : '#4a5568'
            }
          }
        },
    tooltip: {
      enabled: true,
      shared: true,
      intersect: false,
      theme: isDark.value ? 'dark' : 'light',
      custom: ({ series, dataPointIndex, w }: any) => {
        const label = w.globals.labels[dataPointIndex]
        const background = isDark.value ? '#161d27' : '#ffffff'
        const border = isDark.value ? 'rgba(99,143,255,0.12)' : 'rgba(30,63,189,0.10)'
        const textColor = isDark.value ? '#e8edf5' : '#0f1923'
        const muted = isDark.value ? '#9baabf' : '#4a5568'
        const seriesColors = ['#2248d4', '#2e7d32', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16']

        const seriesRows = series
          .map((serieData: number[], i: number) => {
            const value = serieData[dataPointIndex]
            const name = w.globals.seriesNames[i]
            const color = seriesColors[i % seriesColors.length]
            return `
              <div class="flex items-center justify-between gap-4 mt-1.5">
                <div class="flex items-center gap-1.5">
                  <span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:${color};flex-shrink:0;"></span>
                  <span style="color:${muted};" class="text-xs font-medium">${name}</span>
                </div>
                <span class="font-bold text-sm" style="color:${color}">${formatNumber(value)}</span>
              </div>
            `
          })
          .join('')

        return `
          <div style="background:${background}; border:1px solid ${border}; color:${textColor}; box-shadow:rgba(0,0,0,0.12) 0px 6px 16px; min-width:200px; padding:12px 16px; border-radius:10px;">
            <div style="color:${muted}; font-size:11px; font-weight:500; margin-bottom:4px;">Categoria</div>
            <div style="font-weight:600; font-size:13px; line-height:1.3; margin-bottom:8px; padding-bottom:8px; border-bottom:1px solid ${border};">${label}</div>
            ${seriesRows}
          </div>
        `
      }
    },
    plotOptions: {
      bar: {
        borderRadius: 6,
        borderRadiusApplication: 'end',
        columnWidth: isHorizontal ? '58%' : '58%',
        barHeight: isHorizontal ? '58%' : undefined,
        horizontal: isHorizontal,
        distributed: seriesCount <= 1
      }
    },
    legend: {
      show: seriesCount > 1,
      position: 'top',
      horizontalAlign: 'left',
      fontSize: '12px',
      labels: {
        colors: isDark.value ? '#9baabf' : '#4a5568'
      }
    },
    colors: ['#2248d4', '#2e7d32', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16']
  }
})
// Filtra séries com escalas incompatíveis para evitar gráficos ilegíveis.
// Mantém apenas séries cujo valor máximo é >= 0.1% do maior valor entre todas.
const chartSeries = computed(() => {
  const series = displayedChart.value?.series || []
  if (series.length <= 1) return [...series]

  const seriesMaxes = series.map(s =>
    Math.max(...s.data.map(v => Math.abs(Number(v) || 0)))
  )
  const overallMax = Math.max(...seriesMaxes)
  if (overallMax === 0) return [...series]

  const threshold = overallMax * 0.001
  return series.filter((_, i) => seriesMaxes[i] >= threshold)
})
</script>

<template>
  <div
    ref="bubbleRef"
    :class="[
      'flex w-full ease-out-premium transform-gpu',
      message.type === 'user' ? 'justify-end' : 'justify-start',
      isVisible ? 'opacity-100 translate-y-0 scale-100 filter-none' : 'opacity-0 translate-y-6 scale-[0.97] blur-[2px] pointer-events-none'
    ]"
  >
    <div :class="[
      (message.chart?.series?.length || (hasRenderableTable && !message.isScalarResult) ? 'w-full' : 'max-w-full md:max-w-3xl'),
      message.type === 'user' ? 'ml-4 md:ml-12 mr-4 md:mr-0' : 'mr-4 md:mr-0'
    ]">
      <div v-if="message.type === 'ai'" class="flex items-center justify-between gap-2 mb-3 pr-1">
        <div class="flex items-center gap-2">
          <div class="w-10 h-10 flex items-center justify-center relative">
            <div v-if="message.isLoading" class="loading-brand-wrapper">
              <img :src="brandIcon" class="w-8 h-8 relative z-10" />
              <div class="loading-brand-ring" />
            </div>
            <img v-else :src="brandIcon" class="w-9 h-9" />
          </div>
          <span class="font-semibold tracking-[-0.03em] text-primary dark:text-white">ORACULO-ESX</span>
        </div>

        <!-- Botão Copiar para AI -->
        <button
          v-if="message.text && !message.isLoading"
          type="button"
          @click="copyToClipboard"
          class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all hover:bg-surface-elevated text-primary dark:text-slate-300 hover:text-accent dark:hover:text-white border border-transparent hover:border-border-subtle"
          :title="isCopied ? 'Copiado!' : 'Copiar resposta completa'"
        >
          <transition mode="out-in">
            <Check v-if="isCopied" class="w-3.5 h-3.5 text-emerald-500" />
            <Copy v-else class="w-3.5 h-3.5" />
          </transition>
          <span class="hidden sm:inline">{{ isCopied ? 'Copiado' : 'Copiar' }}</span>
        </button>
      </div>

      <div
        :class="[
          'relative group rounded-xl p-5 transition-all',
          message.type === 'user'
            ? 'bg-[#0f1923] text-white border border-transparent dark:bg-[#1c2535] dark:border-white/[0.10]'
            : message.isFallback
              ? 'bg-amber-50 dark:bg-amber-500/5 border border-amber-200 dark:border-amber-500/20'
              : 'border border-border-subtle bg-surface dark:border-white/[0.06] dark:bg-surface'
        ]"
      >
        <template v-if="message.isFallback">
          <div class="flex items-start gap-2">
            <div class="flex-1">
              <div class="flex items-center gap-2 mb-1.5">
                <img :src="brandIcon" class="w-4 h-4" />
                <span class="text-sm font-semibold text-amber-800 dark:text-amber-500">ORACULO-ESX Exploratorio</span>
              </div>
              <p class="text-sm text-amber-700 dark:text-amber-400/90 mb-3 leading-relaxed">
                {{ message.fallbackMessage || 'Nao encontrei os dados exatos para esta pergunta. Que tal tentar uma das opcoes abaixo?' }}
              </p>

              <div v-if="message.suggestions?.length" class="space-y-1.5">
                <div class="grid grid-cols-1 gap-1.5">
                  <button
                    v-for="(suggestion, index) in message.suggestions"
                    :key="`fallback-${index}`"
                    class="text-left w-full p-2.5 text-sm bg-white dark:bg-slate-900 border border-amber-200/50 dark:border-amber-900/40 rounded-lg hover:border-amber-400 hover:shadow-sm hover:bg-amber-50/50 transition-all text-slate-700 dark:text-slate-300"
                    @click="emit('suggest', suggestion.question)"
                  >
                    <div class="flex justify-between items-center text-xs">
                      <span class="line-clamp-2 pr-2">"{{ suggestion.question }}"</span>
                      <span class="shrink-0 text-[10px] text-amber-600/50 dark:text-amber-500/40">Sugerido</span>
                    </div>
                  </button>
                </div>
              </div>

              <div
                v-if="message.related_attributes?.length"
                class="mt-4 pt-4 border-t border-amber-200/50 dark:border-amber-900/40"
              >
                <div class="flex items-center gap-1.5 mb-2.5">
                  <Database class="w-3.5 h-3.5 text-amber-600 dark:text-amber-500" />
                  <span class="text-xs font-semibold text-amber-800 dark:text-amber-400">
                    Atributos de Banco Disponiveis Neste Dominio:
                  </span>
                </div>
                <div class="flex flex-wrap gap-2">
                  <div
                    v-for="(attribute, index) in message.related_attributes"
                    :key="`attr-fallback-${index}`"
                    class="group relative"
                  >
                    <span class="inline-flex items-center px-2 py-1 bg-amber-100/50 dark:bg-amber-900/30 border border-amber-200/60 dark:border-amber-700/50 text-amber-800 dark:text-amber-300 text-[11px] font-medium rounded-md cursor-help transition-colors hover:bg-amber-200/50">
                      {{ attribute.coluna }}
                    </span>
                    <div class="absolute bottom-full left-0 mb-1 hidden group-hover:block w-48 p-2 bg-slate-800 text-white text-[10px] rounded shadow-lg z-10">
                      {{ attribute.descricao }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>

        <p v-if="message.type === 'user'" class="text-white">
          {{ message.text }}
        </p>

        <template v-else-if="!message.isFallback">
          <div>
            <div
              v-if="message.text"
              class="chat-markdown text-gray-700 dark:text-gray-300"
              v-html="renderedText"
            />

            <div v-if="message.isLoading" :class="['chat-loading-container', message.text ? 'mt-4' : '']" aria-live="polite">
              <div class="chat-loading-status">
                <div class="status-indicator">
                  <span class="status-dot" />
                  <span class="status-dot delay-100" />
                  <span class="status-dot delay-200" />
                </div>
                <span class="status-text">{{ message.loadingStatus || 'Consultando base de dados' }}</span>
              </div>
              <div v-if="!message.text" class="skeleton-group">
                <div class="skeleton-line w-full" />
                <div class="skeleton-line w-[92%] [animation-delay:0.1s]" />
                <div class="skeleton-line w-[68%] [animation-delay:0.2s]" />
              </div>
            </div>
          </div>
        </template>

        <div
          v-if="message.explanation && !message.isFallback"
          class="mt-3 rounded-lg border border-border-subtle bg-surface-elevated/50 px-3 py-2 text-xs leading-relaxed text-text-secondary dark:border-white/[0.06]"
        >
          <span class="font-semibold text-primary dark:text-slate-100">Interpretação:</span>
          {{ message.explanation }}
        </div>

        <div
          v-if="message.isScalarResult && hasRenderableTable && message.table?.[0]"
          class="mt-4 text-3xl font-semibold text-primary dark:text-slate-100"
        >
          {{ formatTableValue(Object.keys(message.table[0])[0], Object.values(message.table[0])[0]) }}
        </div>

        <div
          v-if="hasRenderableTable && !message.isScalarResult && tableRowCount > 5"
          class="mt-4 flex flex-wrap items-center gap-2 text-xs text-text-secondary"
        >
          <span class="font-medium">Mostrar:</span>
          <button
            v-for="option in rowLimitOptions"
            :key="String(option)"
            type="button"
            :class="[
              'rounded-full border px-3 py-1 font-semibold transition-colors',
              rowLimit === option
                ? 'border-[#2248d4] bg-[#2248d4] text-white'
                : 'border-border-subtle bg-surface-elevated hover:border-accent/50 dark:border-white/[0.08]'
            ]"
            @click="rowLimit = option"
          >
            {{ option === 'all' ? `Todas (${tableRowCount})` : option }}
          </button>
        </div>

        <div v-if="displayedChartHasOthersBar && !showOriginalChart && message.chart?.series?.length && hasRenderableTable" class="mt-4 flex flex-col sm:flex-row items-start sm:items-center justify-between px-4 py-3 rounded-xl border border-border-subtle bg-surface-elevated/50 text-xs shadow-sm dark:border-white/[0.06] gap-3">
          <template v-if="showOriginalChart">
            <span class="text-text-secondary font-semibold flex items-center gap-2">
              <span class="inline-block w-2 h-2 rounded-full bg-accent animate-pulse"></span>
              Exibindo os dados originais expandidos
            </span>
            <button 
              type="button" 
              class="px-3 py-1.5 bg-accent/10 text-accent hover:bg-accent hover:text-white rounded-lg font-bold transition-all flex items-center gap-1.5 border border-accent/20 hover:border-accent shadow-sm shrink-0"
              @click="showOriginalChart = false"
            >
              <Minimize2 class="w-4 h-4" />
              Reagrupar 'Outros'
            </button>
          </template>
          <template v-else>
            <span class="text-text-muted font-medium flex items-center gap-2">
              <span class="text-base leading-none">💡</span>
              <span>Categorias pequenas agrupadas. Clique na coluna ou na palavra <strong>'Outros'</strong> no gráfico abaixo para expandir.</span>
            </span>
          </template>
        </div>

        <div
          v-if="showOriginalChart && hasOthersOption && message.chart?.series?.length && hasRenderableTable"
          class="mt-4 flex justify-end"
        >
          <button
            type="button"
            class="px-3 py-1.5 bg-accent/10 text-accent hover:bg-accent hover:text-white rounded-lg font-bold transition-all flex items-center gap-1.5 border border-accent/20 hover:border-accent shadow-sm shrink-0"
            @click="showOriginalChart = false"
          >
            <Minimize2 class="w-4 h-4" />
            Reagrupar 'Outros'
          </button>
        </div>

        <div
          v-if="message.chart?.series?.length && hasRenderableTable && tableRowCount > 1"
          class="mt-4 flex justify-end px-1"
        >
          <button
            type="button"
            class="flex items-center gap-2 rounded-lg border border-border-subtle bg-surface-elevated px-3.5 py-2 text-sm font-semibold text-primary transition-colors hover:border-accent/30 hover:text-accent dark:text-slate-200"
            :title="isChartAxisSwapped ? 'Restaurar o eixo original' : 'Inverter os eixos X e Y'"
            @click="toggleChartAxes"
          >
            <ArrowLeftRight class="w-4 h-4" />
            {{ isChartAxisSwapped ? 'Restaurar eixos' : 'Inverter eixos' }}
          </button>
        </div>

        <div
          v-if="message.chart?.series?.length && hasRenderableTable && tableRowCount > 1"
          class="mt-4 h-[320px] rounded-lg border border-border-subtle bg-surface-elevated/50 p-3 dark:border-white/[0.06] dark:bg-surface-elevated md:h-[360px] md:p-4"
        >
          <VueApexCharts :key="chartOrientationKey" type="bar" height="100%" :options="chartOptions" :series="chartSeries" />
        </div>

        <div
          v-if="hasRenderableTable && !message.isScalarResult"
          class="mt-4 overflow-auto max-h-[450px] w-full border border-border-subtle rounded-lg bg-surface/30 dark:border-white/[0.06] custom-scrollbar"
        >
          <table class="w-full text-sm min-w-[600px] border-collapse">
            <thead class="sticky top-0 z-10 bg-surface-elevated/95 dark:bg-surface-elevated/95 shadow-[0_1px_0_rgba(0,0,0,0.05)] dark:shadow-[0_1px_0_rgba(255,255,255,0.05)]">
              <tr class="border-b border-border-subtle dark:border-white/[0.04]">
                <th
                  v-for="key in Object.keys(message.table?.[0] || {})"
                  :key="key"
                  :class="[
                    'py-2.5 px-4 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-muted select-none',
                    Number.isFinite(Number(Object.values(message.table?.[0] || {})[Object.keys(message.table?.[0] || {}).indexOf(key)]))
                      ? 'text-right'
                      : 'text-left'
                  ]"
                >
                  {{ key.replace(/_/g, ' ') }}
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border-subtle/40 dark:divide-white/[0.04]">
              <tr
                v-for="(row, i) in displayedRows"
                :key="i"
                class="transition-colors hover:bg-accent/[0.06] dark:hover:bg-accent/[0.08]"
              >
                <td
                  v-for="(value, key) in row"
                  :key="key"
                  :class="[
                    'py-2.5 px-4 whitespace-nowrap overflow-hidden text-ellipsis max-w-[300px] text-sm transition-colors',
                    Number.isFinite(Number(value)) && value !== '' && value !== null
                      ? 'text-right tabular-nums text-text-primary font-medium'
                      : 'text-left text-text-secondary'
                  ]"
                  :title="formatTableValue(key, value)"
                >
                  {{ formatTableValue(key, value) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="hasRenderableTable && !message.isScalarResult && tableRowCount > 1" class="mt-2 flex items-center justify-between px-1">
          <p class="text-[11px] text-text-muted font-medium">
            Mostrando {{ displayedRows.length }} de {{ tableRowCount }} registros
          </p>
        </div>

        <div v-if="message.sql" class="mt-4 flex flex-wrap gap-2">
          <button
            class="flex items-center gap-2 rounded-lg border border-border-subtle bg-surface-elevated px-3.5 py-2.5 text-sm font-semibold text-primary transition-colors hover:border-accent/30 hover:text-accent dark:text-slate-200"
            @click="emit('toggle-sql', message.id)"
          >
            <Code class="w-4 h-4" />
            {{ message.showSQL ? 'Ocultar SQL' : 'Ver SQL Gerado' }}
          </button>

          <button
            v-if="hasRenderableTable"
            class="flex items-center gap-2 rounded-lg border border-border-subtle bg-surface-elevated px-3.5 py-2.5 text-sm font-semibold text-primary transition-colors hover:border-accent/30 hover:text-accent dark:text-slate-200"
            @click="emit('pin', message)"
          >
            <Pin class="w-4 h-4" />
            Fixar no Dashboard
          </button>
        </div>

        <div v-if="message.sql && message.showSQL" class="mt-3 rounded-lg border border-border-subtle bg-surface-elevated overflow-hidden dark:border-white/[0.06] dark:bg-black/20">
          <div class="flex items-center justify-between px-3 py-2 border-b border-border-subtle/50 bg-surface/30">
            <span class="text-[10px] font-bold uppercase tracking-wider text-text-muted">Query SQL</span>
            <button
              type="button"
              @click="copySqlToClipboard"
              class="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-bold uppercase transition-all text-primary dark:text-slate-300 hover:text-accent dark:hover:text-white hover:bg-surface/50"
            >
              <transition mode="out-in">
                <Check v-if="isSqlCopied" class="w-3 h-3 text-emerald-500" />
                <Copy v-else class="w-3 h-3" />
              </transition>
              {{ isSqlCopied ? 'Copiado' : 'Copiar' }}
            </button>
          </div>
          <div class="p-4 overflow-x-auto">
            <pre class="text-sm text-accent font-mono whitespace-pre-wrap">{{ message.sql }}</pre>
          </div>
        </div>

        <div
          v-if="!message.isFallback && message.suggestions?.length"
          class="mt-4 pt-4 border-t border-border-subtle dark:border-white/[0.06]"
        >
          <div class="flex items-center gap-2 mb-3">
            <Lightbulb class="w-4 h-4 text-text-muted" />
            <p class="text-sm font-medium text-text-secondary">
              Sugestão: envie uma nova pergunta ou explore as opções abaixo.
            </p>
          </div>
          <div class="grid grid-cols-1 gap-1.5">
            <button
              v-for="(suggestion, index) in message.suggestions"
              :key="`normal-${index}`"
              class="group w-full rounded-lg border border-border-subtle bg-surface-elevated/40 px-3 py-2.5 text-left text-sm text-text-secondary transition-all hover:border-border-standard hover:bg-surface dark:border-white/[0.05] dark:hover:bg-surface-elevated"
              @click="emit('suggest', suggestion.question)"
            >
              <div class="flex justify-between items-center text-xs">
                <span class="line-clamp-2 pr-2 font-medium">"{{ suggestion.question }}"</span>
                <span class="shrink-0 text-[10px] text-text-muted transition-colors group-hover:text-accent">Executar →</span>
              </div>
            </button>
          </div>

          <div
            v-if="message.related_attributes?.length"
            class="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/50"
          >
            <div class="flex items-center gap-1.5 mb-2">
              <Database class="w-3.5 h-3.5 text-slate-500" />
              <span class="text-xs font-semibold text-slate-600 dark:text-slate-400">
                Atributos Relacionados Disponiveis:
              </span>
            </div>
            <div class="flex flex-wrap gap-2">
              <div
                v-for="(attribute, index) in message.related_attributes"
                :key="`attr-normal-${index}`"
                class="group relative"
              >
                <span class="inline-flex items-center px-2 py-1 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-white/5 text-slate-600 dark:text-slate-300 text-[11px] font-medium rounded-md cursor-help transition-colors hover:bg-slate-200 dark:hover:bg-slate-700">
                  {{ attribute.coluna }}
                </span>
                <div class="absolute bottom-full left-0 mb-1 hidden group-hover:block w-48 p-2 bg-slate-800 text-white text-[10px] rounded shadow-lg z-10">
                  {{ attribute.descricao }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Ações para mensagem do usuário -->
      <div v-if="message.type === 'user'" class="flex justify-end mt-1.5 pr-1">
        <button
          type="button"
          @click="copyToClipboard"
          class="flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all text-primary dark:text-slate-400 hover:text-accent dark:hover:text-white hover:bg-surface-elevated/50"
          :title="isCopied ? 'Copiado!' : 'Copiar pergunta'"
        >
          <transition mode="out-in">
            <Check v-if="isCopied" class="w-3 h-3 text-emerald-500" />
            <Copy v-else class="w-3 h-3" />
          </transition>
          <span>{{ isCopied ? 'Copiado' : 'Copiar' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ease-out-premium {
  transition: opacity 0.8s cubic-bezier(0.16, 1, 0.3, 1),
              transform 0.8s cubic-bezier(0.16, 1, 0.3, 1),
              filter 0.8s cubic-bezier(0.16, 1, 0.3, 1);
  will-change: transform, opacity, filter;
}

.chat-markdown :deep(p) {
  margin: 0 0 0.75rem;
  line-height: 1.75;
}

.chat-markdown :deep(p:last-child) {
  margin-bottom: 0;
}

.chat-markdown :deep(ul) {
  margin: 0.5rem 0 0.75rem 1.25rem;
  list-style: disc;
}

.chat-markdown :deep(ol) {
  margin: 0.5rem 0 0.75rem 1.25rem;
  list-style: decimal;
}

.chat-markdown :deep(li) {
  margin: 0.25rem 0;
  line-height: 1.65;
}

.chat-markdown :deep(strong) {
  font-weight: 700;
  color: rgb(var(--color-primary));
}

.chat-markdown :deep(em) {
  font-style: italic;
}

.chat-markdown :deep(code) {
  border-radius: 0.375rem;
  background: rgba(15, 25, 35, 0.06);
  padding: 0.1rem 0.35rem;
  font-size: 0.9em;
}

.chat-markdown :deep(hr) {
  margin: 1rem 0;
  border: 0;
  border-top: 1px solid rgb(var(--color-border-subtle));
}

.chat-markdown :deep(h1),
.chat-markdown :deep(h2),
.chat-markdown :deep(h3) {
  margin: 0.75rem 0 0.5rem;
  font-weight: 700;
  color: rgb(var(--color-primary));
  letter-spacing: -0.02em;
}

.chat-markdown :deep(h1) {
  font-size: 1.25rem;
}

.chat-markdown :deep(h2) {
  font-size: 1.1rem;
}

.chat-markdown :deep(h3) {
  font-size: 1rem;
}

/* Loading state */
/* Nova animação de carregamento — Estilo Profissional/Marca */
.loading-brand-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-brand-ring {
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 2px solid var(--accent);
  border-top-color: transparent;
  border-right-color: transparent;
  animation: brand-spin 0.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  opacity: 0.8;
}

@keyframes brand-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.chat-loading-container {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.chat-loading-status {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-indicator {
  display: flex;
  gap: 3px;
}

.status-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background-color: var(--accent);
  opacity: 0.4;
  animation: pulse-dot 1.2s ease-in-out infinite;
}

.delay-100 { animation-delay: 0.2s; }
.delay-200 { animation-delay: 0.4s; }

@keyframes pulse-dot {
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.2); }
}

.status-text {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.01em;
  text-transform: uppercase;
  font-family: var(--font-mono);
}

.skeleton-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skeleton-line {
  height: 11px;
  border-radius: 4px;
  background: var(--bg-surface-elevated);
  position: relative;
  overflow: hidden;
}

.skeleton-line::after {
  content: "";
  position: absolute;
  inset: 0;
  transform: translateX(-100%);
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.15),
    transparent
  );
  animation: shimmer 1.8s infinite;
}

.dark .skeleton-line::after {
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.04),
    transparent
  );
}

@keyframes shimmer {
  100% { transform: translateX(100%); }
}

@media (prefers-reduced-motion: reduce) {
  .loading-brand-ring,
  .status-dot,
  .skeleton-line::after {
    animation: none;
  }
}
</style>

<style scoped>
:deep(.apexcharts-tooltip) {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(155, 155, 155, 0.2);
  border-radius: 10px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(155, 155, 155, 0.4);
}

.dark .custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
}

.dark .custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}

.custom-scrollbar::-webkit-scrollbar-corner {
  background: transparent;
}
</style>