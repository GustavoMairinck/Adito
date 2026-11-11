<script setup lang="ts">
import { computed } from 'vue'
import { Database, Lock } from 'lucide-vue-next'
import { useContextos } from '@/common/composables/useContextos'

/**
 * Conversa nova: escolhe o contexto de dados. Conversa existente: mostra o contexto fixo dela.
 */
const props = defineProps<{
  conversationContextoId?: string | null
  isNewConversation: boolean
}>()

const { contextos, selectedId, select, nameOf, loaded } = useContextos()

const fixedName = computed(() => nameOf(props.conversationContextoId) || 'Contexto removido')
</script>

<template>
  <div class="flex items-center gap-2 px-4 pt-2 text-xs text-slate-500 dark:text-slate-400">
    <Database class="h-3.5 w-3.5 shrink-0" />
    <template v-if="isNewConversation">
      <span class="shrink-0">Contexto de dados:</span>
      <select
        :value="selectedId ?? ''"
        class="min-w-0 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs text-slate-700 dark:border-white/10 dark:bg-white/5 dark:text-slate-200"
        @change="select(($event.target as HTMLSelectElement).value || null)"
      >
        <option value="" disabled>Escolha um contexto</option>
        <option v-for="contexto in contextos" :key="contexto.id" :value="contexto.id">
          {{ contexto.name }}
        </option>
      </select>
      <span v-if="loaded && contextos.length === 0" class="text-amber-600">
        Nenhum contexto carregado. Carregue os dados no Admin.
      </span>
    </template>
    <template v-else>
      <Lock class="h-3 w-3 shrink-0" />
      <span>Contexto desta conversa: <strong class="font-semibold">{{ fixedName }}</strong></span>
    </template>
  </div>
</template>
