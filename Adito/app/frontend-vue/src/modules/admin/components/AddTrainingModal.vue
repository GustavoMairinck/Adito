<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Plus, X, Code2, FileText, Database, Loader2 } from 'lucide-vue-next'

export interface TrainingSubmit {
  type: 'ddl' | 'sql' | 'documentation'
  question: string
  content: string
  /** Id do contexto; null = vale para todos os contextos. */
  contexto: string | null
}

const props = defineProps<{
  open: boolean
  contextos: { id: string; nome: string }[]
  /** O contexto já escolhido no filtro da lista, se houver. */
  defaultContexto?: string | null
  submitting?: boolean
  error?: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submit', data: TrainingSubmit): void
}>()

const selectedType = ref<'ddl' | 'sql' | 'documentation'>('sql')
const question = ref('')
const content = ref('')
const contexto = ref<string | null>(null)

// Formulário limpo a cada abertura; o pai fecha o modal quando o item foi salvo.
watch(() => props.open, (open) => {
  if (!open) return
  question.value = ''
  content.value = ''
  selectedType.value = 'sql'
  contexto.value = props.defaultContexto ?? null
})

const isValid = computed(() => {
  if (!content.value.trim()) return false
  if (selectedType.value === 'sql' && !question.value.trim()) return false
  return true
})

const typeOptions = [
  { value: 'ddl', label: 'Estrutura DDL', icon: Database, desc: 'Tabelas e Views' },
  { value: 'sql', label: 'Query SQL', icon: Code2, desc: 'Pergunta + Query' },
  { value: 'documentation', label: 'Conhecimento', icon: FileText, desc: 'Regras e Glossário' }
]

/** Não fecha enquanto a requisição está em andamento. */
function fechar() {
  if (props.submitting) return
  emit('close')
}

function handleSubmit() {
  if (!isValid.value || props.submitting) return
  emit('submit', {
    type: selectedType.value,
    question: question.value.trim(),
    content: content.value.trim(),
    contexto: contexto.value
  })
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="open"
        class="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4"
        @click.self="fechar"
      >
        <Transition
          enter-active-class="transition duration-300 cubic-bezier(0.34, 1.56, 0.64, 1)"
          enter-from-class="scale-95 opacity-0 translate-y-4"
          enter-to-class="scale-100 opacity-100 translate-y-0"
          leave-active-class="transition duration-200 ease-in"
          leave-from-class="scale-100 opacity-100 translate-y-0"
          leave-to-class="scale-95 opacity-0 translate-y-4"
        >
          <div
            v-if="open"
            class="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-border-standard bg-surface shadow-2xl"
          >
            <!-- Header -->
            <div class="flex shrink-0 items-center justify-between border-b border-border-subtle bg-surface/20 px-8 py-6">
              <div class="flex items-center gap-4">
                <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-accent/10 border border-accent/20">
                  <Plus class="h-6 w-6 text-accent" stroke-width="2.5" />
                </div>
                <div>
                  <h3 class="text-xl font-bold text-text-primary">Novo Treinamento</h3>
                  <p class="text-xs text-text-secondary font-medium tracking-wide">Base de conhecimento da IA</p>
                </div>
              </div>
              <button
                :disabled="submitting"
                class="rounded-lg p-2 text-text-muted transition-colors hover:bg-surface-elevated hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-50"
                @click="fechar"
              >
                <X class="h-5 w-5" />
              </button>
            </div>

            <!-- Body -->
            <div class="flex-1 space-y-8 overflow-y-auto p-8">
              <!-- Type Selector -->
              <div>
                <label class="mb-3 block text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">
                  Categoria de Treinamento
                </label>
                <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <button
                    v-for="opt in typeOptions"
                    :key="opt.value"
                    :class="[
                      'flex flex-col items-start gap-2 rounded-xl border p-4 transition-all duration-200',
                      selectedType === opt.value
                        ? 'border-accent bg-accent/5 ring-1 ring-accent/20'
                        : 'border-border-subtle bg-surface/50 hover:border-border-standard hover:bg-surface-elevated'
                    ]"
                    @click="selectedType = opt.value as 'ddl' | 'sql' | 'documentation'"
                  >
                    <component :is="opt.icon" :class="['h-5 w-5', selectedType === opt.value ? 'text-accent' : 'text-text-muted']" stroke-width="2" />
                    <div class="text-left">
                      <p :class="['text-sm font-semibold', selectedType === opt.value ? 'text-text-primary' : 'text-text-secondary']">{{ opt.label }}</p>
                      <p class="text-[10px] text-text-muted mt-0.5">{{ opt.desc }}</p>
                    </div>
                  </button>
                </div>
              </div>

              <!-- Contexto -->
              <div>
                <label class="mb-3 block text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">
                  Contexto
                </label>
                <select
                  v-model="contexto"
                  class="w-full rounded-lg border border-border-subtle bg-primary/20 px-5 py-3 text-sm text-text-primary transition-all focus:border-accent/50 focus:bg-surface focus:ring-4 focus:ring-accent/5 outline-none dark:bg-primary/40 dark:focus:bg-primary/60"
                >
                  <option :value="null">Todos os contextos</option>
                  <option v-for="c in contextos" :key="c.id" :value="c.id">{{ c.nome }}</option>
                </select>
                <p class="mt-2 text-xs text-text-muted">
                  Itens de um contexto só entram nas perguntas feitas nele. O "Wipe &amp; Retrain" mantém os itens adicionados aqui.
                </p>
              </div>

              <!-- Question (SQL only) -->
              <div v-if="selectedType === 'sql'">
                <label class="mb-3 block text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">
                  Pergunta em Linguagem Natural
                </label>
                <input
                  v-model="question"
                  type="text"
                  placeholder="Ex: Quantos projetos de pesquisa existem por campus em 2024?"
                  class="w-full rounded-lg border border-border-subtle bg-primary/20 px-5 py-3 text-sm text-text-primary placeholder-text-muted transition-all focus:border-accent/50 focus:bg-surface focus:ring-4 focus:ring-accent/5 outline-none dark:bg-primary/40 dark:focus:bg-primary/60"
                />
              </div>

              <!-- Content -->
              <div>
                <label class="mb-3 block text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">
                  {{ selectedType === 'sql' ? 'Instrução SQL Associada' : selectedType === 'ddl' ? 'Estrutura DDL' : 'Definição de Conhecimento' }}
                </label>
                <textarea
                  v-model="content"
                  rows="6"
                  :placeholder="selectedType === 'sql'
                    ? 'SELECT campus, COUNT(*) AS total FROM vfact_projeto_pesquisa_resolved GROUP BY campus'
                    : selectedType === 'ddl'
                      ? 'CREATE VIEW vfact_projeto_pesquisa_resolved AS ...'
                      : 'Projetos ativos são os que têm situacao_projeto = ...'"
                  class="w-full rounded-lg border border-border-subtle bg-primary/20 px-5 py-3 font-mono text-sm text-text-primary placeholder-text-muted transition-all focus:border-accent/50 focus:bg-surface focus:ring-4 focus:ring-accent/5 outline-none shadow-inner dark:bg-primary/40 dark:focus:bg-primary/60"
                />
              </div>
            </div>

            <p v-if="error" class="mx-8 mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-300">
              {{ error }}
            </p>

            <!-- Footer -->
            <div class="flex shrink-0 items-center justify-end gap-4 border-t border-border-subtle bg-surface/40 px-8 py-6">
              <button
                :disabled="submitting"
                class="btn-secondary text-sm px-6 disabled:cursor-not-allowed disabled:opacity-50"
                @click="fechar"
              >
                Cancelar
              </button>
              <button
                :disabled="!isValid || submitting"
                :class="[
                  'btn-primary flex items-center gap-3 px-8 text-sm',
                  !isValid || submitting ? 'opacity-50 cursor-not-allowed' : ''
                ]"
                @click="handleSubmit"
              >
                <Plus v-if="!submitting" class="h-4 w-4" stroke-width="3" />
                <Loader2 v-else class="h-4 w-4 animate-spin" />
                {{ submitting ? 'Salvando...' : 'Confirmar Treinamento' }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
