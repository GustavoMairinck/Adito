import { beforeEach, describe, expect, it, vi } from 'vitest'

const callMock = vi.fn()

vi.mock('@/common/api/core', () => ({
  call: (...args: unknown[]) => callMock(...args),
}))

import { nextTick } from 'vue'
import { useContextos } from '@/common/composables/useContextos'
import { _resetAtualizacoes, useAtualizacoes } from '@/common/composables/useAtualizacoes'

describe('common/composables/useContextos', () => {
  beforeEach(() => {
    _resetAtualizacoes()
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
    expect(localStorage.getItem('adito_contexto_selecionado')).toBe('ctx-ifes')
  })

  it('select persiste e limpa a preferência de contexto no localStorage', () => {
    const { select, selectedId } = useContextos()
    select('ctx-2')
    expect(selectedId.value).toBe('ctx-2')
    expect(localStorage.getItem('adito_contexto_selecionado')).toBe('ctx-2')

    select(null)
    expect(selectedId.value).toBeNull()
    expect(localStorage.getItem('adito_contexto_selecionado')).toBeNull()
  })

  it('recarrega contextos automaticamente quando dadosReloadSeq incrementa', async () => {
    callMock
      .mockResolvedValueOnce([
        {
          id: 'ctx-1',
          slug: 'pesquisa-v1',
          name: 'Pesquisa v1',
          description: 'Base v1',
          views: [],
        },
      ])
      .mockResolvedValueOnce([
        {
          id: 'ctx-1',
          slug: 'pesquisa-v2',
          name: 'Pesquisa v2',
          description: 'Base atualizada',
          views: [],
        },
      ])

    const { loadContextos, contextos } = useContextos()
    await loadContextos()
    expect(contextos.value[0]?.name).toBe('Pesquisa v1')

    const { dadosReloadSeq } = useAtualizacoes()
    dadosReloadSeq.value += 1
    await nextTick()
    await Promise.resolve()

    expect(callMock).toHaveBeenCalledTimes(2)
    expect(contextos.value[0]?.name).toBe('Pesquisa v2')
  })
})
