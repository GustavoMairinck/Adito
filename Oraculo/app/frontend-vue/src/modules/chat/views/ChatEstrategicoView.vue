<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { AlertCircle, CheckCircle2 } from 'lucide-vue-next'

import ConfirmModal from '@/common/components/feedback/ConfirmModal.vue'
import { useToast } from '@/common/composables/useToast'
import ChatConversation from '@/modules/chat/components/ChatConversation.vue'
import ChatInputArea from '@/modules/chat/components/ChatInputArea.vue'
import DashboardPinDialog from '@/modules/dashboard/components/DashboardPinDialog.vue'
import ChatSidebar from '@/modules/chat/components/ChatSidebar.vue'
import ContextoSelector from '@/modules/chat/components/ContextoSelector.vue'
import { useContextos } from '@/common/composables/useContextos'
import { useAuth } from '@/modules/auth/composables/useAuth'
import { useChatApi } from '@/modules/chat/composables/useChatApi'
import { useChatHistory } from '@/modules/chat/composables/useChatHistory'
import { useChatPin } from '@/modules/chat/composables/useChatPin'
import type { ChatMessage } from '@/modules/chat/types'

const route = useRoute()
const { toast, showToast } = useToast()

const {
  conversations,
  currentConvId,
  setCurrentConvId,
  handleNewConversation,
  handleDeleteConversation,
  updateCurrentConversation,
  replaceConversationId,
  setConversationContexto,
  currentConversation
} = useChatHistory()

const { askQuestionStream, checkHealth, isLoading } = useChatApi()
const { selectedId: selectedContextoId, loadContextos } = useContextos()

// Conversa ainda não salva no backend: o contexto pode ser escolhido.
const isNewConversation = computed(() => !!currentConvId.value?.startsWith('local-'))

// Sem chave da Mistral o app abre, mas o chat fica desativado com o motivo à vista.
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
const healthOnline = ref<boolean | null>(null)
const isConvSidebarOpen = ref(false)
const conversationToDelete = ref<{ id: string; title: string } | null>(null)

const messages = computed(() => currentConversation.value?.messages || [])
const starterCategories = [
  {
    key: 'receita',
    label: 'Receita',
    questions: [
      'Qual a receita líquida total em 2025?',
      'Como foi a evolução mensal da receita em 2025?',
      'Qual o crescimento de receita comparado ao ano anterior?'
    ]
  },
  {
    key: 'produtos',
    label: 'Produtos',
    questions: [
      'Mostre os top 5 produtos por receita.',
      'Qual a receita por categoria de produto?',
      'Quais produtos têm maior margem de lucro?'
    ]
  },
  {
    key: 'clientes',
    label: 'Clientes',
    questions: [
      'Quantos clientes existem em cada porte?',
      'Quais são os 10 clientes com maior receita?',
      'Qual a receita por setor de cliente?'
    ]
  },
  {
    key: 'canais',
    label: 'Canais',
    questions: [
      'Qual a receita líquida por canal de venda?',
      'Qual canal tem o maior volume de vendas?'
    ]
  },
  {
    key: 'vendedores',
    label: 'Vendedores',
    questions: [
      'Quais são os vendedores com maior receita?',
      'Qual a média de receita por vendedor em 2025?'
    ]
  },
  {
    key: 'margens',
    label: 'Margens',
    questions: [
      'Qual o lucro total por categoria de produto?',
      'Qual a margem de lucro média em 2025?',
      'Quais produtos têm margem abaixo de 10%?'
    ]
  }
]

const scrollToBottom = async () => {
  await nextTick()
  const anchor = document.getElementById('chat-bottom-anchor')
  anchor?.scrollIntoView({ behavior: 'smooth' })
}

watch(messages, scrollToBottom, { deep: true })
watch(isLoading, scrollToBottom)

onMounted(() => {
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

const sendQuestion = async (questionText?: string) => {
  const userInput = (questionText ?? input.value).trim()
  if (!userInput || isLoading.value) return
  if (!llmConfigured.value) {
    showToast('Configure a chave da Mistral em Configurações para usar o chat.', 'error')
    return
  }

  input.value = ''

  const userMessage: ChatMessage = {
    id: Date.now().toString(),
    type: 'user',
    text: userInput,
    timestamp: new Date().toISOString()
  }

  updateCurrentConversation((conversation) => ({
    ...conversation,
    title: conversation.messages.length === 1 ? userInput.slice(0, 50) : conversation.title,
    messages: [...conversation.messages, userMessage],
    updatedAt: new Date().toISOString()
  }))

  const activeConversationId = currentConvId.value
  const contextoId = currentConversation.value?.contextoId || selectedContextoId.value
  let serverConversationId: string | null = null
  let draftCounter = 1
  let currentDraftId = `${Date.now()}-draft-${draftCounter}`
  let currentLoadingStatus: string | undefined = undefined

  const createDraft = (id: string): ChatMessage => ({
    id,
    type: 'ai',
    text: '',
    timestamp: new Date().toISOString(),
    isLoading: true,
    loadingStatus: currentLoadingStatus
  })

  updateCurrentConversation((conversation) => ({
    ...conversation,
    messages: [...conversation.messages, createDraft(currentDraftId)],
    updatedAt: new Date().toISOString()
  }))

  const updateDraft = (updater: (message: ChatMessage) => ChatMessage) => {
    updateCurrentConversation((conversation) => ({
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
      updateDraft((message) => ({
        ...message,
        text: `${message.text}${token}`,
        isChat: true,
        isLoading: true
      }))
    },
    onStatus: (status, payload) => {
      // O backend cria a conversa (com o contexto) antes de chamar o LLM e avisa no primeiro status;
      // adotar o id aqui evita duplicar a conversa se a resposta falhar.
      if (activeConversationId?.startsWith('local-') && payload?.conversation_id && !serverConversationId) {
        serverConversationId = String(payload.conversation_id)
        replaceConversationId(activeConversationId, serverConversationId)
        setConversationContexto(serverConversationId, contextoId)
      }
      currentLoadingStatus = status
      updateDraft((message) => ({
        ...message,
        isLoading: true,
        loadingStatus: currentLoadingStatus
      }))
    },
    onResult: (message) => {
      streamedResults += 1
      updateCurrentConversation((conversation) => {
        const alreadyExists = conversation.messages.some((item) => item.id === message.id)
        if (streamedResults === 1) {
          return {
            ...conversation,
            messages: conversation.messages.map((item) =>
              item.id === currentDraftId ? message : item
            ),
            updatedAt: new Date().toISOString()
          }
        }
        if (alreadyExists) {
          return conversation
        }

        const replacedMessages = conversation.messages.map((item) =>
          item.id === currentDraftId ? message : item
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

  if (!serverConversationId && activeConversationId && aiMessage.conversationId && activeConversationId !== aiMessage.conversationId) {
    replaceConversationId(activeConversationId, aiMessage.conversationId)
    // O backend fixou este contexto na conversa recém-criada.
    setConversationContexto(aiMessage.conversationId, contextoId)
  }

  updateCurrentConversation((conversation) => {
    let finalMessages = conversation.messages.filter(m => m.id !== currentDraftId)
    
    if (streamedResults === 0) {
      const alreadyExists = finalMessages.some(m => m.id === aiMessage.id)
      if (!alreadyExists) {
        finalMessages.push(aiMessage)
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
  updateCurrentConversation((conversation) => ({
    ...conversation,
    messages: conversation.messages.map((message) => ({
      ...message,
      showSQL: message.id === messageId ? !message.showSQL : message.showSQL
    }))
  }))
}

const openPinModal = (message: ChatMessage) => {
  let questionOriginal = ''
  if (message.userMessageId) {
    const userMsg = messages.value.find(m => m.id === message.userMessageId)
    if (userMsg) {
      questionOriginal = userMsg.text
    }
  }
  if (!questionOriginal) {
    const index = messages.value.findIndex(m => m.id === message.id)
    if (index > 0) {
      const prevMsg = messages.value[index - 1]
      if (prevMsg && prevMsg.type === 'user') {
        questionOriginal = prevMsg.text
      }
    }
  }
  openPinModalBase(message, questionOriginal, currentConversation.value?.contextoId)
}

const requestDeleteConversation = (id: string) => {
  const conversation = conversations.value.find(item => item.id === id)
  if (!conversation) return
  conversationToDelete.value = { id, title: conversation.title }
}

const confirmDeleteConversation = async () => {
  if (!conversationToDelete.value) return
  try {
    await handleDeleteConversation(conversationToDelete.value.id)
    showToast('Conversa excluida com sucesso.', 'success')
    conversationToDelete.value = null
  } catch (error: any) {
    const detail = error?.response?.data?.detail || error?.message || 'Erro desconhecido.'
    showToast(`Erro ao excluir conversa: ${detail}`, 'error')
  }
}
</script>


<template>
  <div class="flex flex-col h-full relative overflow-hidden">
    <ConfirmModal
      :is-open="!!conversationToDelete"
      title="Excluir conversa"
      :message="conversationToDelete ? `Tem certeza que deseja excluir a conversa '${conversationToDelete.title}'?` : ''"
      confirm-text="Excluir conversa"
      cancel-text="Cancelar"
      @confirm="confirmDeleteConversation"
      @close="conversationToDelete = null"
    />

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
      <ChatSidebar
        :conversations="conversations"
        :current-conv-id="currentConvId"
        :open="isConvSidebarOpen"
        @select="setCurrentConvId($event); isConvSidebarOpen = false"
        @new="handleNewConversation(); isConvSidebarOpen = false"
        @delete="requestDeleteConversation($event)"
        @close="isConvSidebarOpen = false"
      />

      <div
        v-if="isConvSidebarOpen"
        class="lg:hidden fixed inset-0 bg-black/40 z-30 animate-in fade-in"
        @click="isConvSidebarOpen = false"
      />

      <div class="flex-1 flex flex-col min-h-0 min-w-0">
        <ChatConversation
          :messages="messages"
          :current-conversation="currentConversation"
          :loading="isLoading"
          :health-online="healthOnline"
          :starter-categories="starterCategories"
          @open-conversations="isConvSidebarOpen = true"
          @toggle-sql="toggleSql"
          @pin="openPinModal"
          @suggest="sendQuestion($event)"
        />
        <RouterLink
          v-if="!llmConfigured"
          to="/configuracoes"
          class="mx-4 mt-2 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 hover:bg-amber-100 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-300"
        >
          <AlertCircle class="h-4 w-4 shrink-0" />
          O chat está desativado: falta a chave da Mistral. Clique para configurar.
        </RouterLink>
        <ContextoSelector
          :is-new-conversation="isNewConversation"
          :conversation-contexto-id="currentConversation?.contextoId"
        />
        <ChatInputArea v-model="input" :loading="isLoading" @send="sendQuestion()" />
      </div>
    </div>
  </div>
</template>
