import { ref, readonly, computed } from 'vue'
import httpClient from '@/common/api/httpClient'

/**
 * useAuth composable — gerencia estado global de autenticação.
 *
 * SEGURANÇA (VULN-003):
 * O JWT de acesso NÃO é mais armazenado no localStorage (vulnerável a XSS).
 * O backend seta o token como HttpOnly Cookie, inacessível ao JavaScript.
 * O httpClient envia o cookie automaticamente (withCredentials: true).
 *
 * Apenas os dados públicos do usuário (nome, role, email) são armazenados
 * em sessionStorage para UX — sem dados sensíveis.
 */

const USER_KEY = 'oraculo_esx_user'

export interface User {
  id?: string
  username: string
  name?: string
  role?: string
  email?: string
  avatar?: string
  tenant?: string | null
}

function loadUser(): User | null {
  try {
    return JSON.parse(sessionStorage.getItem(USER_KEY) || 'null')
  } catch {
    return null
  }
}

// Estado global em memória (compartilhado entre instâncias do composable)
const user = ref<User | null>(loadUser())

// isAuthenticated é derivado da presença dos dados do usuário em memória/sessionStorage.
// A validade real do token é verificada pelo backend a cada requisição.
const isAuthenticated = computed(() => !!user.value)

export function useAuth() {
  function setAuthenticatedUser(userData: User) {
    user.value = userData
    sessionStorage.setItem(USER_KEY, JSON.stringify(userData))
    return userData
  }

  async function login(email: string, password: string) {
    try {
      // O endpoint cookie/login seta o JWT como HttpOnly Cookie no browser.
      // A resposta JSON contém apenas dados não-sensíveis do usuário.
      const res = await httpClient.post('/api/auth/cookie/login', { email, password })
      const userData: User = res.data.user

      return setAuthenticatedUser(userData)
    } catch (err: any) {
      throw new Error(err.response?.data?.message || 'Credenciais inválidas. Verifique e-mail e senha.')
    }
  }

  async function logout() {
    try {
      // Limpa os cookies HttpOnly no servidor
      await httpClient.post('/api/auth/cookie/logout')
    } catch {
      // Ignora erros de rede no logout — limpa estado local de qualquer forma
    } finally {
      user.value = null
      sessionStorage.removeItem(USER_KEY)
      // Remove resquícios do localStorage legado, se existirem
      localStorage.removeItem('oraculo_token')
      localStorage.removeItem('oraculo_user')
      localStorage.removeItem('oraculo_esx_token')
      localStorage.removeItem('oraculo_esx_user')
    }
  }

  return {
    user: readonly(user),
    isAuthenticated,
    login,
    logout,
    setAuthenticatedUser,
  }
}
