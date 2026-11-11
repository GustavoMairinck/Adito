import axios from 'axios'
import { API_TIMEOUT, apiBase, authHeaders } from './config'

/**
 * Instância Axios pré-configurada para comunicação com o backend local.
 * A URL e o token só são conhecidos depois de initBackend(), por isso entram por requisição.
 */
const httpClient = axios.create({
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json'
  }
})

httpClient.interceptors.request.use((config) => {
  config.baseURL = apiBase()
  Object.assign(config.headers, authHeaders())
  return config
})

export default httpClient
