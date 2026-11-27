import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'

const callMock = vi.fn()
const userRef = ref<Record<string, unknown>>({
  username: 'local',
  role: 'admin',
  llm_configured: true,
  llm_provider: 'gemini',
  llm_provider_label: 'Gemini',
  llm_model: 'gemini-3.5-flash-lite',
})

vi.mock('@/common/api/core', () => ({
  call: (...args: unknown[]) => callMock(...args),
}))

vi.mock('@/modules/auth/composables/useAuth', () => ({
  useAuth: () => ({
    user: userRef,
    loadLocalUser: vi.fn(),
  }),
}))

import AdminView from '@/modules/admin/views/AdminView.vue'
import { _resetAtualizacoes, useAtualizacoes } from '@/common/composables/useAtualizacoes'

function mockAdminCalls(embeddings: Record<string, unknown>) {
  callMock.mockImplementation(async (method: string) => {
    if (method === 'admin.trainings.list') return []
    if (method === 'admin.contextos') return []
    if (method === 'admin.system_status') {
      return {
        services: [],
        systemStats: {
          version: '0.1.0',
          uptime: '0h 1m',
          vectorRows: 4,
          trainedDdl: 1,
          trainedDoc: 1,
          trainedExamples: 2,
          lastTraining: '2026-11-24T12:00:00Z',
        },
        embeddings,
      }
    }
    return []
  })
}

const BUSCA_OK = {
  modelo: 'minilm-l12-int8',
  modelo_pronto: true,
  modelo_erro: null,
  valores_disponiveis: true,
  valores: 1200,
  motivo: null,
}

describe('AdminView.vue — aviso da busca semântica local na Base de conhecimento', () => {
  beforeEach(() => {
    _resetAtualizacoes()
    callMock.mockReset()
  })

  it('avisa quando o dados.db não traz vetores do modelo do app, sem travar os botões', async () => {
    mockAdminCalls({
      ...BUSCA_OK,
      valores_disponiveis: false,
      valores: 0,
      motivo: 'Os vetores do dados.db são de outro modelo (e5-large-int8).',
    })

    const wrapper = mount(AdminView, { global: { directives: { motion: {} } } })
    await flushPromises()

    expect(wrapper.text()).toContain('Busca semântica de valores desligada')
    expect(wrapper.text()).toContain('outro modelo (e5-large-int8)')
    const novoBtn = wrapper.findAll('button').find((b) => b.text().includes('Novo Treinamento'))
    const wipeBtn = wrapper.findAll('button').find((b) => b.text().includes('Wipe & Retrain'))
    expect((novoBtn!.element as HTMLButtonElement).disabled).toBe(false)
    expect((wipeBtn!.element as HTMLButtonElement).disabled).toBe(false)
  })

  it('não mostra aviso quando o modelo e os vetores estão prontos', async () => {
    mockAdminCalls(BUSCA_OK)

    const wrapper = mount(AdminView, { global: { directives: { motion: {} } } })
    await flushPromises()

    expect(wrapper.text()).not.toContain('Busca semântica de valores desligada')
    expect(wrapper.text()).not.toContain('Modelo de embedding local indisponível')
  })

  it('recarrega status e contextos quando dadosReloadSeq incrementa sem disparar retrain automático', async () => {
    mockAdminCalls(BUSCA_OK)

    const wrapper = mount(AdminView, { global: { directives: { motion: {} } } })
    await flushPromises()
    callMock.mockClear()

    const { dadosReloadSeq } = useAtualizacoes()
    dadosReloadSeq.value += 1
    await flushPromises()

    const metodos = callMock.mock.calls.map((c) => c[0])
    expect(metodos).toContain('admin.contextos')
    expect(metodos).toContain('admin.system_status')
    expect(metodos).toContain('admin.trainings.list')
    expect(metodos).not.toContain('admin.trainings.retrain')
    expect(metodos).not.toContain('admin.bootstrap')
    wrapper.unmount()
  })
})
