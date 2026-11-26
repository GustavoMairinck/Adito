<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import VueApexCharts from 'vue3-apexcharts'
import { Minimize2 } from 'lucide-vue-next'
import type { ApexOptions } from 'apexcharts'
import type { ChatChart } from '@/modules/chat/types'
import { apexChartType, type ChatChartType } from '@/modules/chat/utils/chartType'
import { fmt, formatNumber } from '@/modules/chat/utils/format'

/**
 * Gráfico de uma resposta: agrupamento em "Outros", limite de linhas, formatação e tema.
 * Usado pela resposta do chat, pelo relatório no chat e pela página de impressão do relatório.
 */
const props = withDefaults(defineProps<{
  chart: ChatChart
  type: ChatChartType
  rowLimit?: number | 'all'
  /** Página de impressão: tema claro, sem animação, sem o aviso de "Outros". */
  print?: boolean
}>(), {
  rowLimit: 10,
  print: false
})

const darkClass = ref(false)
const isDark = computed(() => !props.print && darkClass.value)
let observer: MutationObserver | null = null

onMounted(() => {
  if (typeof document === 'undefined') return
  darkClass.value = document.documentElement.classList.contains('dark')
  observer = new MutationObserver(() => {
    darkClass.value = document.documentElement.classList.contains('dark')
  })
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
})

onBeforeUnmount(() => {
  observer?.disconnect()
})

const showOriginalChart = ref(false)
const displayedRowLimit = computed(() => (props.rowLimit === 'all' ? props.chart.categories.length : props.rowLimit))

const isChartAxisSwapped = computed(() => props.type === 'horizontal_bar')
const isPieChart = computed(() => props.type === 'pie')
const isLineLikeChart = computed(() => props.type === 'line' || props.type === 'area')


const othersHint = computed(() => {
  if (isPieChart.value) return 'na fatia'
  if (isLineLikeChart.value) return 'no ponto'
  return props.type === 'horizontal_bar' ? 'na barra' : 'na coluna'
})


const expandOthersIfClicked = (label: unknown) => {
  if (label === 'Outros') {
    showOriginalChart.value = true
  }
}

const hasOthersOption = computed(() => {
  if (!props.chart) return false
  const chartData = props.chart
  if (!chartData.series || chartData.series.length === 0) return false
  
  // Garantir que todos os valores sejam convertidos para números reais (NaN ou undefined viram 0)
  const data = chartData.series[0].data.map(v => {
    const n = Number.parseFloat(String(v))
    return Number.isNaN(n) ? 0 : n
  })

  if (data.length <= 1) return false

  // Se a quantidade de dados for menor ou igual à quantidade limitadora (5, 10, 15 ou todos), não precisa agrupar
  const limit = typeof props.rowLimit === 'number' ? props.rowLimit : Infinity
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
  if (!props.chart) return null

  const original = props.chart
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


const chartColors = ['#2B7A42', '#749E30', '#1E5E3A', '#0d9488', '#d97706', '#C50707', '#4f46e5', '#0284c7']

const chartTooltipHtml = (label: string, rows: Array<{ name: string; value: number; color: string }>) => {
  const background = isDark.value ? '#1A221D' : '#ffffff'
  const border = isDark.value ? 'rgba(54,146,81,0.25)' : '#E2E8DF'
  const textColor = isDark.value ? '#F0F4F1' : '#241920'
  const muted = isDark.value ? 'rgba(255,255,255,0.72)' : '#465249'

  const seriesRows = rows
    .map(({ name, value, color }) => `
              <div class="flex items-center justify-between gap-4 mt-1.5">
                <div class="flex items-center gap-1.5">
                  <span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:${color};flex-shrink:0;"></span>
                  <span style="color:${muted};" class="text-xs font-medium">${name}</span>
                </div>
                <span class="font-bold text-sm" style="color:${color}">${formatNumber(value)}</span>
              </div>
            `)
    .join('')

  return `
          <div style="background:${background}; border:1px solid ${border}; color:${textColor}; box-shadow:rgba(0,0,0,0.16) 0px 6px 16px; min-width:200px; padding:12px 16px; border-radius:10px;">
            <div style="color:${muted}; font-size:11px; font-weight:500; margin-bottom:4px;">Categoria</div>
            <div style="font-weight:600; font-size:13px; line-height:1.3; margin-bottom:8px; padding-bottom:8px; border-bottom:1px solid ${border};">${label}</div>
            ${seriesRows}
          </div>
        `
}

const baseChartOptions = computed<ApexOptions>(() => {
  const categories = displayedChart.value?.categories || []
  const isHorizontal = isChartAxisSwapped.value
  const seriesCount = displayedChart.value?.series.length || 0
  const labelColor = isDark.value ? 'rgba(255,255,255,0.72)' : '#465249'
  const baseChart = {
    type: apexChartType(props.type),
    toolbar: { show: false },
    background: 'transparent',
    animations: {
      enabled: !props.print,
      easing: 'easeinout',
      speed: 700
    }
  }

  // Pizza: série plana, uma fatia por categoria, com legenda para dar nome às fatias.
  if (isPieChart.value) {
    const seriesName = chartSeries.value[0]?.name || 'Total'
    return {
      chart: {
        ...baseChart,
        events: {
          dataPointSelection: (_event: any, _chartContext: any, config?: any) => {
            expandOthersIfClicked(categories[config?.dataPointIndex ?? -1])
          },
          legendClick: (_chartContext: any, seriesIndex?: number) => {
            expandOthersIfClicked(categories[seriesIndex ?? -1])
          }
        }
      },
      labels: categories,
      dataLabels: {
        enabled: true,
        formatter: (value: number) => `${fmt(Number(value), 1)}%`,
        style: { fontSize: '11px', fontWeight: 600 },
        dropShadow: { enabled: false }
      },
      stroke: {
        width: 2,
        colors: [isDark.value ? '#1A221D' : '#ffffff']
      },
      tooltip: {
        enabled: true,
        theme: isDark.value ? 'dark' : 'light',
        custom: ({ series, seriesIndex, w }: any) => chartTooltipHtml(w.globals.labels[seriesIndex], [
          { name: seriesName, value: series[seriesIndex], color: w.globals.colors[seriesIndex] }
        ])
      },
      legend: {
        show: true,
        position: 'bottom',
        horizontalAlign: 'center',
        fontSize: '12px',
        labels: { colors: labelColor }
      },
      colors: chartColors
    }
  }

  const isBar = !isLineLikeChart.value

  return {
    chart: {
      ...baseChart,
      events: {
        dataPointSelection: (_event: any, _chartContext: any, config?: any) => {
          expandOthersIfClicked(config?.w?.globals?.labels?.[config.dataPointIndex])
        },
        click: (_event: any, _chartContext: any, config?: any) => {
          if (config && config.dataPointIndex !== undefined && config.dataPointIndex !== -1) {
            expandOthersIfClicked(config?.w?.globals?.labels?.[config.dataPointIndex])
          }
        },
        xAxisLabelClick: (_event: any, _chartContext: any, config?: any) => {
          if (config && config.labelIndex !== undefined) {
            expandOthersIfClicked(config?.w?.globals?.labels?.[config.labelIndex] || config?.config?.xaxis?.categories?.[config.labelIndex])
          }
        }
      }
    },
    dataLabels: { enabled: false },
    grid: {
      borderColor: isDark.value ? 'rgba(255,255,255,0.08)' : 'rgba(22,70,43,0.08)',
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
              colors: labelColor
            }
          },
          axisBorder: { show: false },
          axisTicks: { show: false }
        }
      : {
          categories,
          tooltip: { enabled: false },
          // Linha e área com os pontos no meio de cada categoria, como as colunas: assim o
          // rótulo da primeira e da última categoria não fica cortado na borda.
          tickPlacement: 'between',
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
              colors: labelColor
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
              colors: labelColor
            }
          }
        }
      : {
          // Área começa do zero quando não há negativos, para o tamanho da área não enganar.
          min: props.type === 'area' && chartSeries.value.every(serie => serie.data.every(value => Number(value) >= 0))
            ? 0
            : undefined,
          labels: {
            formatter: (value: number) => formatNumber(value),
            style: {
              fontSize: '11px',
              fontWeight: 600,
              colors: labelColor
            }
          }
        },
    tooltip: {
      enabled: true,
      shared: true,
      intersect: false,
      theme: isDark.value ? 'dark' : 'light',
      custom: ({ series, dataPointIndex, w }: any) => chartTooltipHtml(
        w.globals.labels[dataPointIndex],
        series.map((serieData: number[], i: number) => ({
          name: w.globals.seriesNames[i],
          value: serieData[dataPointIndex],
          color: chartColors[i % chartColors.length]
        }))
      )
    },
    // Linha e área: traço suave com marcadores nos pontos.
    ...(isLineLikeChart.value
      ? {
          stroke: { curve: 'smooth' as const, width: 3 },
          markers: { size: 4, strokeWidth: 0, hover: { size: 6 } },
          fill: props.type === 'area'
            ? { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.55, opacityTo: 0.12, stops: [0, 90, 100] } }
            : { type: 'solid' }
        }
      : {}),
    plotOptions: {
      bar: {
        borderRadius: 6,
        borderRadiusApplication: 'end',
        columnWidth: '58%',
        barHeight: isHorizontal ? '58%' : undefined,
        horizontal: isHorizontal,
        distributed: isBar && seriesCount <= 1
      }
    },
    legend: {
      show: seriesCount > 1,
      position: 'top',
      horizontalAlign: 'left',
      fontSize: '12px',
      labels: {
        colors: labelColor
      }
    },
    colors: chartColors
  }
})

/** Cores e tipografia do PDF do relatório: tons de verde sóbrios, valores escritos no gráfico, sem arredondamento. */
const printColors = ['#1F5F3A', '#6B9F7C', '#A9C7B2', '#3D7F57', '#8FB89C', '#2E4A3A', '#C9DCCF', '#557A63']
const PRINT_FONT = 'Arial, "Liberation Sans", Helvetica, sans-serif'

const withPrintStyle = (options: ApexOptions): ApexOptions => {
  const isPie = isPieChart.value
  const isHorizontal = isChartAxisSwapped.value
  const textColor = '#222222'
  const printed: ApexOptions = {
    ...options,
    chart: { ...options.chart, fontFamily: PRINT_FONT, foreColor: textColor },
    colors: printColors,
    legend: { ...options.legend, labels: { colors: textColor } }
  }
  if (isPie) return printed
  return {
    ...printed,
    grid: { ...options.grid, borderColor: '#DDDDDD', strokeDashArray: 0, padding: { top: 18, right: 12 } },
    fill: { type: 'solid', opacity: 1 },
    states: { hover: { filter: { type: 'none' } }, active: { filter: { type: 'none' } } },
    dataLabels: {
      enabled: true,
      formatter: (value: number) => formatNumber(Number(value)),
      offsetY: isLineLikeChart.value ? -6 : (isHorizontal ? 0 : -18),
      offsetX: isHorizontal ? 22 : 0,
      style: { fontSize: '10px', fontWeight: 700, colors: [textColor] },
      background: { enabled: false },
      dropShadow: { enabled: false }
    },
    ...(isLineLikeChart.value
      ? { stroke: { curve: 'straight' as const, width: 2 }, markers: { size: 4, strokeWidth: 0 } }
      : {}),
    plotOptions: {
      ...options.plotOptions,
      bar: {
        ...options.plotOptions?.bar,
        borderRadius: 0,
        distributed: false,
        dataLabels: { position: 'top' }
      }
    }
  }
}

const chartOptions = computed<ApexOptions>(() => props.print ? withPrintStyle(baseChartOptions.value) : baseChartOptions.value)

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

// A pizza recebe uma lista plana de números (uma fatia por categoria).
const apexSeries = computed(() => {
  if (isPieChart.value) return (chartSeries.value[0]?.data || []).map(value => Number(value) || 0)
  return chartSeries.value
})
</script>

<template>
  <div>
    <div
      v-if="!print && displayedChartHasOthersBar && !showOriginalChart"
      class="mt-4 flex flex-col sm:flex-row items-start sm:items-center justify-between px-4 py-3 rounded-xl border border-border-subtle bg-surface-elevated/50 text-xs shadow-sm dark:border-white/[0.06] gap-3"
    >
      <span class="text-text-muted font-medium flex items-center gap-2">
        <span class="text-base leading-none">💡</span>
        <span>Categorias pequenas agrupadas. Clique {{ othersHint }} ou na palavra <strong>'Outros'</strong> no gráfico abaixo para expandir.</span>
      </span>
    </div>

    <div v-if="!print && showOriginalChart && hasOthersOption" class="mt-4 flex justify-end">
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
      :class="print
        ? 'report-print-chart h-[260px]'
        : 'mt-4 h-[320px] rounded-lg border border-border-subtle bg-surface-elevated/50 p-3 dark:border-white/[0.06] dark:bg-surface-elevated md:h-[360px] md:p-4'"
    >
      <VueApexCharts :key="`chart-${type}`" :type="apexChartType(type)" height="100%" :options="chartOptions" :series="apexSeries" />
    </div>
  </div>
</template>

<style scoped>
:deep(.apexcharts-tooltip) {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
}
</style>
