<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import SidebarNav from '@/common/components/navigation/SidebarNav.vue'
import { CheckCircle2, Menu, RefreshCw, X } from 'lucide-vue-next'

import BrandIcon from '@/common/components/BrandIcon.vue'
import PrimeiroUsoDados from '@/common/components/feedback/PrimeiroUsoDados.vue'
import { useAtualizacoes } from '@/common/composables/useAtualizacoes'

const isSidebarOpen = ref(false)

// Monitora atualizações ao abrir, a cada 30 min e ao retornar foco (cooldown 15 min).
const {
  app,
  precisaPrimeiraCarga,
  segundosParaReinicio,
  toastDadosAtualizados,
  iniciarMonitoramento,
  pararMonitoramento,
  reiniciarAgora,
  adiarReinicio,
  fecharToastDados,
} = useAtualizacoes()

onMounted(() => {
  iniciarMonitoramento()
})

onBeforeUnmount(() => {
  pararMonitoramento()
})

function toggleSidebar() {
  isSidebarOpen.value = !isSidebarOpen.value
}
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-primary text-primary">
    <header class="md:hidden fixed top-0 left-0 right-0 z-50 flex h-16 items-center justify-between border-b border-border-subtle bg-surface/95 px-5 backdrop-blur-md">
      <div class="flex items-center gap-2">
        <BrandIcon class="h-8 w-8" />
        <h1 class="text-xl font-semibold tracking-[-0.04em] text-primary">Adito</h1>
      </div>

      <button
        aria-label="Abrir menu de navegação"
        :aria-expanded="isSidebarOpen"
        @click="toggleSidebar"
        class="rounded-lg border border-border-subtle bg-surface-elevated/90 p-2.5 text-text-secondary transition-colors hover:bg-surface-elevated hover:text-primary"
      >
        <Menu class="h-6 w-6" />
      </button>
    </header>

    <SidebarNav v-model:isOpen="isSidebarOpen" />

    <main class="min-w-0 flex-1 overflow-y-auto pt-16 md:pt-0">
      <RouterView />
    </main>

    <div
      v-if="isSidebarOpen"
      class="md:hidden fixed inset-0 z-[55] bg-black/45 backdrop-blur-sm transition-opacity duration-300"
      @click="isSidebarOpen = false"
    />

    <PrimeiroUsoDados v-if="precisaPrimeiraCarga" />

    <div
      v-if="(app && segundosParaReinicio !== null) || toastDadosAtualizados"
      class="pointer-events-none fixed bottom-4 right-4 z-[65] flex max-w-md flex-col items-end gap-2.5 px-4"
    >
      <div
        v-if="app && segundosParaReinicio !== null"
        role="status"
        aria-live="polite"
        data-testid="banner-reinicio-atualizacao"
        class="pointer-events-auto flex flex-col gap-2.5 rounded-xl border border-[var(--brand-primary)]/30 bg-surface p-3.5 text-sm text-text-primary shadow-premium dark:border-[#68d388]/35"
      >
        <div class="flex items-start gap-2.5">
          <RefreshCw class="mt-0.5 h-4 w-4 shrink-0 text-[var(--brand-primary)] dark:text-[#68d388]" />
          <p class="leading-snug">
            Nova versão <strong>v{{ app.version }}</strong> pronta — reiniciando em
            <strong>{{ segundosParaReinicio }}s</strong>…
          </p>
        </div>
        <div class="flex items-center justify-end gap-2">
          <button
            type="button"
            class="rounded-md border border-border-subtle px-2.5 py-1 text-xs font-medium text-text-secondary transition-colors hover:bg-surface-elevated hover:text-text-primary"
            @click="adiarReinicio"
          >
            Adiar
          </button>
          <button
            type="button"
            class="btn-primary px-3 py-1 text-xs"
            @click="reiniciarAgora"
          >
            Reiniciar agora
          </button>
        </div>
      </div>

      <div
        v-if="toastDadosAtualizados"
        role="status"
        aria-live="polite"
        data-testid="toast-dados-atualizados"
        class="pointer-events-auto flex items-center gap-2.5 rounded-xl border border-emerald-300/70 bg-surface px-3.5 py-2.5 text-xs font-medium text-text-primary shadow-premium dark:border-emerald-500/35"
      >
        <CheckCircle2 class="h-4 w-4 shrink-0 text-emerald-600 dark:text-[#68d388]" />
        <span>{{ toastDadosAtualizados }}</span>
        <button
          type="button"
          aria-label="Fechar aviso de dados atualizados"
          class="ml-1 rounded p-0.5 text-text-muted transition-colors hover:text-text-primary"
          @click="fecharToastDados"
        >
          <X class="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  </div>
</template>
