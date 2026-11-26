import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatReportForm from '@/modules/chat/components/ChatReportForm.vue'

const options = [
  { id: 'a', question: 'Projetos por área', chartType: 'bar' },
  { id: 'b', question: 'Projetos por ano', chartType: 'line' },
]

describe('modules/chat/components/ChatReportForm', () => {
  it('usa o tipo de gráfico atual ao gerar, sem perder marcação, títulos e ordem editados (FR08)', async () => {
    const wrapper = mount(ChatReportForm, { props: { options, defaultTitle: 'Panorama' } })

    // Edita: renomeia a seção "a", desce ela para depois de "b" e desmarca "b"
    await wrapper.find('input[aria-label="Título da seção 1"]').setValue('Por grande área')
    await wrapper.find('button[aria-label="Descer a seção 1"]').trigger('click')
    await wrapper.find('input[aria-label="Incluir a seção: Projetos por ano"]').setValue(false)

    // Com o formulário aberto, o usuário troca o gráfico da resposta "a" na conversa
    await wrapper.setProps({ options: [{ ...options[0], chartType: 'pie' }, options[1]] })

    await wrapper.findAll('button').find(button => button.text().includes('Gerar relatório'))!.trigger('click')
    expect(wrapper.emitted('generate')?.[0]?.[0]).toEqual({
      title: 'Panorama',
      sections: [{ message_id: 'a', title: 'Por grande área', chart_type: 'pie' }],
    })
  })

  it('inclui no fim uma resposta nova que aparece com o formulário aberto', async () => {
    const wrapper = mount(ChatReportForm, { props: { options: [options[0]], defaultTitle: 'Panorama' } })
    await wrapper.setProps({ options })
    expect(wrapper.text()).toContain('2 de 2')
  })
})
