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
  // A chave do Gemini está no cofre do SO e chegou ao backend.
  llm_configured?: boolean
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
