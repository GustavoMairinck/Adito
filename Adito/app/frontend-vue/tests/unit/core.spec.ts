import { beforeEach, describe, expect, it, vi } from 'vitest'

const invokeMock = vi.fn()
const createdChannels: Array<{ onmessage?: (msg: unknown) => void }> = []

vi.mock('@tauri-apps/api/core', () => {
  class MockChannel<T = unknown> {
    onmessage?: (msg: T) => void
    constructor() {
      createdChannels.push(this as unknown as { onmessage?: (msg: unknown) => void })
    }
  }
  return {
    invoke: (...args: unknown[]) => invokeMock(...args),
    Channel: MockChannel,
  }
})

import { CoreError, call, coreReady, stream } from '@/common/api/core'

describe('common/api/core', () => {
  beforeEach(() => {
    invokeMock.mockReset()
    createdChannels.length = 0
  })

  it('CoreError extrai mensagem de detail, error ou message e preserva response', () => {
    const errDetail = new CoreError(404, { detail: 'Tabela indisponível' })
    expect(errDetail.status).toBe(404)
    expect(errDetail.message).toBe('Tabela indisponível')
    expect(errDetail.response).toEqual({ status: 404, data: { detail: 'Tabela indisponível' } })

    const errFallback = new CoreError(500, null)
    expect(errFallback.message).toBe('status 500')
  })

  it('coreReady invoca o comando core_ready no Tauri', async () => {
    invokeMock.mockResolvedValueOnce(undefined)
    await coreReady()
    expect(invokeMock).toHaveBeenCalledWith('core_ready')
  })

  it('call envia id numérico, method e params via core_call', async () => {
    invokeMock.mockResolvedValueOnce({ status: 'ok' })
    const result = await call('health', { verbose: true })

    expect(result).toEqual({ status: 'ok' })
    expect(invokeMock).toHaveBeenCalledWith(
      'core_call',
      expect.objectContaining({
        id: expect.any(Number),
        method: 'health',
        params: { verbose: true },
      }),
    )
  })

  it('call normaliza erros estruturados e erros genéricos em CoreError', async () => {
    invokeMock.mockRejectedValueOnce({ status: 404, data: { detail: 'Não encontrado' } })
    await expect(call('explorer.rows')).rejects.toMatchObject({
      name: 'CoreError',
      status: 404,
      message: 'Não encontrado',
    })

    invokeMock.mockRejectedValueOnce(new Error('IPC indisponível'))
    await expect(call('health')).rejects.toMatchObject({
      name: 'CoreError',
      status: 503,
    })
  })

  it('call cancela imediatamente com CanceledError e aciona core_cancel ao abortar', async () => {
    const controller = new AbortController()
    invokeMock.mockImplementation((cmd: string) => {
      if (cmd === 'core_cancel') return Promise.resolve()
      return new Promise(() => {})
    })

    const promise = call('dashboard.kpis', {}, { signal: controller.signal })
    controller.abort()

    await expect(promise).rejects.toMatchObject({
      name: 'CanceledError',
      status: 499,
    })
    expect(invokeMock).toHaveBeenCalledWith(
      'core_cancel',
      expect.objectContaining({ id: expect.any(Number) }),
    )
  })

  it('stream entrega eventos em ordem e resolve ao receber $end com ok=true', async () => {
    invokeMock.mockImplementation((cmd: string, args: { onEvent: { onmessage: (m: unknown) => void } }) => {
      if (cmd === 'core_stream') {
        queueMicrotask(() => {
          args.onEvent.onmessage({ event: 'status', data: { message: 'Consultando dados...' } })
          args.onEvent.onmessage({ event: 'token', data: { text: 'Olá ' } })
          args.onEvent.onmessage({ event: '$end', ok: true, result: { done: true } })
          // Evento após $end deve ser ignorado
          args.onEvent.onmessage({ event: 'token', data: { text: 'ignorado' } })
        })
      }
      return Promise.resolve()
    })

    const received: Array<{ event: string; data: unknown }> = []
    const res = await stream('chat.stream', { question: 'Quantos projetos?' }, (event, data) => {
      received.push({ event, data })
    })

    expect(res).toEqual({ done: true })
    expect(received).toEqual([
      { event: 'status', data: { message: 'Consultando dados...' } },
      { event: 'token', data: { text: 'Olá ' } },
    ])
  })

  it('stream rejeita com CoreError ao receber $end com ok=false', async () => {
    invokeMock.mockImplementation((_cmd: string, args: { onEvent: { onmessage: (m: unknown) => void } }) => {
      queueMicrotask(() => {
        args.onEvent.onmessage({
          event: '$end',
          ok: false,
          error: { status: 503, data: { detail: 'Chave LLM não configurada' } },
        })
      })
      return Promise.resolve()
    })

    await expect(stream('chat.stream', { question: 'oi' }, () => {})).rejects.toMatchObject({
      name: 'CoreError',
      status: 503,
      message: 'Chave LLM não configurada',
    })
  })

  it('stream dispara core_cancel, rejeita com CanceledError e ignora eventos atrasados após abort()', async () => {
    invokeMock.mockImplementation((cmd: string) => {
      if (cmd === 'core_stream') return new Promise(() => {})
      return Promise.resolve(undefined)
    })

    const controller = new AbortController()
    const received: Array<{ event: string; data: unknown }> = []
    const promise = stream(
      'chat.stream',
      { question: 'Teste' },
      (event, data) => received.push({ event, data }),
      { signal: controller.signal },
    )

    expect(createdChannels).toHaveLength(1)
    createdChannels[0].onmessage?.({ event: 'token', data: { text: 'Parcial' } })
    expect(received).toEqual([{ event: 'token', data: { text: 'Parcial' } }])

    controller.abort()

    await expect(promise).rejects.toMatchObject({ name: 'CanceledError', status: 499 })
    expect(invokeMock).toHaveBeenCalledWith('core_cancel', { id: expect.any(Number) })

    // Eventos atrasados do canal após abort devem ser totalmente ignorados.
    createdChannels[0].onmessage?.({ event: 'token', data: { text: 'Atrasado' } })
    createdChannels[0].onmessage?.({ event: 'result', data: { text: 'Final atrasado' } })
    expect(received).toEqual([{ event: 'token', data: { text: 'Parcial' } }])
  })

  it('stream rejeita imediatamente sem chamar core_stream quando o signal já chega abortado', async () => {
    const controller = new AbortController()
    controller.abort()

    await expect(
      stream('chat.stream', { question: 'Teste' }, () => {}, { signal: controller.signal }),
    ).rejects.toMatchObject({ name: 'CanceledError', status: 499 })

    expect(invokeMock).not.toHaveBeenCalled()
  })
})
