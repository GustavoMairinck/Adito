<script setup lang="ts">
import DataValidationChecksTable from '@/modules/dataExplorer/components/DataValidationChecksTable.vue'

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
</script>

<template>
  <DataValidationChecksTable
    :checks="props.checks"
    :format-currency="props.formatCurrency"
    :format-number="props.formatNumber"
  />
</template>
