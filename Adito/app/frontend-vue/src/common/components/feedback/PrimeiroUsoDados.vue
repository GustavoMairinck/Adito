<script setup lang="ts">
import { ref } from 'vue'
import { Database, Loader2, LockKeyhole, ShieldAlert } from 'lucide-vue-next'
import BrandIcon from '@/common/components/BrandIcon.vue'
import { useAtualizacoes } from '@/common/composables/useAtualizacoes'

/**
 * Primeiro uso (ADR-0007): o instalador não traz dados. A pessoa digita a chave institucional
 * uma vez; o app baixa a base cifrada do GitHub, confere, destranca e guarda a chave no cofre do SO.
 */
const { instalandoDados, erro, instalarDados } = useAtualizacoes()
const chave = ref('')

async function baixar() {
  if (!chave.value.trim()) return
  const ok = await instalarDados(chave.value)
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
    <div class="w-full max-w-md rounded-2xl border border-border-subtle bg-surface p-6 text-text-primary shadow-premium">
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
        <input
          v-model="chave"
          type="password"
          autocomplete="off"
          spellcheck="false"
          placeholder="Cole a chave dos dados"
          aria-label="Chave dos dados"
          :disabled="instalandoDados"
          class="rounded-md border border-border-subtle bg-surface-elevated/60 px-3 py-2 text-sm placeholder:text-text-muted focus:border-[var(--brand-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--brand-primary)]/20"
        />
        <button type="submit" class="btn-primary disabled:opacity-50" :disabled="instalandoDados || !chave.trim()">
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
