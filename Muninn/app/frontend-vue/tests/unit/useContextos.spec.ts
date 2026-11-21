import { beforeEach, describe, expect, it, vi } from 'vitest'

const callMock = vi.fn()

vi.mock('@/common/api/core', () => ({
  call: (...args: unknown[]) => callMock(...args),
}))

import { useContextos } from '@/common/composables/useContextos'

describe('common/composables/useContextos', () => {
  beforeEach(() => {
    callMock.mockReset()
    localStorage.clear()
    const { select } = useContextos()
    select(null)
  })

  it('loadContextos seleciona automaticamente quando há apenas um contexto disponível', async () => {
    callMock.mockResolvedValueOnce([
      {
        id: 'ctx-ifes',
        slug: 'pesquisa-extensao-ifes',
        name: 'Pesquisa e Extensão IFES',
        description: 'Dados acadêmicos',
        views: [{ name: 'vfact_projeto_pesquisa_resolved', description: 'Projetos' }],
      },
    ])

    const { loadContextos, selectedId, selected, loaded, nameOf } = useContextos()
    await loadContextos()

    expect(loaded.value).toBe(true)
    expect(selectedId.value).toBe('ctx-ifes')
    expect(selected.value?.slug).toBe('pesquisa-extensao-ifes')
    expect(nameOf('ctx-ifes')).toBe('Pesquisa e Extensão IFES')
    expect(localStorage.getItem('muninn_contexto_selecionado')).toBe('ctx-ifes')
  })

  it('select persiste e limpa a preferência de contexto no localStorage', () => {
    const { select, selectedId } = useContextos()
    select('ctx-2')
    expect(selectedId.value).toBe('ctx-2')
    expect(localStorage.getItem('muninn_contexto_selecionado')).toBe('ctx-2')

    select(null)
    expect(selectedId.value).toBeNull()
    expect(localStorage.getItem('muninn_contexto_selecionado')).toBeNull()
  })
})
