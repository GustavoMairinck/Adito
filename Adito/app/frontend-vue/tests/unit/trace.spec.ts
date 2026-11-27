import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AditoReasoningTrace from '@/modules/chat/components/AditoReasoningTrace.vue'
import {
  applyTraceEvent,
  createInitialTrace,
  formatTraceDuration,
  formatTraceTime,
  normalizeTrace,
} from '@/modules/chat/utils/trace'

describe('modules/chat/utils/trace e AditoReasoningTrace', () => {
  it('createInitialTrace e applyTraceEvent atualizam etapas, detalhes, código SQL e status', () => {
    let trace = createInitialTrace('2026-11-25T14:00:00Z')
    expect(trace.steps).toHaveLength(1)
    expect(trace.steps[0].id).toBe('routing')
    expect(trace.steps[0].title).toBe('Orquestrador')

    trace = applyTraceEvent(trace, {
      event: 'step_detail',
      data: { step_id: 'routing', detail: 'Consultando projetos' },
    })
    trace = applyTraceEvent(trace, { event: 'step_complete', data: { step_id: 'routing' } })
    trace = applyTraceEvent(trace, {
      event: 'step_start',
      data: { step_id: 'query', title: 'Agente de dados', header_status: 'Consultando base...' },
    })
    trace = applyTraceEvent(trace, {
      event: 'step_code',
      data: { step_id: 'query', language: 'sql', code: 'SELECT COUNT(*) FROM vfact_projeto_pesquisa_resolved' },
    })
    trace = applyTraceEvent(trace, {
      event: 'step_complete',
      data: { step_id: 'query', detail: '1 registro encontrado.' },
    })

    expect(trace.steps).toHaveLength(2)
    expect(trace.steps[0].status).toBe('done')
    expect(trace.steps[1].code).toContain('SELECT COUNT(*)')
    expect(trace.steps[1].details).toContain('1 registro encontrado.')
  })

  it('normalizeTrace, formatTraceDuration e formatTraceTime formatam corretamente', () => {
    const normalized = normalizeTrace({
      duration_ms: 1460,
      compact: true,
      steps: [{ id: 'routing', title: 'Orquestrador', status: 'done', details: ['Ok'] }],
    })
    expect(normalized?.durationMs).toBe(1460)
    expect(normalized?.compact).toBe(true)
    expect(normalizeTrace(null)).toBeNull()

    expect(formatTraceDuration(350)).toBe('0,4s')
    expect(formatTraceDuration(1460)).toBe('1,5s')
    expect(formatTraceDuration(2000)).toBe('2s')
    expect(formatTraceDuration(65000)).toBe('1m 5s')
    expect(formatTraceTime('2026-11-25T14:35:00Z')).toMatch(/^\d{2}:\d{2}$/)
  })

  it('AditoReasoningTrace abre durante streaming, recolhe ao concluir e permite abrir manualmente', async () => {
    const trace = createInitialTrace()
    const wrapper = mount(AditoReasoningTrace, {
      props: { trace, isLoading: true, hasFinalContent: false },
    })

    const headerBtn = wrapper.get('button[aria-expanded]')
    expect(headerBtn.attributes('aria-expanded')).toBe('true')
    expect(wrapper.text()).toContain('Analisando contexto...')

    const doneTrace = applyTraceEvent(trace, { event: 'step_complete', data: { step_id: 'routing' } })
    await wrapper.setProps({ trace: { ...doneTrace, durationMs: 1200 }, isLoading: false, hasFinalContent: true })

    expect(headerBtn.attributes('aria-expanded')).toBe('false')
    expect(wrapper.text()).toContain('Etapas da consulta')

    await headerBtn.trigger('click')
    expect(headerBtn.attributes('aria-expanded')).toBe('true')
  })

  it('exibe rótulo compacto e estado de alerta em erro', () => {
    const compactWrapper = mount(AditoReasoningTrace, {
      props: {
        trace: {
          compact: true,
          steps: [{ id: 'routing', title: 'Orquestrador', status: 'done', details: [] }],
        },
        isLoading: false,
        hasFinalContent: true,
      },
    })
    expect(compactWrapper.text()).toContain('Processo de análise')

    const errorWrapper = mount(AditoReasoningTrace, {
      props: {
        trace: {
          compact: false,
          steps: [{ id: 'query', title: 'Agente de dados', status: 'error', details: ['Falha SQL'] }],
        },
        isLoading: false,
        hasFinalContent: false,
      },
    })
    expect(errorWrapper.text()).toContain('Etapas com alerta')
    expect(errorWrapper.get('button[aria-expanded]').attributes('aria-expanded')).toBe('true')
  })
})
