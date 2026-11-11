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
  <div class="mx-auto flex max-w-2xl flex-col gap-6 p-6 text-slate-700 dark:text-slate-200">
    <h1 class="text-xl font-semibold">Configurações</h1>

    <section class="rounded-xl border border-slate-200 bg-white p-5 dark:border-white/10 dark:bg-white/5">
      <div class="mb-3 flex items-center gap-2">
        <KeyRound class="h-5 w-5" />
        <h2 class="font-semibold">Chave da Mistral</h2>
        <span
          :class="[
            'ml-auto rounded-full px-2.5 py-0.5 text-xs font-medium',
            configured
              ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300'
              : 'bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300'
          ]"
        >
          {{ configured ? 'Configurada' : 'Não configurada' }}
        </span>
      </div>

      <p class="mb-4 text-sm text-slate-500 dark:text-slate-400">
        O chat usa a API da Mistral com a sua chave. Ela fica no cofre do sistema operacional
        (Secret Service no Linux, Gerenciador de Credenciais no Windows), nunca em arquivo do app.
      </p>

      <p v-if="!desktop" class="text-sm text-amber-600">
        A chave só pode ser configurada no app desktop. No navegador de desenvolvimento, use a variável MISTRAL_API_KEY do backend.
      </p>

      <p v-else-if="status && !status.store_available" class="flex items-start gap-2 text-sm text-red-600">
        <ShieldAlert class="mt-0.5 h-4 w-4 shrink-0" />
        Cofre do sistema indisponível: {{ status.error }}
      </p>

      <form v-else class="flex flex-col gap-3 sm:flex-row" @submit.prevent="save">
        <input
          v-model="key"
          type="password"
          autocomplete="off"
          spellcheck="false"
          :placeholder="configured ? 'Nova chave (substitui a atual)' : 'Cole a sua chave da Mistral'"
          class="min-w-0 flex-1 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm dark:border-white/10 dark:bg-white/5"
        />
        <button
          type="submit"
          :disabled="busy || !key.trim()"
          class="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-slate-900"
        >
          {{ busy ? 'Testando…' : 'Testar e salvar' }}
        </button>
        <button
          v-if="configured"
          type="button"
          :disabled="busy"
          class="flex items-center justify-center gap-1.5 rounded-md border border-red-200 px-3 py-2 text-sm text-red-600 disabled:opacity-50 dark:border-red-500/30"
          @click="remove"
        >
          <Trash2 class="h-4 w-4" /> Remover
        </button>
      </form>

      <p
        v-if="message"
        :class="['mt-3 flex items-start gap-2 text-sm', message.type === 'ok' ? 'text-emerald-600' : 'text-red-600']"
      >
        <CheckCircle2 v-if="message.type === 'ok'" class="mt-0.5 h-4 w-4 shrink-0" />
        <ShieldAlert v-else class="mt-0.5 h-4 w-4 shrink-0" />
        {{ message.text }}
      </p>
    </section>

    <section class="rounded-xl border border-slate-200 bg-white p-5 text-sm dark:border-white/10 dark:bg-white/5">
      <h2 class="mb-2 font-semibold">O que sai do seu computador</h2>
      <p class="mb-2 text-slate-500 dark:text-slate-400">Para responder, o app envia à Mistral:</p>
      <ul class="mb-3 list-disc space-y-1 pl-5">
        <li>a pergunta que você digita (nomes escritos na pergunta também vão);</li>
        <li>o esquema das views do contexto, as regras e os exemplos, sem as colunas sensíveis;</li>
        <li>os valores únicos das colunas marcadas para busca semântica, ao carregar os dados;</li>
        <li>uma prévia de até 5 linhas do resultado de cada consulta, que entra no histórico da conversa.</li>
      </ul>
      <p class="text-slate-500 dark:text-slate-400">
        Não saem: o arquivo de dados inteiro, as colunas declaradas como sensíveis e as tabelas fora das views do contexto.
        Os dados ficam neste computador; a proteção deles é a sua conta do sistema e a criptografia de disco (BitLocker ou LUKS).
      </p>
    </section>
  </div>
</template>
