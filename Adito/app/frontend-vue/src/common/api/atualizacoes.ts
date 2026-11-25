import { coreReady } from './core'

/**
 * Distribuição do Adito (ADR-0006/0007), tudo pelo GitHub Releases, sem servidor nem conta:
 *
 * - app: o `tauri-plugin-updater` lê o `latest.json` do release mais recente e só instala
 *   versão assinada por nós (Ed25519);
 * - dados: o Rust lê o `manifest.json` da release `dados`, baixa o `dados.db.enc`, confere o
 *   SHA-256 e decifra com a chave institucional guardada no cofre do SO.
 *
 * Por padrão o modo é assistido (ADR-0006); quando o usuário ativa o modo opt-in em Configurações,
 * o download ocorre em segundo plano via `appBaixar` e o reinício só acontece após o chat ficar
 * livre e a contagem regressiva concluir (`appAplicarEReiniciar`).
 */

export interface DadosStatus {
  /** Há um dados.db para o núcleo usar (baixado, ou o do repositório em desenvolvimento). */
  instalado: boolean
  versao: string | null
  desenvolvimento: boolean
  chave_configurada: boolean
}

export interface DadosRemoto {
  versao: string
  tamanho: number
  /** A versão publicada é outra que a instalada. */
  atualizacao: boolean
  /** A chave guardada não abre esta versão (falta, ou a instituição trocou a chave). */
  precisa_chave: boolean
}

export interface AppDownloadEvent {
  event?: string
  data?: {
    contentLength?: number
    chunkLength?: number
  }
}

export interface AppUpdate {
  version: string
  download?: (onEvent?: (event: AppDownloadEvent) => void) => Promise<void>
  install?: () => Promise<void>
  downloadAndInstall: (onEvent?: (event: AppDownloadEvent) => void) => Promise<void>
  close?: () => Promise<void>
}

function criarHandlerProgresso(onProgresso?: (fracao: number) => void) {
  let total = 0
  let baixado = 0
  return (evento: AppDownloadEvent) => {
    if (evento?.event === 'Started') total = evento.data?.contentLength ?? 0
    if (evento?.event === 'Progress') {
      baixado += evento.data?.chunkLength ?? 0
      if (total > 0) onProgresso?.(Math.min(baixado / total, 1))
    }
    if (evento?.event === 'Finished') onProgresso?.(1)
  }
}

async function invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  const { invoke } = await import('@tauri-apps/api/core')
  return invoke<T>(cmd, args)
}

/** `null` fora do app (navegador, testes sem mock) ou quando o Rust não responde o esperado. */
export async function dadosStatus(): Promise<DadosStatus | null> {
  const status = await invoke<DadosStatus | undefined>('dados_status')
  return status && typeof status.instalado === 'boolean' ? status : null
}

/** Lê o manifesto publicado. Rejeita sem internet ou sem release de dados. */
export async function dadosVerificar(): Promise<DadosRemoto | null> {
  const remoto = await invoke<DadosRemoto | undefined>('dados_verificar')
  return remoto && typeof remoto.versao === 'string' ? remoto : null
}

/**
 * Baixa, confere e troca o dados.db; com `chave`, guarda no cofre se ela abrir o pacote.
 * O núcleo reinicia com os dados novos; espera ele voltar antes de devolver a versão.
 */
export async function dadosInstalar(chave?: string): Promise<string> {
  const versao = await invoke<string>('dados_instalar', { chave: chave?.trim() || null })
  await coreReady()
  return versao
}

/** Versão nova do app publicada, ou `null`. */
export async function appVerificar(): Promise<AppUpdate | null> {
  const { check } = await import('@tauri-apps/plugin-updater')
  const update = await check()
  return update ?? null
}

/** Reinicia o executável desktop via `tauri-plugin-process`. */
export async function relaunchApp(): Promise<void> {
  const { relaunch } = await import('@tauri-apps/plugin-process')
  await relaunch()
}

/**
 * Baixa o pacote de atualização em segundo plano sem executar o instalador (seguro no Windows NSIS).
 * Retorna `true` se o download separado foi executado; `false` se o objeto só suportar `downloadAndInstall`.
 */
export async function appBaixar(
  update: AppUpdate,
  onProgresso?: (fracao: number) => void,
): Promise<boolean> {
  if (typeof update.download !== 'function') return false
  await update.download(criarHandlerProgresso(onProgresso))
  return true
}

/** Baixa e instala (confere a assinatura) e reinicia o app. `onProgresso` recebe 0..1. */
export async function appInstalar(update: AppUpdate, onProgresso?: (fracao: number) => void): Promise<void> {
  await update.downloadAndInstall(criarHandlerProgresso(onProgresso))
  await relaunchApp()
}

/**
 * Aplica um pacote já baixado (`update.install()`) e reinicia, ou cai no fluxo combinado
 * (`appInstalar`) quando o objeto não suporta download/instalação separados.
 */
export async function appAplicarEReiniciar(
  update: AppUpdate,
  jaBaixado: boolean,
  onProgresso?: (fracao: number) => void,
): Promise<void> {
  if (jaBaixado && typeof update.install === 'function') {
    await update.install()
    await relaunchApp()
    return
  }
  await appInstalar(update, onProgresso)
}
