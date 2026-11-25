<script setup lang="ts">
import { computed } from 'vue'
import type { ExplorerResult } from '../types'

const props = defineProps<{ distribution: ExplorerResult['distribution']; total: number }>()
const maximum = computed(() => Math.max(1, ...props.distribution.map(item => item.count)))
</script>

<template>
  <div class="space-y-5 p-5 md:p-6">
    <p class="text-sm text-text-secondary">
      Até 12 valores mais frequentes entre os
      {{ total.toLocaleString('pt-BR') }}
      registros filtrados.
    </p>
    <p v-if="!distribution.length" class="py-12 text-center text-sm text-text-muted">
      Nenhum registro encontrado para este agrupamento.
    </p>
    <ul v-else class="space-y-4" aria-label="Distribuição de registros por valor">
      <li v-for="(item, index) in distribution" :key="index" class="space-y-1.5">
        <div class="flex items-start justify-between gap-4 text-sm">
          <span class="min-w-0 break-words text-text-secondary">
            {{ item.value ?? 'Sem valor' }}
          </span>
          <span class="shrink-0 font-mono tabular-nums text-primary">
            {{ item.count.toLocaleString('pt-BR') }}
          </span>
        </div>
        <div class="h-2 overflow-hidden rounded bg-surface-elevated" aria-hidden="true">
          <div class="h-full rounded bg-accent" :style="{ width: `${item.count / maximum * 100}%` }" />
        </div>
      </li>
    </ul>
  </div>
</template>
