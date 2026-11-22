import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = {
  dadosStatus: vi.fn(),
  dadosVerificar: vi.fn(),
  dadosInstalar: vi.fn(),
  appVerificar: vi.fn(),
  appInstalar: vi.fn(),
}

vi.mock('@/common/api/atualizacoes', () => ({
  dadosStatus: (...a: unknown[]) => api.dadosStatus(...a),
  dadosVerificar: (...a: unknown[]) => api.dadosVerificar(...a),
  dadosInstalar: (...a: unknown[]) => api.dadosInstalar(...a),
  appVerificar: (...a: unknown[]) => api.appVerificar(...a),
  appInstalar: (...a: unknown[]) => api.appInstalar(...a),
}))

import { _resetAtualizacoes, useAtualizacoes } from '@/common/composables/useAtualizacoes'

const instalado = { instalado: true, versao: '2026-11-01', desenvolvimento: false, chave_configurada: true }
const remotoNovo = { versao: '2026-11-22', tamanho: 8_000_000, atualizacao: true, precisa_chave: false }

describe('useAtualizacoes', () => {
  beforeEach(() => {
    _resetAtualizacoes()
    Object.values(api).forEach((m) => m.mockReset())
    api.appVerificar.mockResolvedValue(null)
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

  it('em desenvolvimento não oferece trocar o dados.db do repositório', async () => {
    api.dadosStatus.mockResolvedValue({ ...instalado, versao: null, desenvolvimento: true })
    api.dadosVerificar.mockResolvedValue(remotoNovo)
    const a = useAtualizacoes()
    await a.verificar()
    expect(a.dadosNovos.value).toBeNull()
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
})
