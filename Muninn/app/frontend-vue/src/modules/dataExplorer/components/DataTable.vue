<script setup lang="ts">
import { ArrowDown, ArrowUp, ArrowUpDown, Database } from 'lucide-vue-next'
import type { DataColumn, DataValue } from '../types'

defineProps<{
  rows: Record<string, DataValue>[]
  columns: DataColumn[]
  sort: string
  direction: 'asc' | 'desc'
}>()

defineEmits<{ sort: [column: string] }>()

const formatValue = (value: DataValue) => {
  if (value === null) return '—'
  if (typeof value === 'boolean') return value ? 'Sim' : 'Não'
  return String(value)
}
</script>

<template>
  <div v-if="!rows.length" class="flex flex-col items-center gap-3 px-6 py-20 text-center text-text-muted">
    <Database :size="36" :stroke-width="1.5" aria-hidden="true" />
    <p class="font-medium text-primary">
      Nenhum registro encontrado
    </p>
    <p class="text-sm">
      Altere a busca ou limpe os filtros para consultar outros registros.
    </p>
  </div>
  <div v-else class="overflow-x-auto">
    <table class="w-full text-sm">
      <caption class="sr-only">
        Registros da tabela selecionada. Use os cabeçalhos para ordenar.
      </caption>
      <thead class="border-b border-border-subtle bg-surface-elevated">
        <tr>
          <th
            v-for="column in columns"
            :key="column.name"
            scope="col"
            :aria-sort="sort === column.name ? (direction === 'asc' ? 'ascending' : 'descending') : 'none'"
            class="px-4 py-3 text-left font-medium text-text-secondary"
          >
            <button
              class="flex w-full items-center gap-3 whitespace-nowrap rounded focus-visible:outline-2 focus-visible:outline-accent"
              @click="$emit('sort', column.name)"
            >
              {{ column.name }}
              <ArrowUp v-if="sort === column.name && direction === 'asc'" :size="14" aria-hidden="true" />
              <ArrowDown v-else-if="sort === column.name" :size="14" aria-hidden="true" />
              <ArrowUpDown v-else :size="14" class="text-text-muted" aria-hidden="true" />
            </button>
          </th>
        </tr>
      </thead>
      <tbody class="divide-y divide-border-subtle">
        <tr v-for="(row, index) in rows" :key="index" class="hover:bg-surface-elevated/50">
          <td
            v-for="column in columns"
            :key="column.name"
            :class="['min-w-32 max-w-md break-words px-4 py-3 align-top', typeof row[column.name] === 'number' ? 'text-right font-mono tabular-nums' : 'text-text-secondary']"
          >
            {{ formatValue(row[column.name] ?? null) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
