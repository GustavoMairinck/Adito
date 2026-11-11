<script setup lang="ts">
import { Loader2, Pin, X } from 'lucide-vue-next'

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
    enter-active-class="transition duration-200 ease-out"
    enter-from-class="opacity-0"
    enter-to-class="opacity-100"
    leave-active-class="transition duration-150 ease-in"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <!-- Backdrop — sem blur excessivo -->
      <div class="absolute inset-0 bg-black/50" @click="emit('close')" />

      <!-- Modal — mesma linguagem do sistema -->
      <div
        v-motion="{
          initial: { scale: 0.97, opacity: 0, y: 8 },
          enter: { scale: 1, opacity: 1, y: 0, transition: { duration: 180 } }
        }"
        class="relative w-full max-w-xl overflow-hidden rounded-2xl border border-border-subtle bg-surface shadow-[rgba(0,0,0,0.12)_0px_0px_0px_1px,rgba(0,0,0,0.08)_0px_12px_32px] dark:border-white/[0.08]"
      >
        <!-- Botão fechar -->
        <button
          class="absolute right-4 top-4 rounded-md p-2 text-text-muted transition-colors hover:bg-surface-elevated hover:text-text-primary"
          @click="emit('close')"
        >
          <X class="h-5 w-5" />
        </button>

        <!-- Header -->
        <div class="border-b border-border-subtle p-8 dark:border-white/[0.06]">
          <div class="mb-5 flex h-14 w-14 items-center justify-center rounded-xl border border-accent/20 bg-accent/10 text-accent">
            <Pin class="h-7 w-7" />
          </div>
          <h3 class="text-2xl font-semibold text-primary tracking-tight">
            Fixar no Dashboard
          </h3>
          <p class="mt-2.5 text-base leading-relaxed text-text-secondary">
            Dê um nome estratégico para esta análise. Ela ficará fixada e sempre atualizada no seu painel principal.
          </p>
        </div>

        <!-- Form -->
        <div class="p-6">
          <div class="mb-6 space-y-2.5">
            <label class="eyebrow px-1 text-xs">Título do Widget</label>
            <input
              :value="title"
              type="text"
              autofocus
              class="w-full rounded-xl border border-border-subtle bg-surface-elevated/50 px-5 py-4 text-base text-primary outline-none transition-colors placeholder:text-text-muted focus:border-accent dark:border-white/[0.07] dark:bg-surface-elevated"
              placeholder="Ex: Evolução de Pagamentos"
              @input="emit('update:title', ($event.target as HTMLInputElement).value)"
            >
          </div>

          <div class="flex gap-3">
            <button
              class="btn-secondary flex-1 py-3.5 text-base font-medium"
              @click="emit('close')"
            >
              Cancelar
            </button>
            <button
              :disabled="loading || !title.trim()"
              class="btn-accent flex flex-1 items-center justify-center py-3.5 text-base font-semibold disabled:cursor-not-allowed disabled:opacity-60"
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
