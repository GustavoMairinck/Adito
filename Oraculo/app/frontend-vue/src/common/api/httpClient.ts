import axios from 'axios'
import { API_BASE, API_TIMEOUT } from './config'

/**
 * Instância Axios pré-configurada para comunicação com o backend.
 * Interceptors de autenticação serão adicionados conforme necessário.
 */
const httpClient = axios.create({
  baseURL: API_BASE,
  timeout: API_TIMEOUT,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Interceptor: injeta o token JWT em todas as requisições autenticadas
httpClient.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('oraculo_esx_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default httpClient
