<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import { AlertTriangle, X } from 'lucide-vue-next'

interface Props {
  isOpen: boolean
  title: string
  message: string
  confirmText?: string
  cancelText?: string
}

const props = defineProps<Props>()
const emit = defineEmits(['confirm', 'close'])

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && props.isOpen) {
    event.preventDefault()
    event.stopPropagation()
    event.stopImmediatePropagation()
    emit('close')
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown, true)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown, true)
})
</script>

<template>
  <Teleport to="body">
    <transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isOpen"
        role="dialog"
        aria-modal="true"
        :aria-label="title"
        class="fixed inset-0 z-[90] flex items-center justify-center p-4"
      >
        <!-- Backdrop — sem blur excessivo -->
        <div
          class="absolute inset-0 bg-black/50"
          @click="emit('close')"
        />

        <!-- Modal Content — centralizado na viewport e com a mesma cor de fundo do chat -->
        <div
          v-motion="{
            initial: { scale: 0.97, opacity: 0, y: 8 },
            enter: { scale: 1, opacity: 1, y: 0, transition: { duration: 180 } }
          }"
          class="relative w-full max-w-sm overflow-hidden rounded-xl border border-border-subtle bg-[var(--bg-primary)] text-text-primary shadow-[rgba(0,0,0,0.16)_0px_0px_0px_1px,rgba(0,0,0,0.14)_0px_12px_32px] dark:border-white/[0.12]"
        >
          <button
            type="button"
            aria-label="Fechar"
            class="absolute right-3 top-3 rounded-md p-1.5 text-text-muted transition-colors hover:bg-surface-elevated hover:text-text-primary"
            @click="emit('close')"
          >
            <X class="h-4 w-4" />
          </button>

          <!-- Header -->
          <div class="flex flex-col items-center border-b border-border-subtle px-6 py-6 text-center dark:border-white/[0.08]">
            <div class="mb-3 flex h-10 w-10 items-center justify-center rounded-lg border border-[#C50707]/25 bg-[#C50707]/10 dark:border-red-400/30 dark:bg-red-500/15">
              <AlertTriangle class="h-5 w-5 text-[#C50707] dark:text-red-300" />
            </div>
            <h3 class="text-base font-semibold tracking-tight text-text-primary">
              {{ title }}
            </h3>
            <p class="mt-1.5 text-sm leading-relaxed text-text-secondary">
              {{ message }}
            </p>
          </div>

          <!-- Actions -->
          <div class="flex gap-2 p-4">
            <button
              type="button"
              class="btn-secondary flex-1 py-2 text-sm font-medium cursor-pointer"
              @click="emit('close')"
            >
              {{ cancelText || 'Cancelar' }}
            </button>
            <button
              type="button"
              class="flex flex-1 items-center justify-center rounded-lg bg-[#C50707] py-2 text-sm font-semibold text-white transition-colors hover:bg-[#9E0505] dark:bg-red-600 dark:hover:bg-red-500 cursor-pointer"
              @click="emit('confirm')"
            >
              {{ confirmText || 'Excluir' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>