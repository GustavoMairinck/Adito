<script setup lang="ts">
import { computed, ref } from 'vue'
import { Code2, FileText, Database, Trash2, ChevronDown, ChevronUp, Copy, Check } from 'lucide-vue-next'

export interface TrainingItem {
  id: string
  type: 'ddl' | 'sql' | 'documentation'
  name: string
  content: string
  question?: string
  created_at?: string
}

const props = defineProps<{
  item: TrainingItem
  expanded: boolean
}>()

const emit = defineEmits<{
  (e: 'toggle'): void
  (e: 'remove', item: TrainingItem): void
}>()

const typeConfig = computed(() => {
  switch (props.item.type) {
    case 'ddl':
      return {
        icon: Database,
        label: 'DDL',
        badgeClass: 'border-accent/20 bg-accent/5 text-accent'
      }
    case 'sql':
      return {
        icon: Code2,
        label: 'SQL',
        badgeClass: 'border-accent/20 bg-accent/5 text-accent'
      }
    case 'documentation':
      return {
        icon: FileText,
        label: 'Docs',
        badgeClass: 'border-accent/20 bg-accent/5 text-accent'
      }
  }
})

const truncatedContent = computed(() => {
  const text = props.item.content || ''
  return text.length > 120 ? text.substring(0, 120) + '...' : text
})

const copied = ref(false)
const copyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(props.item.content)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch (err) {
    console.error('Failed to copy text: ', err)
  }
}
</script>

<template>
  <div
    :class="[
      'overflow-hidden rounded-xl border transition-all duration-300 backdrop-blur-md',
      expanded
        ? 'border-accent/30 bg-surface-elevated/40 shadow-elevated'
        : 'border-border-subtle bg-surface/30 hover:border-border-standard hover:bg-surface/50 shadow-premium'
    ]"
  >
    <!-- Header Row -->
    <button
      class="flex w-full items-center gap-5 px-6 py-5 text-left transition-all group"
      @click="emit('toggle')"
    >
      <!-- Type Badge -->
      <span
        :class="[
          'inline-flex shrink-0 items-center gap-1.5 rounded-md border px-3 py-1 text-[10px] font-bold uppercase tracking-widest',
          typeConfig.badgeClass
        ]"
      >
        <component :is="typeConfig.icon" class="h-3 w-3" stroke-width="2.5" />
        {{ typeConfig.label }}
      </span>

      <!-- Name & Preview -->
      <div class="min-w-0 flex-1">
        <p class="truncate text-sm font-semibold text-text-primary group-hover:text-accent transition-colors">
          {{ item.name }}
        </p>
        <p v-if="item.question" class="mt-1 truncate text-xs text-text-secondary leading-relaxed">
          <span class="text-text-muted font-bold mr-1">Q:</span> {{ item.question }}
        </p>
        <p v-else class="mt-1 truncate text-xs text-text-muted font-medium">
          {{ truncatedContent }}
        </p>
      </div>

      <!-- Actions -->
      <div class="flex shrink-0 items-center gap-3">
        <button
          class="rounded-lg p-2 text-text-muted transition-all hover:bg-red-500/10 hover:text-red-400"
          title="Remover treinamento"
          @click.stop="emit('remove', item)"
        >
          <Trash2 class="h-4 w-4" stroke-width="2" />
        </button>
        <div class="p-1.5 rounded-md bg-surface/50 border border-border-subtle">
          <ChevronUp v-if="expanded" class="h-4 w-4 text-text-muted" />
          <ChevronDown v-else class="h-4 w-4 text-text-muted" />
        </div>
      </div>
    </button>

    <div
      v-if="expanded"
      class="border-t border-border-subtle bg-background/40"
    >
      <div class="px-6 py-6">
        <!-- SQL type: question + code side by side -->
        <div v-if="item.type === 'sql'" class="grid gap-8 xl:grid-cols-2">
          <!-- Question Panel -->
          <div class="space-y-4">
            <div class="flex items-center gap-2 px-1">
              <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-text-muted">Pergunta do Usuário</p>
            </div>
            <div class="relative overflow-hidden rounded-xl border border-border-subtle bg-surface-elevated/40 p-6 shadow-sm">
              <div class="absolute left-0 top-0 h-full w-1 bg-accent/20"></div>
              <p class="text-base italic leading-relaxed text-text-primary">
                "{{ item.question || '(sem pergunta)' }}"
              </p>
            </div>
          </div>

          <!-- Code Panel -->
          <div class="space-y-4">
            <div class="flex items-center justify-between px-1">
              <div class="flex items-center gap-2">
                <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-text-muted">Query SQL Resultante</p>
              </div>
              <button
                class="flex items-center gap-1.5 rounded-md border border-border-subtle bg-surface/50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-text-secondary transition-all hover:border-accent hover:text-accent active:scale-95"
                @click="copyToClipboard"
              >
                <component :is="copied ? Check : Copy" class="h-3 w-3" />
                {{ copied ? 'Copiado' : 'Copiar' }}
              </button>
            </div>
            <div class="relative overflow-hidden rounded-xl border border-border-subtle bg-primary shadow-inner dark:bg-black/20">
              <pre class="font-mono text-sm leading-relaxed text-sky-700 dark:text-sky-400 overflow-x-auto p-6 whitespace-pre-wrap">{{ item.content }}</pre>
            </div>
          </div>
        </div>

        <!-- DDL / Documentation: full content -->
        <div v-else class="space-y-4">
          <div class="flex items-center justify-between px-1">
            <div class="flex items-center gap-2">
              <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-text-muted">
                {{ item.type === 'ddl' ? 'Estrutura DDL' : 'Definição de Conhecimento' }}
              </p>
            </div>
            <button
              class="flex items-center gap-1.5 rounded-md border border-border-subtle bg-surface/50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-text-secondary transition-all hover:border-accent hover:text-accent active:scale-95"
              @click="copyToClipboard"
            >
              <component :is="copied ? Check : Copy" class="h-3 w-3" />
              {{ copied ? 'Copiado' : 'Copiar' }}
            </button>
          </div>
          <div class="relative overflow-hidden rounded-xl border border-border-subtle bg-primary shadow-inner dark:bg-black/20">
            <pre class="font-mono text-sm leading-relaxed text-text-primary overflow-x-auto p-6 whitespace-pre-wrap">{{ item.content }}</pre>
          </div>
        </div>

        <!-- Footer / Metadata -->
        <div class="mt-5 flex items-center justify-end border-t border-border-subtle/50 pt-3">
          <p v-if="item.created_at" class="text-[11px] font-medium text-text-muted">
            Sincronizado em {{ new Date(item.created_at).toLocaleString('pt-BR') }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
