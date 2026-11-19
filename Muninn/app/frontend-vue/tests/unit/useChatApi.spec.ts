import { beforeEach, describe, expect, it, vi } from 'vitest'

const callMock = vi.fn()
const streamMock = vi.fn()

vi.mock('@/common/api/core', () => ({
  call: (...args: unknown[]) => callMock(...args),
  stream: (...args: unknown[]) => streamMock(...args),
}))

import { buildChart, isScalarResultData, useChatApi } from '@/modules/chat/composables/useChatApi'

describe('modules/chat/composables/useChatApi', () => {
  beforeEach(() => {
    callMock.mockReset()
    streamMock.mockReset()
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
    expect(streamMock).toHaveBeenCalledWith(
      'chat.stream',
      expect.objectContaining({
        question: 'Quantos projetos por grande área?',
        conversation_id: 'local-123',
        contexto_id: 'ctx-ifes',
      }),
      expect.any(Function),
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
})
