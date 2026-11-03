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
      <div class="relative flex items-end rounded-3xl bg-white dark:bg-surface border border-border-subtle shadow-sm transition-all focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/20">
        <textarea
          ref="textareaRef"
          :value="modelValue"
          rows="1"
          placeholder="Como posso ajudar em sua decisão estratégica hoje?"
          class="min-h-[56px] w-full resize-none bg-transparent px-5 py-4 text-sm leading-relaxed text-text-primary outline-none placeholder:text-text-muted rounded-3xl"
          @input="handleInput"
          @keydown="handleKeydown"
        />
        <div class="flex items-center gap-2 pr-3 pb-2 pt-2">
          <button
            type="button"
            class="flex h-10 w-10 items-center justify-center rounded-full text-text-muted hover:bg-surface hover:text-text-primary transition-colors disabled:opacity-50"
            @click="toggleRecording"
            :class="{ 'text-red-500 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/30': isRecording }"
            title="Ditar por voz"
          >
            <MicOff v-if="isRecording" class="h-5 w-5 animate-pulse" />
            <Mic v-else class="h-5 w-5" />
          </button>
          <button
            id="btn-send-chat"
            :disabled="!modelValue.trim() || loading"
            class="flex h-10 w-10 items-center justify-center rounded-full transition-all disabled:cursor-not-allowed disabled:bg-surface disabled:text-text-muted bg-accent text-white hover:bg-accent-hover"
            @click="emit('send')"
            title="Enviar mensagem"
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
