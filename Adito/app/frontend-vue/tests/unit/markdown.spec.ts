import { describe, expect, it } from 'vitest'
import { renderMarkdown } from '@/modules/chat/utils/markdown'

describe('modules/chat/utils/markdown', () => {
  it('escapa HTML malicioso para prevenir XSS', () => {
    const html = renderMarkdown('<script>alert("xss")</script>')
    expect(html).toBe('<p>&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;</p>')
    expect(html).not.toContain('<script>')
  })

  it('renderiza headings, separadores e formatação inline', () => {
    const md = [
      '# Panorama IFES',
      '## Resumo',
      '---',
      'Existem **236 projetos** com *bolsas* na view `vfact_projeto_pesquisa_resolved`.',
    ].join('\n')

    const html = renderMarkdown(md)
    expect(html).toContain('<h1>Panorama IFES</h1>')
    expect(html).toContain('<h2>Resumo</h2>')
    expect(html).toContain('<hr>')
    expect(html).toContain(
      '<p>Existem <strong>236 projetos</strong> com <em>bolsas</em> na view <code>vfact_projeto_pesquisa_resolved</code>.</p>',
    )
  })

  it('agrupa listas não ordenadas e ordenadas e fecha tags corretamente', () => {
    const md = [
      '- SRC',
      '- SigPesq',
      '1. Primeiro',
      '2. Segundo',
      'Parágrafo final',
    ].join('\n')

    const html = renderMarkdown(md)
    expect(html).toBe(
      '<ul><li>SRC</li><li>SigPesq</li></ul><ol><li>Primeiro</li><li>Segundo</li></ol><p>Parágrafo final</p>',
    )
  })
})
