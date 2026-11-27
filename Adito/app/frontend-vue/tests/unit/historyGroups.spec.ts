import { describe, expect, it } from 'vitest'
import type { Conversation } from '@/modules/chat/types'
import {
  formatBaseVersion,
  formatConversationDate,
  groupConversations,
} from '@/modules/chat/utils/historyGroups'

function makeConv(id: string, updatedAt: string, isPinned = false): Conversation {
  return {
    id,
    title: `Conversa ${id}`,
    isPinned,
    messages: [],
    createdAt: updatedAt,
    updatedAt,
  }
}

describe('modules/chat/utils/historyGroups', () => {
  const now = new Date('2026-11-25T15:30:00')

  it('agrupa conversas em Fixadas, Hoje, Últimos 7 dias, Este mês e Anteriores', () => {
    const groups = groupConversations(
      [
        makeConv('pinned', '2026-09-01T10:00:00', true),
        makeConv('today', '2026-11-25T11:00:00'),
        makeConv('week', '2026-11-21T10:00:00'),
        makeConv('month', '2026-11-05T10:00:00'),
        makeConv('old', '2026-10-10T10:00:00'),
      ],
      now,
    )

    expect(groups.map((g) => g.label)).toEqual([
      'Fixadas',
      'Hoje',
      'Últimos 7 dias',
      'Este mês',
      'Anteriores',
    ])
    expect(groups[0].items.map((c) => c.id)).toEqual(['pinned'])
    expect(groups[1].items.map((c) => c.id)).toEqual(['today'])
    expect(groups[2].items.map((c) => c.id)).toEqual(['week'])
    expect(groups[3].items.map((c) => c.id)).toEqual(['month'])
    expect(groups[4].items.map((c) => c.id)).toEqual(['old'])
  })

  it('formatConversationDate formata hoje como HH:mm, ontem como Ontem e datas antigas com dia/mês', () => {
    expect(formatConversationDate('2026-11-25T09:15:00', now)).toMatch(/^09:15$/)
    expect(formatConversationDate('2026-11-24T18:00:00', now)).toBe('Ontem')
    expect(formatConversationDate('2026-10-05T12:00:00', now)).toContain('05')
  })

  it('formatBaseVersion converte YYYY-MM-DD e vYYYY.MM.DD para DD/MM/YYYY', () => {
    expect(formatBaseVersion('2026-11-22')).toBe('22/11/2026')
    expect(formatBaseVersion('v2026.11.22')).toBe('22/11/2026')
    expect(formatBaseVersion('')).toBeNull()
    expect(formatBaseVersion('invalido')).toBeNull()
  })
})
