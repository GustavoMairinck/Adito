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
  isScalarResult?: boolean
  isLoading?: boolean
  loadingStatus?: string
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
}

export interface Conversation {
  id: string
  title: string
  messages: ChatMessage[]
  createdAt: string
  updatedAt: string
}
