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
  llm_supports_embeddings: true,
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

describe('AdminView.vue — banners de embeddings na Base de conhecimento', () => {
  beforeEach(() => {
    callMock.mockReset()
  })

  it('exibe banner informativo e desabilita Novo Treinamento e Wipe & Retrain quando provedor não suporta embeddings', async () => {
    mockAdminCalls({
      supports_embeddings: false,
      provider: 'groq',
      provider_label: 'Groq',
      embedding_model: null,
      expected_dim: null,
      stored_dims: [],
      needs_retrain: false,
      incompatible_vectors: 0,
    })

    const wrapper = mount(AdminView, { global: { directives: { motion: {} } } })
    await flushPromises()

    expect(wrapper.text()).toContain('Provedor ativo (Groq) não gera embeddings')
    expect(wrapper.text()).toContain('modo fallback textual')

    const novoBtn = wrapper.findAll('button').find((b) => b.text().includes('Novo Treinamento'))
    const wipeBtn = wrapper.findAll('button').find((b) => b.text().includes('Wipe & Retrain'))
    expect((novoBtn!.element as HTMLButtonElement).disabled).toBe(true)
    expect((wipeBtn!.element as HTMLButtonElement).disabled).toBe(true)
  })

  it('exibe banner de reindexação recomendada quando há vetores com dimensão divergente', async () => {
    mockAdminCalls({
      supports_embeddings: true,
      provider: 'openai',
      provider_label: 'OpenAI',
      embedding_model: 'text-embedding-3-small',
      expected_dim: 1536,
      stored_dims: [1024],
      needs_retrain: true,
      incompatible_vectors: 18,
    })

    const wrapper = mount(AdminView, { global: { directives: { motion: {} } } })
    await flushPromises()

    expect(wrapper.text()).toContain('Reindexação recomendada (Wipe & Retrain)')
    expect(wrapper.text()).toContain('18 vetor(es)')
    const wipeBtn = wrapper.findAll('button').find((b) => b.text().includes('Wipe & Retrain'))
    expect((wipeBtn!.element as HTMLButtonElement).disabled).toBe(false)
  })

  it('oculta ambos os banners quando provedor suporta embeddings e base está consistente', async () => {
    mockAdminCalls({
      supports_embeddings: true,
      provider: 'gemini',
      provider_label: 'Gemini',
      embedding_model: 'gemini-embedding-2',
      expected_dim: 1024,
      stored_dims: [1024],
      needs_retrain: false,
      incompatible_vectors: 0,
    })

    const wrapper = mount(AdminView, { global: { directives: { motion: {} } } })
    await flushPromises()

    expect(wrapper.text()).not.toContain('não gera embeddings')
    expect(wrapper.text()).not.toContain('Reindexação recomendada')
  })
})
