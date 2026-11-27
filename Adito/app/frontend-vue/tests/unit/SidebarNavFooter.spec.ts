import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'

const apiMock = {
  dadosStatus: vi.fn(),
  dadosVerificar: vi.fn(),
  dadosInstalar: vi.fn(),
  appVerificar: vi.fn(),
  appInstalar: vi.fn(),
}

vi.mock('@/common/api/atualizacoes', () => ({
  dadosStatus: (...args: unknown[]) => apiMock.dadosStatus(...args),
  dadosVerificar: (...args: unknown[]) => apiMock.dadosVerificar(...args),
  dadosInstalar: (...args: unknown[]) => apiMock.dadosInstalar(...args),
  appVerificar: (...args: unknown[]) => apiMock.appVerificar(...args),
  appInstalar: (...args: unknown[]) => apiMock.appInstalar(...args),
}))

vi.mock('vue-router', () => ({
  useRoute: () => ({ path: '/chat' }),
  useRouter: () => ({ push: vi.fn() }),
  RouterLink: {
    props: ['to'],
    template: '<a :href="to"><slot /></a>',
  },
}))

vi.mock('@/modules/auth/composables/useAuth', () => ({
  useAuth: () => ({ user: ref({ role: 'user' }) }),
}))

vi.mock('@/modules/chat/composables/useChatApi', () => ({
  useChatApi: () => ({ activeConversationIds: ref([]) }),
}))

vi.mock('@/modules/chat/composables/useChatHistory', () => ({
  useChatHistory: () => ({
    conversations: ref([]),
    currentConvId: ref(null),
    setCurrentConvId: vi.fn(),
    handleNewConversation: vi.fn(),
    handleDeleteConversation: vi.fn(),
    handleRenameConversation: vi.fn(),
    handleTogglePinConversation: vi.fn(),
  }),
}))

import SidebarNav from '@/common/components/navigation/SidebarNav.vue'
import { _resetAtualizacoes, useAtualizacoes } from '@/common/composables/useAtualizacoes'

describe('SidebarNav — rodapé e funcionalidades vinculadas', () => {
  beforeEach(() => {
    _resetAtualizacoes()
    Object.values(apiMock).forEach((fn) => fn.mockReset())
    apiMock.appVerificar.mockResolvedValue(null)
    document.documentElement.classList.remove('dark')
    localStorage.clear()
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockReturnValue({
        matches: false,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }),
    })
  })

  it('exibe botão de tema e assinatura Powered by LEDS & SmartIdea no rodapé', () => {
    const wrapper = mount(SidebarNav, { attachTo: document.body })

    expect(wrapper.find('[data-testid="atualizacao-disponivel"]').exists()).toBe(false)
    const themeBtn = wrapper.get('[data-testid="theme-toggle-btn"]')
    expect(themeBtn.text()).toContain('Modo Escuro')
    expect(wrapper.text()).toContain('Powered by LEDS & SmartIdea')
    wrapper.unmount()
  })

  it('alterna tema escuro/claro corretamente e sincroniza com a classe dark no html', async () => {
    const wrapper = mount(SidebarNav, { attachTo: document.body })
    const themeBtn = wrapper.get('[data-testid="theme-toggle-btn"]')

    await themeBtn.trigger('click')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('theme')).toBe('dark')
    expect(themeBtn.text()).toContain('Modo Claro')

    await themeBtn.trigger('click')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(localStorage.getItem('theme')).toBe('light')
    expect(themeBtn.text()).toContain('Modo Escuro')

    // Simula inicialização externa de tema (como App.vue onMounted)
    document.documentElement.classList.add('dark')
    await flushPromises()
    expect(themeBtn.text()).toContain('Modo Claro')

    wrapper.unmount()
  })

  it('exibe Atualização disponível quando há atualização, abre o painel e fecha com Escape', async () => {
    apiMock.dadosStatus.mockResolvedValue({
      instalado: true,
      versao: '2026-11-01',
      desenvolvimento: false,
      chave_configurada: true,
    })
    apiMock.dadosVerificar.mockResolvedValue({
      versao: '2026-11-26',
      tamanho: 4_500_000,
      atualizacao: true,
      precisa_chave: false,
    })

    await useAtualizacoes().verificar()
    const wrapper = mount(SidebarNav, { attachTo: document.body })
    await flushPromises()

    const updateBtn = wrapper.get('[data-testid="atualizacao-disponivel"] button')
    expect(updateBtn.text()).toContain('Atualização disponível')

    await updateBtn.trigger('click')
    await flushPromises()

    const dialog = document.body.querySelector('[role="dialog"][aria-label="Atualizações do Adito"]')
    expect(dialog).not.toBeNull()
    expect(dialog?.textContent).toContain('Dados novos')
    expect(dialog?.textContent).toContain('2026-11-26')

    const bubbleEscSpy = vi.fn()
    window.addEventListener('keydown', bubbleEscSpy)
    try {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }))
      await flushPromises()
      expect(document.body.querySelector('[role="dialog"][aria-label="Atualizações do Adito"]')).toBeNull()
      // O modal captura o Esc antes do listener global do chat para não abortar geração em andamento
      expect(bubbleEscSpy).not.toHaveBeenCalled()
    } finally {
      window.removeEventListener('keydown', bubbleEscSpy)
    }

    wrapper.unmount()
  })

  it('mantém ações independentes sem bloqueio cruzado quando há atualização do app e dos dados simultaneamente', async () => {
    apiMock.dadosStatus.mockResolvedValue({
      instalado: true,
      versao: '2026-11-01',
      desenvolvimento: false,
      chave_configurada: true,
    })
    apiMock.dadosVerificar.mockResolvedValue({
      versao: '2026-11-26',
      tamanho: 4_500_000,
      atualizacao: true,
      precisa_chave: true,
    })
    apiMock.appVerificar.mockResolvedValue({
      version: '0.2.0',
      downloadAndInstall: vi.fn(),
    })

    await useAtualizacoes().verificar()
    const wrapper = mount(SidebarNav, { attachTo: document.body })
    await flushPromises()

    await wrapper.get('[data-testid="atualizacao-disponivel"] button').trigger('click')
    await flushPromises()

    const dialog = document.body.querySelector('[role="dialog"][aria-label="Atualizações do Adito"]')!
    const buttons = Array.from(dialog.querySelectorAll('button'))
    const appBtn = buttons.find((b) => b.textContent?.includes('Atualizar o app'))
    const dataBtn = buttons.find((b) => b.textContent?.includes('Atualizar os dados'))
    expect(appBtn).toBeDefined()
    expect(dataBtn).toBeDefined()
    // Mesmo sem informar a nova chave dos dados, atualizar o app continua liberado
    expect(appBtn!.disabled).toBe(false)
    expect(dataBtn!.disabled).toBe(true)

    wrapper.unmount()
  })

  it('fechar busca da sidebar com Escape impede propagação para o listener do chat', async () => {
    const wrapper = mount(SidebarNav, { attachTo: document.body })
    await wrapper.get('button[aria-label="Buscar conversas"]').trigger('click')
    expect(wrapper.find('input[aria-label="Filtrar conversas"]').exists()).toBe(true)

    const bubbleEscSpy = vi.fn()
    window.addEventListener('keydown', bubbleEscSpy)
    try {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }))
      await flushPromises()
      expect(wrapper.find('input[aria-label="Filtrar conversas"]').exists()).toBe(false)
      expect(bubbleEscSpy).not.toHaveBeenCalled()
    } finally {
      window.removeEventListener('keydown', bubbleEscSpy)
      wrapper.unmount()
    }
  })
})
