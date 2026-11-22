<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ArrowRight, Database, Download, Loader2, X } from 'lucide-vue-next'
import { useAtualizacoes } from '@/common/composables/useAtualizacoes'

/**
 * Aviso discreto no rodapé da barra lateral, como o "Atualização disponível" do Claude:
 * não abre sozinho nem bloqueia o uso. Clicar mostra o que há de novo e o usuário escolhe.
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
const raiz = ref<HTMLElement | null>(null)
const painel = ref<HTMLElement | null>(null)
// O painel vai para o <body>: a barra lateral corta o que passa da borda (overflow-hidden).
const posicao = ref<Record<string, string>>({})
const ocupado = computed(() => instalandoApp.value || instalandoDados.value)

function tamanhoMb(bytes: number) {
  return `${(bytes / 1024 / 1024).toFixed(1).replace('.', ',')} MB`
}

function posicionar() {
  const r = raiz.value?.getBoundingClientRect()
  if (!r) return
  posicao.value = props.collapsed
    ? { left: `${r.right + 8}px`, bottom: `${window.innerHeight - r.bottom}px`, width: '18rem' }
    : { left: `${r.left}px`, bottom: `${window.innerHeight - r.top + 8}px`, width: `${Math.max(r.width, 240)}px` }
}

function alternar() {
  aberto.value = !aberto.value
  if (aberto.value) posicionar()
  else limparErro()
}

function depois() {
  aberto.value = false
  limparErro()
}

async function atualizarDados() {
  const ok = await instalarDados(dadosNovos.value?.precisa_chave ? chave.value : undefined)
  if (ok) chave.value = ''
}

function fora(ev: MouseEvent) {
  const alvo = ev.target as Node
  if (aberto.value && !ocupado.value && !raiz.value?.contains(alvo) && !painel.value?.contains(alvo)) depois()
}

function reposicionar() {
  if (aberto.value) posicionar()
}

onMounted(() => {
  document.addEventListener('mousedown', fora)
  window.addEventListener('resize', reposicionar)
})
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', fora)
  window.removeEventListener('resize', reposicionar)
})
</script>

<template>
  <div v-if="temAtualizacao" ref="raiz" class="relative" data-testid="atualizacao-disponivel">
    <button
      type="button"
      :aria-expanded="aberto"
      :title="props.collapsed ? 'Atualização disponível' : undefined"
      :class="[
        'flex w-full items-center gap-2 rounded-md border border-white/[0.14] bg-white/[0.08] text-[13px] font-medium text-white transition-colors hover:bg-white/[0.14]',
        props.collapsed ? 'justify-center p-3' : 'px-3.5 py-2.5'
      ]"
      @click="alternar"
    >
      <span class="relative flex h-2 w-2 shrink-0">
        <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#68d388] opacity-60" />
        <span class="relative inline-flex h-2 w-2 rounded-full bg-[#68d388]" />
      </span>
      <template v-if="!props.collapsed">
        <span class="flex-1 text-left">Atualização disponível</span>
        <ArrowRight class="h-4 w-4 text-white/70" />
      </template>
    </button>

    <Teleport to="body">
    <div
      v-if="aberto"
      ref="painel"
      role="dialog"
      aria-label="Atualizações do Adito"
      :style="posicao"
      class="fixed z-[70] rounded-xl border border-border-subtle bg-surface p-4 text-sm text-text-primary shadow-premium"
    >
      <div class="mb-3 flex items-center justify-between">
        <h3 class="font-semibold">Atualizações</h3>
        <button type="button" aria-label="Fechar" class="rounded p-1 text-text-muted hover:text-text-primary" :disabled="ocupado" @click="depois">
          <X class="h-4 w-4" />
        </button>
      </div>

      <div v-if="app" class="mb-3 rounded-lg border border-border-subtle p-3">
        <div class="mb-1 flex items-center gap-2 font-medium">
          <Download class="h-4 w-4 text-[var(--brand-primary)] dark:text-[#68d388]" />
          Nova versão do Adito
        </div>
        <p class="mb-2 text-xs text-text-secondary">
          Versão {{ app.version }}. O app reinicia no fim; suas conversas e painéis continuam.
        </p>
        <button type="button" class="btn-primary w-full disabled:opacity-50" :disabled="ocupado" @click="instalarApp">
          <template v-if="instalandoApp">
            <Loader2 class="mr-1 inline h-4 w-4 animate-spin" />
            {{ progressoApp > 0 ? `Baixando… ${Math.round(progressoApp * 100)}%` : 'Baixando…' }}
          </template>
          <template v-else>Atualizar o app</template>
        </button>
      </div>

      <div v-if="dadosNovos" class="mb-3 rounded-lg border border-border-subtle p-3">
        <div class="mb-1 flex items-center gap-2 font-medium">
          <Database class="h-4 w-4 text-[var(--brand-primary)] dark:text-[#68d388]" />
          Dados novos
        </div>
        <p class="mb-2 text-xs text-text-secondary">
          Versão {{ dadosNovos.versao }} ({{ tamanhoMb(dadosNovos.tamanho) }}). Não precisa reinstalar o app.
        </p>
        <form class="flex flex-col gap-2" @submit.prevent="atualizarDados">
          <template v-if="dadosNovos.precisa_chave">
            <p class="text-xs text-amber-700 dark:text-amber-300">A chave dos dados mudou. Informe a nova chave.</p>
            <input
              v-model="chave"
              type="password"
              autocomplete="off"
              spellcheck="false"
              placeholder="Nova chave dos dados"
              class="rounded-md border border-border-subtle bg-surface-elevated/60 px-3 py-2 text-sm placeholder:text-text-muted focus:border-[var(--brand-primary)] focus:outline-none"
            />
          </template>
          <button
            type="submit"
            class="btn-primary w-full disabled:opacity-50"
            :disabled="ocupado || (dadosNovos.precisa_chave && !chave.trim())"
          >
            <template v-if="instalandoDados">
              <Loader2 class="mr-1 inline h-4 w-4 animate-spin" /> Baixando e conferindo…
            </template>
            <template v-else>Atualizar os dados</template>
          </button>
        </form>
      </div>

      <p v-if="erro" class="mb-3 text-xs text-[#C50707] dark:text-red-300">{{ erro }}</p>

      <button
        type="button"
        class="w-full rounded-md px-3 py-1.5 text-xs text-text-secondary hover:bg-surface-elevated disabled:opacity-50"
        :disabled="ocupado"
        @click="depois"
      >
        Depois
      </button>
    </div>
    </Teleport>
  </div>
</template>
