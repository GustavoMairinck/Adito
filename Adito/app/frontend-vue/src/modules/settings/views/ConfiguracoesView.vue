<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CheckCircle2, ChevronDown, ChevronUp, Database, Eye, EyeOff, Info, KeyRound, RefreshCw, ShieldAlert, ShieldCheck, Trash2 } from 'lucide-vue-next'
import {
  clearKey,
  DEFAULT_LLM_PROVIDERS,
  isLoopbackUrl,
  listProviders,
  llmConfigStatus,
  testAndSaveConfig,
  type LlmConfigStatus,
  type LlmProviderSpec,
} from '@/common/api/llmKey'
import ConfirmModal from '@/common/components/feedback/ConfirmModal.vue'
import { useAtualizacoes } from '@/common/composables/useAtualizacoes'
import { useAuth } from '@/modules/auth/composables/useAuth'
import { formatBaseVersion } from '@/modules/chat/utils/historyGroups'
import ProviderSelect from '@/modules/settings/components/ProviderSelect.vue'

const { user, loadLocalUser } = useAuth()
const {
  status: baseStatus,
  app: appUpdate,
  dadosNovos,
  verificando,
  erroVerificacao,
  verificar,
  autoAtualizar,
  setAutoAtualizar,
} = useAtualizacoes()

function handleAutoUpdateToggle(event: Event) {
  const checked = (event.target as HTMLInputElement).checked
  setAutoAtualizar(checked)
}

const providers = ref<LlmProviderSpec[]>([...DEFAULT_LLM_PROVIDERS])
const status = ref<LlmConfigStatus | null>(null)
const selectedProviderId = ref<string>('gemini')
const model = ref<string>(DEFAULT_LLM_PROVIDERS[0].default_model)
const baseUrl = ref<string>('')
const key = ref<string>('')
const showKey = ref(false)
const confirmRemoveOpen = ref(false)
const showAdvanced = ref(false)
const busy = ref(false)
const message = ref<{ type: 'ok' | 'error'; text: string } | null>(null)
const baseCheckFeedback = ref<{ type: 'info' | 'error'; text: string } | null>(null)

const formattedBaseSync = computed(() => formatBaseVersion(baseStatus.value?.versao))

async function checkUpdatesNow() {
  baseCheckFeedback.value = null
  await verificar({ forcar: true })
  if (baseStatus.value?.desenvolvimento) {
    baseCheckFeedback.value = {
      type: 'info',
      text: 'Modo desenvolvimento: a base local do repositório é usada diretamente.',
    }
    return
  }
  if (erroVerificacao.value) {
    baseCheckFeedback.value = {
      type: 'error',
      text: 'Não foi possível verificar atualizações agora (sem conexão ou serviço indisponível).',
    }
    return
  }
  if (appUpdate.value && dadosNovos.value) {
    baseCheckFeedback.value = {
      type: 'info',
      text: `Há novas versões do aplicativo (${appUpdate.value.version}) e da base de dados (${formatBaseVersion(dadosNovos.value.versao) || dadosNovos.value.versao}) disponíveis.`,
    }
    return
  }
  if (appUpdate.value) {
    baseCheckFeedback.value = {
      type: 'info',
      text: `Nova versão do aplicativo disponível (${appUpdate.value.version}). Use "Atualização disponível" na barra lateral.`,
    }
    return
  }
  if (dadosNovos.value) {
    baseCheckFeedback.value = {
      type: 'info',
      text: `Nova versão de dados disponível (${formatBaseVersion(dadosNovos.value.versao) || dadosNovos.value.versao}).`,
    }
    return
  }
  if (!baseStatus.value) {
    baseCheckFeedback.value = {
      type: 'error',
      text: 'Não foi possível consultar o status da base local no momento.',
    }
    return
  }
  baseCheckFeedback.value = {
    type: 'info',
    text: 'Aplicativo e base local já estão na versão mais recente.',
  }
}

const selectedProvider = computed<LlmProviderSpec>(
  () => providers.value.find((p) => p.id === selectedProviderId.value) ?? providers.value[0]
)

// Prioriza `user` (retornado pelo núcleo Python em execução via RPC `me`) para refletir
// exatamente qual provedor e modelo estão respondendo no chat neste momento.
const activeProviderId = computed(() => user.value?.llm_provider || status.value?.provider || 'gemini')
const activeProviderLabel = computed(
  () =>
    user.value?.llm_provider_label ||
    providers.value.find((p) => p.id === activeProviderId.value)?.label ||
    'Gemini'
)
const activeModel = computed(() => user.value?.llm_model || status.value?.model || '')
const configured = computed(() => {
  if (typeof user.value?.llm_configured === 'boolean') return user.value.llm_configured
  return Boolean(status.value?.configured)
})
const inUseProviderId = computed(() => (configured.value ? activeProviderId.value : undefined))

const selectedHasSavedKey = computed(() => Boolean(status.value?.has_key_by_provider?.[selectedProviderId.value]))

const effectiveBaseUrl = computed(() => {
  const typed = baseUrl.value.trim()
  if (typed) return typed
  return selectedProvider.value.base_url
})

const selectedIsLocal = computed(
  () => selectedProvider.value.protocol === 'openai_compatible' && isLoopbackUrl(effectiveBaseUrl.value)
)

const showBaseUrlField = computed(
  () => selectedProvider.value.allow_custom_base_url && showAdvanced.value
)

const canSubmit = computed(() => {
  if (busy.value) return false
  if (!model.value.trim()) return false
  if (selectedIsLocal.value) return true
  return Boolean(key.value.trim() || selectedHasSavedKey.value)
})

const keyPlaceholder = computed(() => {
  if (selectedIsLocal.value) return 'Opcional para servidor local (localhost)'
  if (selectedHasSavedKey.value) return 'Chave já salva no cofre (deixe vazio para reutilizar ou cole nova)'
  return `Cole a sua chave de API (${selectedProvider.value.label})`
})

function applyProviderDefaults(providerId: string, savedStatus?: LlmConfigStatus | null) {
  const spec = providers.value.find((p) => p.id === providerId) ?? providers.value[0]
  const isActive = savedStatus && savedStatus.provider === spec.id
  model.value = (isActive && savedStatus.model) || spec.default_model
  baseUrl.value = (isActive && savedStatus.base_url) || spec.base_url
  showAdvanced.value = Boolean(isActive && savedStatus.base_url && savedStatus.base_url !== spec.base_url)
  key.value = ''
}

function handleProviderChange() {
  message.value = null
  applyProviderDefaults(selectedProviderId.value, status.value)
}

async function refresh() {
  const [loadedProviders, loadedStatus] = await Promise.all([
    listProviders(),
    llmConfigStatus(),
    loadLocalUser(),
  ])
  providers.value = loadedProviders
  status.value = loadedStatus
  selectedProviderId.value = loadedStatus.provider || 'gemini'
  applyProviderDefaults(selectedProviderId.value, loadedStatus)
}

async function save() {
  if (!canSubmit.value) return
  busy.value = true
  message.value = null
  const typedKey = key.value.trim()
  const useSavedKey = !typedKey && selectedHasSavedKey.value
  const spec = selectedProvider.value
  const customUrl =
    spec.allow_custom_base_url && baseUrl.value.trim() && baseUrl.value.trim() !== spec.base_url
      ? baseUrl.value.trim()
      : undefined

  try {
    const result = await testAndSaveConfig({
      provider: spec.id,
      model: model.value.trim(),
      baseUrl: customUrl,
      key: typedKey || undefined,
      useSavedKey,
    })
    if (result.ok) {
      key.value = ''
      message.value = {
        type: 'ok',
        text: selectedIsLocal.value
          ? `Conexão validada e provedor local (${spec.label}) ativado. O chat já pode ser usado.`
          : `Chave válida e guardada no cofre do sistema para ${spec.label}. O chat já pode ser usado.`,
      }
      await refresh()
    } else {
      message.value = { type: 'error', text: result.reason || 'Não foi possível validar a configuração.' }
    }
  } catch (err: unknown) {
    const errMsg = err instanceof Error ? err.message : String(err)
    message.value = { type: 'error', text: errMsg }
  } finally {
    busy.value = false
  }
}

async function remove() {
  confirmRemoveOpen.value = false
  busy.value = true
  message.value = null
  const label = selectedProvider.value.label
  try {
    await clearKey(selectedProviderId.value)
    message.value = { type: 'ok', text: `Chave de ${label} removida do cofre do sistema.` }
    await refresh()
  } catch (err: unknown) {
    const errMsg = err instanceof Error ? err.message : String(err)
    message.value = { type: 'error', text: errMsg }
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
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <KeyRound class="h-5 w-5 text-[var(--brand-primary)] dark:text-[#68d388]" />
        <h2 class="font-semibold text-text-primary">Provedor de IA</h2>
        <span
          :class="[
            'ml-auto rounded-full border px-2.5 py-0.5 text-xs font-semibold',
            configured
              ? 'border-emerald-300/70 bg-emerald-100 text-emerald-800 dark:border-emerald-500/35 dark:bg-emerald-950/70 dark:text-emerald-300'
              : 'border-amber-300/80 bg-amber-100 text-amber-800 dark:border-amber-500/40 dark:bg-amber-950/80 dark:text-amber-300',
          ]"
        >
          {{ configured ? 'Configurada' : 'Não configurada' }}
        </span>
      </div>

      <p class="mb-4 text-sm text-text-secondary">
        Escolha o provedor de IA que deseja usar no chat (BYOK). As chaves ficam isoladas por provedor no cofre do
        sistema operacional (Secret Service no Linux, Gerenciador de Credenciais no Windows), nunca em arquivo de texto.
      </p>

      <div
        v-if="configured"
        class="mb-4 flex flex-wrap items-center gap-2 rounded-lg border border-[var(--brand-primary)]/25 bg-[var(--accent-light)] px-3.5 py-2.5 text-xs dark:border-[#68d388]/30"
      >
        <span class="inline-flex items-center gap-1.5 rounded-full bg-[var(--brand-primary)] px-2.5 py-0.5 text-[10px] font-semibold text-white">
          <span class="h-1.5 w-1.5 rounded-full bg-[#8ef0aa]" aria-hidden="true" />
          Em uso
        </span>
        <span class="font-semibold text-[var(--brand-dark)] dark:text-[#F0F4F1]">
          {{ activeProviderLabel }}
        </span>
        <span v-if="activeModel" class="text-text-muted">·</span>
        <code v-if="activeModel" class="font-mono text-text-secondary">{{ activeModel }}</code>
      </div>

      <p v-if="status && !status.store_available" class="flex items-start gap-2 text-sm text-[#C50707] dark:text-red-300">
        <ShieldAlert class="mt-0.5 h-4 w-4 shrink-0" />
        Cofre do sistema indisponível: {{ status.error }}
      </p>

      <form v-else class="flex flex-col gap-4" @submit.prevent="save">
        <div class="grid gap-4 sm:grid-cols-2">
          <div class="flex flex-col gap-1.5">
            <label id="llm-provider-label" for="llm-provider" class="eyebrow px-0.5">
              Provedor
            </label>
            <ProviderSelect
              id="llm-provider"
              v-model="selectedProviderId"
              labelled-by="llm-provider-label"
              :providers="providers"
              :active-provider-id="inUseProviderId"
              :has-key-by-provider="status?.has_key_by_provider"
              :disabled="busy"
              @change="handleProviderChange"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label for="llm-model" class="eyebrow px-0.5">
              Modelo
            </label>
            <input
              id="llm-model"
              v-model="model"
              type="text"
              autocomplete="off"
              spellcheck="false"
              :disabled="busy"
              :placeholder="selectedProvider.default_model || 'Ex.: gpt-4o-mini ou qwen2.5:7b'"
              class="min-h-[42px] rounded-lg border border-border-subtle bg-surface px-3 py-2 font-mono text-sm text-text-primary shadow-card placeholder:font-sans placeholder:text-text-muted transition-colors hover:border-[var(--brand-primary)]/50 focus:border-[var(--brand-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--brand-primary)]/20 dark:hover:border-[#68d388]/50 dark:focus:border-[#68d388]"
            />
          </div>
        </div>

        <div v-if="selectedProvider.allow_custom_base_url">
          <button
            type="button"
            class="inline-flex items-center gap-1 text-xs font-medium text-[var(--brand-primary)] hover:underline dark:text-[#68d388]"
            @click="showAdvanced = !showAdvanced"
          >
            <ChevronUp v-if="showAdvanced" class="h-3.5 w-3.5" />
            <ChevronDown v-else class="h-3.5 w-3.5" />
            Opções avançadas (Base URL)
          </button>
        </div>

        <div v-if="showBaseUrlField" class="flex flex-col gap-1.5">
          <label for="llm-base-url" class="eyebrow px-0.5">
            Base URL (OpenAI-compatível)
          </label>
          <input
            id="llm-base-url"
            v-model="baseUrl"
            type="url"
            autocomplete="off"
            spellcheck="false"
            :disabled="busy"
            :placeholder="selectedProvider.base_url || 'https://api.exemplo.com/v1'"
            class="min-h-[42px] rounded-lg border border-border-subtle bg-surface px-3 py-2 font-mono text-sm text-text-primary shadow-card placeholder:font-sans placeholder:text-text-muted transition-colors hover:border-[var(--brand-primary)]/50 focus:border-[var(--brand-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--brand-primary)]/20 dark:hover:border-[#68d388]/50 dark:focus:border-[#68d388]"
          />
        </div>

        <div class="flex flex-col gap-1.5">
          <label for="llm-api-key" class="eyebrow px-0.5">
            Chave API {{ selectedIsLocal ? '(opcional para servidor local)' : '' }}
          </label>
          <div class="relative flex items-center">
            <input
              id="llm-api-key"
              v-model="key"
              :type="showKey ? 'text' : 'password'"
              autocomplete="off"
              spellcheck="false"
              :disabled="busy"
              :placeholder="keyPlaceholder"
              class="min-h-[42px] min-w-0 flex-1 rounded-lg border border-border-subtle bg-surface py-2 pl-3 pr-10 text-sm text-text-primary shadow-card placeholder:text-text-muted transition-colors hover:border-[var(--brand-primary)]/50 focus:border-[var(--brand-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--brand-primary)]/20 dark:hover:border-[#68d388]/50 dark:focus:border-[#68d388]"
            />
            <button
              type="button"
              class="absolute right-2 rounded-md p-1.5 text-text-muted transition-colors hover:bg-surface-elevated hover:text-text-primary"
              :aria-label="showKey ? 'Ocultar valor da chave' : 'Mostrar valor da chave'"
              :title="showKey ? 'Ocultar chave' : 'Mostrar chave'"
              @click="showKey = !showKey"
            >
              <EyeOff v-if="showKey" class="h-4 w-4" />
              <Eye v-else class="h-4 w-4" />
            </button>
          </div>
          <p v-if="selectedHasSavedKey && !selectedIsLocal" class="text-xs text-[var(--brand-primary)] dark:text-[#68d388]">
            Já existe uma chave salva no cofre para {{ selectedProvider.label }}. Você pode trocar de provedor ou modelo
            sem precisar digitá-la novamente.
          </p>
          <p v-else-if="selectedIsLocal" class="text-xs text-text-muted">
            Endpoint local (<code class="font-mono">{{ effectiveBaseUrl }}</code>): a chave pode ficar vazia.
          </p>
        </div>

        <p
          v-if="!selectedProvider.supports_embeddings"
          class="flex items-start gap-2 rounded-lg border border-amber-300/60 bg-amber-50/70 px-3 py-2 text-xs text-amber-900 dark:border-amber-500/30 dark:bg-amber-950/30 dark:text-amber-200"
        >
          <Info class="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            {{ selectedProvider.label }} funciona em modo só-chat: o Adito usa fallback textual automático (regras, views,
            exemplos e busca local) sem precisar gerar embeddings.
          </span>
        </p>

        <div class="flex flex-wrap items-center gap-3">
          <button type="submit" :disabled="!canSubmit" class="btn-primary disabled:opacity-50">
            {{ busy ? 'Testando…' : 'Testar e salvar' }}
          </button>
          <button
            v-if="selectedHasSavedKey"
            type="button"
            :disabled="busy"
            class="flex items-center justify-center gap-1.5 rounded-md border border-[#C50707]/30 px-3 py-2 text-sm text-[#C50707] hover:bg-[#C50707]/8 disabled:opacity-50 dark:border-red-400/40 dark:text-red-300 dark:hover:bg-red-500/15"
            @click="confirmRemoveOpen = true"
          >
            <Trash2 class="h-4 w-4" /> Remover
          </button>
        </div>
      </form>

      <ConfirmModal
        :is-open="confirmRemoveOpen"
        title="Remover chave de API"
        :message="`Tem certeza que deseja remover a chave salva de ${selectedProvider.label} do cofre do sistema?`"
        confirm-text="Remover chave"
        cancel-text="Cancelar"
        @confirm="remove"
        @close="confirmRemoveOpen = false"
      />

      <p
        v-if="message"
        role="status"
        :class="[
          'mt-3 flex items-start gap-2 text-sm',
          message.type === 'ok' ? 'text-emerald-600 dark:text-emerald-300' : 'text-[#C50707] dark:text-red-300',
        ]"
      >
        <CheckCircle2 v-if="message.type === 'ok'" class="mt-0.5 h-4 w-4 shrink-0" />
        <ShieldAlert v-else class="mt-0.5 h-4 w-4 shrink-0" />
        {{ message.text }}
      </p>
    </section>

    <section class="rounded-xl border border-border-subtle bg-surface p-5 shadow-premium">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex items-center gap-2.5">
          <Database class="h-5 w-5 text-[var(--brand-primary)] dark:text-[#68d388]" />
          <div>
            <h2 class="font-semibold text-text-primary">Base de dados local</h2>
            <p class="text-xs text-text-secondary">
              <template v-if="formattedBaseSync">
                Última sincronização semanal: <strong class="text-text-primary">{{ formattedBaseSync }}</strong>
              </template>
              <template v-else-if="baseStatus?.desenvolvimento">
                Usando base local do repositório (modo desenvolvimento).
              </template>
              <template v-else>
                Sincronizada semanalmente (SigPesq, Lattes, CNPq e SRC).
              </template>
            </p>
          </div>
        </div>
        <button
          type="button"
          :disabled="verificando"
          class="btn-secondary inline-flex items-center gap-1.5 text-xs disabled:opacity-50"
          @click="checkUpdatesNow"
        >
          <RefreshCw :class="['h-3.5 w-3.5', verificando ? 'animate-spin' : '']" />
          {{ verificando ? 'Verificando…' : 'Verificar atualizações agora' }}
        </button>
      </div>
      <p
        v-if="baseCheckFeedback"
        role="status"
        :class="[
          'mt-3 text-xs',
          baseCheckFeedback.type === 'error' ? 'text-[#C50707] dark:text-red-300' : 'text-text-secondary',
        ]"
      >
        {{ baseCheckFeedback.text }}
      </p>
    </section>

    <section class="rounded-xl border border-border-subtle bg-surface p-5 shadow-premium">
      <div class="mb-3 flex flex-wrap items-center gap-2">
        <RefreshCw class="h-5 w-5 text-[var(--brand-primary)] dark:text-[#68d388]" />
        <h2 class="font-semibold text-text-primary">Atualizações</h2>
      </div>

      <div class="flex items-start justify-between gap-4">
        <div class="space-y-1">
          <label
            for="auto-update-toggle"
            class="cursor-pointer text-sm font-medium text-text-primary"
          >
            Atualização automática (app e dados)
          </label>
          <p id="auto-update-desc" class="text-xs text-text-secondary">
            Quando ativada, o Adito verifica novas versões em segundo plano, baixa o executável sem interromper
            perguntas ativas no chat (exibindo contagem de 10 segundos com opção de adiar) e atualiza o banco
            <code class="font-mono">dados.db</code> recarregando as telas abertas automaticamente — sem reindexar
            embeddings. Desligada por padrão (modo assistido na barra lateral).
          </p>
        </div>

        <label class="relative mt-0.5 inline-flex h-6 w-11 shrink-0 cursor-pointer items-center">
          <input
            id="auto-update-toggle"
            type="checkbox"
            role="switch"
            aria-describedby="auto-update-desc"
            :aria-checked="autoAtualizar"
            :checked="autoAtualizar"
            class="peer absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0"
            @change="handleAutoUpdateToggle"
          />
          <span
            aria-hidden="true"
            class="pointer-events-none h-6 w-11 rounded-full border border-border-subtle bg-surface-elevated transition-colors peer-checked:border-[var(--brand-primary)] peer-checked:bg-[var(--brand-primary)] peer-focus-visible:ring-2 peer-focus-visible:ring-[var(--brand-primary)]/40 dark:peer-checked:border-[#68d388] dark:peer-checked:bg-[#2f9e59]"
          />
          <span
            aria-hidden="true"
            class="pointer-events-none absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform peer-checked:translate-x-5"
          />
        </label>
      </div>
    </section>

    <section class="rounded-xl border border-border-subtle bg-surface p-5 text-sm shadow-premium">
      <h2 class="mb-2 font-semibold text-text-primary">O que sai do seu computador</h2>

      <template v-if="selectedIsLocal">
        <p class="mb-2 flex items-start gap-2 text-emerald-700 dark:text-emerald-300">
          <ShieldCheck class="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            <strong>100% local — nenhum dado sai do seu computador.</strong>
            Com {{ selectedProvider.label }} em <code class="font-mono">{{ effectiveBaseUrl }}</code>, as perguntas,
            o esquema das views e os resumos de consulta permanecem na sua máquina.
          </span>
        </p>
      </template>

      <template v-else>
        <p class="mb-2 text-text-secondary">
          Para responder, o app envia para <strong>{{ selectedProvider.label }}</strong>:
        </p>
        <ul class="mb-3 list-disc space-y-1 pl-5 text-text-secondary">
          <li>a pergunta que você digita (nomes escritos na pergunta também vão);</li>
          <li>o esquema das views do contexto, as regras e os exemplos, sem as colunas sensíveis;</li>
          <li v-if="selectedProvider.supports_embeddings">
            os valores únicos das colunas marcadas para busca semântica, ao carregar ou reindexar os dados;
          </li>
          <li>uma prévia de até 5 linhas do resultado de cada consulta, que entra no histórico da conversa.</li>
        </ul>
      </template>

      <p class="text-text-secondary">
        Não saem: o arquivo de dados inteiro, as colunas declaradas como sensíveis e as tabelas fora das views do contexto.
        Os dados ficam neste computador; a proteção deles é a sua conta do sistema e a criptografia de disco (BitLocker ou LUKS).
      </p>
    </section>
  </div>
</template>
