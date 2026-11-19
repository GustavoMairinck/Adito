import { beforeEach, describe, expect, it, vi } from 'vitest'

const invokeMock = vi.fn()
const callMock = vi.fn()
const coreReadyMock = vi.fn()

vi.mock('@tauri-apps/api/core', () => ({
  invoke: (...args: unknown[]) => invokeMock(...args),
}))

vi.mock('@/common/api/core', () => ({
  call: (...args: unknown[]) => callMock(...args),
  coreReady: (...args: unknown[]) => coreReadyMock(...args),
}))

import { clearKey, keyStatus, testAndSaveKey } from '@/common/api/llmKey'

describe('common/api/llmKey', () => {
  beforeEach(() => {
    invokeMock.mockReset()
    callMock.mockReset()
    coreReadyMock.mockReset()
  })

  it('keyStatus consulta llm_key_status no Tauri', async () => {
    const status = { configured: true, store_available: true, error: null }
    invokeMock.mockResolvedValueOnce(status)

    expect(await keyStatus()).toEqual(status)
    expect(invokeMock).toHaveBeenCalledWith('llm_key_status', undefined)
  })

  it('testAndSaveKey valida chave, salva no cofre e aguarda coreReady quando válida', async () => {
    callMock.mockResolvedValueOnce({ ok: true })
    invokeMock.mockResolvedValueOnce(undefined)
    coreReadyMock.mockResolvedValueOnce(undefined)

    const result = await testAndSaveKey('chave-teste-valida')

    expect(result).toEqual({ ok: true })
    expect(callMock).toHaveBeenCalledWith('config.test_llm_key', { key: 'chave-teste-valida' })
    expect(invokeMock).toHaveBeenCalledWith('set_llm_key', { key: 'chave-teste-valida' })
    expect(coreReadyMock).toHaveBeenCalledOnce()
  })

  it('testAndSaveKey não salva no cofre quando validação retorna ok=false', async () => {
    callMock.mockResolvedValueOnce({ ok: false, reason: 'Chave inválida' })

    const result = await testAndSaveKey('chave-invalida')

    expect(result).toEqual({ ok: false, reason: 'Chave inválida' })
    expect(invokeMock).not.toHaveBeenCalled()
    expect(coreReadyMock).not.toHaveBeenCalled()
  })

  it('testAndSaveKey devolve corpo estruturado quando núcleo responde erro 400 com {ok, reason}', async () => {
    callMock.mockRejectedValueOnce({ status: 400, data: { ok: false, reason: 'Chave vazia' } })

    const result = await testAndSaveKey('')
    expect(result).toEqual({ ok: false, reason: 'Chave vazia' })
  })

  it('clearKey limpa a chave no cofre e aguarda coreReady', async () => {
    invokeMock.mockResolvedValueOnce(undefined)
    coreReadyMock.mockResolvedValueOnce(undefined)

    await clearKey()

    expect(invokeMock).toHaveBeenCalledWith('clear_llm_key', undefined)
    expect(coreReadyMock).toHaveBeenCalledOnce()
  })
})
