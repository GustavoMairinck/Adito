<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'
import { Loader2, Send, Mic, MicOff } from 'lucide-vue-next'

const props = defineProps<{
  modelValue: string
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'send'): void
}>()

const textareaRef = ref<HTMLTextAreaElement | null>(null)
const isRecording = ref(false)
const recognition = ref<any>(null)

onMounted(() => {
  const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  if (SpeechRecognition) {
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
  if (!recognition.value) {
    alert('Reconhecimento de voz não suportado neste navegador.')
    return
  }

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
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    emit('send')
  }
}
</script>

<template>
  <div class="px-4 py-4 bg-transparent">
    <div class="mx-auto flex max-w-3xl flex-col">
      <div class="relative flex items-end rounded-2xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] shadow-card transition-all focus-within:border-[var(--brand-primary)] focus-within:ring-2 focus-within:ring-[var(--brand-primary)]/20">
        <textarea
          ref="textareaRef"
          :value="modelValue"
          rows="1"
          aria-label="Pergunta sobre pesquisa e extensão"
          placeholder="O que você quer consultar sobre pesquisa e extensão?"
          class="min-h-[56px] w-full resize-none bg-transparent px-5 py-4 text-sm leading-relaxed text-[var(--neutral-dark)] outline-none placeholder:text-text-muted rounded-2xl"
          @input="handleInput"
          @keydown="handleKeydown"
        />
        <div class="flex items-center gap-2 pr-3 pb-2 pt-2">
          <button
            type="button"
            class="flex h-10 w-10 items-center justify-center rounded-full text-text-muted hover:bg-surface-elevated hover:text-[var(--neutral-dark)] transition-colors disabled:opacity-50"
            @click="toggleRecording"
            :class="{ 'text-[var(--brand-accent-danger)] hover:bg-[var(--brand-accent-danger)]/10 hover:text-[var(--brand-accent-danger)]': isRecording }"
            title="Ditar por voz"
          >
            <MicOff v-if="isRecording" class="h-5 w-5 animate-pulse" />
            <Mic v-else class="h-5 w-5" />
          </button>
          <button
            id="btn-send-chat"
            :disabled="!modelValue.trim() || loading"
            class="flex h-10 w-10 items-center justify-center rounded-full transition-all disabled:cursor-not-allowed disabled:bg-surface-elevated disabled:text-text-muted bg-[var(--brand-primary)] text-white hover:bg-[var(--brand-dark)]"
            @click="emit('send')"
            title="Enviar mensagem"
            aria-label="Enviar mensagem"
          >
            <Loader2 v-if="loading" class="h-5 w-5 animate-spin" />
            <Send v-else class="h-4 w-4 ml-0.5" />
          </button>
        </div>
      </div>
      <p class="mt-2 text-center text-xs text-text-muted">
        Enter para enviar · Shift+Enter para nova linha
      </p>
    </div>
  </div>
</template>
