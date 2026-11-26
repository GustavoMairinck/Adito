<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { Database, Eye, EyeOff, Loader2, LockKeyhole, ShieldAlert } from 'lucide-vue-next'
import BrandIcon from '@/common/components/BrandIcon.vue'
import { useAtualizacoes } from '@/common/composables/useAtualizacoes'

/**
 * Primeiro uso (ADR-0007): o instalador não traz dados. A pessoa digita a chave institucional
 * uma vez; o app baixa a base cifrada do GitHub, confere, destranca e guarda a chave no cofre do SO.
 */
const { instalandoDados, erro, instalarDados } = useAtualizacoes()
const chave = ref('')
const showChave = ref(false)
const dialogRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)

const trimmedChave = computed(() => chave.value.trim())
const chaveLen = computed(() => trimmedChave.value.length)
const isValidHexKey = computed(() => /^[0-9a-f]{64}$/i.test(trimmedChave.value))

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])'

function handleKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    event.stopPropagation()
    return
  }
  if (event.key !== 'Tab' || !dialogRef.value) return
  const focusables = Array.from(dialogRef.value.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR))
  if (focusables.length === 0) return
  const first = focusables[0]
  const last = focusables[focusables.length - 1]
  const active = document.activeElement as HTMLElement | null
  if (event.shiftKey) {
    if (!active || active === first || !dialogRef.value.contains(active)) {
      event.preventDefault()
      last.focus()
    }
  } else if (!active || active === last || !dialogRef.value.contains(active)) {
    event.preventDefault()
    first.focus()
  }
}

onMounted(() => {
  nextTick(() => inputRef.value?.focus())
  window.addEventListener('keydown', handleKeydown, true)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown, true)
})

async function baixar() {
  if (!trimmedChave.value) return
  const ok = await instalarDados(trimmedChave.value)
  if (ok) chave.value = ''
}
</script>

<template>
  <div
    class="fixed inset-0 z-[80] flex items-center justify-center bg-primary/95 p-6 backdrop-blur-sm"
    role="dialog"
    aria-modal="true"
    aria-labelledby="primeiro-uso-titulo"
    data-testid="primeiro-uso-dados"
  >
    <div
      ref="dialogRef"
      class="w-full max-w-md rounded-2xl border border-border-subtle bg-surface p-6 text-text-primary shadow-premium"
    >
      <div class="mb-4 flex items-center gap-3">
        <BrandIcon class="h-10 w-10" />
        <div>
          <h1 id="primeiro-uso-titulo" class="text-lg font-semibold">Bem-vindo ao Adito</h1>
          <p class="text-xs text-text-secondary">Falta só baixar os dados</p>
        </div>
      </div>

      <p class="mb-3 text-sm text-text-secondary">
        Os dados de pesquisa e extensão são baixados à parte e chegam trancados. Para abrir, informe a
        <strong class="text-text-primary">chave dos dados</strong> que a instituição te passou.
      </p>
      <ul class="mb-4 space-y-1.5 text-xs text-text-secondary">
        <li class="flex gap-2"><LockKeyhole class="h-4 w-4 shrink-0" /> Você digita a chave só uma vez: ela fica no cofre do sistema.</li>
        <li class="flex gap-2"><Database class="h-4 w-4 shrink-0" /> Quando houver dados novos, o Adito avisa no canto da barra lateral.</li>
      </ul>

      <form class="flex flex-col gap-3" @submit.prevent="baixar">
        <div class="flex flex-col gap-1.5">
          <div class="flex items-center justify-between">
            <label for="primeiro-uso-chave" class="eyebrow px-0.5">
              Chave dos dados
            </label>
            <span
              data-testid="chave-counter"
              :class="[
                'text-[11px] font-medium tabular-nums',
                isValidHexKey
                  ? 'text-emerald-700 dark:text-emerald-300'
                  : 'text-text-muted',
              ]"
            >
              {{ chaveLen }}/64 caracteres
            </span>
          </div>

          <div class="relative flex items-center">
            <input
              id="primeiro-uso-chave"
              ref="inputRef"
              v-model="chave"
              :type="showChave ? 'text' : 'password'"
              autocomplete="off"
              spellcheck="false"
              placeholder="Cole a chave dos dados"
              :disabled="instalandoDados"
              class="w-full rounded-md border border-border-subtle bg-surface-elevated/60 py-2 pl-3 pr-10 font-mono text-sm placeholder:font-sans placeholder:text-text-muted focus:border-[var(--brand-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--brand-primary)]/20"
            />
            <button
              type="button"
              class="absolute right-2 rounded-md p-1.5 text-text-muted transition-colors hover:bg-surface hover:text-text-primary"
              :aria-label="showChave ? 'Ocultar valor da chave' : 'Mostrar valor da chave'"
              :title="showChave ? 'Ocultar chave' : 'Mostrar chave'"
              @click="showChave = !showChave"
            >
              <EyeOff v-if="showChave" class="h-4 w-4" />
              <Eye v-else class="h-4 w-4" />
            </button>
          </div>
        </div>

        <button type="submit" class="btn-primary disabled:opacity-50" :disabled="instalandoDados || !trimmedChave">
          <template v-if="instalandoDados">
            <Loader2 class="mr-1 inline h-4 w-4 animate-spin" /> Baixando e conferindo…
          </template>
          <template v-else>Baixar os dados</template>
        </button>
      </form>

      <p v-if="erro" class="mt-3 flex items-start gap-2 text-sm text-[#C50707] dark:text-red-300">
        <ShieldAlert class="mt-0.5 h-4 w-4 shrink-0" /> {{ erro }}
      </p>
    </div>
  </div>
</template>
