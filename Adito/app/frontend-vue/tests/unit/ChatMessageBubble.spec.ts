import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatMessageBubble from '@/modules/chat/components/ChatMessageBubble.vue'
import type { ChatMessage } from '@/modules/chat/types'

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

    const wrapper = mount(ChatMessageBubble, {
      props: { message },
      global: { stubs: { VueApexCharts: true } },
    })

    const ths = wrapper.findAll('thead th')
    expect(ths[0].classes()).toContain('text-left')
    expect(ths[1].classes()).toContain('text-right')
    expect(ths[2].classes()).toContain('text-right')

    const firstRowTds = wrapper.findAll('tbody tr')[0].findAll('td')
    expect(firstRowTds[0].classes()).toContain('text-left')
    expect(firstRowTds[1].classes()).toContain('text-right')
    expect(firstRowTds[2].classes()).toContain('text-right')
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

    const traceWrapper = mount(ChatMessageBubble, {
      props: { message: withTrace },
      global: { stubs: { VueApexCharts: true } },
    })
    expect(traceWrapper.find('[data-testid="adito-reasoning-trace"]').exists()).toBe(true)
    expect(traceWrapper.find('.chat-loading-container').exists()).toBe(false)

    const withoutTrace: ChatMessage = {
      id: 'm-legacy-load',
      type: 'ai',
      text: '',
      timestamp: '2026-11-25T14:00:00Z',
      isLoading: true,
      loadingStatus: 'Consultando base...',
    }
    const legacyWrapper = mount(ChatMessageBubble, {
      props: { message: withoutTrace },
      global: { stubs: { VueApexCharts: true } },
    })
    expect(legacyWrapper.find('.chat-loading-container').exists()).toBe(true)
    expect(legacyWrapper.text()).toContain('Consultando base...')
  })
})
