<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CheckCircle2, KeyRound, ShieldAlert, Trash2 } from 'lucide-vue-next'
import { isTauri } from '@/common/api/config'
import { clearKey, keyStatus, testAndSaveKey, type KeyStatus } from '@/common/api/llmKey'
import { useAuth } from '@/modules/auth/composables/useAuth'

const { user, loadLocalUser } = useAuth()

const status = ref<KeyStatus | null>(null)
const key = ref('')
const busy = ref(false)
const message = ref<{ type: 'ok' | 'error'; text: string } | null>(null)

const desktop = isTauri()
const configured = computed(() => status.value?.configured ?? !!user.value?.llm_configured)

async function refresh() {
  status.value = await keyStatus()
  await loadLocalUser()
}

async function save() {
  if (!key.value.trim()) return
  busy.value = true
  message.value = null
  try {
    const result = await testAndSaveKey(key.value.trim())
    if (result.ok) {
      key.value = ''
      message.value = { type: 'ok', text: 'Chave válida e guardada no cofre do sistema. O chat já pode ser usado.' }
      await refresh()
    } else {
      message.value = { type: 'error', text: result.reason || 'Não foi possível validar a chave.' }
    }
  } catch (err: any) {
    message.value = { type: 'error', text: String(err?.message || err) }
  } finally {
    busy.value = false
  }
}

async function remove() {
  busy.value = true
  message.value = null
  try {
    await clearKey()
    message.value = { type: 'ok', text: 'Chave removida do cofre do sistema.' }
    await refresh()
  } catch (err: any) {
    message.value = { type: 'error', text: String(err?.message || err) }
  } finally {
    busy.value = false
  }
}

onMounted(() => {
  refresh().catch(() => {})
})
</script>

<template>
  <div class="mx-auto flex max-w-2xl flex-col gap-6 p-6 text-text-primary">
    <h1 class="text-xl font-semibold text-text-primary">Configurações</h1>

    <section class="rounded-xl border border-border-subtle bg-surface p-5 shadow-premium">
      <div class="mb-3 flex items-center gap-2">
        <KeyRound class="h-5 w-5 text-[var(--brand-primary)] dark:text-[#68d388]" />
        <h2 class="font-semibold text-text-primary">Chave do Gemini</h2>
        <span
          :class="[
            'ml-auto rounded-full border px-2.5 py-0.5 text-xs font-semibold',
            configured
              ? 'border-emerald-300/70 bg-emerald-100 text-emerald-800 dark:border-emerald-500/35 dark:bg-emerald-950/70 dark:text-emerald-300'
              : 'border-amber-300/80 bg-amber-100 text-amber-800 dark:border-amber-500/40 dark:bg-amber-950/80 dark:text-amber-300'
          ]"
        >
          {{ configured ? 'Configurada' : 'Não configurada' }}
        </span>
      </div>

      <p class="mb-4 text-sm text-text-secondary">
        O chat usa a API do Gemini com a sua chave. Ela fica no cofre do sistema operacional
        (Secret Service no Linux, Gerenciador de Credenciais no Windows), nunca em arquivo do app.
      </p>

      <p v-if="!desktop" class="rounded-lg border border-amber-300/60 bg-amber-50/80 px-3 py-2 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-950/50 dark:text-amber-300">
        A chave só pode ser configurada no app desktop. No navegador de desenvolvimento, use a variável GEMINI_API_KEY do backend.
      </p>

      <p v-else-if="status && !status.store_available" class="flex items-start gap-2 text-sm text-[#C50707] dark:text-red-300">
        <ShieldAlert class="mt-0.5 h-4 w-4 shrink-0" />
        Cofre do sistema indisponível: {{ status.error }}
      </p>

      <form v-else class="flex flex-col gap-3 sm:flex-row" @submit.prevent="save">
        <input
          v-model="key"
          type="password"
          autocomplete="off"
          spellcheck="false"
          :placeholder="configured ? 'Nova chave (substitui a atual)' : 'Cole a sua chave do Gemini'"
          class="min-w-0 flex-1 rounded-md border border-border-subtle bg-surface-elevated/60 px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-[var(--brand-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--brand-primary)]/20"
        />
        <button
          type="submit"
          :disabled="busy || !key.trim()"
          class="btn-primary disabled:opacity-50"
        >
          {{ busy ? 'Testando…' : 'Testar e salvar' }}
        </button>
        <button
          v-if="configured"
          type="button"
          :disabled="busy"
          class="flex items-center justify-center gap-1.5 rounded-md border border-[#C50707]/30 px-3 py-2 text-sm text-[#C50707] hover:bg-[#C50707]/8 disabled:opacity-50 dark:border-red-400/40 dark:text-red-300 dark:hover:bg-red-500/15"
          @click="remove"
        >
          <Trash2 class="h-4 w-4" /> Remover
        </button>
      </form>

      <p
        v-if="message"
        :class="['mt-3 flex items-start gap-2 text-sm', message.type === 'ok' ? 'text-emerald-600 dark:text-emerald-300' : 'text-[#C50707] dark:text-red-300']"
      >
        <CheckCircle2 v-if="message.type === 'ok'" class="mt-0.5 h-4 w-4 shrink-0" />
        <ShieldAlert v-else class="mt-0.5 h-4 w-4 shrink-0" />
        {{ message.text }}
      </p>
    </section>

    <section class="rounded-xl border border-border-subtle bg-surface p-5 text-sm shadow-premium">
      <h2 class="mb-2 font-semibold text-text-primary">O que sai do seu computador</h2>
      <p class="mb-2 text-text-secondary">Para responder, o app envia ao Gemini:</p>
      <ul class="mb-3 list-disc space-y-1 pl-5 text-text-secondary">
        <li>a pergunta que você digita (nomes escritos na pergunta também vão);</li>
        <li>o esquema das views do contexto, as regras e os exemplos, sem as colunas sensíveis;</li>
        <li>os valores únicos das colunas marcadas para busca semântica, ao carregar os dados;</li>
        <li>uma prévia de até 5 linhas do resultado de cada consulta, que entra no histórico da conversa.</li>
      </ul>
      <p class="text-text-secondary">
        Não saem: o arquivo de dados inteiro, as colunas declaradas como sensíveis e as tabelas fora das views do contexto.
        Os dados ficam neste computador; a proteção deles é a sua conta do sistema e a criptografia de disco (BitLocker ou LUKS).
      </p>
    </section>
  </div>
</template>
