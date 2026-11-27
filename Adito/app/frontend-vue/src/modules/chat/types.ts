import type { ChatChartType } from '@/modules/chat/utils/chartType'

export interface RelatedAttribute {
  coluna: string
  descricao: string
}

export interface ChatSuggestion {
  question: string
}

export interface ChartSeries {
  name: string
  data: number[]
}

export interface ChatChart {
  categories: string[]
  series: ChartSeries[]
}

export type FieldFormat = 'text' | 'integer' | 'decimal' | 'currency' | 'date' | 'percent'

export type ReasoningStepStatus = 'pending' | 'running' | 'done' | 'error'

export interface ReasoningStep {
  id: string
  title: string
  subtitle?: string
  status: ReasoningStepStatus
  details: string[]
  code?: string
  language?: string
  headerStatus?: string
}

export interface ReasoningTrace {
  steps: ReasoningStep[]
  durationMs?: number
  compact?: boolean
  startedAt?: string
  finishedAt?: string
}

export type TraceStreamEventName =
  | 'step_start'
  | 'step_detail'
  | 'step_code'
  | 'step_complete'
  | 'step_error'

export interface TraceStreamEvent {
  event: TraceStreamEventName
  data: {
    step_id?: string
    id?: string
    title?: string
    subtitle?: string
    header_status?: string
    detail?: string
    code?: string
    language?: string
  }
}

/** Seção de relatório: definição gravada no núcleo + linhas reexecutadas a cada exibição. */
export interface ChatReportSection {
  sourceMessageId: string
  title: string
  sql: string
  fieldFormats: Record<string, FieldFormat>
  chartType: ChatChartType | null
  data?: Array<Record<string, any>>
  error?: string | null
}

/** Relatório montado por modelo fixo a partir de respostas da conversa (EPIC-14). Não usa LLM. */
export interface ChatReport {
  title: string
  contextoNome?: string | null
  generatedAt: string
  sections: ChatReportSection[]
  /** Linhas das seções já carregadas (o núcleo guarda só o SQL). */
  loaded: boolean
}

export interface ChatMessage {
  id: string
  type: 'user' | 'ai'
  text: string
  timestamp: string
  conversationId?: string
  userMessageId?: string
  sql?: string
  table?: Array<Record<string, any>>
  fieldFormats?: Record<string, FieldFormat>
  chart?: ChatChart | null
  // Tipo de gráfico escolhido no chat; vai junto ao fixar a resposta no Meu painel.
  chartType?: ChatChartType
  // Tipo sugerido pelo agente de painéis do núcleo; abre o gráfico até o usuário escolher outro.
  suggestedChartType?: ChatChartType
  // Relatório (mensagem própria da conversa, sem texto de LLM).
  report?: ChatReport
  isScalarResult?: boolean
  isLoading?: boolean
  loadingStatus?: string
  interrupted?: boolean
  isFallback?: boolean
  isChat?: boolean
  error?: boolean
  fallbackScore?: number
  fallbackMessage?: string
  explanation?: string | null
  suggestions?: ChatSuggestion[]
  related_attributes?: RelatedAttribute[]
  question_temp?: string
  showSQL?: boolean
  // Histórico guarda só o SQL: as linhas são recarregadas do dados.db ao abrir a conversa.
  needsRows?: boolean
  trace?: ReasoningTrace | null
}

export interface Conversation {
  id: string
  title: string
  isPinned?: boolean
  // Contexto de dados fixo da conversa (no backend); nulo enquanto é uma conversa local nova.
  contextoId?: string | null
  messages: ChatMessage[]
  createdAt: string
  updatedAt: string
}
