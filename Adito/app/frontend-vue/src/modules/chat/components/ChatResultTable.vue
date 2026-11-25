<script setup lang="ts">
import { computed } from 'vue'
import type { FieldFormat } from '@/modules/chat/types'
import { formatFieldValue } from '@/modules/chat/utils/format'

/** Tabela de uma resposta, com a formatação de cada coluna. Usada no chat, no relatório e na impressão. */
const props = withDefaults(defineProps<{
  rows: Array<Record<string, any>>
  fieldFormats?: Record<string, FieldFormat | string>
  /** Página de impressão: sem rolagem, cabeçalho repetido a cada página e linhas alternadas. */
  print?: boolean
}>(), {
  fieldFormats: () => ({}),
  print: false
})

const columns = computed(() => Object.keys(props.rows[0] || {}))
const isNumeric = (value: unknown) => value !== '' && value !== null && value !== undefined && Number.isFinite(Number(value))
const format = (key: string | number, value: unknown) => formatFieldValue(props.fieldFormats, key, value)
</script>

<template>
  <div
    :class="print
      ? 'report-print-table'
      : 'mt-4 overflow-auto max-h-[450px] w-full border border-border-subtle rounded-lg bg-surface/30 dark:border-white/[0.06] custom-scrollbar'"
  >
    <table :class="print ? 'w-full border-collapse text-[9.5pt]' : 'w-full text-sm min-w-[600px] border-collapse'">
      <thead :class="print ? '' : 'sticky top-0 z-10 bg-surface-elevated/95 dark:bg-surface-elevated/95 shadow-[0_1px_0_rgba(0,0,0,0.05)] dark:shadow-[0_1px_0_rgba(255,255,255,0.05)]'">
        <tr :class="print ? '' : 'border-b border-border-subtle dark:border-white/[0.04]'">
          <th
            v-for="key in columns"
            :key="key"
            :class="[
              print ? 'report-print-th' : 'py-2.5 px-4 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-muted select-none',
              isNumeric(rows[0]?.[key]) ? 'text-right' : 'text-left'
            ]"
          >
            {{ key.replace(/_/g, ' ') }}
          </th>
        </tr>
      </thead>
      <tbody :class="print ? '' : 'divide-y divide-border-subtle/40 dark:divide-white/[0.04]'">
        <tr
          v-for="(row, i) in rows"
          :key="i"
          :class="print ? 'report-print-tr' : 'transition-colors hover:bg-accent/[0.06] dark:hover:bg-accent/[0.08]'"
        >
          <td
            v-for="(value, key) in row"
            :key="key"
            :class="[
              print ? 'report-print-td' : 'py-2.5 px-4 whitespace-nowrap overflow-hidden text-ellipsis max-w-[300px] text-sm transition-colors',
              isNumeric(value)
                ? (print ? 'text-right tabular-nums' : 'text-right tabular-nums text-text-primary font-medium')
                : (print ? 'text-left' : 'text-left text-text-secondary')
            ]"
            :title="print ? undefined : format(key, value)"
          >
            {{ format(key, value) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
