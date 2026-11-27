import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import ChatMessageBubble from '@/modules/chat/components/ChatMessageBubble.vue'
import type { ChatMessage } from '@/modules/chat/types'

const mountBubble = (message: ChatMessage) =>
  mount(ChatMessageBubble, {
    props: { message },
    attachTo: document.body,
    global: {
      stubs: {
        VueApexCharts: { template: '<div data-testid="apex-stub" />' },
      },
    },
  })

const findExportMenu = () => document.body.querySelector<HTMLElement>('[data-testid="chat-export-menu"]')

function makeTableRows(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    grande_area: `Área ${i + 1}`,
    total: (i + 1) * 10,
  }))
}

describe('modules/chat/components/ChatMessageBubble', () => {
  it('alinha <th> e <td> à direita em coluna numérica mesmo quando a linha 0 está vazia/nula', () => {
    const message: ChatMessage = {
      id: 'm-align',
      type: 'ai',
      text: 'Tabela com célula nula na primeira linha.',
      timestamp: '2026-11-25T14:00:00Z',
      table: [
        { area: 'Engenharias', total: null, investimento: '' },
        { area: 'Exatas', total: 42, investimento: 1500.5 },
      ],
    }

    const wrapper = mountBubble(message)

    const ths = wrapper.findAll('thead th')
    expect(ths[0].classes()).toContain('text-left')
    expect(ths[1].classes()).toContain('text-right')
    expect(ths[2].classes()).toContain('text-right')

    const firstRowTds = wrapper.findAll('tbody tr')[0].findAll('td')
    expect(firstRowTds[0].classes()).toContain('text-left')
    expect(firstRowTds[1].classes()).toContain('text-right')
    expect(firstRowTds[2].classes()).toContain('text-right')
    wrapper.unmount()
  })

  it('renderiza AditoReasoningTrace sem exibir card vazio enquanto carrega e usa fallback loading sem trace', () => {
    const withTrace: ChatMessage = {
      id: 'm-trace-load',
      type: 'ai',
      text: '',
      timestamp: '2026-11-25T14:00:00Z',
      isLoading: true,
      trace: {
        steps: [
          {
            id: 'routing',
            title: 'Orquestrador',
            subtitle: 'Analisando...',
            status: 'running',
            headerStatus: 'Analisando contexto...',
            details: [],
          },
        ],
      },
    }

    const traceWrapper = mountBubble(withTrace)
    expect(traceWrapper.find('[data-testid="adito-reasoning-trace"]').exists()).toBe(true)
    expect(traceWrapper.find('.chat-loading-container').exists()).toBe(false)
    traceWrapper.unmount()

    const withoutTrace: ChatMessage = {
      id: 'm-legacy-load',
      type: 'ai',
      text: '',
      timestamp: '2026-11-25T14:00:00Z',
      isLoading: true,
      loadingStatus: 'Consultando base...',
    }
    const legacyWrapper = mountBubble(withoutTrace)
    expect(legacyWrapper.find('.chat-loading-container').exists()).toBe(true)
    expect(legacyWrapper.text()).toContain('Consultando base...')
    legacyWrapper.unmount()
  })
})

describe('ChatMessageBubble.vue — exportação CSV e Excel', () => {
  it('oculta botão Exportar em mensagens puramente textuais ou resultados escalares', () => {
    const textOnly = mountBubble({
      id: 'm-text',
      type: 'ai',
      text: 'Olá! Como posso ajudar?',
      timestamp: '2026-11-26T14:00:00Z',
    })
    expect(textOnly.find('[data-testid="chat-export-btn"]').exists()).toBe(false)
    textOnly.unmount()

    const scalar = mountBubble({
      id: 'm-scalar',
      type: 'ai',
      text: 'Existem 236 projetos.',
      timestamp: '2026-11-26T14:00:00Z',
      sql: 'SELECT COUNT(*) AS total FROM vfact_projeto_pesquisa_resolved',
      table: [{ total: 236 }],
      isScalarResult: true,
    })
    expect(scalar.find('[data-testid="chat-export-btn"]').exists()).toBe(false)
    scalar.unmount()
  })

  it('exibe botão Exportar em respostas com tabela/gráfico e emite todos os registros (ignorando rowLimit=10)', async () => {
    const rows = makeTableRows(20)
    const wrapper = mountBubble({
      id: 'm-table',
      type: 'ai',
      text: 'Projetos por área.',
      timestamp: '2026-11-26T14:00:00Z',
      sql: 'SELECT grande_area, COUNT(*) AS total FROM vfact_projeto_pesquisa_resolved GROUP BY grande_area',
      table: rows,
    })

    // Na tela, padrão exibe 10 de 20
    expect(wrapper.text()).toContain('Mostrando 10 de 20 registros')

    const exportBtn = wrapper.get('[data-testid="chat-export-btn"]')
    expect(exportBtn.attributes('aria-haspopup')).toBe('menu')
    expect(exportBtn.attributes('aria-expanded')).toBe('false')

    await exportBtn.trigger('click')
    expect(exportBtn.attributes('aria-expanded')).toBe('true')
    const menu = findExportMenu()
    expect(menu).not.toBeNull()
    expect(menu!.getAttribute('role')).toBe('menu')

    menu!.querySelector<HTMLButtonElement>('button[role="menuitem"]:first-child')!.click()
    await wrapper.vm.$nextTick()
    expect(findExportMenu()).toBeNull()

    const emittedCsv = wrapper.emitted('export')
    expect(emittedCsv).toHaveLength(1)
    expect(emittedCsv![0][0]).toMatchObject({ format: 'csv' })
    expect((emittedCsv![0][0] as { message: ChatMessage }).message.table).toHaveLength(20)

    await exportBtn.trigger('click')
    findExportMenu()!.querySelector<HTMLButtonElement>('button[role="menuitem"]:last-child')!.click()
    await wrapper.vm.$nextTick()
    const emittedAll = wrapper.emitted('export')
    expect(emittedAll).toHaveLength(2)
    expect(emittedAll![1][0]).toMatchObject({ format: 'xlsx' })
    expect((emittedAll![1][0] as { message: ChatMessage }).message.table).toHaveLength(20)

    wrapper.unmount()
  })

  it('fecha menu Exportar com Esc bloqueando propagação para o listener global do chat', async () => {
    const wrapper = mountBubble({
      id: 'm-esc',
      type: 'ai',
      text: 'Tabela.',
      timestamp: '2026-11-26T14:00:00Z',
      sql: 'SELECT 1',
      table: makeTableRows(3),
    })

    const windowEscSpy = vi.fn()
    window.addEventListener('keydown', windowEscSpy)
    try {
      await wrapper.get('[data-testid="chat-export-btn"]').trigger('click')
      expect(findExportMenu()).not.toBeNull()

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }))
      await wrapper.vm.$nextTick()

      expect(findExportMenu()).toBeNull()
      expect(windowEscSpy).not.toHaveBeenCalled()
    } finally {
      window.removeEventListener('keydown', windowEscSpy)
      wrapper.unmount()
    }
  })

  it('fecha menu Exportar ao clicar fora', async () => {
    const wrapper = mountBubble({
      id: 'm-outside',
      type: 'ai',
      text: 'Tabela.',
      timestamp: '2026-11-26T14:00:00Z',
      sql: 'SELECT 1',
      table: makeTableRows(3),
    })

    await wrapper.get('[data-testid="chat-export-btn"]').trigger('click')
    expect(findExportMenu()).not.toBeNull()

    document.body.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
    await wrapper.vm.$nextTick()
    expect(findExportMenu()).toBeNull()

    wrapper.unmount()
  })
})
