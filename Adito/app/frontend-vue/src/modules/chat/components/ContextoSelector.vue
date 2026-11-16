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
  <div class="mx-auto flex w-full max-w-3xl items-center gap-2 px-5 pt-2 text-xs text-text-secondary">
    <Database class="h-3.5 w-3.5 shrink-0 text-[var(--brand-primary)] dark:text-[#68d388]" />
    <template v-if="isNewConversation">
      <span class="shrink-0">Contexto de dados:</span>
      <select
        :value="selectedId ?? ''"
        class="min-w-0 cursor-pointer rounded-lg border border-border-subtle bg-surface px-2.5 py-1 text-xs font-medium text-text-primary outline-none transition-all hover:border-border-standard focus:border-[var(--brand-primary)] focus:ring-2 focus:ring-[var(--brand-primary)]/20"
        @change="select(($event.target as HTMLSelectElement).value || null)"
      >
        <option value="" disabled>Escolha um contexto</option>
        <option v-for="contexto in contextos" :key="contexto.id" :value="contexto.id">
          {{ contexto.name }}
        </option>
      </select>
      <span v-if="loaded && contextos.length === 0" class="text-amber-600 dark:text-amber-300">
        Nenhum contexto carregado. Carregue os dados no Admin.
      </span>
    </template>
    <template v-else>
      <Lock class="h-3 w-3 shrink-0 text-text-muted" />
      <span>Contexto desta conversa: <strong class="font-semibold text-text-primary">{{ fixedName }}</strong></span>
    </template>
  </div>
</template>
