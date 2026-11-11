<script setup lang="ts">
import { ref, computed } from 'vue'
import { Trash2, X, Search, Edit } from 'lucide-vue-next'
import type { Conversation } from '@/modules/chat/types'

const props = defineProps<{
  conversations: Conversation[]
  currentConvId: string | null
  open: boolean
}>()

const emit = defineEmits<{
  (e: 'select', id: string): void
  (e: 'new'): void
  (e: 'delete', id: string): void
  (e: 'close'): void
}>()

const searchQuery = ref('')

const filteredConversations = computed(() => {
  if (!searchQuery.value.trim()) return props.conversations
  const query = searchQuery.value.toLowerCase()
  return props.conversations.filter(c => c.title.toLowerCase().includes(query))
})
</script>

<template>
  <aside
    :class="[
      'absolute lg:relative z-40 flex h-full w-72 flex-shrink-0 flex-col border-r border-border-subtle bg-surface transition-all duration-300',
      open ? 'translate-x-0 shadow-[4px_0_24px_-4px_rgba(0,0,0,0.15)]' : '-translate-x-full lg:translate-x-0',
      !open ? 'hidden lg:flex' : ''
    ]"
  >
    <div class="flex flex-col gap-2.5 p-3 lg:p-4 border-b border-border-subtle">
      <!-- Cabeçalho Mobile -->
      <div class="mb-1 flex items-center justify-between lg:hidden px-1">
        <span class="text-sm font-semibold text-primary">Conversas</span>
        <button
          class="rounded-md p-1.5 transition-colors hover:bg-surface-elevated text-text-muted hover:text-primary"
          @click="emit('close')"
        >
          <X class="h-4 w-4" />
        </button>
      </div>

      <!-- Botão Novo Chat -->
      <button
        class="flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors text-primary hover:bg-surface-elevated"
        @click="emit('new')"
      >
        <Edit class="h-4 w-4 text-text-secondary" />
        <span>Novo chat</span>
      </button>

      <!-- Busca -->
      <div class="relative">
        <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
          <Search class="h-3.5 w-3.5 text-text-muted" />
        </div>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Buscar chats"
          class="w-full rounded-lg bg-surface-elevated py-2 pl-9 pr-3 text-sm text-primary placeholder:text-text-muted border border-border-subtle focus:border-border-standard focus:outline-none transition-colors"
        />
      </div>
    </div>

    <!-- Lista de Conversas -->
    <div class="flex-1 overflow-y-auto px-2 lg:px-3 py-3">
      <div v-if="filteredConversations.length > 0">
        <p class="px-2 pb-1.5 pt-1 text-xs font-semibold text-text-muted tracking-wide uppercase" style="font-size: 0.68rem; letter-spacing: 0.1em;">Recentes</p>
        <div class="space-y-0.5">
          <div
            v-for="conversation in filteredConversations"
            :key="conversation.id"
            :class="[
              'conv-item group relative flex cursor-pointer items-center justify-between rounded-lg px-2.5 py-2 text-sm',
              currentConvId === conversation.id
                ? 'conv-item--selected text-primary font-medium'
                : 'text-text-secondary'
            ]"
            @click="emit('select', conversation.id)"
          >
            <div class="min-w-0 flex-1 pr-1">
              <div class="truncate leading-snug">{{ conversation.title }}</div>
              <div class="text-xs mt-0.5 text-text-muted" :class="currentConvId === conversation.id ? '' : 'opacity-60'">
                {{ new Date(conversation.updatedAt).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' }) }}
              </div>
            </div>
            <button
              class="ml-1 shrink-0 rounded-md p-1.5 text-text-muted transition-all hover:text-red-500 hover:bg-red-500/10 opacity-0 group-hover:opacity-100"
              title="Excluir chat"
              @click.stop="emit('delete', conversation.id)"
            >
              <Trash2 class="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
      <div v-else class="px-2 py-8 text-center text-sm text-text-muted">
        Nenhuma conversa encontrada.
      </div>
    </div>
  </aside>
</template>

<style scoped>
.conv-item {
  background-color: transparent;
  transition: background-color 150ms ease;
}

.conv-item:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

.conv-item--selected {
  background-color: rgba(0, 0, 0, 0.08);
}

:global(.dark) .conv-item:hover {
  background-color: rgba(255, 255, 255, 0.06);
}

:global(.dark) .conv-item--selected {
  background-color: rgba(255, 255, 255, 0.09);
}
</style>
