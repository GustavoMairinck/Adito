<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ArrowRight, Database, Download, Loader2, X } from 'lucide-vue-next'
import { useAtualizacoes } from '@/common/composables/useAtualizacoes'

/**
 * Aviso discreto no rodapé da barra lateral: não abre sozinho nem bloqueia o uso.
 * Ao clicar, abre o diálogo centralizado na tela com as atualizações disponíveis.
 */
const props = defineProps<{ collapsed?: boolean }>()

const {
  app,
  dadosNovos,
  temAtualizacao,
  instalandoApp,
  instalandoDados,
  progressoApp,
  erro,
  instalarApp,
  instalarDados,
  limparErro,
} = useAtualizacoes()

const aberto = ref(false)
const chave = ref('')
const ocupado = computed(() => instalandoApp.value || instalandoDados.value)

function tamanhoMb(bytes: number) {
  return `${(bytes / 1024 / 1024).toFixed(1).replace('.', ',')} MB`
}

function alternar() {
  aberto.value = !aberto.value
  if (!aberto.value) limparErro()
}

function depois() {
  if (ocupado.value) return
  aberto.value = false
  limparErro()
}

const podeBaixar = computed(() => {
  if (ocupado.value) return false
  if (dadosNovos.value?.precisa_chave && !chave.value.trim()) return false
  return !!app.value || !!dadosNovos.value
})

async function baixarAgora() {
  if (!podeBaixar.value) return
  if (dadosNovos.value) {
    const ok = await instalarDados(dadosNovos.value.precisa_chave ? chave.value : undefined)
    if (!ok) return
    chave.value = ''
  }
  if (app.value) {
    await instalarApp()
  }
  if (!temAtualizacao.value) {
    aberto.value = false
  }
}

function aoTeclar(ev: KeyboardEvent) {
  if (ev.key === 'Escape' && aberto.value && !ocupado.value) {
    ev.preventDefault()
    depois()
  }
}

onMounted(() => {
  window.addEventListener('keydown', aoTeclar)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', aoTeclar)
})
</script>

<template>
  <div v-if="temAtualizacao" class="relative" data-testid="atualizacao-disponivel">
    <button
      type="button"
      :aria-expanded="aberto"
      :title="props.collapsed ? 'Atualização disponível' : undefined"
      :class="[
        'flex w-full items-center gap-2.5 rounded-lg border border-white/[0.14] bg-white/[0.06] text-[14.5px] font-medium text-white transition-colors hover:bg-white/[0.12]',
        props.collapsed ? 'justify-center p-2.5' : 'px-3.5 py-2.5'
      ]"
      @click="alternar"
    >
      <span class="relative flex h-2.5 w-2.5 shrink-0">
        <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#68d388] opacity-60" />
        <span class="relative inline-flex h-2.5 w-2.5 rounded-full bg-[#68d388]" />
      </span>
      <template v-if="!props.collapsed">
        <span class="flex-1 text-left">Atualização disponível</span>
        <ArrowRight class="h-4 w-4 shrink-0 text-white/75" />
      </template>
    </button>

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
          v-if="aberto"
          class="fixed inset-0 z-[90] flex items-center justify-center p-4"
        >
          <!-- Backdrop -->
          <div
            class="absolute inset-0 bg-black/50"
            @click="depois"
          />

          <!-- Modal centralizado na tela -->
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Atualizações do Adito"
            class="relative w-full max-w-md overflow-hidden rounded-2xl border border-border-subtle bg-surface p-6 text-left text-sm text-text-primary shadow-[rgba(0,0,0,0.16)_0px_0px_0px_1px,rgba(0,0,0,0.16)_0px_16px_40px] dark:border-white/[0.12]"
          >
            <button
              type="button"
              aria-label="Fechar"
              class="absolute right-4 top-4 rounded-lg p-1.5 text-text-muted transition-colors hover:bg-surface-elevated hover:text-text-primary disabled:opacity-50"
              :disabled="ocupado"
              @click="depois"
            >
              <X class="h-4 w-4" />
            </button>

            <div class="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-[var(--accent-light)] text-[var(--brand-primary)] dark:bg-[#2B7A42]/20 dark:text-[#68d388]">
              <Download class="h-5 w-5" />
            </div>

            <h3 class="text-lg font-semibold tracking-tight text-text-primary">
              Nova atualização disponível
            </h3>
            <p class="mt-1.5 text-sm leading-relaxed text-text-secondary">
              Há novidades para o Adito. Você pode baixar agora ou continuar e atualizar mais tarde.
            </p>

            <form class="mt-5 space-y-3" @submit.prevent="baixarAgora">
              <div v-if="app" class="rounded-xl border border-border-subtle bg-surface p-4 dark:border-white/[0.1]">
                <div class="flex items-center gap-2 text-sm font-semibold text-text-primary">
                  <Download class="h-4 w-4 shrink-0 text-[var(--brand-primary)] dark:text-[#68d388]" />
                  <span>Nova versão do Adito</span>
                </div>
                <p class="mt-1.5 text-xs leading-relaxed text-text-secondary">
                  Versão {{ app.version }}. O download instala a atualização e reinicia o aplicativo. Suas conversas e painéis são preservados.
                </p>
              </div>

              <div v-if="dadosNovos" class="rounded-xl border border-border-subtle bg-surface p-4 dark:border-white/[0.1]">
                <div class="flex items-center gap-2 text-sm font-semibold text-text-primary">
                  <Database class="h-4 w-4 shrink-0 text-[var(--brand-primary)] dark:text-[#68d388]" />
                  <span>Dados novos</span>
                </div>
                <p class="mt-1.5 text-xs leading-relaxed text-text-secondary">
                  Versão {{ dadosNovos.versao }} ({{ tamanhoMb(dadosNovos.tamanho) }}). Não precisa reinstalar o aplicativo.
                </p>
                <div v-if="dadosNovos.precisa_chave" class="mt-3 flex flex-col gap-2">
                  <p class="text-xs text-amber-700 dark:text-amber-300">A chave dos dados mudou. Informe a nova chave.</p>
                  <input
                    v-model="chave"
                    type="password"
                    autocomplete="off"
                    spellcheck="false"
                    placeholder="Nova chave dos dados"
                    class="rounded-lg border border-border-subtle bg-surface-elevated/60 px-3 py-2 text-sm placeholder:text-text-muted focus:border-[var(--brand-primary)] focus:outline-none"
                  />
                </div>
              </div>

              <p v-if="erro" class="text-xs text-[#C50707] dark:text-red-300">{{ erro }}</p>

              <div class="flex items-center gap-3 pt-2">
                <button
                  type="button"
                  class="flex-1 cursor-pointer rounded-xl border border-border-standard bg-surface px-4 py-2.5 text-sm font-medium text-text-primary transition-colors hover:bg-surface-elevated focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-primary)] disabled:opacity-50"
                  :disabled="ocupado"
                  @click="depois"
                >
                  Deixar para depois
                </button>
                <button
                  type="submit"
                  class="flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-xl bg-[var(--brand-primary)] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[var(--brand-dark)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-primary)] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="!podeBaixar"
                >
                  <template v-if="instalandoApp">
                    <Loader2 class="h-4 w-4 animate-spin" />
                    <span>{{ progressoApp > 0 ? `Baixando… ${Math.round(progressoApp * 100)}%` : 'Baixando…' }}</span>
                  </template>
                  <template v-else-if="instalandoDados">
                    <Loader2 class="h-4 w-4 animate-spin" />
                    <span>Baixando…</span>
                  </template>
                  <template v-else>Baixar agora</template>
                </button>
              </div>
            </form>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>
