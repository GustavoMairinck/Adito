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

import {
  clearKey,
  DEFAULT_LLM_PROVIDERS,
  isLoopbackUrl,
  keyStatus,
  listProviders,
  llmConfigStatus,
  testAndSaveConfig,
  testAndSaveKey,
} from '@/common/api/llmKey'

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

  it('llmConfigStatus consulta llm_config_status multi-provedor no Tauri', async () => {
    const status = {
      provider: 'openai',
      model: 'gpt-4o-mini',
      base_url: null,
      configured: true,
      store_available: true,
      has_key_by_provider: { gemini: true, openai: true },
      error: null,
    }
    invokeMock.mockResolvedValueOnce(status)

    expect(await llmConfigStatus()).toEqual(status)
    expect(invokeMock).toHaveBeenCalledWith('llm_config_status', undefined)
  })

  it('listProviders busca config.llm_providers no núcleo e usa fallback em caso de falha', async () => {
    callMock.mockResolvedValueOnce(DEFAULT_LLM_PROVIDERS)
    expect(await listProviders()).toHaveLength(8)
    expect(callMock).toHaveBeenCalledWith('config.llm_providers')

    callMock.mockRejectedValueOnce(new Error('offline'))
    expect(await listProviders()).toEqual(DEFAULT_LLM_PROVIDERS)
  })

  it('testAndSaveConfig valida via Rust, salva e aguarda coreReady quando válida', async () => {
    invokeMock.mockResolvedValueOnce({ ok: true })
    invokeMock.mockResolvedValueOnce(undefined)
    coreReadyMock.mockResolvedValueOnce(undefined)

    const result = await testAndSaveConfig({
      provider: 'openai',
      model: 'gpt-4o-mini',
      key: 'sk-valid',
      useSavedKey: false,
    })

    expect(result).toEqual({ ok: true })
    expect(invokeMock).toHaveBeenNthCalledWith(1, 'test_llm_config', {
      provider: 'openai',
      model: 'gpt-4o-mini',
      baseUrl: null,
      key: 'sk-valid',
      useSavedKey: false,
    })
    expect(invokeMock).toHaveBeenNthCalledWith(2, 'set_llm_config', {
      provider: 'openai',
      model: 'gpt-4o-mini',
      baseUrl: null,
      key: 'sk-valid',
      useSavedKey: false,
    })
    expect(coreReadyMock).toHaveBeenCalledOnce()
  })

  it('testAndSaveConfig reutiliza chave salva sem enviar segredo ao frontend', async () => {
    invokeMock.mockResolvedValueOnce({ ok: true })
    invokeMock.mockResolvedValueOnce(undefined)
    coreReadyMock.mockResolvedValueOnce(undefined)

    const result = await testAndSaveConfig({
      provider: 'gemini',
      model: 'gemini-3.5-flash-lite',
      useSavedKey: true,
    })

    expect(result).toEqual({ ok: true })
    expect(invokeMock).toHaveBeenNthCalledWith(1, 'test_llm_config', {
      provider: 'gemini',
      model: 'gemini-3.5-flash-lite',
      baseUrl: null,
      key: null,
      useSavedKey: true,
    })
  })

  it('testAndSaveConfig não salva quando validação falha', async () => {
    invokeMock.mockResolvedValueOnce({ ok: false, reason: 'Chave inválida para OpenAI.' })

    const result = await testAndSaveConfig({
      provider: 'openai',
      model: 'gpt-4o-mini',
      key: 'sk-bad',
    })

    expect(result).toEqual({ ok: false, reason: 'Chave inválida para OpenAI.' })
    expect(invokeMock).toHaveBeenCalledTimes(1)
    expect(coreReadyMock).not.toHaveBeenCalled()
  })

  it('testAndSaveKey legado valida chave, salva no cofre e aguarda coreReady quando válida', async () => {
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

  it('clearKey limpa a chave no cofre (global legado ou por provedor) e aguarda coreReady', async () => {
    invokeMock.mockResolvedValueOnce(undefined)
    coreReadyMock.mockResolvedValueOnce(undefined)

    await clearKey()
    expect(invokeMock).toHaveBeenCalledWith('clear_llm_key', undefined)

    invokeMock.mockResolvedValueOnce(undefined)
    coreReadyMock.mockResolvedValueOnce(undefined)

    await clearKey('openai')
    expect(invokeMock).toHaveBeenLastCalledWith('clear_llm_key', { provider: 'openai' })
    expect(coreReadyMock).toHaveBeenCalledTimes(2)
  })

  it('isLoopbackUrl valida exclusivamente localhost, 127.0.0.1 e ::1 sobre http/https', () => {
    expect(isLoopbackUrl('http://localhost:11434/v1')).toBe(true)
    expect(isLoopbackUrl('http://127.0.0.1:8080/v1')).toBe(true)
    expect(isLoopbackUrl('http://[::1]:11434/v1')).toBe(true)
    expect(isLoopbackUrl('https://localhost.evil.com/v1')).toBe(false)
    expect(isLoopbackUrl('ftp://localhost:11434/v1')).toBe(false)
    expect(isLoopbackUrl('https://api.openai.com/v1')).toBe(false)
  })
})
