<script setup lang="ts">
import { ref } from 'vue'
import { Search, Sparkles } from 'lucide-vue-next'

defineProps<{
  placeholder?: string
}>()

const emit = defineEmits(['search'])
const query = ref('')

function handleSearch() {
  if (!query.value.trim()) return
  emit('search', query.value)
}
</script>

<template>
  <div
    v-motion="{
      initial: { opacity: 0, y: -20 },
      enter: { opacity: 1, y: 0 }
    }"
    class="premium-card mb-8 p-5 md:p-6"
  >
    <div class="flex flex-col items-stretch gap-4 md:flex-row md:items-center">
      <div class="relative flex-1">
        <Search class="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-text-muted" />
        <input
          v-model="query"
          type="text"
          :placeholder="placeholder || 'Pergunte algo como: Qual o total investido por edital em 2024?'"
          class="w-full rounded-lg border border-border-subtle bg-surface px-4 py-3 pl-12 text-sm text-primary outline-none transition-colors placeholder:text-text-muted focus:border-accent md:text-base"
          @keydown.enter="handleSearch"
        />
      </div>

      <button
        class="btn-primary flex h-[48px] items-center justify-center gap-2 whitespace-nowrap px-6 text-sm md:h-auto"
        @click="handleSearch"
      >
        <Sparkles class="h-4 w-4" />
        Perguntar a IA
      </button>
    </div>

    <p class="mt-3 text-xs text-text-secondary md:ml-12 md:text-left">
      Use linguagem natural para explorar seus dados estrategicos com mais contexto e menos ruido visual.
    </p>
  </div>
</template>
