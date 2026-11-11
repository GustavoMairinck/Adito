<script setup lang="ts">
import { ref, computed } from 'vue'
import { Plus, X, Code2, FileText, Database } from 'lucide-vue-next'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submit', data: { type: string; question: string; content: string }): void
}>()

const selectedType = ref<'ddl' | 'sql' | 'documentation'>('sql')
const question = ref('')
const content = ref('')
const submitting = ref(false)

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

async function handleSubmit() {
  if (!isValid.value) return
  submitting.value = true

  // Simulate API call
  await new Promise(resolve => setTimeout(resolve, 800))

  emit('submit', {
    type: selectedType.value,
    question: question.value.trim(),
    content: content.value.trim()
  })

  // Reset form
  question.value = ''
  content.value = ''
  selectedType.value = 'sql'
  submitting.value = false
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
        @click.self="emit('close')"
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
            class="w-full max-w-2xl overflow-hidden rounded-2xl border border-border-standard bg-surface shadow-2xl"
          >
            <!-- Header -->
            <div class="flex items-center justify-between border-b border-border-subtle bg-surface/20 px-8 py-6">
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
                class="rounded-lg p-2 text-text-muted transition-colors hover:bg-surface-elevated hover:text-text-primary"
                @click="emit('close')"
              >
                <X class="h-5 w-5" />
              </button>
            </div>

            <!-- Body -->
            <div class="space-y-8 p-8">
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

              <!-- Question (SQL only) -->
              <div v-if="selectedType === 'sql'">
                <label class="mb-3 block text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">
                  Pergunta em Linguagem Natural
                </label>
                <input
                  v-model="question"
                  type="text"
                  placeholder="Ex: Qual a receita liquida total em 2024?"
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
                    ? 'SELECT SUM(receita_liquida) FROM vfactvendasresolved WHERE ano = 2024'
                    : selectedType === 'ddl'
                      ? 'CREATE OR REPLACE VIEW public.vfactvendasresolved AS ...'
                      : 'Receita sempre usa receita_liquida no contexto ORACULO-ESX...'"
                  class="w-full rounded-lg border border-border-subtle bg-primary/20 px-5 py-3 font-mono text-sm text-text-primary placeholder-text-muted transition-all focus:border-accent/50 focus:bg-surface focus:ring-4 focus:ring-accent/5 outline-none shadow-inner dark:bg-primary/40 dark:focus:bg-primary/60"
                />
              </div>
            </div>

            <!-- Footer -->
            <div class="flex items-center justify-end gap-4 border-t border-border-subtle bg-surface/40 px-8 py-6">
              <button
                class="btn-secondary text-sm px-6"
                @click="emit('close')"
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
                {{ submitting ? 'Processando...' : 'Confirmar Treinamento' }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
