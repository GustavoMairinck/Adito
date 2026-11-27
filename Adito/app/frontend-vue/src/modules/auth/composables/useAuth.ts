import { ref, readonly, computed } from 'vue'
import { call } from '@/common/api/core'

/**
 * useAuth composable — desktop sem login.
 *
 * Há um único usuário local. O app carrega os dados dele (método `me`) ao abrir;
 * a chamada vai ao núcleo local pelo Tauri (common/api/core.ts), sem rede.
 */

export interface User {
  id?: string
  username: string
  name?: string
  role?: string
  email?: string
  avatar?: string
  tenant?: string | null
  // Estado e metadados do provedor de IA ativo (BYOK).
  llm_configured?: boolean
  llm_provider?: string
  llm_provider_label?: string
  llm_model?: string
  llm_is_local?: boolean
}

// Estado global em memória (compartilhado entre instâncias do composable)
const user = ref<User | null>(null)

const isAuthenticated = computed(() => !!user.value)

export function useAuth() {
  async function loadLocalUser() {
    user.value = await call<User>('me')
    return user.value
  }

  return {
    user: readonly(user),
    isAuthenticated,
    loadLocalUser,
  }
}
