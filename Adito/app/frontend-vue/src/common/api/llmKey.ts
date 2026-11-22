import { call, coreReady } from './core'

/**
 * Chave do Gemini: o Tauri guarda no cofre do SO (Secret Service / Credential Manager)
 * e reinicia o núcleo com ela. O front nunca guarda a chave.
 */

export interface KeyStatus {
  configured: boolean
  store_available: boolean
  error: string | null
}

async function invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  const { invoke } = await import('@tauri-apps/api/core')
  return invoke<T>(cmd, args)
}

export async function keyStatus(): Promise<KeyStatus | null> {
  return invoke<KeyStatus>('llm_key_status')
}

/** Testa a chave no Gemini; só guarda se ela funcionar. Devolve o motivo quando falha. */
export async function testAndSaveKey(key: string): Promise<{ ok: boolean; reason?: string }> {
  let data: { ok: boolean; reason?: string }
  try {
    data = await call('config.test_llm_key', { key })
  } catch (err: any) {
    // Chave vazia volta como erro 400 com o mesmo corpo {ok, reason}.
    if (err?.data && typeof err.data.ok === 'boolean') return err.data
    throw err
  }
  if (!data.ok) return data
  await invoke('set_llm_key', { key })
  // O núcleo reinicia com a chave nova; espera ele voltar antes de seguir.
  await coreReady()
  return { ok: true }
}

export async function clearKey(): Promise<void> {
  await invoke('clear_llm_key')
  await coreReady()
}
