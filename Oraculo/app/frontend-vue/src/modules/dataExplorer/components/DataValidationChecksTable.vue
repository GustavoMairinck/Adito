<script setup lang="ts">
import { computed } from 'vue'


interface ValidationCheck {
  id: string
  name: string
  oltp_value: number | null
  olap_value: number | null
  delta_pct: number | null
  detail?: string
  status: 'ok' | 'warning' | 'critical' | 'info'
}

const props = defineProps<{
  checks: ValidationCheck[]
  formatCurrency: (value: number | null) => string
  formatNumber: (value: number | null) => string
}>()

const orderedChecks = computed(() =>
  [...props.checks].sort((a, b) => {
    if (a.status === 'ok' && b.status !== 'ok') return 1
    if (a.status !== 'ok' && b.status === 'ok') return -1
    return a.id.localeCompare(b.id)
  })
)
</script>

<template>
  <div class="overflow-x-auto">
    <table class="min-w-[920px] w-full text-left text-sm">
      <thead class="border-b border-border-subtle bg-surface-elevated/45 text-text-muted">
        <tr>
          <th class="px-6 py-4 text-[11px] font-semibold uppercase tracking-[0.18em]">Verificação</th>
          <th class="px-6 py-4 text-[11px] font-semibold uppercase tracking-[0.18em]">OLTP</th>
          <th class="px-6 py-4 text-[11px] font-semibold uppercase tracking-[0.18em]">OLAP</th>
          <th class="px-6 py-4 text-[11px] font-semibold uppercase tracking-[0.18em]">Delta</th>
          <th class="px-6 py-4 text-[11px] font-semibold uppercase tracking-[0.18em]">Status</th>
        </tr>
      </thead>

      <tbody class="divide-y divide-border-subtle">
        <tr
          v-for="check in orderedChecks"
          :key="check.id"
          class="transition-colors hover:bg-surface-elevated/50"
        >
          <td class="min-w-[320px] px-6 py-5 align-top">
            <div class="whitespace-normal break-words font-semibold text-text-primary">
              {{ check.id }} - {{ check.name }}
            </div>
            <div v-if="check.detail" class="mt-1 whitespace-normal break-words text-xs leading-5 text-text-secondary">
              {{ check.detail }}
            </div>
          </td>

          <td class="px-6 py-5 font-medium text-text-secondary">
            {{ check.name.includes('Valor') ? formatCurrency(check.oltp_value) : formatNumber(check.oltp_value) }}
          </td>

          <td class="px-6 py-5 font-medium text-text-secondary">
            {{ check.name.includes('Valor') ? formatCurrency(check.olap_value) : formatNumber(check.olap_value) }}
          </td>

          <td class="px-6 py-5">
            <span
              v-if="check.delta_pct !== null && check.delta_pct !== undefined"
              :class="[
                'font-semibold',
                check.delta_pct === 0 ? 'text-text-muted' : 'text-amber-600 dark:text-amber-500'
              ]"
            >
              {{ check.delta_pct }}%
            </span>
            <span v-else class="text-text-muted">-</span>
          </td>

          <td class="px-6 py-5">
            <div
              v-if="check.status === 'ok'"
              class="text-xs font-bold uppercase tracking-wider text-emerald-500"
            >
              OK
            </div>

            <div
              v-else-if="check.status === 'warning'"
              class="text-xs font-bold uppercase tracking-wider text-amber-400"
            >
              Divergência
            </div>

            <div
              v-else-if="check.status === 'critical'"
              class="text-xs font-bold uppercase tracking-wider text-red-500"
            >
              Erro crítico
            </div>

            <div
              v-else
              class="text-xs font-bold uppercase tracking-wider text-sky-400"
            >
              Info
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
