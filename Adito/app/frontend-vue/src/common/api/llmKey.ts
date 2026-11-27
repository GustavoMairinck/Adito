import { call, coreReady } from './core'

/**
 * Configuração multi-provedor de IA (BYOK):
 * - Chaves ficam isoladas por provedor no cofre do SO (Secret Service / Credential Manager) via Tauri.
 * - Metadados não-sensíveis (provider, model, base_url) ficam em `llm_config.json` na data_dir.
 * - O frontend nunca recebe nem grava segredos; ao reutilizar chave salva, o Rust lê do cofre e envia ao núcleo.
 */

export interface LlmProviderSpec {
  id: string
  label: string
  protocol: 'gemini' | 'openai_compatible'
  base_url: string
  default_model: string
  requires_key: boolean
  allow_custom_base_url: boolean
}

export interface KeyStatus {
  configured: boolean
  store_available: boolean
  error: string | null
}

export interface LlmConfigStatus {
  provider: string
  model: string | null
  base_url: string | null
  configured: boolean
  store_available: boolean
  has_key_by_provider: Record<string, boolean>
  error: string | null
}

export interface LlmConfigInput {
  provider: string
  model?: string
  baseUrl?: string
  key?: string
  useSavedKey?: boolean
}

export interface LlmTestResult {
  ok: boolean
  reason?: string
}

export const DEFAULT_LLM_PROVIDERS: LlmProviderSpec[] = [
  {
    id: 'gemini',
    label: 'Gemini',
    protocol: 'gemini',
    base_url: 'https://generativelanguage.googleapis.com/v1beta',
    default_model: 'gemini-3.5-flash-lite',
    requires_key: true,
    allow_custom_base_url: false,
  },
  {
    id: 'openai',
    label: 'OpenAI',
    protocol: 'openai_compatible',
    base_url: 'https://api.openai.com/v1',
    default_model: 'gpt-4o-mini',
    requires_key: true,
    allow_custom_base_url: false,
  },
  {
    id: 'openrouter',
    label: 'OpenRouter',
    protocol: 'openai_compatible',
    base_url: 'https://openrouter.ai/api/v1',
    default_model: 'google/gemini-2.5-flash',
    requires_key: true,
    allow_custom_base_url: false,
  },
  {
    id: 'mistral',
    label: 'Mistral AI',
    protocol: 'openai_compatible',
    base_url: 'https://api.mistral.ai/v1',
    default_model: 'ministral-8b-latest',
    requires_key: true,
    allow_custom_base_url: false,
  },
  {
    id: 'zai',
    label: 'Z.AI (GLM)',
    protocol: 'openai_compatible',
    base_url: 'https://api.z.ai/api/paas/v4',
    default_model: 'glm-4.5-flash',
    requires_key: true,
    allow_custom_base_url: true,
  },
  {
    id: 'together',
    label: 'Together AI',
    protocol: 'openai_compatible',
    base_url: 'https://api.together.xyz/v1',
    default_model: 'meta-llama/Llama-3.3-70B-Instruct-Turbo',
    requires_key: true,
    allow_custom_base_url: false,
  },
  {
    id: 'fireworks',
    label: 'Fireworks AI',
    protocol: 'openai_compatible',
    base_url: 'https://api.fireworks.ai/inference/v1',
    default_model: 'accounts/fireworks/models/llama-v3p3-70b-instruct',
    requires_key: true,
    allow_custom_base_url: false,
  },
  {
    id: 'ollama',
    label: 'Ollama (Local)',
    protocol: 'openai_compatible',
    base_url: 'http://localhost:11434/v1',
    default_model: 'qwen2.5:7b',
    requires_key: false,
    allow_custom_base_url: true,
  },
]

const LOOPBACK_HOSTS = new Set(['localhost', '127.0.0.1', '::1', '[::1]'])

export function isLoopbackUrl(url: string): boolean {
  const cleaned = url.trim()
  if (!cleaned) return false
  try {
    const parsed = new URL(cleaned)
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return false
    return LOOPBACK_HOSTS.has(parsed.hostname.toLowerCase())
  } catch {
    return false
  }
}

async function invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  const { invoke: tauriInvoke } = await import('@tauri-apps/api/core')
  return tauriInvoke<T>(cmd, args)
}

function extractTestError(err: unknown): LlmTestResult | null {
  if (err && typeof err === 'object' && 'data' in err) {
    const data = (err as { data?: unknown }).data
    if (data && typeof data === 'object' && 'ok' in data && typeof (data as { ok?: unknown }).ok === 'boolean') {
      return data as LlmTestResult
    }
  }
  return null
}

export async function listProviders(): Promise<LlmProviderSpec[]> {
  try {
    const providers = await call<LlmProviderSpec[]>('config.llm_providers')
    if (Array.isArray(providers) && providers.length > 0) return providers
  } catch {
    // Fallback para catálogo embutido caso o núcleo ainda não tenha respondido.
  }
  return DEFAULT_LLM_PROVIDERS
}

export async function keyStatus(): Promise<KeyStatus | null> {
  return invoke<KeyStatus>('llm_key_status')
}

export async function llmConfigStatus(): Promise<LlmConfigStatus> {
  return invoke<LlmConfigStatus>('llm_config_status')
}

/** Testa credencial/modelo/URL direto via Tauri → núcleo; só persiste e reinicia se passar. */
export async function testAndSaveConfig(input: LlmConfigInput): Promise<LlmTestResult> {
  const payload = {
    provider: input.provider,
    model: input.model?.trim() || null,
    baseUrl: input.baseUrl?.trim() || null,
    key: input.key?.trim() || null,
    useSavedKey: Boolean(input.useSavedKey),
  }

  let data: LlmTestResult
  try {
    data = await invoke<LlmTestResult>('test_llm_config', payload)
  } catch (err: unknown) {
    const structured = extractTestError(err)
    if (structured) return structured
    throw err
  }
  if (!data.ok) return data

  await invoke('set_llm_config', payload)
  await coreReady()
  return { ok: true }
}

/** Compatibilidade com chamadas legadas que validavam e salvavam apenas a chave do Gemini. */
export async function testAndSaveKey(key: string): Promise<LlmTestResult> {
  let data: LlmTestResult
  try {
    data = await call<LlmTestResult>('config.test_llm_key', { key })
  } catch (err: unknown) {
    const structured = extractTestError(err)
    if (structured) return structured
    throw err
  }
  if (!data.ok) return data
  await invoke('set_llm_key', { key })
  await coreReady()
  return { ok: true }
}

export async function clearKey(provider?: string): Promise<void> {
  await invoke('clear_llm_key', provider ? { provider } : undefined)
  await coreReady()
}
