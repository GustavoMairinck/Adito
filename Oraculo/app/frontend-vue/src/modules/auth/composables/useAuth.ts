import { ref, readonly, computed } from 'vue'
import httpClient from '@/common/api/httpClient'

/**
 * useAuth composable — desktop sem login.
 *
 * Há um único usuário local. O app carrega os dados dele de /api/me ao abrir;
 * o acesso ao backend é protegido pelo token local que o Tauri entrega (common/api/config.ts).
 */

export interface User {
  id?: string
  username: string
  name?: string
  role?: string
  email?: string
  avatar?: string
  tenant?: string | null
}

// Estado global em memória (compartilhado entre instâncias do composable)
const user = ref<User | null>(null)

const isAuthenticated = computed(() => !!user.value)

export function useAuth() {
  async function loadLocalUser() {
    const res = await httpClient.get('/api/me')
    user.value = res.data
    return user.value
  }

  return {
    user: readonly(user),
    isAuthenticated,
    loadLocalUser,
  }
}
