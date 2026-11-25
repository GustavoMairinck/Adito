import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, ref } from 'vue'

const api = {
  dadosStatus: vi.fn(),
  dadosVerificar: vi.fn(),
  dadosInstalar: vi.fn(),
  appVerificar: vi.fn(),
  appInstalar: vi.fn(),
  appBaixar: vi.fn(),
  appAplicarEReiniciar: vi.fn(),
}

const chatLoadingRef = ref(false)

vi.mock('@/common/api/atualizacoes', () => ({
  dadosStatus: (...a: unknown[]) => api.dadosStatus(...a),
  dadosVerificar: (...a: unknown[]) => api.dadosVerificar(...a),
  dadosInstalar: (...a: unknown[]) => api.dadosInstalar(...a),
  appVerificar: (...a: unknown[]) => api.appVerificar(...a),
  appInstalar: (...a: unknown[]) => api.appInstalar(...a),
  appBaixar: (...a: unknown[]) => api.appBaixar(...a),
  appAplicarEReiniciar: (...a: unknown[]) => api.appAplicarEReiniciar(...a),
}))

vi.mock('@/modules/chat/composables/useChatApi', () => ({
  useChatApi: () => ({
    isLoading: chatLoadingRef,
  }),
}))

import {
  _resetAtualizacoes,
  AUTO_UPDATE_STORAGE_KEY,
  COOLDOWN_FOCO_MS,
  INTERVALO_VERIFICACAO_MS,
  useAtualizacoes,
} from '@/common/composables/useAtualizacoes'

const instalado = { instalado: true, versao: '2026-11-01', desenvolvimento: false, chave_configurada: true }
const remotoNovo = { versao: '2026-11-22', tamanho: 8_000_000, atualizacao: true, precisa_chave: false }

describe('useAtualizacoes', () => {
  beforeEach(() => {
    vi.useRealTimers()
    chatLoadingRef.value = false
    _resetAtualizacoes()
    Object.values(api).forEach((m) => m.mockReset())
    api.appVerificar.mockResolvedValue(null)
    api.appBaixar.mockResolvedValue(true)
    api.appAplicarEReiniciar.mockResolvedValue(undefined)
  })

  afterEach(() => {
    _resetAtualizacoes()
    vi.useRealTimers()
  })

  it('sem nada novo não mostra o aviso', async () => {
    api.dadosStatus.mockResolvedValue(instalado)
    api.dadosVerificar.mockResolvedValue({ ...remotoNovo, versao: '2026-11-01', atualizacao: false })
    const a = useAtualizacoes()
    await a.verificar()
    expect(a.temAtualizacao.value).toBe(false)
    expect(a.precisaPrimeiraCarga.value).toBe(false)
  })

  it('dados novos publicados acendem o aviso', async () => {
    api.dadosStatus.mockResolvedValue(instalado)
    api.dadosVerificar.mockResolvedValue(remotoNovo)
    const a = useAtualizacoes()
    await a.verificar()
    expect(a.dadosNovos.value?.versao).toBe('2026-11-22')
    expect(a.temAtualizacao.value).toBe(true)
  })

  it('versão nova do app acende o aviso', async () => {
    api.dadosStatus.mockResolvedValue(instalado)
    api.dadosVerificar.mockRejectedValue('sem rede')
    api.appVerificar.mockResolvedValue({ version: '0.2.0', downloadAndInstall: vi.fn() })
    const a = useAtualizacoes()
    await a.verificar()
    expect(a.app.value?.version).toBe('0.2.0')
    expect(a.dadosNovos.value).toBeNull()
    expect(a.temAtualizacao.value).toBe(true)
  })

  it('sem internet fica quieto', async () => {
    api.dadosStatus.mockResolvedValue(instalado)
    api.dadosVerificar.mockRejectedValue('sem rede')
    api.appVerificar.mockRejectedValue('sem rede')
    const a = useAtualizacoes()
    await a.verificar()
    expect(a.temAtualizacao.value).toBe(false)
    expect(a.erro.value).toBeNull()
  })

  it('confere uma vez só por sessão', async () => {
    api.dadosStatus.mockResolvedValue(instalado)
    api.dadosVerificar.mockResolvedValue(remotoNovo)
    const a = useAtualizacoes()
    await Promise.all([a.verificar(), a.verificar()])
    await a.verificar()
    expect(api.dadosVerificar).toHaveBeenCalledTimes(1)
  })

  it('sem dados instalados pede a primeira carga', async () => {
    api.dadosStatus.mockResolvedValue({ instalado: false, versao: null, desenvolvimento: false, chave_configurada: false })
    api.dadosVerificar.mockResolvedValue({ ...remotoNovo, precisa_chave: true })
    const a = useAtualizacoes()
    await a.verificar()
    expect(a.precisaPrimeiraCarga.value).toBe(true)
    // O aviso do canto é para quem já tem dados.
    expect(a.dadosNovos.value).toBeNull()
  })

  it('fora do app (status desconhecido) não pede nada', async () => {
    api.dadosStatus.mockResolvedValue(null)
    api.dadosVerificar.mockResolvedValue(null)
    const a = useAtualizacoes()
    await a.verificar()
    expect(a.precisaPrimeiraCarga.value).toBe(false)
    expect(a.temAtualizacao.value).toBe(false)
  })

  it('em desenvolvimento não oferece trocar o dados.db do repositório nem atualizar o executável', async () => {
    api.dadosStatus.mockResolvedValue({ ...instalado, versao: null, desenvolvimento: true })
    api.dadosVerificar.mockResolvedValue(remotoNovo)
    api.appVerificar.mockResolvedValue({ version: '0.1.1', downloadAndInstall: vi.fn() })
    const a = useAtualizacoes()
    await a.verificar()
    expect(a.dadosNovos.value).toBeNull()
    expect(a.app.value).toBeNull()
    expect(api.appVerificar).not.toHaveBeenCalled()
    expect(a.temAtualizacao.value).toBe(false)
  })

  it('instalar os dados some com o aviso e atualiza a versão', async () => {
    api.dadosStatus.mockResolvedValueOnce(instalado).mockResolvedValueOnce({ ...instalado, versao: '2026-11-22' })
    api.dadosVerificar.mockResolvedValue(remotoNovo)
    api.dadosInstalar.mockResolvedValue('2026-11-22')
    const a = useAtualizacoes()
    await a.verificar()
    expect(await a.instalarDados()).toBe(true)
    expect(api.dadosInstalar).toHaveBeenCalledWith(undefined)
    expect(a.status.value?.versao).toBe('2026-11-22')
    expect(a.temAtualizacao.value).toBe(false)
  })

  it('primeiro uso com chave errada mostra o erro e continua pedindo', async () => {
    api.dadosStatus.mockResolvedValue({ instalado: false, versao: null, desenvolvimento: false, chave_configurada: false })
    api.dadosVerificar.mockResolvedValue({ ...remotoNovo, precisa_chave: true })
    api.dadosInstalar.mockRejectedValue('Essa chave não abre esta versão dos dados.')
    const a = useAtualizacoes()
    await a.verificar()
    expect(await a.instalarDados('chave-errada')).toBe(false)
    expect(a.erro.value).toContain('não abre')
    expect(a.precisaPrimeiraCarga.value).toBe(true)
    expect(a.instalandoDados.value).toBe(false)
  })

  it('falha ao atualizar o app vira mensagem', async () => {
    api.dadosStatus.mockResolvedValue(instalado)
    api.dadosVerificar.mockResolvedValue(null)
    api.appVerificar.mockResolvedValue({ version: '0.2.0', downloadAndInstall: vi.fn() })
    api.appInstalar.mockRejectedValue(new Error('assinatura inválida'))
    const a = useAtualizacoes()
    await a.verificar()
    await a.instalarApp()
    expect(a.erro.value).toContain('assinatura inválida')
    expect(a.instalandoApp.value).toBe(false)
  })

  it('preferência opt-in inicia desligada por padrão e persiste em localStorage', () => {
    const a = useAtualizacoes()
    expect(a.autoAtualizar.value).toBe(false)

    a.setAutoAtualizar(true)
    expect(a.autoAtualizar.value).toBe(true)
    expect(localStorage.getItem(AUTO_UPDATE_STORAGE_KEY)).toBe('true')

    _resetAtualizacoes({ preservarPreferencia: true })
    expect(a.autoAtualizar.value).toBe(true)

    a.setAutoAtualizar(false)
    expect(localStorage.getItem(AUTO_UPDATE_STORAGE_KEY)).toBe('false')
  })

  it('monitoramento verifica ao abrir, respeita cooldown de 15 min no foco e repete a cada 30 min', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-11-25T10:00:00Z'))
    api.dadosStatus.mockResolvedValue(instalado)
    api.dadosVerificar.mockResolvedValue({ ...remotoNovo, versao: '2026-11-01', atualizacao: false })

    const a = useAtualizacoes()
    a.iniciarMonitoramento()
    await vi.advanceTimersByTimeAsync(0)
    expect(api.dadosVerificar).toHaveBeenCalledTimes(1)

    // Foco antes de 15 min: respeita cooldown.
    await vi.advanceTimersByTimeAsync(5 * 60 * 1000)
    window.dispatchEvent(new Event('focus'))
    await vi.advanceTimersByTimeAsync(0)
    expect(api.dadosVerificar).toHaveBeenCalledTimes(1)

    // Foco após 15 min: verifica novamente.
    await vi.advanceTimersByTimeAsync(COOLDOWN_FOCO_MS)
    window.dispatchEvent(new Event('focus'))
    await vi.advanceTimersByTimeAsync(0)
    expect(api.dadosVerificar).toHaveBeenCalledTimes(2)

    // Ciclo periódico de 30 min: verifica novamente.
    await vi.advanceTimersByTimeAsync(INTERVALO_VERIFICACAO_MS)
    expect(api.dadosVerificar).toHaveBeenCalledTimes(3)

    a.pararMonitoramento()
    await vi.advanceTimersByTimeAsync(INTERVALO_VERIFICACAO_MS)
    expect(api.dadosVerificar).toHaveBeenCalledTimes(3)
  })

  it('no modo opt-in baixa o executável em segundo plano, aguarda chat livre, pausa se chat reiniciar e aplica após 10s', async () => {
    vi.useFakeTimers()
    const update = {
      version: '0.2.0',
      download: vi.fn().mockResolvedValue(undefined),
      install: vi.fn().mockResolvedValue(undefined),
      downloadAndInstall: vi.fn().mockResolvedValue(undefined),
    }
    api.dadosStatus.mockResolvedValue(instalado)
    api.dadosVerificar.mockResolvedValue({ ...remotoNovo, atualizacao: false })
    api.appVerificar.mockResolvedValue(update)

    const a = useAtualizacoes()
    chatLoadingRef.value = true
    a.setAutoAtualizar(true)

    await a.verificar()
    await vi.advanceTimersByTimeAsync(0)

    expect(api.appBaixar).toHaveBeenCalledTimes(1)
    expect(a.appProntoParaReinicio.value).toBe(true)
    // Chat ocupado: não inicia contagem nem reinicia.
    expect(a.segundosParaReinicio.value).toBeNull()
    expect(api.appAplicarEReiniciar).not.toHaveBeenCalled()

    // Chat fica livre: inicia contagem de 10s.
    chatLoadingRef.value = false
    await nextTick()
    await vi.advanceTimersByTimeAsync(0)
    expect(a.segundosParaReinicio.value).toBe(10)

    await vi.advanceTimersByTimeAsync(3000)
    expect(a.segundosParaReinicio.value).toBe(7)

    // Novo prompt no chat durante a contagem: pausa imediatamente.
    chatLoadingRef.value = true
    await nextTick()
    expect(a.segundosParaReinicio.value).toBeNull()
    await vi.advanceTimersByTimeAsync(15_000)
    expect(api.appAplicarEReiniciar).not.toHaveBeenCalled()

    // Chat volta a ficar livre: retoma contagem e reinicia ao zerar.
    chatLoadingRef.value = false
    await nextTick()
    await vi.advanceTimersByTimeAsync(0)
    expect(a.segundosParaReinicio.value).toBe(10)

    await vi.advanceTimersByTimeAsync(10_000)
    expect(api.appAplicarEReiniciar).toHaveBeenCalledTimes(1)
    expect(api.appAplicarEReiniciar).toHaveBeenCalledWith(update, true, expect.any(Function))
  })

  it('adiar silencia a contagem daquela versão na sessão sem bloquear clique manual', async () => {
    vi.useFakeTimers()
    const update = {
      version: '0.2.0',
      download: vi.fn().mockResolvedValue(undefined),
      install: vi.fn().mockResolvedValue(undefined),
      downloadAndInstall: vi.fn().mockResolvedValue(undefined),
    }
    api.dadosStatus.mockResolvedValue(instalado)
    api.dadosVerificar.mockResolvedValue(null)
    api.appVerificar.mockResolvedValue(update)

    const a = useAtualizacoes()
    a.setAutoAtualizar(true)
    await a.verificar()
    await vi.advanceTimersByTimeAsync(0)
    expect(a.segundosParaReinicio.value).toBe(10)

    a.adiarReinicio()
    expect(a.segundosParaReinicio.value).toBeNull()
    expect(a.versaoAdiada.value).toBe('0.2.0')

    // Nova verificação com mesma versão não reabre contagem.
    await a.verificarNovamente({ forcar: true })
    await vi.advanceTimersByTimeAsync(0)
    expect(a.segundosParaReinicio.value).toBeNull()

    // Clique manual no painel lateral continua funcionando usando pacote já baixado.
    await a.instalarApp()
    expect(api.appAplicarEReiniciar).toHaveBeenCalledTimes(1)
  })

  it('prioriza o executável quando há atualização de app e dados.db simultaneamente', async () => {
    vi.useFakeTimers()
    const update = {
      version: '0.2.0',
      download: vi.fn().mockResolvedValue(undefined),
      install: vi.fn().mockResolvedValue(undefined),
      downloadAndInstall: vi.fn().mockResolvedValue(undefined),
    }
    api.dadosStatus.mockResolvedValue(instalado)
    api.dadosVerificar.mockResolvedValue(remotoNovo)
    api.appVerificar.mockResolvedValue(update)

    const a = useAtualizacoes()
    a.setAutoAtualizar(true)
    await a.verificar()
    await vi.advanceTimersByTimeAsync(0)

    expect(api.appBaixar).toHaveBeenCalledTimes(1)
    expect(api.dadosInstalar).not.toHaveBeenCalled()
    expect(a.segundosParaReinicio.value).toBe(10)
  })

  it('no modo opt-in atualiza dados.db automaticamente quando chat fica livre, incrementa dadosReloadSeq e exibe toast', async () => {
    api.dadosStatus.mockResolvedValueOnce(instalado).mockResolvedValueOnce({ ...instalado, versao: '2026-11-22' })
    api.dadosVerificar.mockResolvedValue(remotoNovo)
    api.dadosInstalar.mockResolvedValue('2026-11-22')

    const a = useAtualizacoes()
    chatLoadingRef.value = true
    a.setAutoAtualizar(true)

    await a.verificar()
    expect(api.dadosInstalar).not.toHaveBeenCalled()
    expect(a.dadosReloadSeq.value).toBe(0)

    chatLoadingRef.value = false
    await nextTick()
    await Promise.resolve()
    await Promise.resolve()

    expect(api.dadosInstalar).toHaveBeenCalledTimes(1)
    expect(a.dadosReloadSeq.value).toBe(1)
    expect(a.ultimaVersaoDadosAtualizada.value).toBe('2026-11-22')
    expect(a.toastDadosAtualizados.value).toContain('2026-11-22')
  })

  it('não tenta instalar dados.db automaticamente quando precisa_chave é true', async () => {
    api.dadosStatus.mockResolvedValue(instalado)
    api.dadosVerificar.mockResolvedValue({ ...remotoNovo, precisa_chave: true })

    const a = useAtualizacoes()
    a.setAutoAtualizar(true)
    await a.verificar()

    expect(api.dadosInstalar).not.toHaveBeenCalled()
    expect(a.dadosNovos.value?.precisa_chave).toBe(true)
    expect(a.erro.value).toBeNull()
  })

  it('aplica backoff de 30 min após falha no download automático sem bloquear clique manual', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-11-25T10:00:00Z'))
    const update = {
      version: '0.2.0',
      download: vi.fn(),
      install: vi.fn(),
      downloadAndInstall: vi.fn(),
    }
    api.dadosStatus.mockResolvedValue(instalado)
    api.dadosVerificar.mockResolvedValue(null)
    api.appVerificar.mockResolvedValue(update)
    api.appBaixar.mockRejectedValueOnce(new Error('falha de rede'))

    const a = useAtualizacoes()
    a.setAutoAtualizar(true)
    await a.verificar()
    await vi.advanceTimersByTimeAsync(0)
    expect(api.appBaixar).toHaveBeenCalledTimes(1)

    // Nova verificação antes de 30 min não entra em loop de erro.
    await vi.advanceTimersByTimeAsync(16 * 60 * 1000)
    await a.verificarNovamente({ forcar: true })
    await vi.advanceTimersByTimeAsync(0)
    expect(api.appBaixar).toHaveBeenCalledTimes(1)

    // Clique manual continua funcionando.
    api.appInstalar.mockResolvedValueOnce(undefined)
    await a.instalarApp()
    expect(api.appInstalar).toHaveBeenCalledTimes(1)
  })

  it('preserva instância já baixada em nova verificação da mesma versão ou offline e fecha recurso duplicado', async () => {
    vi.useFakeTimers()
    const update1 = {
      version: '0.2.0',
      download: vi.fn().mockResolvedValue(undefined),
      install: vi.fn().mockResolvedValue(undefined),
      downloadAndInstall: vi.fn().mockResolvedValue(undefined),
      close: vi.fn().mockResolvedValue(undefined),
    }
    const update2 = {
      version: '0.2.0',
      download: vi.fn().mockResolvedValue(undefined),
      install: vi.fn().mockResolvedValue(undefined),
      downloadAndInstall: vi.fn().mockResolvedValue(undefined),
      close: vi.fn().mockResolvedValue(undefined),
    }
    api.dadosStatus.mockResolvedValue(instalado)
    api.dadosVerificar.mockResolvedValue(null)
    api.appVerificar.mockResolvedValueOnce(update1)

    const a = useAtualizacoes()
    a.setAutoAtualizar(true)
    await a.verificar()
    await vi.advanceTimersByTimeAsync(0)
    a.adiarReinicio()

    // Nova verificação devolve nova instância da mesma versão 0.2.0: mantém update1 e fecha update2.
    api.appVerificar.mockResolvedValueOnce(update2)
    await a.verificarNovamente({ forcar: true })
    await vi.advanceTimersByTimeAsync(0)
    expect(a.app.value).toBe(update1)
    expect(a.appProntoParaReinicio.value).toBe(true)
    expect(update2.close).toHaveBeenCalledTimes(1)
    expect(update1.close).not.toHaveBeenCalled()

    // Queda transitória de rede não descarta o update1 já baixado.
    api.appVerificar.mockRejectedValueOnce(new Error('offline'))
    await a.verificarNovamente({ forcar: true })
    await vi.advanceTimersByTimeAsync(0)
    expect(a.app.value).toBe(update1)
    expect(a.appProntoParaReinicio.value).toBe(true)

    // Clique manual usa update1 (com bytes já baixados).
    await a.instalarApp()
    expect(api.appAplicarEReiniciar).toHaveBeenCalledWith(update1, true, expect.any(Function))
  })

  it('versão mais nova volta a notificar após adiamento da versão anterior (BR05)', async () => {
    vi.useFakeTimers()
    const update020 = {
      version: '0.2.0',
      download: vi.fn().mockResolvedValue(undefined),
      install: vi.fn().mockResolvedValue(undefined),
      downloadAndInstall: vi.fn().mockResolvedValue(undefined),
      close: vi.fn().mockResolvedValue(undefined),
    }
    const update030 = {
      version: '0.3.0',
      download: vi.fn().mockResolvedValue(undefined),
      install: vi.fn().mockResolvedValue(undefined),
      downloadAndInstall: vi.fn().mockResolvedValue(undefined),
      close: vi.fn().mockResolvedValue(undefined),
    }
    api.dadosStatus.mockResolvedValue(instalado)
    api.dadosVerificar.mockResolvedValue(null)
    api.appVerificar.mockResolvedValueOnce(update020)

    const a = useAtualizacoes()
    a.setAutoAtualizar(true)
    await a.verificar()
    await vi.advanceTimersByTimeAsync(0)
    a.adiarReinicio()
    expect(a.segundosParaReinicio.value).toBeNull()

    api.appVerificar.mockResolvedValueOnce(update030)
    await a.verificarNovamente({ forcar: true })
    await vi.advanceTimersByTimeAsync(0)

    expect(update020.close).toHaveBeenCalledTimes(1)
    expect(a.app.value).toBe(update030)
    expect(a.appProntoParaReinicio.value).toBe(true)
    expect(a.segundosParaReinicio.value).toBe(10)
  })

  it('fallback sem download/install separados só dispara appInstalar após chat livre e contagem de 10s (A01)', async () => {
    vi.useFakeTimers()
    const updateLegado = {
      version: '0.2.0',
      downloadAndInstall: vi.fn().mockResolvedValue(undefined),
    }
    api.dadosStatus.mockResolvedValue(instalado)
    api.dadosVerificar.mockResolvedValue(null)
    api.appVerificar.mockResolvedValue(updateLegado)
    api.appInstalar.mockResolvedValue(undefined)

    const a = useAtualizacoes()
    chatLoadingRef.value = true
    a.setAutoAtualizar(true)
    await a.verificar()
    await vi.advanceTimersByTimeAsync(0)

    expect(api.appBaixar).not.toHaveBeenCalled()
    expect(api.appInstalar).not.toHaveBeenCalled()
    expect(a.segundosParaReinicio.value).toBeNull()

    chatLoadingRef.value = false
    await nextTick()
    await vi.advanceTimersByTimeAsync(0)
    expect(a.segundosParaReinicio.value).toBe(10)
    expect(api.appInstalar).not.toHaveBeenCalled()

    await vi.advanceTimersByTimeAsync(10_000)
    expect(api.appInstalar).toHaveBeenCalledTimes(1)
    expect(api.appInstalar).toHaveBeenCalledWith(updateLegado, expect.any(Function))
  })
})
