import { computed, ref, watch } from 'vue'
import { call } from '@/common/api/core'
import { useAtualizacoes } from '@/common/composables/useAtualizacoes'

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

const STORAGE_KEY = 'adito_contexto_selecionado'

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

async function fetchAndApplyContextos() {
  const data = await call<Contexto[]>('contextos.list')
  contextos.value = data
  if (!data.some(c => c.id === selectedId.value)) {
    // Sem seleção válida: o único contexto, ou nenhum (o usuário escolhe).
    selectedId.value = data.length === 1 ? data[0].id : null
    save(selectedId.value)
  }
  loaded.value = true
}

const { dadosReloadSeq } = useAtualizacoes()
watch(dadosReloadSeq, (seq) => {
  if (seq > 0 && loaded.value) {
    void fetchAndApplyContextos().catch(() => {})
  }
})

export function useContextos() {
  async function loadContextos() {
    await fetchAndApplyContextos()
  }

  function select(id: string | null) {
    selectedId.value = id
    save(id)
  }

  const selected = computed(() => contextos.value.find(c => c.id === selectedId.value) || null)
  const nameOf = (id?: string | null) => contextos.value.find(c => c.id === id)?.name || null

  return { contextos, selectedId, selected, loaded, loadContextos, select, nameOf }
}
