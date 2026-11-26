import { afterEach, describe, expect, it } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import ChatReportPrint from '@/modules/chat/components/ChatReportPrint.vue'
import type { ChatReport } from '@/modules/chat/types'
import { sectionView } from '@/modules/chat/utils/report'

const report: ChatReport = {
  title: 'Panorama de projetos',
  contextoNome: 'Pesquisa e Extensão IFES',
  generatedAt: '2026-11-25T17:30:00Z',
  loaded: true,
  sections: [
    { sourceMessageId: 'a1', title: 'Projetos por área', sql: 'SELECT 1', fieldFormats: {}, chartType: 'bar',
      data: [{ area: 'Engenharias', total: 120 }, { area: 'Humanas', total: 45 }] },
    { sourceMessageId: 'a2', title: 'Quantos projetos?', sql: 'SELECT 2', fieldFormats: {}, chartType: null,
      data: [{ total_projetos: 236 }] },
    { sourceMessageId: 'a3', title: 'Seção quebrada', sql: 'SELECT 3', fieldFormats: {}, chartType: null,
      data: [], error: 'falha' },
    { sourceMessageId: 'a4', title: 'Projetos por ano', sql: 'SELECT 4', fieldFormats: {}, chartType: 'line',
      data: [{ ano: 2023, total: 60 }, { ano: 2024, total: 52 }] },
  ],
}

let wrapper: VueWrapper | null = null
afterEach(() => { wrapper?.unmount(); wrapper = null })

describe('modules/chat/components/ChatReportPrint', () => {
  it('monta a página de impressão com abertura, Tabela/Figura/Quadro numerados, fonte e apêndice com o SQL', () => {
    wrapper = mount(ChatReportPrint, {
      props: {
        messageId: 'abc-123',
        report,
        views: report.sections.map(section => sectionView(section, true)),
        dataVersion: '2026-11-01',
        appVersion: '0.2.0',
      },
      global: { stubs: { ChatResultChart: { template: '<div class="chart-stub" />' } } },
      attachTo: document.body,
    })
    const root = document.querySelector('.report-print-root')!
    const text = (selector: string) => [...root.querySelectorAll(selector)].map(el => el.textContent!.replace(/\s+/g, ' ').trim())

    expect(text('.rp-header')).toEqual(['Adito'])
    expect(root.textContent).not.toContain('Gerado pelo Adito')
    expect(text('.rp-cover-title')).toEqual(['Panorama de projetos'])
    expect(root.querySelector('.rp-info')!.textContent).toContain('Pesquisa e Extensão IFES, versão 2026-11-01')
    expect(root.querySelector('.rp-info')!.textContent).toContain('0.2.0')
    expect(text('.rp-toc li')).toEqual(['1Projetos por área', '2Quantos projetos?', '3Seção quebrada', '4Projetos por ano', 'AConsultas utilizadas'])
    expect(text('.rp-h2')).toEqual(['1 Projetos por área', '2 Quantos projetos?', '3 Seção quebrada', '4 Projetos por ano', 'Apêndice A – Consultas utilizadas'])
    // Numeração própria de tabelas, figuras e quadros; seção quebrada não consome número
    expect(text('.rp-caption')).toEqual([
      'Tabela 1 – Projetos por área',
      'Figura 1 – Projetos por área',
      'Quadro 1 – Quantos projetos?',
      'Tabela 2 – Projetos por ano',
      'Figura 2 – Projetos por ano',
    ])
    expect(text('.rp-note-warn')).toHaveLength(1)
    expect(text('.rp-source')[0]).toBe('Fonte: Adito, Pesquisa e Extensão IFES, versão 2026-11-01.')
    expect(text('.rp-sql pre')).toEqual(['SELECT 1', 'SELECT 2', 'SELECT 3', 'SELECT 4'])
    expect(root.querySelector('.rp-method-note')!.textContent).toContain('sem uso de IA')
  })
})
