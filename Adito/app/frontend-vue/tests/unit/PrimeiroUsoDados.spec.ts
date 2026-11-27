import { describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'

const instalarDadosMock = vi.fn().mockResolvedValue(true)

vi.mock('@/common/composables/useAtualizacoes', () => ({
  useAtualizacoes: () => ({
    instalandoDados: ref(false),
    erro: ref(null),
    instalarDados: (...args: unknown[]) => instalarDadosMock(...args),
  }),
}))

import PrimeiroUsoDados from '@/common/components/feedback/PrimeiroUsoDados.vue'

describe('common/components/feedback/PrimeiroUsoDados', () => {
  it('exibe label explícito, contador 0/64 -> 64/64 com destaque verde em hex válido e alterna visibilidade', async () => {
    const wrapper = mount(PrimeiroUsoDados)

    const label = wrapper.get('label[for="primeiro-uso-chave"]')
    expect(label.text()).toContain('Chave dos dados')

    const input = wrapper.get<HTMLInputElement>('#primeiro-uso-chave')
    expect(input.attributes('type')).toBe('password')

    const counter = wrapper.get('[data-testid="chave-counter"]')
    expect(counter.text()).toBe('0/64 caracteres')
    expect(counter.classes().join(' ')).not.toContain('text-emerald')

    const validHex = 'a1b2c3d4'.repeat(8)
    await input.setValue(validHex)
    expect(counter.text()).toBe('64/64 caracteres')
    expect(counter.classes().join(' ')).toContain('text-emerald')

    const toggleBtn = wrapper.get('button[aria-label="Mostrar valor da chave"]')
    await toggleBtn.trigger('click')
    expect(input.attributes('type')).toBe('text')

    wrapper.unmount()
  })
})
