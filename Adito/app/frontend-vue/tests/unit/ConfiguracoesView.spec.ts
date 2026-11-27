import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import { DEFAULT_LLM_PROVIDERS, type LlmConfigStatus } from '@/common/api/llmKey'

const listProvidersMock = vi.fn()
const llmConfigStatusMock = vi.fn()
const testAndSaveConfigMock = vi.fn()
const clearKeyMock = vi.fn()
const loadLocalUserMock = vi.fn()
const userRef = ref<Record<string, unknown> | null>({
  username: 'local',
  llm_configured: false,
  llm_provider: 'gemini',
  llm_provider_label: 'Gemini',
  llm_model: 'gemini-3.5-flash-lite',
})

vi.mock('@/common/api/llmKey', async () => {
  const actual = await vi.importActual<typeof import('@/common/api/llmKey')>('@/common/api/llmKey')
  return {
    ...actual,
    listProviders: (...args: unknown[]) => listProvidersMock(...args),
    llmConfigStatus: (...args: unknown[]) => llmConfigStatusMock(...args),
    testAndSaveConfig: (...args: unknown[]) => testAndSaveConfigMock(...args),
    clearKey: (...args: unknown[]) => clearKeyMock(...args),
  }
})

vi.mock('@/modules/auth/composables/useAuth', () => ({
  useAuth: () => ({
    user: userRef,
    loadLocalUser: loadLocalUserMock,
  }),
}))

const verificarAtualizacoesMock = vi.fn()
const baseStatusRef = ref<{ instalado: boolean; versao: string | null; desenvolvimento: boolean; chave_configurada: boolean } | null>({
  instalado: true,
  versao: '2026-11-20',
  desenvolvimento: false,
  chave_configurada: true,
})
const appUpdateRef = ref<{ version: string } | null>(null)
const erroVerificacaoRef = ref<string | null>(null)

vi.mock('@/common/composables/useAtualizacoes', async () => {
  const actual = await vi.importActual<typeof import('@/common/composables/useAtualizacoes')>(
    '@/common/composables/useAtualizacoes',
  )
  return {
    ...actual,
    useAtualizacoes: () => {
      const real = actual.useAtualizacoes()
      return {
        ...real,
        status: baseStatusRef,
        app: appUpdateRef,
        dadosNovos: ref(null),
        verificando: ref(false),
        erroVerificacao: erroVerificacaoRef,
        verificar: (...args: unknown[]) => verificarAtualizacoesMock(...args),
      }
    },
  }
})

import ConfiguracoesView from '@/modules/settings/views/ConfiguracoesView.vue'
import { _resetAtualizacoes, AUTO_UPDATE_STORAGE_KEY } from '@/common/composables/useAtualizacoes'

function makeStatus(overrides: Partial<LlmConfigStatus> = {}): LlmConfigStatus {
  return {
    provider: 'gemini',
    model: 'gemini-3.5-flash-lite',
    base_url: null,
    configured: false,
    store_available: true,
    has_key_by_provider: {
      gemini: false,
      openai: false,
      openrouter: false,
      mistral: false,
      zai: false,
      together: false,
      fireworks: false,
      ollama: false,
    },
    error: null,
    ...overrides,
  }
}

async function selectProviderOption(wrapper: VueWrapper, label: string) {
  await wrapper.get('#llm-provider').trigger('click')
  const option = wrapper.findAll('[role="option"]').find((el) => el.text().includes(label))
  expect(option, `opção ${label} deveria existir no dropdown`).toBeDefined()
  await option!.trigger('mousedown')
}

describe('ConfiguracoesView.vue', () => {
  beforeEach(() => {
    _resetAtualizacoes()
    listProvidersMock.mockReset().mockResolvedValue(DEFAULT_LLM_PROVIDERS)
    llmConfigStatusMock.mockReset().mockResolvedValue(makeStatus())
    testAndSaveConfigMock.mockReset()
    clearKeyMock.mockReset().mockResolvedValue(undefined)
    loadLocalUserMock.mockReset().mockResolvedValue(userRef.value)
    verificarAtualizacoesMock.mockReset().mockResolvedValue(undefined)
    baseStatusRef.value = {
      instalado: true,
      versao: '2026-11-20',
      desenvolvimento: false,
      chave_configurada: true,
    }
    appUpdateRef.value = null
    erroVerificacaoRef.value = null
  })

  it('troca de provedor no dropdown customizado preenche modelo padrão e atualiza texto de privacidade para Mistral AI', async () => {
    const wrapper = mount(ConfiguracoesView)
    await flushPromises()

    await selectProviderOption(wrapper, 'Mistral AI')

    const modelInput = wrapper.get<HTMLInputElement>('#llm-model')
    expect(modelInput.element.value).toBe('ministral-8b-latest')
    expect(wrapper.text()).toContain('envia para Mistral AI')
    expect(wrapper.text()).not.toContain('funciona em modo só-chat')
  })

  it('permite abrir Opções avançadas (Base URL) em provedores com URL customizável como Z.AI', async () => {
    const wrapper = mount(ConfiguracoesView)
    await flushPromises()

    await selectProviderOption(wrapper, 'Z.AI (GLM)')
    expect(wrapper.find('#llm-base-url').exists()).toBe(false)
    const advBtn = wrapper.findAll('button').find((b) => b.text().includes('Opções avançadas'))
    expect(advBtn).toBeDefined()
    await advBtn!.trigger('click')
    expect(wrapper.find('#llm-base-url').exists()).toBe(true)
  })

  it('permite salvar Ollama local sem chave e exibe privacidade 100% local', async () => {
    testAndSaveConfigMock.mockResolvedValueOnce({ ok: true })
    llmConfigStatusMock
      .mockResolvedValueOnce(makeStatus())
      .mockResolvedValueOnce(makeStatus({ provider: 'ollama', model: 'qwen2.5:7b', configured: true }))

    const wrapper = mount(ConfiguracoesView)
    await flushPromises()

    await selectProviderOption(wrapper, 'Ollama (Local)')
    expect(wrapper.text()).toContain('100% local — nenhum dado sai do seu computador')

    const submit = wrapper.get<HTMLButtonElement>('button[type="submit"]')
    expect(submit.element.disabled).toBe(false)

    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(testAndSaveConfigMock).toHaveBeenCalledWith({
      provider: 'ollama',
      model: 'qwen2.5:7b',
      baseUrl: undefined,
      key: undefined,
      useSavedKey: false,
    })
    expect(wrapper.text()).toContain('provedor local (Ollama (Local)) ativado')
  })

  it('reutiliza chave já salva no cofre sem exigir redigitação e remove apenas o provedor selecionado', async () => {
    llmConfigStatusMock
      .mockResolvedValueOnce(
        makeStatus({
          provider: 'openai',
          model: 'gpt-4o-mini',
          configured: true,
          has_key_by_provider: { gemini: true, openai: true },
        })
      )
      .mockResolvedValue(
        makeStatus({
          provider: 'gemini',
          model: 'gemini-3.5-flash-lite',
          configured: true,
          has_key_by_provider: { gemini: true, openai: true },
        })
      )
    testAndSaveConfigMock.mockResolvedValueOnce({ ok: true })

    const wrapper = mount(ConfiguracoesView)
    await flushPromises()

    await selectProviderOption(wrapper, 'Gemini')
    expect(wrapper.text()).toContain('Já existe uma chave salva no cofre para Gemini')

    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(testAndSaveConfigMock).toHaveBeenCalledWith({
      provider: 'gemini',
      model: 'gemini-3.5-flash-lite',
      baseUrl: undefined,
      key: undefined,
      useSavedKey: true,
    })

    const removeBtn = wrapper.findAll('button').find((b) => b.text().includes('Remover'))
    expect(removeBtn).toBeDefined()
    await removeBtn!.trigger('click')
    await flushPromises()
    // Exige confirmação via ConfirmModal (teleportado para body) antes de remover a chave
    expect(clearKeyMock).not.toHaveBeenCalled()
    const confirmBtn = Array.from(document.body.querySelectorAll('button')).find(
      (b) => b.textContent?.trim() === 'Remover chave',
    )
    expect(confirmBtn).toBeDefined()
    confirmBtn!.click()
    await flushPromises()
    expect(clearKeyMock).toHaveBeenCalledWith('gemini')
    wrapper.unmount()
  })

  it('alterna visibilidade da chave API e verifica atualizações da base local sob demanda', async () => {
    const wrapper = mount(ConfiguracoesView)
    await flushPromises()

    const keyInput = wrapper.get<HTMLInputElement>('#llm-api-key')
    expect(keyInput.attributes('type')).toBe('password')

    const toggleBtn = wrapper.get('button[aria-label="Mostrar valor da chave"]')
    await toggleBtn.trigger('click')
    expect(keyInput.attributes('type')).toBe('text')

    expect(wrapper.text()).toContain('Base de dados local')
    expect(wrapper.text()).toContain('20/11/2026')
    const checkBtn = wrapper.findAll('button').find((b) => b.text().includes('Verificar atualizações agora'))
    expect(checkBtn).toBeDefined()
    await checkBtn!.trigger('click')
    await flushPromises()
    expect(verificarAtualizacoesMock).toHaveBeenCalledWith({ forcar: true })
  })

  it('exibe erro amigável quando a validação falha', async () => {
    testAndSaveConfigMock.mockResolvedValueOnce({ ok: false, reason: 'Chave inválida para OpenAI.' })

    const wrapper = mount(ConfiguracoesView)
    await flushPromises()

    await selectProviderOption(wrapper, 'OpenAI')
    await wrapper.get('#llm-api-key').setValue('sk-errada')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(wrapper.text()).toContain('Chave inválida para OpenAI.')
  })

  it('exibe indicador "Em uso" apenas para o provedor realmente ativo no núcleo enquanto outros exibem "Chave salva"', async () => {
    userRef.value = {
      username: 'local',
      llm_configured: true,
      llm_provider: 'mistral',
      llm_provider_label: 'Mistral AI',
      llm_model: 'ministral-8b-latest',
    }
    llmConfigStatusMock.mockResolvedValue(
      makeStatus({
        provider: 'mistral',
        model: 'ministral-8b-latest',
        configured: true,
        has_key_by_provider: { gemini: true, mistral: true },
      })
    )

    const wrapper = mount(ConfiguracoesView)
    await flushPromises()

    expect(wrapper.text()).toContain('Em uso')
    expect(wrapper.text()).toContain('Mistral AI')
    expect(wrapper.text()).toContain('ministral-8b-latest')

    await wrapper.get('#llm-provider').trigger('click')
    const options = wrapper.findAll('[role="option"]')
    const mistralOpt = options.find((el) => el.text().includes('Mistral AI'))!
    const geminiOpt = options.find((el) => el.text().includes('Gemini'))!
    expect(mistralOpt.text()).toContain('Em uso')
    expect(geminiOpt.text()).not.toContain('Em uso')
    expect(geminiOpt.text()).toContain('Chave salva')
  })

  it('exibe toggle de atualização automática desligado por padrão e persiste preferência em localStorage', async () => {
    const wrapper = mount(ConfiguracoesView)
    await flushPromises()

    expect(wrapper.text()).toContain('Atualização automática (app e dados)')
    const toggle = wrapper.get<HTMLInputElement>('#auto-update-toggle')
    expect(toggle.element.checked).toBe(false)
    expect(toggle.attributes('role')).toBe('switch')
    expect(toggle.attributes('aria-checked')).toBe('false')

    await toggle.setValue(true)
    expect(toggle.element.checked).toBe(true)
    expect(toggle.attributes('aria-checked')).toBe('true')
    expect(localStorage.getItem(AUTO_UPDATE_STORAGE_KEY)).toBe('true')

    await toggle.setValue(false)
    expect(toggle.element.checked).toBe(false)
    expect(localStorage.getItem(AUTO_UPDATE_STORAGE_KEY)).toBe('false')
  })

  it('diferencia erro de rede, modo dev e atualização de aplicativo ao verificar atualizações manualmente', async () => {
    const wrapper = mount(ConfiguracoesView)
    await flushPromises()
    const checkBtn = () => wrapper.findAll('button').find((b) => b.text().includes('Verificar atualizações agora'))!

    // Caso 1: offline / erro de rede — não deve afirmar que está atualizado
    erroVerificacaoRef.value = 'sem rede'
    await checkBtn().trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Não foi possível verificar atualizações agora')
    expect(wrapper.text()).not.toContain('já estão na versão mais recente')

    // Caso 2: nova versão apenas do aplicativo
    erroVerificacaoRef.value = null
    appUpdateRef.value = { version: '0.2.0' }
    await checkBtn().trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Nova versão do aplicativo disponível (0.2.0)')

    // Caso 3: modo desenvolvimento
    appUpdateRef.value = null
    baseStatusRef.value = { instalado: true, versao: null, desenvolvimento: true, chave_configurada: false }
    await checkBtn().trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Modo desenvolvimento')
  })
})
