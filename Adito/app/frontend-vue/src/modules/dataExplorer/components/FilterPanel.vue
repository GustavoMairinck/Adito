<script setup lang="ts">
import { computed } from 'vue'
import { Filter, XCircle } from 'lucide-vue-next'

const props = defineProps<{
  filters: Record<string, string>
  filtersAvailable: {
    anos?: string[]
    modalidades?: string[]
    status?: string[]
    areas?: string[]
    instituicoes?: string[]
  }
}>()

const emit = defineEmits<{
  (e: 'update:filters', value: Record<string, string>): void
  (e: 'clear'): void
}>()

const hasFilters = computed(() => Object.values(props.filters || {}).some(v => v))

const updateFilter = (key: string, value: string) => {
  emit('update:filters', { ...props.filters, [key]: value })
}

const selectClass = 'w-full rounded-lg border border-border-subtle bg-surface px-3 py-2 text-sm text-primary outline-none transition-colors focus:border-accent dark:border-gray-700 dark:bg-[#1e1e1e] dark:text-gray-200'
</script>

<template>
  <div class="flex h-fit w-full flex-shrink-0 flex-col gap-4 rounded-xl border border-border-subtle bg-surface p-4 shadow-sm lg:w-64">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2 text-sm font-semibold text-primary">
        <Filter :size="15" />
        Filtros
      </div>
      <button
        v-if="hasFilters"
        class="flex items-center gap-1 text-xs text-red-500 transition-colors hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
        @click="emit('clear')"
      >
        <XCircle :size="13" />
        Limpar
      </button>
    </div>

    <div class="flex flex-col gap-3">
      <div class="flex flex-col gap-1">
        <label class="eyebrow">Ano</label>
        <select :value="props.filters.ano" :class="selectClass" @change="updateFilter('ano', ($event.target as HTMLSelectElement).value)">
          <option value="">Todos os anos</option>
          <option v-for="opt in props.filtersAvailable.anos || []" :key="opt" :value="opt">
            {{ opt }}
          </option>
        </select>
      </div>

      <div class="flex flex-col gap-1">
        <label class="eyebrow">Modalidade</label>
        <select :value="props.filters.modalidade" :class="selectClass" @change="updateFilter('modalidade', ($event.target as HTMLSelectElement).value)">
          <option value="">Todas</option>
          <option v-for="opt in props.filtersAvailable.modalidades || []" :key="opt" :value="opt">
            {{ opt }}
          </option>
        </select>
      </div>

      <div class="flex flex-col gap-1">
        <label class="eyebrow">Status</label>
        <select :value="props.filters.status" :class="selectClass" @change="updateFilter('status', ($event.target as HTMLSelectElement).value)">
          <option value="">Todos</option>
          <option v-for="opt in props.filtersAvailable.status || []" :key="opt" :value="opt">
            {{ opt }}
          </option>
        </select>
      </div>

      <div class="flex flex-col gap-1">
        <label class="eyebrow">Área</label>
        <select :value="props.filters.area" :class="selectClass" @change="updateFilter('area', ($event.target as HTMLSelectElement).value)">
          <option value="">Todas</option>
          <option v-for="opt in props.filtersAvailable.areas || []" :key="opt" :value="opt">
            {{ opt }}
          </option>
        </select>
      </div>
    </div>
  </div>
</template>
