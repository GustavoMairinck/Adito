<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { Send, Square, Mic, MicOff, Plus, FileText } from 'lucide-vue-next'

const props = defineProps<{
  modelValue: string
  loading: boolean
  disableEscape?: boolean
  /** A conversa tem ao menos uma resposta com dados: mostra o botão "Mais" com "Criar relatório". */
  canCreateReport?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'send'): void
  (e: 'cancel'): void
  (e: 'create-report'): void
}>()

const moreMenuOpen = ref(false)
const moreRef = ref<HTMLElement | null>(null)

const closeMoreMenu = (event: MouseEvent) => {
  if (moreMenuOpen.value && moreRef.value && !moreRef.value.contains(event.target as Node)) {
    moreMenuOpen.value = false
  }
}

const chooseCreateReport = () => {
  moreMenuOpen.value = false
  emit('create-report')
}

// Esc fecha o menu de qualquer lugar da tela. Os ouvintes globais só existem com o menu aberto.
const closeMoreMenuOnEscape = (event: KeyboardEvent) => {
  if (event.key === 'Escape') moreMenuOpen.value = false
}
const toggleMenuListeners = (open: boolean) => {
  if (open) {
    document.addEventListener('mousedown', closeMoreMenu)
    document.addEventListener('keydown', closeMoreMenuOnEscape)
  } else {
    document.removeEventListener('mousedown', closeMoreMenu)
    document.removeEventListener('keydown', closeMoreMenuOnEscape)
  }
}
watch(moreMenuOpen, toggleMenuListeners)
watch(() => props.canCreateReport, (can) => { if (!can) moreMenuOpen.value = false })
onBeforeUnmount(() => toggleMenuListeners(false))

const textareaRef = ref<HTMLTextAreaElement | null>(null)
const isRecording = ref(false)
const speechSupported = ref(false)
const recognition = ref<any>(null)

onMounted(() => {
  const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  if (SpeechRecognition) {
    speechSupported.value = true
    recognition.value = new SpeechRecognition()
    recognition.value.lang = 'pt-BR'
    recognition.value.continuous = false
    recognition.value.interimResults = false

    recognition.value.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript
      const newValue = props.modelValue ? props.modelValue + ' ' + transcript : transcript
      emit('update:modelValue', newValue)
    }

    recognition.value.onerror = (event: any) => {
      console.error('Erro no reconhecimento de voz:', event.error)
      isRecording.value = false
    }

    recognition.value.onend = () => {
      isRecording.value = false
    }
  }
})

const toggleRecording = () => {
  if (!recognition.value) return

  if (isRecording.value) {
    recognition.value.stop()
  } else {
    recognition.value.start()
    isRecording.value = true
  }
}

const adjustHeight = () => {
  if (!textareaRef.value) return
  textareaRef.value.style.height = 'auto'
  textareaRef.value.style.height = Math.min(textareaRef.value.scrollHeight, 200) + 'px'
}

const handleInput = (event: Event) => {
  emit('update:modelValue', (event.target as HTMLTextAreaElement).value)
}

watch(() => props.modelValue, () => {
  nextTick(adjustHeight)
})

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Escape' && props.loading && !props.disableEscape) {
    event.preventDefault()
    event.stopPropagation()
    emit('cancel')
    return
  }
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    if (!props.loading) {
      emit('send')
    }
  }
}
</script>

<template>
  <div class="px-4 pt-3 pb-8 sm:pb-12 bg-transparent">
    <div class="mx-auto flex max-w-4xl flex-col">
      <div class="relative flex items-end rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] shadow-card transition-all focus-within:border-[var(--brand-primary)] focus-within:ring-2 focus-within:ring-[var(--brand-primary)]/20">
        <div v-if="canCreateReport" ref="moreRef" class="relative pl-2 pb-2 pt-2">
          <button
            type="button"
            class="flex h-9 w-9 items-center justify-center rounded-full text-text-muted hover:bg-surface-elevated hover:text-[var(--neutral-dark)] transition-colors"
            :class="{ 'bg-surface-elevated text-[var(--neutral-dark)]': moreMenuOpen }"
            aria-label="Mais opções"
            aria-haspopup="menu"
            :aria-expanded="moreMenuOpen"
            title="Mais opções"
            @click="moreMenuOpen = !moreMenuOpen"
            @keydown.escape.stop="moreMenuOpen = false"
          >
            <Plus class="h-5 w-5" />
          </button>
          <div
            v-if="moreMenuOpen"
            role="menu"
            aria-label="Mais opções"
            class="absolute bottom-full left-2 z-30 mb-2 w-56 overflow-hidden rounded-xl border border-border-subtle bg-surface p-1 shadow-premium"
            @keydown.escape.stop="moreMenuOpen = false"
          >
            <button
              type="button"
              role="menuitem"
              class="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-text-secondary transition-colors hover:bg-surface-elevated hover:text-[var(--neutral-dark)]"
              @click="chooseCreateReport"
            >
              <FileText class="h-4 w-4" />
              Criar relatório
            </button>
          </div>
        </div>
        <textarea
          ref="textareaRef"
          :value="modelValue"
          rows="1"
          aria-label="Pergunta sobre pesquisa e extensão"
          aria-describedby="chat-ai-notice"
          placeholder="O que você quer consultar sobre pesquisa e extensão?"
          class="min-h-[48px] w-full resize-none bg-transparent px-4 py-3 text-sm leading-relaxed text-[var(--neutral-dark)] outline-none placeholder:text-text-muted rounded-2xl"
          @input="handleInput"
          @keydown="handleKeydown"
        />
        <div class="flex items-center gap-2 pr-3 pb-2 pt-2">
          <button
            v-if="speechSupported"
            type="button"
            class="flex h-9 w-9 items-center justify-center rounded-full text-text-muted hover:bg-surface-elevated hover:text-[var(--neutral-dark)] transition-colors disabled:opacity-50"
            @click="toggleRecording"
            :class="{ 'text-[var(--brand-accent-danger)] hover:bg-[var(--brand-accent-danger)]/10 hover:text-[var(--brand-accent-danger)]': isRecording }"
            title="Ditar por voz"
            aria-label="Ditar por voz"
          >
            <MicOff v-if="isRecording" class="h-5 w-5 animate-pulse" />
            <Mic v-else class="h-5 w-5" />
          </button>
          <button
            v-if="loading"
            id="btn-stop-chat"
            type="button"
            class="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--neutral-dark)] text-[var(--bg-surface)] hover:opacity-90 transition-all cursor-pointer dark:bg-slate-200 dark:text-slate-900"
            @click="emit('cancel')"
            title="Parar geração (Esc)"
            aria-label="Parar geração"
          >
            <Square class="h-3.5 w-3.5 fill-current" />
          </button>
          <button
            v-else
            id="btn-send-chat"
            type="button"
            :disabled="!modelValue.trim()"
            class="flex h-9 w-9 items-center justify-center rounded-full transition-all disabled:cursor-not-allowed disabled:bg-surface-elevated disabled:text-text-muted bg-[var(--brand-primary)] text-white hover:bg-[var(--brand-dark)]"
            @click="emit('send')"
            title="Enviar mensagem"
            aria-label="Enviar mensagem"
          >
            <Send class="h-4 w-4 ml-0.5" />
          </button>
        </div>
      </div>
      <p id="chat-ai-notice" class="mt-2.5 text-center text-xs text-text-muted">
        O Adito utiliza IA e pode cometer erros
      </p>
    </div>
  </div>
</template>
