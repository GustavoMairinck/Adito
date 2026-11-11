<script setup lang="ts">
import { computed } from 'vue'
import { Database } from 'lucide-vue-next'

const props = defineProps<{
  projetos: Array<Record<string, any>>
  loading?: boolean
  columns: Array<{id: string, label: string, visible: boolean, locked: boolean}>
}>()

const statusColor = (status?: string) => {
  const map: Record<string, string> = {
    'Ativo': 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    'Concluído': 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    'Pago': 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    'Cancelado': 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
  }
  return map[status || ''] || 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
}

const hasData = computed(() => (props.projetos || []).length > 0)
const isColumnVisible = (id: string) => props.columns.find(c => c.id === id)?.visible
</script>

<template>
  <div v-if="loading" class="rounded-xl border border-border-subtle bg-surface p-4 shadow-sm">
    <div class="space-y-2 animate-pulse">
      <div v-for="i in 6" :key="i" class="h-12 rounded-lg bg-surface-elevated dark:bg-white/[0.03]" />
    </div>
  </div>

  <div v-else-if="!hasData" class="rounded-xl border border-border-subtle bg-surface shadow-sm">
    <div class="flex flex-col items-center justify-center gap-3 py-20 text-text-muted">
      <Database :size="48" :stroke-width="1" />
      <p class="text-sm font-medium">Nenhum produto encontrado</p>
      <p class="text-xs">Tente alterar ou limpar os filtros aplicados</p>
    </div>
  </div>

  <div v-else class="overflow-hidden rounded-xl border border-border-subtle bg-surface shadow-sm">
    <div class="overflow-x-auto">
      <table class="min-w-[920px] w-full text-sm">
        <thead>
          <tr class="border-b border-border-subtle bg-surface-elevated/45 dark:border-white/[0.04]">
            <th v-if="isColumnVisible('projeto')" class="min-w-[220px] px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">Produto</th>
            <th v-if="isColumnVisible('edital')" class="min-w-[180px] px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">Cliente</th>
            <th v-if="isColumnVisible('modalidade')" class="min-w-[220px] px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">Canal</th>
            <th v-if="isColumnVisible('valor')" class="min-w-[160px] px-4 py-3 text-right text-xs font-semibold uppercase tracking-[0.14em] text-text-muted font-mono whitespace-nowrap">Receita</th>
            <th v-if="isColumnVisible('status')" class="w-28 px-4 py-3 text-center text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">Porte</th>
            <th v-if="isColumnVisible('area')" class="min-w-[140px] px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">Categoria</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border-subtle/40 dark:divide-white/[0.04]">
          <tr
            v-for="(projeto, i) in projetos"
            :key="i"
            class="transition-colors hover:bg-black/[0.04] dark:hover:bg-white/[0.04]"
          >
            <td v-if="isColumnVisible('projeto')" class="whitespace-normal break-words px-4 py-3 font-medium leading-relaxed text-primary dark:text-gray-100">
              {{ projeto.nome || '-' }}
            </td>
            <td v-if="isColumnVisible('edital')" class="whitespace-normal break-words px-4 py-3 leading-relaxed text-text-secondary dark:text-gray-400">
              {{ projeto.edital || '-' }}
            </td>
            <td v-if="isColumnVisible('modalidade')" class="whitespace-normal break-words px-4 py-3 leading-relaxed text-slate-600 dark:text-gray-300">
              {{ projeto.modalidade || '-' }}
            </td>
            <td v-if="isColumnVisible('valor')" class="px-4 py-3 text-right font-semibold text-accent whitespace-nowrap">
              {{ projeto.valor_formatado || '-' }}
            </td>
            <td v-if="isColumnVisible('status')" class="px-4 py-3 text-center">
              <span :class="['rounded-md px-2.5 py-1 text-xs font-medium', statusColor(projeto.status)]">
                {{ projeto.status || '-' }}
              </span>
            </td>
            <td v-if="isColumnVisible('area')" class="px-4 py-3 text-text-secondary dark:text-gray-400">
              {{ projeto.area || '-' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
