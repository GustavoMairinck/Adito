import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatResultTable from '@/modules/chat/components/ChatResultTable.vue'

describe('modules/chat/components/ChatResultTable', () => {
  it('monta as linhas pelas colunas do cabeçalho, mesmo com chaves fora de ordem ou ausentes', () => {
    const wrapper = mount(ChatResultTable, {
      props: { rows: [{ area: 'Engenharias', total: 120 }, { total: 80, area: 'Humanas' }, { area: 'Biológicas' }] },
    })
    const cells = wrapper.findAll('tbody tr').map(tr => tr.findAll('td').map(td => td.text()))
    expect(cells).toEqual([['Engenharias', '120'], ['Humanas', '80'], ['Biológicas', 'nulo']])
  })

  it('alinha à direita só quantidades: ano, texto e data ficam à esquerda; primeira linha nula não engana', () => {
    const wrapper = mount(ChatResultTable, {
      props: {
        rows: [
          { ano: 2024, codigo: '0042', inicio: '2024-03-01', total: null },
          { ano: 2023, codigo: '0043', inicio: '2023-03-01', total: 45 },
        ],
        fieldFormats: { codigo: 'text', inicio: 'date' },
      },
    })
    const align = wrapper.findAll('th').map(th => (th.classes().includes('text-right') ? 'right' : 'left'))
    expect(align).toEqual(['left', 'left', 'left', 'right'])
    const firstRow = wrapper.find('tbody tr').findAll('td').map(td => (td.classes().includes('text-right') ? 'right' : 'left'))
    expect(firstRow).toEqual(align)
  })
})
