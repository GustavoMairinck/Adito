<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  DollarSign,
  Briefcase,
  Users,
  CreditCard
} from 'lucide-vue-next'
import VueApexCharts from 'vue3-apexcharts'

import { useDashboardData } from '../composables/useDashboardData'
import AISearchBar from '../components/AISearchBar.vue'
import FilterBar from '../components/FilterBar.vue'
import KPICard from '../components/KPICard.vue'
import ChartCard from '../components/ChartCard.vue'

const router = useRouter()
const {
  filtros,
  kpis,
  projects,
  charts,
  loading,
  fetchData,
  updateFilters,
  toggleFilter
} = useDashboardData()

const isDark = ref(false)
onMounted(() => {
  fetchData()

  // High-fidelity reactive theme detection for ApexCharts
  if (typeof window !== 'undefined') {
    isDark.value = document.documentElement.classList.contains('dark')
    const observer = new MutationObserver(() => {
      isDark.value = document.documentElement.classList.contains('dark')
    })
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
  }
})

const handleAISearch = (query: string) => {
  router.push({ path: '/chat', state: { initialQuery: query } })
}

const anoVigente = computed(() => charts.value.ano_vigente || new Date().getFullYear())

// Formatting utilities
const formatCurrency = (value: number | undefined) => {
  if (value === undefined || value === null) return 'R$ 0'
  if (value >= 1_000_000) return `R$ ${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `R$ ${(value / 1_000).toFixed(0)}K`
  return `R$ ${value.toFixed(0)}`
}

const downloadCSV = (data: any[], filename: string) => {
  if (!data?.length) return
  const keys = Object.keys(data[0])
  const csv = [keys.join(','), ...data.map(r => keys.map(k => r[k]).join(','))].join('\n')
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

// KPI mapping
const kpiList = computed(() => [
  { title: 'Receita Líquida', value: loading.value ? '...' : (kpis.value?.total_investido || 'R$ 0'), subtitle: 'Acumulado histórico', icon: DollarSign },
  { title: 'Produtos Vendidos', value: loading.value ? '...' : (kpis.value?.projetos_ativos?.toString() || '0'), subtitle: 'Com vendas registradas', icon: Briefcase },
  { title: `Receita ${anoVigente.value}`, value: loading.value ? '...' : (kpis.value?.pagamentos_ano_vigente || 'R$ 0'), subtitle: `Ano vigente (${anoVigente.value})`, icon: CreditCard },
  { title: 'Vendedores', value: loading.value ? '...' : (kpis.value?.equipe_alocada?.toString() || '0'), subtitle: 'Com vendas registradas', icon: Users },
])

// Theme sensitivity for axis colors
const axisColor = computed(() => isDark.value ? '#4b5560' : '#7b7468')
const labelColor = computed(() => isDark.value ? '#e7dece' : '#5d625f')

// ApexCharts options
const chartOptionsBase: any = computed(() => ({
  chart: {
    toolbar: { show: false },
     fontFamily: 'IBM Plex Sans, system-ui, sans-serif',
    background: 'transparent',
    animations: {
      enabled: true,
      easing: 'easeinout',
      speed: 800
    }
  },
  dataLabels: { enabled: false }, // RE-001: No data labels on chart
  grid: {
    show: true,
     borderColor: isDark.value ? 'rgba(255,247,235,0.08)' : 'rgba(70,55,39,0.10)',
    strokeDashArray: 3,
    position: 'back',
    xaxis: { lines: { show: false } },
    yaxis: { lines: { show: true } },
    padding: {
      left: 13, // Moderate negative padding to close the gap without overlapping labels
      right: 0
    }
  },
  xaxis: {
    axisBorder: { show: true, color: axisColor.value },
    axisTicks: { show: true, color: axisColor.value },
    tooltip: { enabled: false },
    labels: {
      style: {
        colors: labelColor.value,
        fontSize: '11px',
        fontWeight: 600
      }
    }
  },
  yaxis: {
    axisBorder: { show: true, color: axisColor.value },
    axisTicks: { show: true, color: axisColor.value },
    labels: {
      style: {
        colors: labelColor.value,
        fontSize: '11px',
        fontWeight: 600
      },
      formatter: (v: number) => formatCurrency(v)
    }
  },
  tooltip: {
    enabled: true,
    shared: true, // Show tooltip when hovering anywhere in the column (RE-004: UX parity)
    intersect: false, // Trigger via proximity, not just direct intersection
    // Use the reactive variable directly for bulletproof theme switches
    theme: isDark.value ? 'dark' : 'light',
    style: { fontSize: '12px' },
    x: { show: false },
    marker: { show: false },
    custom: function({ series, seriesIndex, dataPointIndex, w }: any) {
      const val = series[seriesIndex][dataPointIndex];
      const isBar = w.config.chart.type === 'bar';

      // Fix: Get categorical label correctly
      let label = '';
      if (isBar) {
        label = w.globals.categoryLabels[dataPointIndex] || w.globals.labels[dataPointIndex];
      } else {
        const dataPoint = w.config.series[seriesIndex].data[dataPointIndex];
        label = dataPoint.x || w.globals.categoryLabels[dataPointIndex] || w.globals.labels[dataPointIndex];
      }

      return `
        <div class="min-w-[130px] rounded-xl border border-[rgba(70,55,39,0.12)] bg-[#fffdf8] px-3 py-2 text-xs text-[#1f262b] shadow-[0_14px_30px_-24px_rgba(31,24,17,0.55)] transition-all duration-200 dark:border-white/8 dark:bg-[#1b1f20] dark:text-[#f3ede4]">
          <div class="mb-1 flex items-center justify-between border-b border-[rgba(70,55,39,0.12)] pb-1.5 font-medium text-[#8a867f] dark:border-white/8 dark:text-[#a8a094]">
            <span>${isBar ? 'Ano' : 'Período'}:</span>
             <span class="font-semibold text-[#1f262b] dark:text-[#f3ede4]">${label}</span>
          </div>
          <div class="flex items-center justify-between gap-4">
            <span class="font-medium text-[#5d625f] dark:text-[#bbb2a6]">Total Pago:</span>
            <span class="font-semibold text-base" style="color: ${isBar ? '#2248d4' : '#2e7d32'}">${formatCurrency(val)}</span>
          </div>
        </div>
      `;
    }
  }
}))

const barChartOptions = computed(() => ({
  ...chartOptionsBase.value,
  chart: {
    ...chartOptionsBase.value.chart,
    type: 'bar',
    events: {
      dataPointSelection: (_event: any, _chartContext: any, config: any) => {
        const year = charts.value.por_ano[config.dataPointIndex]?.year
        if (year) toggleFilter('ano', year)
      }
    }
  },
  xaxis: {
    ...chartOptionsBase.value.xaxis,
    tickPlacement: 'on' // Centered ticks for bars
  },
  plotOptions: {
    bar: {
      borderRadius: 6,
      borderRadiusApplication: 'end', // Round ONLY the top
      columnWidth: '85%', // Optimized for natural spacing (85%)
      distributed: false
    }
  },
  colors: ['#2248d4']
}))

const barChartSeries = computed(() => [{
  name: 'Total Pago',
  data: charts.value.por_ano.map((d: any) => ({
    x: String(d.year),
    y: d.value,
    fillColor: filtros.ano === String(d.year) ? '#1a39b8' : '#2248d4'
  }))
}])

const lineChartOptions = computed(() => ({
  ...chartOptionsBase.value,
  chart: {
    ...chartOptionsBase.value.chart,
    type: 'line', // Back to Line (RE-003: Match Recharts exactly)
    sparkline: { enabled: false }
  },
  xaxis: {
    ...chartOptionsBase.value.xaxis,
    tickPlacement: 'on' // Centers points over labels at position 0
  },
  stroke: {
    curve: 'smooth',
    width: 2,
    colors: ['#2e7d32'],
    lineCap: 'butt'
  },
  markers: {
    size: 4,
    colors: ['#2e7d32'],
    strokeColors: '#fff',
    strokeWidth: 2,
    hover: { size: 6 }
  },
  colors: ['#2e7d32']
}))

const lineChartSeries = computed(() => [{
  name: 'Total Pago',
  data: charts.value.mensal.map((d: any) => ({
    x: d.month,
    y: d.value
  }))
}])
</script>

<template>
  <div class="p-4 md:p-8 space-y-6 md:space-y-8">
    <!-- AI Search Bar -->
    <AISearchBar @search="handleAISearch" />

    <!-- Filters Section -->
    <FilterBar
      v-model:filtros="filtros"
      :anos-disponiveis="charts.anos_disponiveis"
      :areas-disponiveis="charts.areas_disponiveis"
      :modalidades-disponiveis="charts.modalidades_disponiveis"
      :status-disponiveis="charts.statuses_disponiveis"
      @update:filtros="fetchData"
      @clear="updateFilters({ ano: '', area: '', modalidade: '', status: '', projeto: '' })"
    />

    <!-- KPI Grid -->
    <div
      v-motion="{
        initial: { opacity: 0 },
        enter: { opacity: 1 }
      }"
      class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 md:gap-6"
    >
      <KPICard
        v-for="(kpi, index) in kpiList"
        :key="index"
        v-bind="kpi"
      />
    </div>

    <!-- Charts Section -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <ChartCard title="Receita por Ano" :loading="loading">
        <template #actions>
          <UButton
            color="gray"
            variant="ghost"
            icon="i-lucide-download"
            size="sm"
            @click="downloadCSV(charts.por_ano, 'receita_por_ano.csv')"
          />
        </template>

        <VueApexCharts
          v-if="!loading && charts.por_ano.length > 0"
          :key="isDark ? 'dark' : 'light'"
          height="300"
          :options="barChartOptions"
          :series="barChartSeries"
        />
        <div v-else-if="!loading" class="h-[300px] flex items-center justify-center text-text-muted text-sm">
          Sem dados disponíveis
        </div>
      </ChartCard>

      <ChartCard title="Evolução Mensal — Últimos 12 Meses" :loading="loading">
        <template #actions>
          <UButton
            color="gray"
            variant="ghost"
            icon="i-lucide-download"
            size="sm"
            @click="downloadCSV(charts.mensal, 'evolucao_mensal.csv')"
          />
        </template>

        <VueApexCharts
          v-if="!loading && charts.mensal.length > 0"
          :key="isDark ? 'dark' : 'light'"
          height="300"
          :options="lineChartOptions"
          :series="lineChartSeries"
        />
        <div v-else-if="!loading" class="h-[300px] flex items-center justify-center text-text-muted text-sm">
          Sem dados para {{ anoVigente }}
        </div>
      </ChartCard>
    </div>

    <!-- Top Projects Table -->
    <div class="premium-card premium-shadow overflow-hidden">
      <div class="p-6 border-b border-border dark:border-white/5">
        <h3 class="text-sm font-bold uppercase tracking-[2px] text-primary dark:text-white">
          Top 10 Produtos por Receita
        </h3>
      </div>

      <div class="overflow-x-auto" v-if="projects.length > 0">
        <table class="w-full">
          <thead>
            <tr class="border-b border-border dark:border-white/5">
              <th class="hidden sm:table-cell text-left py-4 px-4 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/80">#</th>
              <th class="text-left py-4 px-4 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/80">Produto</th>
              <th class="text-left py-4 px-4 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/80">Receita</th>
              <th class="text-left py-4 px-4 text-[10px] font-bold uppercase tracking-widest text-muted-foreground/80">Categoria</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(project, index) in projects"
              :key="index"
              class="group border-b border-border transition-all hover:bg-surface-elevated/30 dark:hover:bg-white/5"
            >
              <td class="hidden sm:table-cell py-4 px-4 text-xs font-bold text-muted-foreground/60">{{ index + 1 }}</td>
              <td class="py-4 px-4 text-sm font-semibold text-primary group-hover:text-accent transition-colors">
                {{ project.nome }}
              </td>
              <td class="py-4 px-4 text-sm font-semibold text-text-secondary">
                {{ project.valor_formatado || formatCurrency(project.valor) }}
              </td>
              <td class="py-4 px-4">
                <span
                  class="inline-flex items-center px-3 py-1 rounded-md text-[10px] font-semibold uppercase tracking-[0.14em]"
                  :class="[
                    project.status?.toLowerCase().includes('ativo') || project.status?.toLowerCase().includes('execu')
                      ? 'bg-green-500/10 text-green-600 dark:text-green-400'
                      : project.status?.toLowerCase().includes('conclu')
                          ? 'bg-blue-500/10 text-accent'
                          : 'bg-muted text-muted-foreground'
                  ]"
                >
                  {{ project.status || 'Ativo' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="py-12 text-center text-muted-foreground">
        {{ loading ? 'Carregando produtos...' : 'Nenhum produto encontrado' }}
      </div>
    </div>
  </div>
</template>

<style>
/*
  Total Tooltip Transparency
  Stripping default ApexCharts container to solve persistent border artifacts once and for all.
*/
.apexcharts-tooltip {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  border-radius: 0 !important;
}

.apexcharts-tooltip-active {
  background: transparent !important;
  border: none !important;
}

.apexcharts-xaxistooltip {
  display: none !important;
}

/* Bulletproof interactive cursor for bar charts (RE-005) */
.apexcharts-bar-area {
  cursor: pointer;
}
</style>
