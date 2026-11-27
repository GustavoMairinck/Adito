import { beforeEach, describe, expect, it, vi } from 'vitest'

const callMock = vi.fn()
const streamMock = vi.fn()

vi.mock('@/common/api/core', () => ({
  call: (...args: unknown[]) => callMock(...args),
  stream: (...args: unknown[]) => streamMock(...args),
}))

import { resetChatApiForTests, useChatApi } from '@/modules/chat/composables/useChatApi'
import { createConversation, resetChatHistoryForTests, useChatHistory } from '@/modules/chat/composables/useChatHistory'

describe('modules/chat/composables/useChatHistory', () => {
  beforeEach(() => {
    callMock.mockReset()
    streamMock.mockReset()
    localStorage.clear()
    resetChatHistoryForTests()
    resetChatApiForTests()
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
                metadata: {
                  sql: 'SELECT COUNT(*) AS total FROM vfact_orientacao_bolsa_resolved',
                  type: 'analysis',
                  chart_type: 'horizontal_bar',
                },
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
    // O tipo de gráfico sugerido continua ao reabrir a conversa
    expect(aiMsg.suggestedChartType).toBe('horizontal_bar')
  })

  it('reloadReports reexecuta os relatórios já carregados (dados.db atualizado em segundo plano)', async () => {
    let total = 120
    callMock.mockImplementation(async (method: string) => {
      if (method === 'chat.conversations.list') {
        return [{
          id: 'conv-1',
          title: 'Bolsas',
          contexto: 'ctx-1',
          created_at: '2026-11-18T10:00:00Z',
          messages: [{
            id: 'r1',
            role: 'assistant',
            content: 'Relatório',
            created_at: '2026-11-18T10:00:03Z',
            metadata: {
              type: 'report',
              title: 'Bolsas',
              generated_at: '2026-11-18T10:00:03Z',
              sections: [{ source_message_id: 'a1', title: 'Total', sql: 'SELECT 1', field_formats: {}, chart_type: null }],
            },
          }],
        }]
      }
      if (method === 'chat.report_rows') return { sections: [{ data: [{ total }], error: null }] }
      return null
    })

    const { currentConversation, currentConvId, syncFromBackend, reloadReports } = useChatHistory()
    await syncFromBackend()
    await new Promise((r) => setTimeout(r, 0))
    const report = () => currentConversation.value.messages.find((m) => m.report)!.report!
    expect(report().sections[0].data).toEqual([{ total: 120 }])

    const reportCalls = () => callMock.mock.calls.filter(([method]) => method === 'chat.report_rows').length
    const before = reportCalls()
    total = 130
    await reloadReports(currentConvId.value)
    expect(report().sections[0].data).toEqual([{ total: 130 }])
    expect(reportCalls()).toBe(before + 1)
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

  it('updateConversationById atualiza conversa em segundo plano sem mudar o foco e excluir cancela stream ativo', async () => {
    callMock.mockResolvedValue([])
    const history = useChatHistory()
    await history.syncFromBackend()
    const convA = history.currentConvId.value!

    history.handleNewConversation()
    const convB = history.currentConvId.value!
    expect(convB).not.toBe(convA)

    // Atualiza conversa A enquanto B está selecionada
    history.updateConversationById(convA, (conv) => ({
      ...conv,
      title: 'Título atualizado em segundo plano',
    }))
    expect(history.currentConvId.value).toBe(convB)
    expect(history.conversations.value.find((c) => c.id === convA)?.title).toBe('Título atualizado em segundo plano')

    // Excluir conversa com stream ativo aborta automaticamente
    const { askQuestionStream, isConversationLoading } = useChatApi()
    streamMock.mockImplementation((_m, _p, _onEvent, options) => {
      return new Promise((_resolve, reject) => {
        options?.signal?.addEventListener('abort', () => {
          const err = new Error('canceled')
          err.name = 'CanceledError'
          reject(err)
        })
      })
    })
    const pending = askQuestionStream('Pergunta em A', convA)
    expect(isConversationLoading(convA)).toBe(true)

    await history.handleDeleteConversation(convA)
    const res = await pending
    expect(res.interrupted).toBe(true)
    expect(isConversationLoading(convA)).toBe(false)
  })

  it('syncFromBackend atrasado preserva conversa local com stream em andamento sem roubar foco', async () => {
    callMock.mockResolvedValueOnce([])
    const history = useChatHistory()
    const activeLocalId = history.currentConvId.value!

    // Usuário envia pergunta antes de um syncFromBackend atrasado resolver
    history.updateConversationById(activeLocalId, (conv) => ({
      ...conv,
      title: 'Pergunta rápida',
      messages: [
        ...conv.messages,
        { id: 'u-local', type: 'user', text: 'Pergunta rápida', timestamp: new Date().toISOString() },
      ],
    }))
    const { askQuestionStream, cancelStream } = useChatApi()
    streamMock.mockImplementation((_m, _p, _onEvent, options) => {
      return new Promise((_resolve, reject) => {
        options?.signal?.addEventListener('abort', () => {
          const err = new Error('canceled')
          err.name = 'CanceledError'
          reject(err)
        })
      })
    })
    const pending = askQuestionStream('Pergunta rápida', activeLocalId)

    callMock.mockResolvedValueOnce([
      {
        id: 'conv-remota-1',
        title: 'Histórico antigo',
        contexto: 'ctx-1',
        created_at: '2026-11-18T10:00:00Z',
        messages: [],
      },
    ])
    await history.syncFromBackend()

    expect(history.currentConvId.value).toBe(activeLocalId)
    expect(history.conversations.value.map((c) => c.id)).toEqual([activeLocalId, 'conv-remota-1'])

    cancelStream(activeLocalId)
    await pending

    // Mesmo após interrompida e migrada para conv-remota-1 (já presente no sync), não duplica nem perde o aviso
    history.updateConversationById(activeLocalId, (conv) => ({
      ...conv,
      messages: [
        ...conv.messages,
        { id: 'ai-int', type: 'ai', text: 'Parcial', timestamp: new Date().toISOString(), interrupted: true },
      ],
    }))
    history.replaceConversationId(activeLocalId, 'conv-remota-1')
    expect(history.conversations.value.filter((c) => c.id === 'conv-remota-1')).toHaveLength(1)
    expect(history.currentConvId.value).toBe('conv-remota-1')

    // Novo syncFromBackend preserva a conversa recém-interrompida em memória
    callMock.mockResolvedValueOnce([
      {
        id: 'conv-remota-1',
        title: 'Histórico antigo',
        contexto: 'ctx-1',
        created_at: '2026-11-18T10:00:00Z',
        messages: [],
      },
    ])
    await history.syncFromBackend()
    const preserved = history.conversations.value.find((c) => c.id === 'conv-remota-1')
    expect(preserved?.messages.some((m) => m.interrupted)).toBe(true)
  })

  it('handleRenameConversation e handleTogglePinConversation atualizam com persistência e fazem rollback em erro', async () => {
    callMock.mockImplementation(async (method: string, params?: Record<string, unknown>) => {
      if (method === 'chat.conversations.list') {
        return [
          {
            id: 'conv-pin-1',
            title: 'Título Original',
            is_pinned: false,
            contexto: 'ctx-1',
            created_at: '2026-11-18T10:00:00Z',
            updated_at: '2026-11-18T10:00:00Z',
            messages: [
              {
                id: 'a-trace',
                role: 'assistant',
                content: 'Ok',
                created_at: '2026-11-18T10:00:02Z',
                metadata: {
                  type: 'chat',
                  trace: { duration_ms: 300, compact: true, steps: [{ id: 'routing', title: 'Orquestrador', status: 'done', details: [] }] },
                },
              },
            ],
          },
        ]
      }
      if (method === 'chat.conversations.update') {
        if (params?.title === 'Erro') throw new Error('Falha de escrita')
        return { ok: true }
      }
      return null
    })

    const history = useChatHistory()
    await history.syncFromBackend()

    expect(history.conversations.value[0].messages[1].trace?.compact).toBe(true)

    await history.handleRenameConversation('conv-pin-1', 'Novo Título')
    expect(callMock).toHaveBeenCalledWith('chat.conversations.update', { id: 'conv-pin-1', title: 'Novo Título' })
    expect(history.conversations.value[0].title).toBe('Novo Título')

    await expect(history.handleRenameConversation('conv-pin-1', 'Erro')).rejects.toThrow('Falha de escrita')
    expect(history.conversations.value[0].title).toBe('Novo Título')

    await history.handleTogglePinConversation('conv-pin-1')
    expect(callMock).toHaveBeenCalledWith('chat.conversations.update', { id: 'conv-pin-1', is_pinned: true })
    expect(history.conversations.value[0].isPinned).toBe(true)

    callMock.mockRejectedValueOnce(new Error('Falha ao desafixar'))
    await expect(history.handleTogglePinConversation('conv-pin-1')).rejects.toThrow('Falha ao desafixar')
    expect(history.conversations.value[0].isPinned).toBe(true)
  })
})
