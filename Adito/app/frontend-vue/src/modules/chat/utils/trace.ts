import type {
  ReasoningStep,
  ReasoningStepStatus,
  ReasoningTrace,
  TraceStreamEvent,
} from '@/modules/chat/types'

const VALID_STATUSES = new Set<ReasoningStepStatus>(['pending', 'running', 'done', 'error'])

export function createInitialTrace(startedAt = new Date().toISOString()): ReasoningTrace {
  return {
    startedAt,
    compact: false,
    steps: [
      {
        id: 'routing',
        title: 'Orquestrador',
        subtitle: 'Interpretando a solicitação e definindo a estratégia de busca.',
        status: 'running',
        headerStatus: 'Analisando contexto...',
        details: [],
      },
    ],
  }
}

export function applyTraceEvent(
  current: ReasoningTrace | null | undefined,
  event: TraceStreamEvent,
): ReasoningTrace {
  const base: ReasoningTrace = current
    ? {
        ...current,
        steps: current.steps.map((step) => ({ ...step, details: [...step.details] })),
      }
    : createInitialTrace()

  const data = event.data || {}
  const stepId = String(data.step_id || data.id || base.steps[base.steps.length - 1]?.id || 'routing')
  let idx = base.steps.findIndex((s) => s.id === stepId)

  const ensureStep = (): ReasoningStep => {
    if (idx === -1) {
      const created: ReasoningStep = {
        id: stepId,
        title: data.title || stepId,
        subtitle: data.subtitle || '',
        status: 'running',
        headerStatus: data.header_status,
        details: [],
      }
      base.steps.push(created)
      idx = base.steps.length - 1
    }
    return base.steps[idx]
  }

  const step = ensureStep()

  switch (event.event) {
    case 'step_start': {
      if (data.title) step.title = data.title
      if (data.subtitle) step.subtitle = data.subtitle
      if (data.header_status) step.headerStatus = data.header_status
      step.status = 'running'
      if (stepId === 'synthesis' && !base.steps.some((s) => s.id === 'query')) {
        base.compact = true
      }
      break
    }
    case 'step_detail': {
      const detail = (data.detail || '').trim()
      if (detail && step.details[step.details.length - 1] !== detail) {
        step.details.push(detail)
      }
      break
    }
    case 'step_code': {
      const code = (data.code || '').trim()
      if (code) {
        step.code = code
        step.language = data.language || 'sql'
      }
      break
    }
    case 'step_complete': {
      step.status = 'done'
      const detail = (data.detail || '').trim()
      if (detail && step.details[step.details.length - 1] !== detail) {
        step.details.push(detail)
      }
      break
    }
    case 'step_error': {
      step.status = 'error'
      const detail = (data.detail || '').trim()
      if (detail && step.details[step.details.length - 1] !== detail) {
        step.details.push(detail)
      }
      break
    }
  }

  return base
}

export function normalizeTrace(raw: unknown): ReasoningTrace | null {
  if (!raw || typeof raw !== 'object') return null
  const obj = raw as Record<string, unknown>
  if (!Array.isArray(obj.steps) || obj.steps.length === 0) return null

  const steps: ReasoningStep[] = []
  for (const entry of obj.steps) {
    if (!entry || typeof entry !== 'object') continue
    const s = entry as Record<string, unknown>
    const id = String(s.id || s.step_id || `step-${steps.length + 1}`)
    const rawStatus = String(s.status || 'done') as ReasoningStepStatus
    const status: ReasoningStepStatus = VALID_STATUSES.has(rawStatus) ? rawStatus : 'done'
    const details = Array.isArray(s.details)
      ? s.details.map((d) => String(d || '').trim()).filter(Boolean)
      : []

    steps.push({
      id,
      title: String(s.title || id),
      subtitle: s.subtitle ? String(s.subtitle) : '',
      status,
      details,
      code: s.code ? String(s.code) : undefined,
      language: s.language ? String(s.language) : s.code ? 'sql' : undefined,
      headerStatus: s.headerStatus
        ? String(s.headerStatus)
        : s.header_status
          ? String(s.header_status)
          : undefined,
    })
  }

  if (steps.length === 0) return null

  const rawDuration = obj.durationMs ?? obj.duration_ms
  const durationMs =
    typeof rawDuration === 'number' && Number.isFinite(rawDuration) && rawDuration >= 0
      ? rawDuration
      : undefined

  return {
    steps,
    durationMs,
    compact: Boolean(obj.compact),
    startedAt: obj.startedAt ? String(obj.startedAt) : undefined,
    finishedAt: obj.finishedAt ? String(obj.finishedAt) : undefined,
  }
}

export function formatTraceDuration(durationMs?: number | null): string {
  if (durationMs === null || durationMs === undefined || !Number.isFinite(durationMs) || durationMs < 0) {
    return ''
  }
  const tenths = Math.round(durationMs / 100)
  if (tenths < 10) {
    return `0,${tenths}s`
  }
  const totalSeconds = tenths / 10
  if (totalSeconds < 60) {
    const formatted = totalSeconds.toFixed(1).replace('.', ',')
    return formatted.endsWith(',0') ? `${Math.round(totalSeconds)}s` : `${formatted}s`
  }
  const minutes = Math.floor(totalSeconds / 60)
  const remainingSeconds = Math.round(totalSeconds % 60)
  return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`
}

export function formatTraceTime(timestamp?: string | null): string {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}
