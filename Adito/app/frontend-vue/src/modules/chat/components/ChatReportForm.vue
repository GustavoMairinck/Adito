<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ArrowDown, ArrowUp, FileText, Loader2, Sparkles } from 'lucide-vue-next'
import { REPORT_MAX_SECTIONS } from '@/modules/chat/utils/report'

export interface ReportOption {
  id: string
  question: string
  chartType?: string | null
}

const props = defineProps<{
  options: ReportOption[]
  defaultTitle: string
  saving?: boolean
  error?: string
}>()

const emit = defineEmits<{
  (e: 'cancel'): void
  (e: 'generate', payload: { title: string; sections: Array<{ message_id: string; title: string; chart_type?: string | null }> }): void
}>()

const title = ref(props.defaultTitle)
// Ordem inicial: a da conversa. Cada seção começa com a pergunta como título (editável).
const items = ref(props.options.map(option => ({
  id: option.id,
  question: option.question,
  title: option.question,
  chartType: option.chartType ?? null,
  checked: true,
})))

// FR08: o tipo de gráfico é o que está na tela ao gerar. Se ele mudar com o formulário aberto
// (ou surgir uma resposta nova), atualiza sem perder marcação, títulos e ordem já editados.
watch(() => props.options, (options) => {
  const byId = new Map(options.map(option => [option.id, option]))
  const kept = items.value
    .filter(item => byId.has(item.id))
    .map(item => ({ ...item, chartType: byId.get(item.id)!.chartType ?? null }))
  const known = new Set(kept.map(item => item.id))
  const added = options
    .filter(option => !known.has(option.id))
    .map(option => ({ id: option.id, question: option.question, title: option.question, chartType: option.chartType ?? null, checked: true }))
  items.value = [...kept, ...added]
}, { deep: true })

const checkedCount = computed(() => items.value.filter(item => item.checked).length)
const emptySectionTitle = computed(() => items.value.some(item => item.checked && !item.title.trim()))
const blockedReason = computed(() => {
  if (!title.value.trim()) return 'Dê um título ao relatório.'
  if (checkedCount.value === 0) return 'Marque ao menos uma seção.'
  if (checkedCount.value > REPORT_MAX_SECTIONS) return `O relatório aceita no máximo ${REPORT_MAX_SECTIONS} seções.`
  if (emptySectionTitle.value) return 'Toda seção marcada precisa de um título.'
  return ''
})

const move = (index: number, delta: number) => {
  const target = index + delta
  if (target < 0 || target >= items.value.length) return
  const next = [...items.value]
  ;[next[index], next[target]] = [next[target], next[index]]
  items.value = next
}

const generate = () => {
  if (blockedReason.value || props.saving) return
  emit('generate', {
    title: title.value.trim(),
    sections: items.value
      .filter(item => item.checked)
      .map(item => ({ message_id: item.id, title: item.title.trim(), chart_type: item.chartType })),
  })
}
</script>

<template>
  <section
    class="w-full max-w-2xl rounded-2xl border border-border-subtle bg-surface p-5 shadow-premium"
    aria-label="Criar relatório"
    data-testid="report-form"
  >
    <h2 class="flex items-center gap-2 text-sm font-semibold text-primary dark:text-white">
      <FileText class="h-4 w-4 text-accent" />
      O que você quer no relatório?
    </h2>

    <label for="report-title" class="mt-4 block text-xs font-medium text-text-secondary">Título do relatório</label>
    <input
      id="report-title"
      v-model="title"
      maxlength="200"
      class="mt-1.5 w-full rounded-lg border border-border-standard bg-surface px-3 py-2 text-sm text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent"
    >

    <div class="mt-4 flex items-center justify-between text-xs text-text-secondary">
      <span>Marque as respostas que viram seções e ajuste a ordem e os títulos.</span>
      <span class="font-semibold" aria-live="polite">{{ checkedCount }} de {{ items.length }}</span>
    </div>

    <ol class="mt-2 space-y-2">
      <li
        v-for="(item, index) in items"
        :key="item.id"
        class="flex items-start gap-2 rounded-xl border border-border-subtle bg-surface-elevated/40 p-2.5 dark:border-white/[0.06]"
      >
        <input
          :id="`report-section-${item.id}`"
          v-model="item.checked"
          type="checkbox"
          class="mt-2.5 h-4 w-4 shrink-0 accent-[var(--brand-primary)]"
          :aria-label="`Incluir a seção: ${item.question}`"
        >
        <div class="min-w-0 flex-1">
          <input
            v-model="item.title"
            maxlength="300"
            :disabled="!item.checked"
            :aria-label="`Título da seção ${index + 1}`"
            :class="[
              'w-full rounded-md border bg-surface px-2.5 py-1.5 text-sm text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent disabled:opacity-50',
              item.checked && !item.title.trim() ? 'border-error' : 'border-border-subtle'
            ]"
          >
          <p v-if="item.title.trim() !== item.question" class="mt-1 truncate text-[11px] text-text-muted" :title="item.question">
            Pergunta: {{ item.question }}
          </p>
        </div>
        <div class="flex shrink-0 flex-col gap-1">
          <button
            type="button"
            class="rounded-md border border-border-subtle p-1 text-text-secondary hover:bg-surface hover:text-primary disabled:opacity-30"
            :disabled="index === 0"
            :aria-label="`Subir a seção ${index + 1}`"
            @click="move(index, -1)"
          >
            <ArrowUp class="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            class="rounded-md border border-border-subtle p-1 text-text-secondary hover:bg-surface hover:text-primary disabled:opacity-30"
            :disabled="index === items.length - 1"
            :aria-label="`Descer a seção ${index + 1}`"
            @click="move(index, 1)"
          >
            <ArrowDown class="h-3.5 w-3.5" />
          </button>
        </div>
      </li>
    </ol>

    <p v-if="blockedReason" class="mt-3 text-xs text-text-muted">{{ blockedReason }}</p>
    <p v-if="error" role="alert" class="mt-3 text-xs text-error">{{ error }}</p>

    <div class="mt-4 flex items-center justify-between gap-3">
      <button
        type="button"
        class="rounded-lg px-3 py-2 text-sm font-medium text-text-secondary hover:bg-surface-elevated hover:text-primary"
        @click="emit('cancel')"
      >
        Cancelar
      </button>
      <button
        type="button"
        class="flex items-center gap-2 rounded-lg bg-[var(--brand-primary)] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[var(--brand-dark)] disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="!!blockedReason || saving"
        @click="generate"
      >
        <Loader2 v-if="saving" class="h-4 w-4 animate-spin" />
        <Sparkles v-else class="h-4 w-4" />
        Gerar relatório
      </button>
    </div>
  </section>
</template>
