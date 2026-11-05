<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import VueApexCharts from 'vue3-apexcharts'
import type { ApexOptions } from 'apexcharts'

const props = defineProps<{
  projetos: Array<Record<string, any>>
  loading?: boolean
}>()

const formatCurrency = (val: number) => {
  if (val === null || val === undefined || Number.isNaN(val)) return 'R$ 0'
  if (Math.abs(val) >= 1_000_000_000) return `R$ ${(val / 1_000_000_000).toFixed(1)}B`
  if (Math.abs(val) >= 1_000_000) return `R$ ${(val / 1_000_000).toFixed(1)}M`
  if (Math.abs(val) >= 1_000) return `R$ ${(val / 1_000).toFixed(1)}K`
  return `R$ ${val.toFixed(0)}`
}

const isDark = ref(false)

onMounted(() => {
  if (typeof window !== 'undefined') {
    isDark.value = document.documentElement.classList.contains('dark')
    const observer = new MutationObserver(() => {
      isDark.value = document.documentElement.classList.contains('dark')
    })
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
  }
})

const topData = computed(() =>
  (props.projetos || [])
    .slice(0, 15)
    .map((p) => ({
      nome: p.nome,
      valor: p.valor
    }))
)

// Escala de cores baseada no Azul ORACULO-ESX (#2248d4)
const colorScale = computed(() => {
  const data = topData.value
  if (!data.length) return []
  const max = Math.max(...data.map(d => d.valor || 0))
  const min = Math.min(...data.map(d => d.valor || 0))

  return data.map(d => {
    const t = max === min ? 0.5 : (d.valor - min) / (max - min)
    // Interpola entre um azul bem escuro e o azul ORACULO-ESX padrão
    // ORACULO-ESX Blue: rgb(34, 72, 212)
    // Darker Blue: rgb(13, 27, 80)
    const r = Math.round(13 + (34 - 13) * t)
    const g = Math.round(27 + (72 - 27) * t)
    const b = Math.round(80 + (212 - 80) * t)
    return `rgb(${r}, ${g}, ${b})`
  })
})

const options = computed<ApexOptions>(() => ({
  chart: {
    type: 'bar',
    toolbar: { show: false },
    background: 'transparent',
    fontFamily: 'IBM Plex Sans, system-ui, sans-serif',
    animations: { enabled: true, easing: 'easeinout', speed: 600 }
  },
  grid: {
    borderColor: isDark.value ? 'rgba(99,143,255,0.08)' : 'rgba(30,63,189,0.08)',
    strokeDashArray: 3,
    xaxis: { lines: { show: false } }
  },
  plotOptions: {
    bar: {
      horizontal: true,
      borderRadius: 6,
      borderRadiusApplication: 'end',
      barHeight: '85%',
      distributed: true // Necessário para cores diferentes por barra
    }
  },
  dataLabels: { enabled: false },
  xaxis: {
    labels: {
      style: {
        colors: isDark.value ? '#9baabf' : '#4a5568',
        fontSize: '11px',
        fontWeight: 600
      },
      formatter: (val: number) => formatCurrency(val)
    }
  },
  yaxis: {
    categories: topData.value.map(d => d.nome),
    labels: {
      style: {
        colors: isDark.value ? '#9baabf' : '#4a5568',
        fontSize: '11px',
        fontWeight: 600
      },
      formatter: (val: number) => String(val)
    }
  },
  tooltip: {
    theme: isDark.value ? 'dark' : 'light',
    shared: true,
    intersect: false,
    custom: ({ series, seriesIndex, dataPointIndex, w }: any) => {
      const name = w.globals.labels[dataPointIndex]
      const value = series[seriesIndex][dataPointIndex]
      const bg = isDark.value ? '#161d27' : '#ffffff'
      const border = isDark.value ? 'rgba(99,143,255,0.12)' : 'rgba(30,63,189,0.10)'
      const text = isDark.value ? '#e8edf5' : '#0f1923'
      const muted = isDark.value ? '#9baabf' : '#4a5568'

      return `
        <div style="background:${bg}; border:1px solid ${border}; color:${text}; box-shadow:rgba(0,0,0,0.08) 0px 4px 12px;"
             class="rounded-lg px-4 py-3 max-w-[320px]">
          <div style="color:${muted};" class="text-[11px] font-medium mb-1 uppercase tracking-wider">Produto</div>
          <div class="text-sm mb-2 whitespace-normal break-words font-semibold leading-tight">
            ${name}
          </div>
          <div class="flex items-center justify-between gap-3">
            <span style="color:${muted};" class="text-xs font-medium">Receita Total</span>
            <span class="font-bold text-sm text-accent">${formatCurrency(value)}</span>
          </div>
        </div>
      `
    }
  },
  legend: { show: false },
  colors: colorScale.value.length ? colorScale.value : ['#2248d4']
}))

const series = computed(() => [
  {
    name: 'Valor',
    data: topData.value.map((d) => ({ x: d.nome, y: d.valor }))
  }
])
</script>

<template>
  <div v-if="loading" class="h-80 animate-pulse rounded-xl border border-border-subtle bg-surface p-6 shadow-sm" />

  <div v-else class="rounded-xl border border-border-subtle bg-surface p-6 shadow-sm">
    <h3 class="mb-4 text-base font-semibold text-text-secondary">
      Top {{ topData.length }} Produtos por Receita
    </h3>

    <VueApexCharts type="bar" height="520" :options="options" :series="series" />
  </div>
</template>

<style scoped>
:deep(.apexcharts-tooltip) {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
}
</style>
