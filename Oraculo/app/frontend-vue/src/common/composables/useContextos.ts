import { computed, ref } from 'vue'
import httpClient from '@/common/api/httpClient'

/**
 * Contextos de dados (views do dados.db) que o usuário pode consultar.
 * Uma conversa nova usa o contexto selecionado aqui; a existente mantém o dela.
 */

export interface Contexto {
  id: string
  slug: string
  name: string
  description: string
  views: Array<{ name: string; description: string }>
}

const STORAGE_KEY = 'oraculo_contexto_selecionado'

const contextos = ref<Contexto[]>([])
const selectedId = ref<string | null>(readSaved())
const loaded = ref(false)

function readSaved(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

function save(id: string | null) {
  try {
    if (id) localStorage.setItem(STORAGE_KEY, id)
    else localStorage.removeItem(STORAGE_KEY)
  } catch {
    // Preferência só de conveniência; sem storage o app continua funcionando.
  }
}

export function useContextos() {
  async function loadContextos() {
    const { data } = await httpClient.get<Contexto[]>('/api/contextos')
    contextos.value = data
    if (!data.some(c => c.id === selectedId.value)) {
      // Sem seleção válida: o único contexto, ou nenhum (o usuário escolhe).
      select(data.length === 1 ? data[0].id : null)
    }
    loaded.value = true
  }

  function select(id: string | null) {
    selectedId.value = id
    save(id)
  }

  const selected = computed(() => contextos.value.find(c => c.id === selectedId.value) || null)
  const nameOf = (id?: string | null) => contextos.value.find(c => c.id === id)?.name || null

  return { contextos, selectedId, selected, loaded, loadContextos, select, nameOf }
}
