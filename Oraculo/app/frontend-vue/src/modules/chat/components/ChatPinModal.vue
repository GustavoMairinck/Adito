<script setup lang="ts">
import { Loader2, Plus, X } from 'lucide-vue-next'

defineProps<{
  isOpen: boolean
  title: string
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'save'): void
  (e: 'update:title', value: string): void
}>()
</script>

<template>
  <transition
    enter-active-class="transition duration-300 ease-out"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition duration-200 ease-in"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-slate-950/60 backdrop-blur-md" @click="emit('close')" />

      <div
        v-motion="{
          initial: { scale: 0.9, opacity: 0, y: 20 },
          enter: { scale: 1, opacity: 1, y: 0 }
        }"
        class="relative w-full max-w-md overflow-hidden rounded-3xl border border-border-subtle bg-surface shadow-2xl dark:border-white/10 dark:bg-slate-900"
      >
        <button class="absolute right-4 top-4 rounded-full p-2 transition-colors hover:bg-surface-elevated dark:hover:bg-slate-800" @click="emit('close')">
          <X class="h-4 w-4 text-text-secondary dark:text-slate-300" />
        </button>

        <div class="p-8 pb-4">
          <div class="mb-6 flex h-12 w-12 items-center justify-center rounded-2xl border border-accent/20 bg-accent/10 text-accent">
            <Plus class="h-6 w-6" />
          </div>
          <h3 class="mb-2 text-2xl font-semibold text-primary dark:text-white">
            Fixar no Dashboard
          </h3>
          <p class="text-sm leading-relaxed text-text-secondary dark:text-slate-400">
            Dê um nome estratégico para esta análise. Ela ficará fixada e sempre atualizada no seu painel principal.
          </p>
        </div>

        <div class="space-y-6 p-8 pt-4">
          <div class="space-y-2">
            <label class="eyebrow px-1">Título do Widget</label>
            <input
              :value="title"
              type="text"
              autofocus
              class="w-full rounded-2xl border border-border-subtle bg-surface-elevated/50 px-5 py-4 font-medium text-primary outline-none transition-colors placeholder:text-text-muted focus:border-accent dark:border-white/5 dark:bg-slate-950/50 dark:text-white"
              placeholder="Ex: Evolução de Pagamentos"
              @input="emit('update:title', ($event.target as HTMLInputElement).value)"
            >
          </div>

          <div class="flex gap-3 pt-2">
            <button
              class="btn-secondary h-12 flex-1"
              @click="emit('close')"
            >
              Cancelar
            </button>
            <button
              :disabled="loading || !title.trim()"
              class="btn-primary flex h-12 flex-1 items-center justify-center disabled:cursor-not-allowed disabled:opacity-60"
              @click="emit('save')"
            >
              <Loader2 v-if="loading" class="h-5 w-5 animate-spin" />
              <span v-else>Salvar no Painel</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </transition>
</template>
