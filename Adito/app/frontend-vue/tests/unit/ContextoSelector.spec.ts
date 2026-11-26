import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

const contextosRef = ref<Array<{ id: string; slug: string; name: string; description: string; views: [] }>>([])
const selectedIdRef = ref<string | null>(null)
const loadedRef = ref(true)
const selectMock = vi.fn()
const baseStatusRef = ref<{ instalado: boolean; versao: string | null; desenvolvimento: boolean; chave_configurada: boolean } | null>({
  instalado: true,
  versao: '2026-11-22',
  desenvolvimento: false,
  chave_configurada: true,
})

vi.mock('@/common/composables/useContextos', () => ({
  useContextos: () => ({
    contextos: contextosRef,
    selectedId: selectedIdRef,
    select: selectMock,
    nameOf: (id?: string | null) => contextosRef.value.find((c) => c.id === id)?.name || '',
    loaded: loadedRef,
  }),
}))

vi.mock('@/common/composables/useAtualizacoes', () => ({
  useAtualizacoes: () => ({
    status: baseStatusRef,
  }),
}))

import ContextoSelector from '@/modules/chat/components/ContextoSelector.vue'

describe('modules/chat/components/ContextoSelector', () => {
  beforeEach(() => {
    contextosRef.value = []
    selectedIdRef.value = null
    loadedRef.value = true
    selectMock.mockReset()
  })

  it('exibe link para /admin quando há 0 contextos carregados', () => {
    const wrapper = mount(ContextoSelector, {
      props: { isNewConversation: true },
      global: { stubs: { RouterLink: { template: '<a :href="to"><slot /></a>', props: ['to'] } } },
    })

    const link = wrapper.get('a[href="/admin"]')
    expect(link.text()).toContain('Carregar dados no Admin')
    expect(wrapper.find('select').exists()).toBe(false)
  })

  it('exibe badge limpo sem <select> e sem texto de base semanal quando há 1 contexto', () => {
    contextosRef.value = [
      { id: 'c1', slug: 'pesquisa-extensao-ifes', name: 'Pesquisa e Extensão IFES', description: '', views: [] },
    ]
    const wrapper = mount(ContextoSelector, {
      props: { isNewConversation: true },
      global: { stubs: { RouterLink: true } },
    })

    expect(wrapper.find('select').exists()).toBe(false)
    expect(wrapper.text()).toContain('Pesquisa e Extensão IFES')
    expect(wrapper.text()).not.toContain('Base semanal')
    expect(wrapper.text()).not.toContain('22/11/2026')
  })

  it('exibe <label> e <select> associados quando há múltiplos contextos', async () => {
    contextosRef.value = [
      { id: 'c1', slug: 'ctx-1', name: 'Contexto A', description: '', views: [] },
      { id: 'c2', slug: 'ctx-2', name: 'Contexto B', description: '', views: [] },
    ]
    selectedIdRef.value = 'c1'

    const wrapper = mount(ContextoSelector, {
      props: { isNewConversation: true },
      global: { stubs: { RouterLink: true } },
    })

    expect(wrapper.find('label[for="chat-contexto-select"]').exists()).toBe(true)
    const select = wrapper.get('#chat-contexto-select')
    expect(select.attributes('aria-label')).toBe('Contexto de dados')
    await select.setValue('c2')
    expect(selectMock).toHaveBeenCalledWith('c2')
  })
})
