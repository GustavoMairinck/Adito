<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { AlertCircle, CheckCircle2, RefreshCw } from 'lucide-vue-next'

import { exportarTabela } from '@/common/api/export'
import { useToast } from '@/common/composables/useToast'
import type { ExportFormat } from '@/common/utils/exportData'
import ChatConversation from '@/modules/chat/components/ChatConversation.vue'
import ChatInputArea from '@/modules/chat/components/ChatInputArea.vue'
import ChatReportForm, { type ReportOption } from '@/modules/chat/components/ChatReportForm.vue'
import { isReportEligible, questionFor } from '@/modules/chat/utils/report'
import type { ChatChartType } from '@/modules/chat/utils/chartType'
import DashboardPinDialog from '@/modules/dashboard/components/DashboardPinDialog.vue'
import ContextoSelector from '@/modules/chat/components/ContextoSelector.vue'
import { useContextos } from '@/common/composables/useContextos'
import { useAuth } from '@/modules/auth/composables/useAuth'
import { useChatApi } from '@/modules/chat/composables/useChatApi'
import { useChatHistory } from '@/modules/chat/composables/useChatHistory'
import { useChatPin } from '@/modules/chat/composables/useChatPin'
import { useAtualizacoes } from '@/common/composables/useAtualizacoes'
import type { ChatMessage, ReasoningTrace } from '@/modules/chat/types'
import { applyTraceEvent, createInitialTrace } from '@/modules/chat/utils/trace'

const route = useRoute()
const { toast, showToast } = useToast()

const {
  currentConvId,
  updateConversationById,
  replaceConversationId,
  setConversationContexto,
  currentConversation,
  createReport,
  reloadReports
} = useChatHistory()

// Relatórios guardam só o SQL: quando o dados.db é atualizado em segundo plano, recalcula os números.
const { dadosReloadSeq } = useAtualizacoes()
watch(dadosReloadSeq, (seq) => {
  if (seq > 0) void reloadReports(currentConvId.value)
})

const {
  askQuestionStream,
  cancelStream,
  checkHealth,
  isConversationLoading,
} = useChatApi()
const { selectedId: selectedContextoId, loadContextos } = useContextos()

const isCurrentConvLoading = computed(() => isConversationLoading(currentConvId.value))

// Conversa ainda não salva no backend: o contexto pode ser escolhido.
const isNewConversation = computed(() => !!currentConvId.value?.startsWith('local-'))

// Sem chave do Gemini o app abre, mas o chat fica desativado com o motivo à vista.
const { user } = useAuth()
const llmConfigured = computed(() => !!user.value?.llm_configured)

const {
  pinModalOpen,
  pinTitle,
  isPinning,
  openPinModal: openPinModalBase,
  savePin,
  closePin
} = useChatPin(showToast)

const input = ref('')

// ── Relatório (EPIC-14): modelo fixo a partir das respostas da conversa, sem LLM ──
const reportFormOpen = ref(false)
const reportSaving = ref(false)
const reportError = ref('')
const reportOptions = computed<ReportOption[]>(() => {
  const all = messages.value
  return all
    .filter(isReportEligible)
    .map(message => ({
      id: message.id,
      question: questionFor(all, message),
      chartType: message.chartType ?? message.suggestedChartType ?? null,
    }))
})
const canCreateReport = computed(() =>
  reportOptions.value.length > 0
  && !!currentConvId.value
  && !currentConvId.value.startsWith('local-')
  && !isCurrentConvLoading.value
)

const openReportForm = () => {
  reportError.value = ''
  reportFormOpen.value = true
}

const generateReport = async (payload: { title: string; sections: Array<{ message_id: string; title: string; chart_type?: string | null }> }) => {
  const convId = currentConvId.value
  if (!convId) return
  reportSaving.value = true
  reportError.value = ''
  try {
    await createReport(convId, payload.title, payload.sections)
    reportFormOpen.value = false
  } catch (error: any) {
    reportError.value = error?.data?.sections?.[0] || error?.data?.title?.[0] || 'Não foi possível gerar o relatório. Tente novamente.'
  } finally {
    reportSaving.value = false
  }
}

const rememberChartType = ({ id, type }: { id: string; type: ChatChartType }) => {
  if (!currentConvId.value) return
  updateConversationById(currentConvId.value, conversation => ({
    ...conversation,
    messages: conversation.messages.map(message => (message.id === id ? { ...message, chartType: type } : message)),
  }))
}

watch(currentConvId, () => { reportFormOpen.value = false })
const healthOnline = ref<boolean | null>(null)
const reconnecting = ref(false)

const retryConnection = async () => {
  if (reconnecting.value) return
  reconnecting.value = true
  try {
    const ok = await checkHealth()
    healthOnline.value = ok
    if (ok) {
      await loadContextos().catch(() => {})
    }
  } finally {
    reconnecting.value = false
  }
}

const messages = computed(() => currentConversation.value?.messages || [])
const starterCategories = [
  {
    key: 'pesquisa',
    label: 'Pesquisa',
    subtitle: 'Projetos & SigPesq',
    questions: [
      'Quantos projetos de pesquisa estão cadastrados por área de conhecimento?',
      'Quais pesquisadores coordenam mais projetos de pesquisa ativos?',
      'Qual a distribuição de projetos de pesquisa por campus e natureza?'
    ]
  },
  {
    key: 'extensao',
    label: 'Extensão',
    subtitle: 'Ações & SRC',
    questions: [
      'Quantas ações e atividades de extensão foram registradas por área?',
      'Qual o total de participantes certificados nas atividades de extensão?',
      'Quais ações de extensão possuem maior carga horária acumulada?'
    ]
  },
  {
    key: 'grupos',
    label: 'Grupos CNPq',
    subtitle: 'Diretório & Linhas',
    questions: [
      'Quais grupos de pesquisa estão certificados no diretório do CNPq?',
      'Quantas linhas de pesquisa e membros ativos existem por grupo?',
      'Qual a evolução de criação dos grupos de pesquisa por ano?'
    ]
  },
  {
    key: 'producao',
    label: 'Produção Lattes',
    subtitle: 'Artigos, Livros & Patentes',
    questions: [
      'Qual a evolução anual de artigos publicados e trabalhos em eventos?',
      'Quantos livros, capítulos e patentes foram registrados pelos pesquisadores?',
      'Quais grandes áreas concentram o maior volume de produção científica?'
    ]
  },
  {
    key: 'pesquisadores',
    label: 'Pesquisadores',
    subtitle: 'Docentes & Orientações',
    questions: [
      'Qual a distribuição de pesquisadores por titulação acadêmica?',
      'Quantas orientações concluídas e em andamento constam nos currículos?',
      'Quais pesquisadores possuem bolsa de produtividade ou mais orientações?'
    ]
  }
]

const scrollToBottom = async () => {
  await nextTick()
  const anchor = document.getElementById('chat-bottom-anchor')
  anchor?.scrollIntoView({ behavior: 'smooth' })
}

watch(messages, scrollToBottom, { deep: true })
watch(isCurrentConvLoading, scrollToBottom)
watch(reportFormOpen, open => { if (open) scrollToBottom() })

const cancelCurrentQuestion = () => {
  if (pinModalOpen.value) return
  if (!currentConvId.value || !isCurrentConvLoading.value) return
  cancelStream(currentConvId.value)
}

const handleGlobalKeydown = (event: KeyboardEvent) => {
  if (event.key !== 'Escape') return
  if (pinModalOpen.value) return
  if (!isCurrentConvLoading.value) return
  event.preventDefault()
  cancelCurrentQuestion()
}

onMounted(() => {
  window.addEventListener('keydown', handleGlobalKeydown)
  checkHealth().then((status) => {
    healthOnline.value = status
  })
  loadContextos().catch(() => {
    // Backend offline: o seletor fica vazio e a pergunta mostra o erro.
  })

  const initialQuery = window.history.state?.initialQuery || route.query.q
  if (typeof initialQuery === 'string' && initialQuery.trim()) {
    input.value = initialQuery
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
})

const sendQuestion = async (questionText?: string) => {
  const userInput = (questionText ?? input.value).trim()
  const activeConversationId = currentConvId.value
  if (!userInput || !activeConversationId || isConversationLoading(activeConversationId)) return
  if (!llmConfigured.value) {
    const provLabel = user.value?.llm_provider_label || 'Gemini'
    showToast(`Configure ${user.value?.llm_is_local ? `o servidor local (${provLabel})` : `a chave do ${provLabel}`} em Configurações para usar o chat.`, 'error')
    return
  }

  input.value = ''

  let targetConvId = activeConversationId

  const userMessage: ChatMessage = {
    id: Date.now().toString(),
    type: 'user',
    text: userInput,
    timestamp: new Date().toISOString()
  }

  updateConversationById(targetConvId, (conversation) => ({
    ...conversation,
    title: conversation.messages.length === 1 ? userInput.slice(0, 50) : conversation.title,
    messages: [...conversation.messages, userMessage],
    updatedAt: new Date().toISOString()
  }))

  const contextoId = currentConversation.value?.contextoId || selectedContextoId.value
  let serverConversationId: string | null = null
  let draftCounter = 1
  let currentDraftId = `${Date.now()}-draft-${draftCounter}`
  let currentLoadingStatus: string | undefined = 'Analisando sua pergunta...'
  let currentTrace: ReasoningTrace = createInitialTrace()

  const createDraft = (id: string): ChatMessage => ({
    id,
    type: 'ai',
    text: '',
    timestamp: new Date().toISOString(),
    isLoading: true,
    loadingStatus: currentLoadingStatus,
    trace: currentTrace,
  })

  updateConversationById(targetConvId, (conversation) => ({
    ...conversation,
    messages: [...conversation.messages, createDraft(currentDraftId)],
    updatedAt: new Date().toISOString()
  }))

  const updateDraft = (updater: (message: ChatMessage) => ChatMessage) => {
    updateConversationById(targetConvId, (conversation) => ({
      ...conversation,
      messages: conversation.messages.map((message) =>
        message.id === currentDraftId ? updater(message) : message
      ),
      updatedAt: new Date().toISOString()
    }))
  }

  let streamedResults = 0

  const aiMessage = await askQuestionStream(userInput, activeConversationId, {
    onToken: (token) => {
      currentLoadingStatus = 'Gerando resposta...'
      updateDraft((message) => ({
        ...message,
        text: `${message.text}${token}`,
        isChat: true,
        isLoading: true,
        loadingStatus: currentLoadingStatus,
      }))
    },
    onStatus: (status, payload) => {
      // O backend cria a conversa (com o contexto) antes de chamar o LLM e avisa no primeiro status;
      // adotar o id aqui evita duplicar a conversa e mantém a geração vinculada mesmo em segundo plano.
      if (targetConvId.startsWith('local-') && payload?.conversation_id && !serverConversationId) {
        serverConversationId = String(payload.conversation_id)
        replaceConversationId(targetConvId, serverConversationId)
        setConversationContexto(serverConversationId, contextoId)
        targetConvId = serverConversationId
      }
      currentLoadingStatus = status
      updateDraft((message) => ({
        ...message,
        isLoading: true,
        loadingStatus: currentLoadingStatus
      }))
    },
    onTraceEvent: (traceEvent) => {
      currentTrace = applyTraceEvent(currentTrace, traceEvent)
      updateDraft((message) => ({
        ...message,
        trace: currentTrace,
      }))
    },
    onResult: (message) => {
      streamedResults += 1
      const finalMessage: ChatMessage = {
        ...message,
        trace: message.trace ?? currentTrace,
      }
      if (targetConvId.startsWith('local-') && finalMessage.conversationId && !serverConversationId) {
        serverConversationId = String(finalMessage.conversationId)
        replaceConversationId(targetConvId, serverConversationId)
        setConversationContexto(serverConversationId, contextoId)
        targetConvId = serverConversationId
      }
      updateConversationById(targetConvId, (conversation) => {
        const alreadyExists = conversation.messages.some((item) => item.id === finalMessage.id)
        if (streamedResults === 1) {
          return {
            ...conversation,
            messages: conversation.messages.map((item) =>
              item.id === currentDraftId ? finalMessage : item
            ),
            updatedAt: new Date().toISOString()
          }
        }
        if (alreadyExists) {
          return conversation
        }

        const replacedMessages = conversation.messages.map((item) =>
          item.id === currentDraftId ? finalMessage : item
        )
        draftCounter++
        currentDraftId = `${Date.now()}-draft-${draftCounter}`

        return {
          ...conversation,
          messages: [...replacedMessages, createDraft(currentDraftId)],
          updatedAt: new Date().toISOString()
        }
      })
    }
  }, contextoId)

  if (!serverConversationId && aiMessage.conversationId && targetConvId !== aiMessage.conversationId) {
    replaceConversationId(targetConvId, aiMessage.conversationId)
    setConversationContexto(aiMessage.conversationId, contextoId)
    targetConvId = aiMessage.conversationId
  }

  if (aiMessage.interrupted) {
    updateConversationById(targetConvId, (conversation) => ({
      ...conversation,
      messages: conversation.messages.map((m) =>
        m.id === currentDraftId
          ? { ...m, isLoading: false, loadingStatus: undefined, interrupted: true, trace: currentTrace }
          : m
      ),
      updatedAt: new Date().toISOString()
    }))
    return
  }

  const finalFallbackMessage: ChatMessage = aiMessage.error
    ? {
        ...aiMessage,
        trace:
          aiMessage.trace ??
          (currentTrace.steps.some((s) => s.status === 'error')
            ? currentTrace
            : applyTraceEvent(currentTrace, {
                event: 'step_error',
                data: { detail: aiMessage.text },
              })),
      }
    : { ...aiMessage, trace: aiMessage.trace ?? currentTrace }

  updateConversationById(targetConvId, (conversation) => {
    let finalMessages = conversation.messages.filter(m => m.id !== currentDraftId)

    if (streamedResults === 0) {
      const alreadyExists = finalMessages.some(m => m.id === finalFallbackMessage.id)
      if (!alreadyExists) {
        finalMessages.push(finalFallbackMessage)
      }
    }

    finalMessages = finalMessages.map(m => m.isLoading ? { ...m, isLoading: false } : m)

    return {
      ...conversation,
      messages: finalMessages,
      updatedAt: new Date().toISOString()
    }
  })
}

const toggleSql = (messageId: string) => {
  if (!currentConvId.value) return
  updateConversationById(currentConvId.value, (conversation) => ({
    ...conversation,
    messages: conversation.messages.map((message) => ({
      ...message,
      showSQL: message.id === messageId ? !message.showSQL : message.showSQL
    }))
  }))
}

const findQuestionForMessage = (message: ChatMessage): string => {
  if (message.userMessageId) {
    const userMsg = messages.value.find(m => m.id === message.userMessageId)
    if (userMsg) return userMsg.text
  }
  const index = messages.value.findIndex(m => m.id === message.id)
  if (index > 0) {
    const prevMsg = messages.value[index - 1]
    if (prevMsg && prevMsg.type === 'user') return prevMsg.text
  }
  return ''
}

const openPinModal = (message: ChatMessage) => {
  const questionOriginal = findQuestionForMessage(message)
  openPinModalBase(message, questionOriginal, currentConversation.value?.contextoId)
}

const isExporting = ref(false)

const extractFolderName = (caminho: string | null): string => {
  if (!caminho) return ''
  const parts = caminho.split(/[\\/]+/).filter(Boolean)
  return parts.length >= 2 ? parts[parts.length - 2] : ''
}

const handleExport = async ({ message, format }: { message: ChatMessage; format: ExportFormat }) => {
  if (isExporting.value || !message.table?.length) return
  isExporting.value = true
  try {
    const label = findQuestionForMessage(message) || currentConversation.value?.title
    const res = await exportarTabela(message.table, format, {
      fieldFormats: message.fieldFormats,
      label,
    })
    if (res.cancelado) return
    if (res.modo === 'tauri') {
      const folder = extractFolderName(res.caminho)
      showToast(folder ? `Arquivo salvo em ${folder}: ${res.nome}` : `Arquivo salvo: ${res.nome}`, 'success')
    } else {
      showToast(`Arquivo salvo: ${res.nome}`, 'success')
    }
  } catch (error: unknown) {
    const detail = error instanceof Error ? error.message : String(error)
    showToast(`Não foi possível exportar os dados: ${detail}`, 'error')
  } finally {
    isExporting.value = false
  }
}
</script>


<template>
  <div class="flex flex-col h-full relative overflow-hidden">
    <DashboardPinDialog
      :is-open="pinModalOpen"
      :title="pinTitle"
      :loading="isPinning"
      @close="closePin"
      @save="savePin"
      @update:title="pinTitle = $event"
    />

    <transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0 translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 translate-y-2"
    >
      <div
        v-if="toast"
        role="status"
        data-testid="chat-toast"
        :class="[
          'fixed right-4 bottom-4 z-[70] max-w-sm rounded-2xl px-4 py-3 shadow-2xl border flex items-start gap-3',
          toast.type === 'success'
            ? 'bg-emerald-50 border-emerald-200 text-emerald-800 dark:bg-emerald-500/10 dark:border-emerald-500/20 dark:text-emerald-300'
            : 'bg-red-50 border-red-200 text-red-800 dark:bg-red-500/10 dark:border-red-500/20 dark:text-red-300'
        ]"
      >
        <CheckCircle2 v-if="toast.type === 'success'" class="w-5 h-5 mt-0.5 shrink-0" />
        <AlertCircle v-else class="w-5 h-5 mt-0.5 shrink-0" />
        <span class="text-sm font-medium">{{ toast.message }}</span>
      </div>
    </transition>

    <div class="flex flex-col lg:flex-row h-full relative overflow-hidden">
      <div class="flex-1 flex flex-col min-h-0 min-w-0">
        <ChatConversation
          :messages="messages"
          :current-conversation="currentConversation"
          :loading="isCurrentConvLoading"
          :health-online="healthOnline"
          :starter-categories="starterCategories"
          :llm-configured="llmConfigured"
          @toggle-sql="toggleSql"
          @pin="openPinModal"
          @export="handleExport"
          @suggest="sendQuestion($event)"
          @chart-type="rememberChartType"
        >
          <template #after-messages>
            <ChatReportForm
              v-if="reportFormOpen && reportOptions.length"
              :key="currentConvId ?? 'none'"
              :options="reportOptions"
              :default-title="currentConversation?.title || 'Relatório'"
              :saving="reportSaving"
              :error="reportError"
              @cancel="reportFormOpen = false"
              @generate="generateReport"
            />
          </template>
        </ChatConversation>
        <div
          v-if="healthOnline === false"
          role="alert"
          class="mx-auto mt-2 w-full max-w-4xl px-4"
        >
          <div class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800 dark:border-red-500/30 dark:bg-red-950/50 dark:text-red-200">
            <span class="flex items-center gap-2">
              <AlertCircle class="h-4 w-4 shrink-0" />
              O núcleo local do Adito não está respondendo no momento.
            </span>
            <button
              type="button"
              :disabled="reconnecting"
              class="inline-flex items-center gap-1.5 rounded-md border border-red-300 bg-white px-2.5 py-1 font-semibold text-red-800 transition-colors hover:bg-red-100 disabled:opacity-50 dark:border-red-400/40 dark:bg-red-900/40 dark:text-red-100 dark:hover:bg-red-900/70"
              @click="retryConnection"
            >
              <RefreshCw :class="['h-3.5 w-3.5', reconnecting ? 'animate-spin' : '']" />
              Tentar reconectar
            </button>
          </div>
        </div>
        <div v-if="!llmConfigured" class="mx-auto mt-2 w-full max-w-4xl px-4">
          <RouterLink
            to="/configuracoes"
            class="flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 hover:bg-amber-100 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-300"
          >
            <AlertCircle class="h-4 w-4 shrink-0" />
            O chat está desativado: falta {{ user?.llm_is_local ? `configurar ${user?.llm_provider_label || 'o provedor local'}` : `a chave do ${user?.llm_provider_label || 'Gemini'}` }}. Clique para configurar.
          </RouterLink>
        </div>
        <ContextoSelector
          :is-new-conversation="isNewConversation"
          :conversation-contexto-id="currentConversation?.contextoId"
        />
        <ChatInputArea
          v-model="input"
          :loading="isCurrentConvLoading"
          :disable-escape="pinModalOpen"
          :can-create-report="canCreateReport"
          @create-report="openReportForm"
          @send="sendQuestion()"
          @cancel="cancelCurrentQuestion()"
        />
      </div>
    </div>
  </div>
</template>
