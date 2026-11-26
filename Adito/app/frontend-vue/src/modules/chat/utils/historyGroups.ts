import type { Conversation } from '@/modules/chat/types'

export type ConversationGroupKey = 'pinned' | 'today' | 'last7days' | 'thisMonth' | 'older'

export interface ConversationGroup {
  key: ConversationGroupKey
  label: string
  items: Conversation[]
}

const GROUP_META: Array<{ key: ConversationGroupKey; label: string }> = [
  { key: 'pinned', label: 'Fixadas' },
  { key: 'today', label: 'Hoje' },
  { key: 'last7days', label: 'Últimos 7 dias' },
  { key: 'thisMonth', label: 'Este mês' },
  { key: 'older', label: 'Anteriores' },
]

function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate())
}

function parseDate(iso?: string | null): Date | null {
  if (!iso) return null
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? null : d
}

export function groupConversations(
  conversations: Conversation[],
  now: Date = new Date(),
): ConversationGroup[] {
  const buckets: Record<ConversationGroupKey, Conversation[]> = {
    pinned: [],
    today: [],
    last7days: [],
    thisMonth: [],
    older: [],
  }

  const todayStart = startOfDay(now)
  const sevenDaysAgo = new Date(todayStart)
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 6)
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1)

  for (const conv of conversations) {
    if (conv.isPinned) {
      buckets.pinned.push(conv)
      continue
    }
    const updated = parseDate(conv.updatedAt || conv.createdAt)
    if (!updated) {
      buckets.older.push(conv)
      continue
    }
    const dayStart = startOfDay(updated)
    if (dayStart.getTime() >= todayStart.getTime()) {
      buckets.today.push(conv)
    } else if (dayStart.getTime() >= sevenDaysAgo.getTime()) {
      buckets.last7days.push(conv)
    } else if (dayStart.getTime() >= monthStart.getTime()) {
      buckets.thisMonth.push(conv)
    } else {
      buckets.older.push(conv)
    }
  }

  return GROUP_META
    .filter(({ key }) => buckets[key].length > 0)
    .map(({ key, label }) => ({ key, label, items: buckets[key] }))
}

export function formatConversationDate(iso?: string | null, now: Date = new Date()): string {
  const date = parseDate(iso)
  if (!date) return ''

  const todayStart = startOfDay(now)
  const targetStart = startOfDay(date)
  const diffDays = Math.round((todayStart.getTime() - targetStart.getTime()) / 86_400_000)

  if (diffDays === 0) {
    return date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  }
  if (diffDays === 1) {
    return 'Ontem'
  }
  const formatted = date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
  return formatted.replace(/\.$/, '').replace(/\s+de\s+/i, ' ')
}

export function formatBaseVersion(versao?: string | null): string | null {
  if (!versao) return null
  const trimmed = versao.trim()
  const match = trimmed.match(/^v?(\d{4})[-./](\d{2})[-./](\d{2})$/i)
  if (!match) return null
  const [, year, month, day] = match
  return `${day}/${month}/${year}`
}
