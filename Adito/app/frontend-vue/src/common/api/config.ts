/**
 * Configurações globais da aplicação Frontend.
 *
 * No desktop, a URL do backend (porta livre escolhida na hora) e o token local
 * vêm do Tauri em tempo de execução; no navegador (desenvolvimento) vêm do .env do Vite.
 */

interface BackendInfo {
  baseUrl: string
  token: string
}

let backend: BackendInfo = {
  baseUrl: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001',
  token: import.meta.env.VITE_LOCAL_TOKEN || '',
}

export const isTauri = () => typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window

/** Chamado uma vez antes de montar o app. No Tauri, espera o backend subir. */
export async function initBackend(): Promise<void> {
  if (!isTauri()) return
  const { invoke } = await import('@tauri-apps/api/core')
  const info = await invoke<{ base_url: string; token: string }>('backend_info')
  backend = { baseUrl: info.base_url, token: info.token }
}

export const apiBase = () => backend.baseUrl

/** Header que o backend exige em toda chamada (core/local_auth.py). */
export const authHeaders = (): Record<string, string> =>
  backend.token ? { 'X-Oraculo-Token': backend.token } : {}

// Timeout padrão para requisições (em milissegundos)
export const API_TIMEOUT = parseInt(import.meta.env.VITE_API_TIMEOUT as string) || 90000

// Versão da aplicação
export const APP_VERSION = '1.0.0'
