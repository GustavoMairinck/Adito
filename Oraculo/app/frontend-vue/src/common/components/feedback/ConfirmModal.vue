<script setup lang="ts">
import { AlertTriangle, X } from 'lucide-vue-next'

interface Props {
  isOpen: boolean
  title: string
  message: string
  confirmText?: string
  cancelText?: string
}

defineProps<Props>()
const emit = defineEmits(['confirm', 'close'])
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
      <div
        class="absolute inset-0 bg-black/50"
        @click="emit('close')"
      />

      <!-- Modal Content — dinâmico claro/escuro e largura adequada -->
      <div
        v-motion="{
          initial: { scale: 0.97, opacity: 0, y: 8 },
          enter: { scale: 1, opacity: 1, y: 0, transition: { duration: 180 } }
        }"
        class="relative w-full max-w-sm overflow-hidden rounded-xl border border-border-subtle bg-surface shadow-[rgba(0,0,0,0.12)_0px_0px_0px_1px,rgba(0,0,0,0.08)_0px_8px_24px] dark:border-white/[0.08]"
      >
        <button
          class="absolute right-3 top-3 rounded-md p-1.5 text-text-muted transition-colors hover:bg-surface-elevated hover:text-text-primary"
          @click="emit('close')"
        >
          <X class="h-4 w-4" />
        </button>

        <!-- Header -->
        <div class="border-b border-border-subtle p-5 pr-12 dark:border-white/[0.06]">
          <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-lg border border-red-200 bg-red-50 dark:border-red-900/40 dark:bg-red-500/10">
            <AlertTriangle class="h-5 w-5 text-red-600 dark:text-red-400" />
          </div>
          <h3 class="text-base font-semibold tracking-tight text-primary">
            {{ title }}
          </h3>
          <p class="mt-1.5 text-sm leading-relaxed text-text-secondary">
            {{ message }}
          </p>
        </div>

        <!-- Actions -->
        <div class="flex gap-2 p-4">
          <button
            class="btn-secondary flex-1 py-2 text-sm font-medium"
            @click="emit('close')"
          >
            {{ cancelText || 'Cancelar' }}
          </button>
          <button
            class="flex flex-1 items-center justify-center rounded-lg bg-red-600 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-800"
            @click="emit('confirm')"
          >
            {{ confirmText || 'Excluir' }}
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>