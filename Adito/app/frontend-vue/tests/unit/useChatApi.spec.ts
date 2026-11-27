import { beforeEach, describe, expect, it, vi } from 'vitest'

const callMock = vi.fn()
const streamMock = vi.fn()

vi.mock('@/common/api/core', () => ({
  call: (...args: unknown[]) => callMock(...args),
  stream: (...args: unknown[]) => streamMock(...args),
}))

import { buildChart, isScalarResultData, resetChatApiForTests, useChatApi } from '@/modules/chat/composables/useChatApi'

describe('modules/chat/composables/useChatApi', () => {
  beforeEach(() => {
    callMock.mockReset()
    streamMock.mockReset()
    resetChatApiForTests()
  })

  it('isScalarResultData identifica corretamente resultado de célula única', () => {
    expect(isScalarResultData([{ total_projetos: 236 }])).toBe(true)
    expect(isScalarResultData([{ area: 'Exatas', total: 40 }])).toBe(false)
    expect(isScalarResultData([{ total: 1 }, { total: 2 }])).toBe(false)
    expect(isScalarResultData([])).toBe(false)
  })

  it('buildChart constrói categorias e séries numéricas normalizadas', () => {
    const chart = buildChart([
      { grande_area: 'Engenharias', total_projetos: 42, investimento_total: '12500.5' },
      { grande_area: 'Ciências Exatas', total_projetos: 31, investimento_total: 8400 },
    ])

    expect(chart).toEqual({
      categories: ['Engenharias', 'Ciências Exatas'],
      series: [
        { name: 'Total Projetos', data: [42, 31] },
        { name: 'Investimento Total', data: [12500.5, 8400] },
      ],
    })
    expect(buildChart([{ nome: 'Sem número' }])).toBeNull()
    expect(buildChart([])).toBeNull()
  })

  it('checkHealth retorna true quando núcleo responde e false em erro', async () => {
    const { checkHealth } = useChatApi()
    callMock.mockResolvedValueOnce({ status: 'ok' })
    expect(await checkHealth()).toBe(true)

    callMock.mockRejectedValueOnce(new Error('offline'))
    expect(await checkHealth()).toBe(false)
  })

  it('askQuestionStream processa status, tokens e resultado analítico com gráfico', async () => {
    const { askQuestionStream, isLoading } = useChatApi()
    streamMock.mockImplementation(async (_method, _payload, onEvent) => {
      onEvent('status', { message: 'Consultando dados...' })
      onEvent('token', { text: 'Resumo: ' })
      onEvent('result', {
        message_id: 'msg-1',
        conversation_id: 'conv-1',
        type: 'analysis',
        text: 'Foram encontrados 236 projetos.',
        sql: 'SELECT grande_area, COUNT(*) AS total FROM vfact_projeto_pesquisa_resolved GROUP BY grande_area',
        data: [
          { grande_area: 'Engenharias', total: 120 },
          { grande_area: 'Exatas', total: 116 },
        ],
        chart_type: 'pie',
      })
    })

    const statuses: string[] = []
    const tokens: string[] = []
    const msg = await askQuestionStream(
      'Quantos projetos por grande área?',
      'local-123',
      {
        onStatus: (m) => statuses.push(m),
        onToken: (t) => tokens.push(t),
      },
      'ctx-ifes',
    )

    expect(isLoading.value).toBe(false)
    expect(statuses).toEqual(['Consultando dados...'])
    expect(tokens).toEqual(['Resumo: '])
    expect(msg.text).toBe('Foram encontrados 236 projetos.')
    expect(msg.chart?.categories).toEqual(['Engenharias', 'Exatas'])
    // Tipo de gráfico sugerido pelo agente de painéis
    expect(msg.suggestedChartType).toBe('pie')
    expect(streamMock).toHaveBeenCalledWith(
      'chat.stream',
      expect.objectContaining({
        question: 'Quantos projetos por grande área?',
        conversation_id: 'local-123',
        contexto_id: 'ctx-ifes',
      }),
      expect.any(Function),
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
  })

  it('askQuestionStream devolve mensagem de erro amigável quando stream falha', async () => {
    const { askQuestionStream } = useChatApi()
    streamMock.mockImplementation(async (_m, _p, onEvent) => {
      onEvent('error', { message: 'Chave Gemini não configurada' })
    })

    const msg = await askQuestionStream('Quantos projetos?')
    expect(msg.error).toBe(true)
    expect(msg.text).toContain('Chave Gemini não configurada')
  })

  it('cancelStream aborta apenas a conversa alvo, retorna interrupted sem erro e mantém outra conversa ativa', async () => {
    const { askQuestionStream, cancelStream, isConversationLoading } = useChatApi()
    let resolveB!: () => void

    streamMock.mockImplementation((_m, payload, onEvent, options) => {
      if (payload.conversation_id === 'conv-a') {
        return new Promise((_resolve, reject) => {
          onEvent('token', { text: 'Parcial A' })
          options?.signal?.addEventListener('abort', () => {
            const err = new Error('canceled')
            err.name = 'CanceledError'
            reject(err)
          })
        })
      }
      return new Promise<void>((resolve) => {
        resolveB = () => {
          onEvent('result', {
            message_id: 'msg-b',
            conversation_id: 'conv-b',
            type: 'chat',
            text: 'Resposta B completa',
          })
          resolve()
        }
      })
    })

    const promiseA = askQuestionStream('Pergunta A', 'conv-a')
    const promiseB = askQuestionStream('Pergunta B', 'conv-b')

    expect(isConversationLoading('conv-a')).toBe(true)
    expect(isConversationLoading('conv-b')).toBe(true)

    expect(cancelStream('conv-a')).toBe(true)
    const resultA = await promiseA

    expect(resultA.interrupted).toBe(true)
    expect(resultA.error).toBeFalsy()
    expect(isConversationLoading('conv-a')).toBe(false)
    expect(isConversationLoading('conv-b')).toBe(true)

    resolveB()
    const resultB = await promiseB
    expect(resultB.text).toBe('Resposta B completa')
    expect(isConversationLoading('conv-b')).toBe(false)
  })

  it('migra a chave do stream quando conversa local-* recebe conversation_id no status', async () => {
    const { askQuestionStream, cancelStream, isConversationLoading } = useChatApi()

    streamMock.mockImplementation((_m, _payload, onEvent, options) => {
      return new Promise((_resolve, reject) => {
        onEvent('status', { message: 'Roteando...', conversation_id: 'conv-real-42' })
        options?.signal?.addEventListener('abort', () => {
          const err = new Error('canceled')
          err.name = 'CanceledError'
          reject(err)
        })
      })
    })

    const promise = askQuestionStream('Nova pergunta', 'local-999')
    expect(isConversationLoading('local-999')).toBe(false)
    expect(isConversationLoading('conv-real-42')).toBe(true)

    expect(cancelStream('conv-real-42')).toBe(true)
    const result = await promise
    expect(result.interrupted).toBe(true)
    expect(isConversationLoading('conv-real-42')).toBe(false)
  })

  it('encaminha eventos step_* para onTraceEvent e normaliza trace no resultado', async () => {
    const { askQuestionStream } = useChatApi()
    streamMock.mockImplementation(async (_m, _p, onEvent) => {
      onEvent('step_start', { step_id: 'routing', title: 'Orquestrador', header_status: 'Analisando contexto...' })
      onEvent('step_detail', { step_id: 'routing', detail: 'Encaminhando para BI' })
      onEvent('step_complete', { step_id: 'routing' })
      onEvent('step_code', { step_id: 'query', language: 'sql', code: 'SELECT 1' })
      onEvent('result', {
        message_id: 'msg-trace-1',
        conversation_id: 'conv-trace-1',
        type: 'analysis',
        text: 'Total **1**.',
        sql: 'SELECT 1',
        data: [{ total: 1 }],
        trace: {
          duration_ms: 1450,
          compact: false,
          steps: [
            { id: 'routing', title: 'Orquestrador', status: 'done', details: ['Encaminhando para BI'] },
            { id: 'query', title: 'Agente de dados', status: 'done', details: ['1 registro encontrado.'], code: 'SELECT 1', language: 'sql' },
          ],
        },
      })
    })

    const receivedEvents: string[] = []
    const msg = await askQuestionStream('Teste trace', 'local-1', {
      onTraceEvent: (evt) => receivedEvents.push(evt.event),
    })

    expect(receivedEvents).toEqual(['step_start', 'step_detail', 'step_complete', 'step_code'])
    expect(msg.trace?.durationMs).toBe(1450)
    expect(msg.trace?.steps).toHaveLength(2)
    expect(msg.trace?.steps[1].code).toBe('SELECT 1')
  })

  it('limpa o estado de carregamento e retorna erro amigável quando o núcleo reinicia com status 503', async () => {
    const { askQuestionStream, isConversationLoading } = useChatApi()
    streamMock.mockRejectedValueOnce(Object.assign(new Error('O núcleo está reiniciando.'), { status: 503 }))

    const msg = await askQuestionStream('Pergunta durante reinício', 'conv-503')

    expect(msg.error).toBe(true)
    expect(msg.interrupted).toBeFalsy()
    expect(msg.text).toContain('O núcleo está reiniciando.')
    expect(isConversationLoading('conv-503')).toBe(false)
  })
})
