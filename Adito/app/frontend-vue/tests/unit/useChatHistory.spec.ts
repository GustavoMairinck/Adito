import { beforeEach, describe, expect, it, vi } from 'vitest'

const callMock = vi.fn()

vi.mock('@/common/api/core', () => ({
  call: (...args: unknown[]) => callMock(...args),
}))

import { createConversation, useChatHistory } from '@/modules/chat/composables/useChatHistory'

describe('modules/chat/composables/useChatHistory', () => {
  beforeEach(() => {
    callMock.mockReset()
    localStorage.clear()
  })

  it('createConversation cria conversa local com mensagem de boas-vindas do Adito', () => {
    const conv = createConversation()
    expect(conv.id.startsWith('local-')).toBe(true)
    expect(conv.title).toBe('Nova Conversa')
    expect(conv.messages).toHaveLength(1)
    expect(conv.messages[0].id).toBe('welcome')
    expect(conv.messages[0].text).toContain('Adito')
  })

  it('limpa chaves antigas de histórico no localStorage ao inicializar', () => {
    localStorage.setItem('adito_chat_history:legado', '[]')
    localStorage.setItem('outra_chave', 'manter')
    callMock.mockResolvedValueOnce([])

    useChatHistory()

    expect(localStorage.getItem('adito_chat_history:legado')).toBeNull()
    expect(localStorage.getItem('outra_chave')).toBe('manter')
  })

  it('syncFromBackend carrega conversas e reexecuta linhas pendentes via chat.message_rows', async () => {
    callMock.mockImplementation(async (method: string) => {
      if (method === 'chat.conversations.list') {
        return [
          {
            id: 'conv-1',
            title: 'Bolsas 2024',
            contexto: 'ctx-1',
            created_at: '2026-11-18T10:00:00Z',
            messages: [
              { id: 'u1', role: 'user', content: 'Quantas bolsas em 2024?', created_at: '2026-11-18T10:00:01Z' },
              {
                id: 'a1',
                role: 'assistant',
                content: 'Foram 120 bolsas.',
                created_at: '2026-11-18T10:00:02Z',
                metadata: { sql: 'SELECT COUNT(*) AS total FROM vfact_orientacao_bolsa_resolved', type: 'analysis' },
              },
            ],
          },
        ]
      }
      if (method === 'chat.message_rows') {
        return { data: [{ total: 120 }] }
      }
      return null
    })

    const { conversations, currentConversation, syncFromBackend } = useChatHistory()
    await syncFromBackend()
    await new Promise((r) => setTimeout(r, 0))

    expect(conversations.value).toHaveLength(1)
    expect(currentConversation.value.title).toBe('Bolsas 2024')
    const aiMsg = currentConversation.value.messages[2]
    expect(aiMsg.table).toEqual([{ total: 120 }])
    expect(aiMsg.isScalarResult).toBe(true)
    expect(aiMsg.needsRows).toBe(false)
  })

  it('handleNewConversation, replaceConversationId e handleDeleteConversation mantêm estado consistente', async () => {
    callMock.mockResolvedValue([])
    const history = useChatHistory()
    await history.syncFromBackend()
    const initialId = history.currentConvId.value!

    await new Promise((r) => setTimeout(r, 5))
    history.handleNewConversation()
    expect(history.conversations.value).toHaveLength(2)

    const newLocalId = history.currentConvId.value!
    expect(newLocalId).not.toBe(initialId)
    history.replaceConversationId(newLocalId, 'conv-remota')
    expect(history.currentConvId.value).toBe('conv-remota')

    await history.handleDeleteConversation('conv-remota')
    expect(callMock).toHaveBeenCalledWith('chat.conversations.delete', { id: 'conv-remota' })
    expect(history.currentConvId.value).toBe(initialId)
  })
})
