/**
 * Configurações globais da aplicação Frontend.
 * Centraliza o consumo de variáveis de ambiente do Vite.
 */

// URL base da API do Backend
export const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001'

// Timeout padrão para requisições (em milissegundos)
export const API_TIMEOUT = parseInt(import.meta.env.VITE_API_TIMEOUT as string) || 90000

// Versão da aplicação
export const APP_VERSION = '1.0.0'
