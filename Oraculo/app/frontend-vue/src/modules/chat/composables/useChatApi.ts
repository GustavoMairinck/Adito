import { ref } from 'vue'
import httpClient from '@/common/api/httpClient'
import { apiBase, authHeaders } from '@/common/api/config'
import type { ChatMessage } from '@/modules/chat/types'

function parseNumeric(value: unknown) {
  if (value === null || value === undefined || value === '') return null

  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null
  }

  const parsed = Number(String(value).trim())
  return Number.isFinite(parsed) ? parsed : null
}

function isNumeric(value: unknown) {
  return parseNumeric(value) !== null
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

  const keys = Object.keys(data[0] || {})
  const numericKeys = keys.filter(key => data.some(row => isNumeric(row[key])))
  if (numericKeys.length === 0) return null

  const rows = data
  const dimensionKeys = keys.filter(key => !numericKeys.includes(key))

  return {
    categories: rows.map((row, index) => buildCategory(row, dimensionKeys, `Item ${index + 1}`)),
    series: numericKeys.map(key => ({
      name: normalizeLabel(key),
      data: rows.map(row => parseNumeric(row[key]) || 0)
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

function parseSseEvent(rawEvent: string) {
  let event = 'message'
  const dataLines: string[] = []

  for (const line of rawEvent.split('\n')) {
    if (line.startsWith('event:')) {
      event = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trimStart())
    }
  }

  if (dataLines.length === 0) return null

  return {
    event,
    data: JSON.parse(dataLines.join('\n'))
  }
}

export function useChatApi() {
  const isLoading = ref(false)

  const checkHealth = async (): Promise<boolean> => {
    try {
      const { data } = await httpClient.get('/health')
      return !!data
    } catch {
      return false
    }
  }

  const askQuestion = async (
    questionText: string,
    conversationId?: string | null,
    contextoId?: string | null
  ): Promise<ChatMessage> => {
    isLoading.value = true
    try {
      const payload: Record<string, any> = { question: questionText }
      if (conversationId && !conversationId.startsWith('local-')) {
        payload.conversation_id = conversationId
      } else if (contextoId) {
        // Conversa nova: o backend fixa este contexto nela.
        payload.contexto_id = contextoId
      }
      const { data } = await httpClient.post('/api/chat', payload)
      return mapResponseToMessage(data)
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

      const response = await fetch(`${apiBase()}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders()
        },
        body: JSON.stringify(payload)
      })

      if (!response.ok || !response.body) {
        let detail = `status ${response.status}`
        try {
          detail = (await response.json()).error || detail
        } catch {
          // corpo não é JSON
        }
        throw new Error(detail)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let lastResult: ChatMessage | null = null

      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() || ''

        for (const part of parts) {
          if (!part.trim()) continue
          const parsed = parseSseEvent(part)
          if (!parsed) continue

          if (parsed.event === 'token') {
            handlers.onToken?.(parsed.data.text || '')
          } else if (parsed.event === 'status') {
            handlers.onStatus?.(parsed.data.message || 'Processando...', parsed.data)
          } else if (parsed.event === 'error') {
            throw new Error(parsed.data.message || 'erro desconhecido')
          } else if (parsed.event === 'result') {
            lastResult = mapResponseToMessage(parsed.data)
            handlers.onResult?.(lastResult)
          }
        }
      }

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

  return { askQuestion, askQuestionStream, checkHealth, isLoading }
}
