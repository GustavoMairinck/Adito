<script setup lang="ts">
import { Search, X } from 'lucide-vue-next'
import type { DataColumn } from '../types'

defineProps<{ columns: DataColumn[]; search: string; column: string; value: string }>()
defineEmits<{
  'update:search': [value: string]
  'update:column': [value: string]
  'update:value': [value: string]
  clear: []
}>()

const inputClass = 'w-full rounded-lg border border-border-standard bg-surface px-3 py-2 text-sm text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent disabled:opacity-50'
</script>

<template>
  <div class="flex flex-wrap items-end gap-3 border-b border-border-subtle p-4">
    <div class="min-w-48 flex-1">
      <label for="explorer-search" class="mb-1.5 block text-xs font-medium text-text-secondary">
        Buscar nos registros
      </label>
      <div class="relative">
        <Search
          :size="16"
          class="pointer-events-none absolute left-3 top-2.5 text-text-muted"
          aria-hidden="true"
        />
        <input
          id="explorer-search"
          :value="search"
          type="search"
          maxlength="200"
          placeholder="Digite um termo…"
          :class="[inputClass, 'pl-9']"
          @input="$emit('update:search', ($event.target as HTMLInputElement).value)"
        />
      </div>
    </div>
    <div class="min-w-40 flex-1">
      <label for="explorer-filter-column" class="mb-1.5 block text-xs font-medium text-text-secondary">
        Filtrar por coluna
      </label>
      <select
        id="explorer-filter-column"
        :value="column"
        :class="inputClass"
        @change="$emit('update:column', ($event.target as HTMLSelectElement).value)"
      >
        <option value="">
          Selecione uma coluna
        </option>
        <option v-for="item in columns" :key="item.name" :value="item.name">
          {{ item.name }}
        </option>
      </select>
    </div>
    <div class="min-w-40 flex-1">
      <label for="explorer-filter-value" class="mb-1.5 block text-xs font-medium text-text-secondary">
        Valor exato
      </label>
      <input
        id="explorer-filter-value"
        :value="value"
        :disabled="!column"
        maxlength="200"
        placeholder="Informe o valor"
        :class="inputClass"
        @input="$emit('update:value', ($event.target as HTMLInputElement).value)"
      />
    </div>
    <button
      v-if="search || column || value"
      class="btn-secondary flex items-center gap-1.5"
      @click="$emit('clear')"
    >
      <X :size="14" aria-hidden="true" />
      Limpar
    </button>
  </div>
</template>
