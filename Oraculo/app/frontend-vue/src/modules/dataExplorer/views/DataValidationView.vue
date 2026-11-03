<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  AlertTriangle,
  BarChart3,
  ChevronDown,
  ChevronUp,
  Download,
  Loader2,
  Play,
  RefreshCw,
  ShieldCheck
} from 'lucide-vue-next'

import httpClient from '@/common/api/httpClient'
import DataValidationChecksTable from '@/modules/dataExplorer/components/DataValidationChecksTable.vue'

interface ValidationCheck {
  id: string
  name: string
  oltp_value: number | null
  olap_value: number | null
  delta_abs: number | null
  delta_pct: number | null
  detail?: string
  status: 'ok' | 'warning' | 'critical' | 'info'
}

interface ValidationSummary {
  total: number
  ok: number
  warning: number
  critical: number
}

interface ValidationResponse {
  timestamp: string
  summary: ValidationSummary
  checks: ValidationCheck[]
}

interface AnalyticsMetric {
  oltp: number
  olap: number
  delta_abs: number
  delta_pct: number
  status: 'ok' | 'warning' | 'critical' | 'info'
}

interface AnalyticsRow {
  ano: number
  valor_pago: AnalyticsMetric
  qtd_projetos: AnalyticsMetric
  qtd_pessoas: AnalyticsMetric
  qtd_editais: AnalyticsMetric
  qtd_modalidades: AnalyticsMetric
  qtd_status: AnalyticsMetric
}



const data = ref<ValidationResponse | null>(null)
const analyticsData = ref<AnalyticsRow[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const expandedYear = ref<number | null>(null)

const authHeaders = computed(() => ({}))

const fetchValidation = async () => {
  loading.value = true
  error.value = null

  try {
    const [validationRes, analyticsRes] = await Promise.all([
      httpClient.get('/api/admin/data-validation', { headers: authHeaders.value }),
      httpClient.get('/api/admin/data-validation/analytics', { headers: authHeaders.value })
    ])

    data.value = validationRes.data
    analyticsData.value = analyticsRes.data?.analytics_by_year || []
  } catch (err: any) {
    error.value = err?.message || 'Falha ao obter os dados de validacao.'
  } finally {
    loading.value = false
  }
}

onMounted(fetchValidation)

const handleExportCSV = () => {
  if (!data.value) return

  const headers = ['ID', 'Verificacao', 'OLTP', 'OLAP', 'DeltaAbs', 'DeltaPct', 'Status', 'Detalhes']
  const rows = data.value.checks.map((check) => [
    check.id,
    `"${check.name}"`,
    check.oltp_value ?? '',
    check.olap_value ?? '',
    check.delta_abs ?? '',
    check.delta_pct ?? '',
    check.status,
    `"${check.detail || ''}"`
  ])

  const csvContent = `data:text/csv;charset=utf-8,${[headers.join(','), ...rows.map((entry) => entry.join(','))].join('\n')}`
  const encodedUri = encodeURI(csvContent)
  const link = document.createElement('a')

  link.setAttribute('href', encodedUri)
  link.setAttribute('download', `validacao_${new Date().toISOString().split('T')[0]}.csv`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const formatCurrency = (value: number | null) => {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)
}

const formatNumber = (value: number | null) => {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat('pt-BR').format(value)
}

const totalWarnings = computed(() => (data.value?.summary.warning || 0) + (data.value?.summary.critical || 0))

const summaryCards = computed(() => {
  if (!data.value) return []

  return [
    {
      label: 'Verificações executadas',
      value: formatNumber(data.value.summary.total),
      tone: 'text-text-primary',
      bg: 'bg-surface',
      border: 'border-border-subtle'
    },
    {
      label: 'Itens consistentes',
      value: formatNumber(data.value.summary.ok),
      tone: 'text-text-primary',
      bg: 'bg-surface',
      border: 'border-border-subtle'
    },
    {
      label: 'Divergências encontradas',
      value: formatNumber(totalWarnings.value),
      tone: 'text-text-primary',
      bg: 'bg-surface',
      border: 'border-border-subtle'
    }
  ]
})

const hasWarning = (row: AnalyticsRow) => {
  return row.valor_pago.status !== 'ok' ||
    row.qtd_projetos.status !== 'ok' ||
    row.qtd_pessoas.status !== 'ok' ||
    row.qtd_editais.status !== 'ok' ||
    row.qtd_modalidades.status !== 'ok' ||
    row.qtd_status.status !== 'ok'
}

const metricBadgeClass = (status: AnalyticsMetric['status']) => {
  if (status === 'ok') return 'text-emerald-500'
  if (status === 'warning') return 'text-amber-400'
  if (status === 'critical') return 'text-red-500'
  return 'text-sky-400'
}

const metricLabel = (status: AnalyticsMetric['status']) => {
  if (status === 'ok') return 'OK'
  if (status === 'warning') return 'Divergencia'
  if (status === 'critical') return 'Critico'
  return 'Info'
}
</script>

<template>
  <div class="p-4 md:p-8 lg:p-10">
    <div class="mx-auto w-full space-y-6">
      <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div class="max-w-4xl">
          <h1 class="flex items-center gap-3 text-3xl font-semibold tracking-[-0.04em] text-text-primary">
            <ShieldCheck class="h-8 w-8 text-accent" />
            Validação de Dados
          </h1>
          <p class="mt-2 text-sm leading-6 text-text-secondary">
            Auditoria de consistência entre o sistema transacional e o Data Warehouse.
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <button
            :disabled="loading"
            class="btn-primary inline-flex items-center gap-2 px-4 py-2.5 text-sm disabled:cursor-not-allowed disabled:opacity-60"
            @click="fetchValidation"
          >
            <Loader2 v-if="loading" class="h-4 w-4 animate-spin" />
            <Play v-else class="h-4 w-4" />
            {{ loading ? 'Executando...' : 'Executar validacao' }}
          </button>

          <button
            :disabled="!data || loading"
            class="btn-secondary inline-flex items-center gap-2 px-4 py-2.5 text-sm disabled:cursor-not-allowed disabled:opacity-60"
            @click="handleExportCSV"
          >
            <Download class="h-4 w-4" />
            Exportar CSV
          </button>
        </div>
      </div>

      <div
        v-if="error"
        class="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400"
      >
        {{ error }}
      </div>

      <template v-if="data">
        <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div
            v-for="card in summaryCards"
            :key="card.label"
            :class="['premium-card border p-5', card.bg, card.border]"
          >
            <p class="eyebrow">
              {{ card.label }}
            </p>
            <p :class="['mt-3 text-3xl font-bold tracking-tight', card.tone]">
              {{ card.value }}
            </p>
          </div>
        </div>

        <div class="premium-card overflow-hidden">
          <div class="flex flex-col gap-3 border-b border-border-subtle bg-surface-elevated/40 px-6 py-5 md:flex-row md:items-center md:justify-between">
            <div>
              <p class="eyebrow">
                Última Execução
              </p>
              <p class="mt-1 text-sm font-medium text-text-primary">
                {{ new Date(data.timestamp).toLocaleString('pt-BR') }}
              </p>
            </div>

            <div class="flex flex-wrap gap-4 text-sm font-semibold">
              <span class="text-text-secondary">Total: {{ data.summary.total }}</span>
              <span class="text-text-secondary">OK: {{ data.summary.ok }}</span>
              <span class="text-text-secondary">Divergências: {{ totalWarnings }}</span>
            </div>
          </div>

          <div class="flex items-center gap-2 border-b border-border-subtle bg-surface px-6 py-3 text-sm text-text-secondary">
            <RefreshCw class="h-4 w-4" />
            Os registros com divergência aparecem primeiro para facilitar a auditoria.
          </div>

          <DataValidationChecksTable
            :checks="data.checks"
            :format-currency="formatCurrency"
            :format-number="formatNumber"
          />
        </div>

        <div v-if="analyticsData.length > 0" class="premium-card overflow-hidden mt-6">
          <div class="flex items-center gap-2 border-b border-border-subtle bg-surface-elevated/40 px-6 py-5">
            <BarChart3 class="h-5 w-5 text-accent" />
            <h2 class="text-lg font-semibold text-text-primary">Análise temporal detalhada</h2>
          </div>

          <div class="space-y-4 p-4">
            <div
              v-for="row in analyticsData"
              :key="row.ano"
              :class="[
                'overflow-hidden rounded-xl border border-border-subtle bg-surface transition-colors'
              ]"
            >
              <button
                class="flex w-full flex-col justify-between gap-4 px-6 py-5 text-left transition-colors hover:bg-surface-elevated/50 sm:flex-row sm:items-center"
                @click="expandedYear = expandedYear === row.ano ? null : row.ano"
              >
                <div class="flex flex-wrap items-center gap-3">
                  <span class="shrink-0 text-xl font-semibold text-text-primary">{{ row.ano }}</span>
                  <AlertTriangle
                    v-if="hasWarning(row)"
                    class="h-4 w-4 text-amber-400"
                    v-tooltip="'Divergências detectadas'"
                  />
                </div>

                <div class="flex items-center justify-between sm:justify-end gap-6 w-full sm:w-auto mt-2 sm:mt-0 pt-3 sm:pt-0 border-t sm:border-t-0 border-border-subtle">
                  <div class="flex flex-col items-start sm:items-end">
                    <span class="text-[11px] font-bold uppercase tracking-[0.16em] text-text-muted">Valor total OLAP</span>
                    <span class="mt-1 font-semibold text-text-primary">{{ formatCurrency(row.valor_pago.olap) }}</span>
                  </div>
                  <ChevronUp v-if="expandedYear === row.ano" class="h-5 w-5 text-text-muted shrink-0" />
                  <ChevronDown v-else class="h-5 w-5 text-text-muted shrink-0" />
                </div>
              </button>

              <div
                v-if="expandedYear === row.ano"
                class="space-y-4 border-t border-border-subtle bg-background/30 px-6 pb-6 pt-5"
              >
                <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
                  <div class="rounded-xl border border-border-subtle bg-surface p-5">
                    <h4 class="mb-4 flex items-center justify-between text-sm font-semibold text-text-primary">
                      Financeiro (Valor pago)
                      <span :class="['text-[11px] font-bold uppercase tracking-wider', metricBadgeClass(row.valor_pago.status)]">
                        {{ metricLabel(row.valor_pago.status) }}
                      </span>
                    </h4>
                    <div class="grid grid-cols-2 gap-4 text-sm">
                      <div class="flex flex-col gap-1"><span class="text-xs text-text-muted">OLTP</span><span class="font-medium text-text-primary">{{ formatCurrency(row.valor_pago.oltp) }}</span></div>
                      <div class="flex flex-col gap-1"><span class="text-xs text-text-muted">OLAP</span><span class="font-medium text-text-primary">{{ formatCurrency(row.valor_pago.olap) }}</span></div>
                      <div class="flex flex-col gap-1"><span class="text-xs text-text-muted">Delta absoluto</span><span :class="row.valor_pago.delta_abs < 0 ? 'font-medium text-red-500' : 'font-medium text-text-primary'">{{ formatCurrency(row.valor_pago.delta_abs) }}</span></div>
                      <div class="flex flex-col gap-1"><span class="text-xs text-text-muted">Delta %</span><span :class="row.valor_pago.delta_pct < 0 ? 'font-medium text-red-500' : 'font-medium text-text-primary'">{{ row.valor_pago.delta_pct }}%</span></div>
                    </div>
                  </div>

                  <div class="rounded-xl border border-border-subtle bg-surface p-5">
                    <h4 class="mb-4 flex items-center justify-between text-sm font-semibold text-text-primary">
                      Volumetria (Produtos)
                      <span :class="['text-[11px] font-bold uppercase tracking-wider', metricBadgeClass(row.qtd_projetos.status)]">
                        {{ metricLabel(row.qtd_projetos.status) }}
                      </span>
                    </h4>
                    <div class="grid grid-cols-2 gap-4 text-sm">
                      <div class="flex flex-col gap-1"><span class="text-xs text-text-muted">OLTP</span><span class="font-medium text-text-primary">{{ formatNumber(row.qtd_projetos.oltp) }}</span></div>
                      <div class="flex flex-col gap-1"><span class="text-xs text-text-muted">OLAP</span><span class="font-medium text-text-primary">{{ formatNumber(row.qtd_projetos.olap) }}</span></div>
                    </div>
                  </div>
                </div>

                <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <div class="rounded-xl border border-border-subtle bg-surface p-5">
                    <h4 class="mb-4 flex items-center justify-between text-sm font-semibold text-text-primary">
                      Volumetria (Pessoas)
                      <span :class="['text-[11px] font-bold uppercase tracking-wider', metricBadgeClass(row.qtd_pessoas.status)]">
                        {{ metricLabel(row.qtd_pessoas.status) }}
                      </span>
                    </h4>
                    <div class="grid grid-cols-2 gap-4 text-sm">
                      <div class="flex flex-col gap-1"><span class="text-xs text-text-muted">OLTP</span><span class="font-medium text-text-primary">{{ formatNumber(row.qtd_pessoas.oltp) }}</span></div>
                      <div class="flex flex-col gap-1"><span class="text-xs text-text-muted">OLAP</span><span class="font-medium text-text-primary">{{ formatNumber(row.qtd_pessoas.olap) }}</span></div>
                    </div>
                  </div>

                  <div class="rounded-xl border border-border-subtle bg-surface p-5">
                    <h4 class="mb-4 flex items-center justify-between text-sm font-semibold text-text-primary">
                      Volumetria (Editais)
                      <span :class="['text-[11px] font-bold uppercase tracking-wider', metricBadgeClass(row.qtd_editais.status)]">
                        {{ metricLabel(row.qtd_editais.status) }}
                      </span>
                    </h4>
                    <div class="grid grid-cols-2 gap-4 text-sm">
                      <div class="flex flex-col gap-1"><span class="text-xs text-text-muted">OLTP</span><span class="font-medium text-text-primary">{{ formatNumber(row.qtd_editais.oltp) }}</span></div>
                      <div class="flex flex-col gap-1"><span class="text-xs text-text-muted">OLAP</span><span class="font-medium text-text-primary">{{ formatNumber(row.qtd_editais.olap) }}</span></div>
                    </div>
                  </div>

                  <div class="rounded-xl border border-border-subtle bg-surface p-5">
                    <h4 class="mb-4 flex items-center justify-between text-sm font-semibold text-text-primary">
                      Auditoria (Modalidades)
                      <span :class="['text-[11px] font-bold uppercase tracking-wider', metricBadgeClass(row.qtd_modalidades.status)]">
                        {{ metricLabel(row.qtd_modalidades.status) }}
                      </span>
                    </h4>
                    <div class="grid grid-cols-2 gap-4 text-sm">
                      <div class="flex flex-col gap-1"><span class="text-xs text-text-muted">OLTP</span><span class="font-medium text-text-primary">{{ formatNumber(row.qtd_modalidades.oltp) }}</span></div>
                      <div class="flex flex-col gap-1"><span class="text-xs text-text-muted">OLAP</span><span class="font-medium text-text-primary">{{ formatNumber(row.qtd_modalidades.olap) }}</span></div>
                    </div>
                  </div>

                  <div class="rounded-xl border border-border-subtle bg-surface p-5">
                    <h4 class="mb-4 flex items-center justify-between text-sm font-semibold text-text-primary">
                      Auditoria (Status únicos)
                      <span :class="['text-[11px] font-bold uppercase tracking-wider', metricBadgeClass(row.qtd_status.status)]">
                        {{ metricLabel(row.qtd_status.status) }}
                      </span>
                    </h4>
                    <div class="grid grid-cols-2 gap-4 text-sm">
                      <div class="flex flex-col gap-1"><span class="text-xs text-text-muted">OLTP</span><span class="font-medium text-text-primary">{{ formatNumber(row.qtd_status.oltp) }}</span></div>
                      <div class="flex flex-col gap-1"><span class="text-xs text-text-muted">OLAP</span><span class="font-medium text-text-primary">{{ formatNumber(row.qtd_status.olap) }}</span></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
