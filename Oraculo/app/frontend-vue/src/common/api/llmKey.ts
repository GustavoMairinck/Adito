import httpClient from './httpClient'
import { initBackend, isTauri } from './config'

/**
 * Chave da Mistral: o Tauri guarda no cofre do SO (Secret Service / Credential Manager)
 * e reinicia o backend com ela. O front nunca guarda a chave.
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
  if (!isTauri()) return null
  return invoke<KeyStatus>('llm_key_status')
}

/** Testa a chave na Mistral; só guarda se ela funcionar. Devolve o motivo quando falha. */
export async function testAndSaveKey(key: string): Promise<{ ok: boolean; reason?: string }> {
  const { data } = await httpClient.post('/api/config/test-llm-key', { key })
  if (!data.ok) return data
  await invoke('set_llm_key', { key })
  // O backend reinicia com a chave nova; espera ele voltar antes de seguir.
  await initBackend()
  return { ok: true }
}

export async function clearKey(): Promise<void> {
  await invoke('clear_llm_key')
  await initBackend()
}
