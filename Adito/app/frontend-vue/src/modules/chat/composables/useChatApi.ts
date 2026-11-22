import { ref } from 'vue'
import { call, stream } from '@/common/api/core'
import type { ChatMessage } from '@/modules/chat/types'
import { chartKeys } from '@/common/utils/chartKeys'

function parseNumeric(value: unknown) {
  if (value === null || value === undefined || value === '') return null

  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null
  }

  const parsed = Number(String(value).trim())
  return Number.isFinite(parsed) ? parsed : null
}

function normalizeLabel(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase())
}

function buildCategory(row: Record<string, any>, dimensionKeys: string[], fallback: string) {
  const values = dimensionKeys
    .map(key => row[key])
    .filter(value => value !== null && value !== undefined && String(value).trim() !== '')

  return values.length ? values.map(String).join(' · ') : fallback
}

export function buildChart(data?: Array<Record<string, any>>) {
  if (!data || data.length === 0) {
    return null
  }

  // Mesma regra do Meu painel: ano, mês e colunas de texto viram o eixo; o resto, séries.
  const { dimensionKeys, metricKeys } = chartKeys(data)
  if (metricKeys.length === 0) return null

  return {
    categories: data.map((row, index) => buildCategory(row, dimensionKeys, `Item ${index + 1}`)),
    series: metricKeys.map(key => ({
      name: normalizeLabel(key),
      data: data.map(row => parseNumeric(row[key]) || 0)
    }))
  }
}

export function isScalarResultData(data?: Array<Record<string, any>>) {
  return !!(data && data.length === 1 && Object.keys(data[0]).length === 1)
}

interface StreamHandlers {
  onToken?: (token: string) => void
  onStatus?: (message: string, payload?: Record<string, any>) => void
  onResult?: (message: ChatMessage) => void
}

function mapResponseToMessage(data: any): ChatMessage {
  const isScalarResult = isScalarResultData(data.data)

  return {
    id: data.message_id || `${Date.now() + 1}`,
    type: 'ai',
    text: data.type === 'fallback' ? '' : (data.text || data.answer || 'Nao consegui processar sua pergunta.'),
    timestamp: new Date().toISOString(),
    conversationId: data.conversation_id,
    userMessageId: data.user_message_id,
    sql: data.sql,
    table: data.data,
    isScalarResult,
    chart: !isScalarResult ? buildChart(data.data) : null,
    isFallback: data.type === 'fallback',
    isChat: data.type === 'chat',
    fallbackScore: data.score,
    fallbackMessage: data.message,
    explanation: data.explanation,
    suggestions: data.suggestions,
    related_attributes: data.related_attributes,
    fieldFormats: data.field_formats
  }
}

export function useChatApi() {
  const isLoading = ref(false)

  const checkHealth = async (): Promise<boolean> => {
    try {
      const data = await call('health')
      return !!data
    } catch {
      return false
    }
  }

  const askQuestionStream = async (
    questionText: string,
    conversationId?: string | null,
    handlers: StreamHandlers = {},
    contextoId?: string | null
  ): Promise<ChatMessage> => {
    isLoading.value = true
    try {
      const payload: Record<string, any> = { question: questionText }
      if (conversationId) {
        payload.conversation_id = conversationId
      }
      if (contextoId && (!conversationId || conversationId.startsWith('local-'))) {
        // Conversa nova: o backend fixa este contexto nela.
        payload.contexto_id = contextoId
      }

      let lastResult: ChatMessage | null = null
      let streamError: string | null = null

      await stream('chat.stream', payload, (event, data) => {
        // Depois de um erro, o resto do stream é ignorado (como no SSE).
        if (streamError) return
        if (event === 'token') {
          handlers.onToken?.(data.text || '')
        } else if (event === 'status') {
          handlers.onStatus?.(data.message || 'Processando...', data)
        } else if (event === 'error') {
          streamError = data.message || 'erro desconhecido'
        } else if (event === 'result') {
          lastResult = mapResponseToMessage(data)
          handlers.onResult?.(lastResult)
        }
      })
      if (streamError) throw new Error(streamError)

      if (lastResult) return lastResult
      throw new Error('stream finalizado sem resultado')
    } catch (error: any) {
      return {
        id: `${Date.now() + 1}`,
        type: 'ai',
        text: `Erro ao processar sua pergunta: ${error?.message || 'erro desconhecido'}. Verifique se o backend esta rodando.`,
        timestamp: new Date().toISOString(),
        error: true
      }
    } finally {
      isLoading.value = false
    }
  }

  return { askQuestionStream, checkHealth, isLoading }
}
