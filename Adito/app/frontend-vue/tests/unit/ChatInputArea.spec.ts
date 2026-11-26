import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatInputArea from '@/modules/chat/components/ChatInputArea.vue'

describe('modules/chat/components/ChatInputArea', () => {
  it('exibe botão Enviar quando não está carregando e emite send', async () => {
    const wrapper = mount(ChatInputArea, {
      props: { modelValue: 'Quantos projetos?', loading: false },
    })

    const sendBtn = wrapper.find('#btn-send-chat')
    expect(sendBtn.exists()).toBe(true)
    expect(wrapper.find('#btn-stop-chat').exists()).toBe(false)

    await sendBtn.trigger('click')
    expect(wrapper.emitted('send')).toHaveLength(1)
  })

  it('substitui Enviar por botão Parar durante loading e emite cancel ao clicar ou pressionar Esc sem perder texto', async () => {
    const wrapper = mount(ChatInputArea, {
      props: { modelValue: 'Próxima pergunta já digitada', loading: true },
    })

    const stopBtn = wrapper.find('#btn-stop-chat')
    expect(stopBtn.exists()).toBe(true)
    expect(stopBtn.attributes('aria-label')).toBe('Parar geração')
    expect(wrapper.find('#btn-send-chat').exists()).toBe(false)

    await stopBtn.trigger('click')
    expect(wrapper.emitted('cancel')).toHaveLength(1)

    const textarea = wrapper.find('textarea')
    expect((textarea.element as HTMLTextAreaElement).value).toBe('Próxima pergunta já digitada')
    await textarea.trigger('keydown', { key: 'Escape' })
    expect(wrapper.emitted('cancel')).toHaveLength(2)
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()

    // Enter durante loading não dispara novo send
    await textarea.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('send')).toBeUndefined()
  })

  it('não dispara cancel nem preventDefault no Esc quando disableEscape está ativo (modal aberto)', async () => {
    const wrapper = mount(ChatInputArea, {
      props: { modelValue: '', loading: true, disableEscape: true },
    })

    await wrapper.find('textarea').trigger('keydown', { key: 'Escape' })
    expect(wrapper.emitted('cancel')).toBeUndefined()
  })

  it('menu "Mais" fecha com Esc de qualquer lugar e quando deixa de haver resposta para relatório', async () => {
    const wrapper = mount(ChatInputArea, {
      props: { modelValue: '', loading: false, canCreateReport: true },
      attachTo: document.body,
    })
    const more = wrapper.find('button[aria-label="Mais opções"]')

    await more.trigger('click')
    expect(wrapper.find('[role="menu"]').exists()).toBe(true)
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('[role="menu"]').exists()).toBe(false)

    await more.trigger('click')
    await wrapper.setProps({ canCreateReport: false })
    expect(wrapper.find('[role="menu"]').exists()).toBe(false)
    wrapper.unmount()
  })
})
