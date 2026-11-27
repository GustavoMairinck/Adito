import { computed, shallowRef } from 'vue'
import { call, stream } from '@/common/api/core'
import type { ChatMessage, TraceStreamEvent, TraceStreamEventName } from '@/modules/chat/types'
import { chartKeys } from '@/common/utils/chartKeys'
import { normalizeTrace } from '@/modules/chat/utils/trace'
import { isChatChartType } from '@/modules/chat/utils/chartType'

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

const TRACE_EVENTS = new Set<TraceStreamEventName>([
  'step_start',
  'step_detail',
  'step_code',
  'step_complete',
  'step_error',
])

interface StreamHandlers {
  onToken?: (token: string) => void
  onStatus?: (message: string, payload?: Record<string, any>) => void
  onTraceEvent?: (event: TraceStreamEvent) => void
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
    fieldFormats: data.field_formats,
    trace: normalizeTrace(data.trace),
    suggestedChartType: isChatChartType(data.chart_type) ? data.chart_type : undefined,
  }
}

const activeControllers = shallowRef<Record<string, AbortController>>({})
let ephemeralStreamSeq = 0

function isCanceledError(error: any, signal: AbortSignal): boolean {
  return (
    signal.aborted
    || error?.name === 'CanceledError'
    || error?.status === 499
  )
}

export function migrateChatStreamKey(oldId: string, newId: string): void {
  if (!oldId || !newId || oldId === newId) return
  const current = activeControllers.value[oldId]
  if (!current) return
  const next = { ...activeControllers.value }
  delete next[oldId]
  next[newId] = current
  activeControllers.value = next
}

export function cancelChatStream(conversationId?: string | null): boolean {
  if (!conversationId) return false
  const controller = activeControllers.value[conversationId]
  if (!controller) return false
  const next = { ...activeControllers.value }
  delete next[conversationId]
  activeControllers.value = next
  controller.abort()
  return true
}

export function isChatConversationLoading(conversationId?: string | null): boolean {
  return !!(conversationId && activeControllers.value[conversationId])
}

export function resetChatApiForTests(): void {
  activeControllers.value = {}
  ephemeralStreamSeq = 0
}

export function useChatApi() {
  const activeConversationIds = computed(() => Object.keys(activeControllers.value))
  const isLoading = computed(() => activeConversationIds.value.length > 0)

  const isConversationLoading = isChatConversationLoading

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
    let streamKey = conversationId || `__ephemeral_${++ephemeralStreamSeq}`
    const controller = new AbortController()
    activeControllers.value = { ...activeControllers.value, [streamKey]: controller }

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

      const maybeMigrateKey = (rawConversationId: unknown) => {
        if (streamKey.startsWith('local-') && rawConversationId) {
          const serverId = String(rawConversationId)
          migrateChatStreamKey(streamKey, serverId)
          streamKey = serverId
        }
      }

      await stream(
        'chat.stream',
        payload,
        (event, data) => {
          // Depois de um erro ou cancelamento, o resto do stream é ignorado.
          if (streamError || controller.signal.aborted) return
          if (event === 'token') {
            handlers.onToken?.(data.text || '')
          } else if (event === 'status') {
            maybeMigrateKey(data?.conversation_id)
            handlers.onStatus?.(data.message || 'Processando...', data)
          } else if (TRACE_EVENTS.has(event as TraceStreamEventName)) {
            handlers.onTraceEvent?.({ event: event as TraceStreamEventName, data: data || {} })
          } else if (event === 'error') {
            streamError = data.message || 'erro desconhecido'
          } else if (event === 'result') {
            maybeMigrateKey(data?.conversation_id)
            lastResult = mapResponseToMessage(data)
            handlers.onResult?.(lastResult)
          }
        },
        { signal: controller.signal },
      )
      if (streamError) throw new Error(streamError)

      if (lastResult) return lastResult
      throw new Error('stream finalizado sem resultado')
    } catch (error: any) {
      if (isCanceledError(error, controller.signal)) {
        return {
          id: `${Date.now() + 1}`,
          type: 'ai',
          text: '',
          timestamp: new Date().toISOString(),
          interrupted: true,
        }
      }
      return {
        id: `${Date.now() + 1}`,
        type: 'ai',
        text: error?.message || 'Erro ao processar sua pergunta. Tente novamente.',
        timestamp: new Date().toISOString(),
        error: true
      }
    } finally {
      if (activeControllers.value[streamKey] === controller) {
        const next = { ...activeControllers.value }
        delete next[streamKey]
        activeControllers.value = next
      }
    }
  }

  return {
    askQuestionStream,
    cancelStream: cancelChatStream,
    migrateStreamKey: migrateChatStreamKey,
    checkHealth,
    isLoading,
    isConversationLoading,
    activeConversationIds,
  }
}
