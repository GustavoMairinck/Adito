import { computed, effectScope, ref, shallowRef, watch, type EffectScope } from 'vue'
import {
  appAplicarEReiniciar,
  appBaixar,
  appInstalar,
  appVerificar,
  dadosInstalar,
  dadosStatus,
  dadosVerificar,
  type AppUpdate,
  type DadosRemoto,
  type DadosStatus,
} from '@/common/api/atualizacoes'
import { useChatApi } from '@/modules/chat/composables/useChatApi'

/**
 * Estado único (compartilhado entre a barra lateral, layout principal, configurações e views)
 * das atualizações do Adito.
 *
 * - Padrão (ADR-0006): modo assistido (`autoAtualizar = false`) — apenas avisa na barra lateral.
 * - Opt-in (`autoAtualizar = true`): monitora a cada 30 min e ao retornar foco (cooldown 15 min),
 *   baixa o executável em segundo plano, aguarda o chat ficar livre (`!useChatApi().isLoading`),
 *   exibe contagem regressiva de 10s com "Reiniciar agora" / "Adiar", ou atualiza `dados.db`
 *   automaticamente quando não houver update do executável pendente nem troca de chave.
 * - Sempre que `dados.db` é instalado (manual ou automático), incrementa `dadosReloadSeq` para
 *   as telas abertas recarregarem os dados sem exigir clique manual.
 */

export const AUTO_UPDATE_STORAGE_KEY = 'adito:auto_update'
export const INTERVALO_VERIFICACAO_MS = 30 * 60 * 1000
export const COOLDOWN_FOCO_MS = 15 * 60 * 1000
export const CONTAGEM_REINICIO_SEGUNDOS = 10
export const DURACAO_TOAST_DADOS_MS = 6000

function lerPreferenciaAutoAtualizar(): boolean {
  try {
    return typeof localStorage !== 'undefined' && localStorage.getItem(AUTO_UPDATE_STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}

function salvarPreferenciaAutoAtualizar(ativo: boolean): void {
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(AUTO_UPDATE_STORAGE_KEY, ativo ? 'true' : 'false')
    }
  } catch {
    /* sem storage disponível: segue funcionando em memória */
  }
}

const status = ref<DadosStatus | null>(null)
const dadosRemoto = ref<DadosRemoto | null>(null)
const app = shallowRef<AppUpdate | null>(null)

const autoAtualizar = ref<boolean>(lerPreferenciaAutoAtualizar())

const instalandoDados = ref(false)
const instalandoApp = ref(false)
const baixandoAppEmSegundoPlano = ref(false)
const progressoApp = ref(0)
const erro = ref<string | null>(null)

const verificando = ref(false)
const erroVerificacao = ref<string | null>(null)
const appBaixadoVersao = ref<string | null>(null)
const segundosParaReinicio = ref<number | null>(null)
const versaoAdiada = ref<string | null>(null)

const dadosReloadSeq = ref(0)
const ultimaVersaoDadosAtualizada = ref<string | null>(null)
const toastDadosAtualizados = ref<string | null>(null)
let verificacao: Promise<void> | null = null
let verificacaoEmCurso: Promise<void> | null = null
let ultimaVerificacaoEm = 0

let monitorando = false
let intervaloVerificacaoId: ReturnType<typeof setInterval> | null = null
let contagemTimerId: ReturnType<typeof setInterval> | null = null
let toastTimerId: ReturnType<typeof setTimeout> | null = null
let cooldownFocoAtualMs = COOLDOWN_FOCO_MS
let chatWatchScope: EffectScope | null = null

let falhaAutoApp: { versao: string; em: number } | null = null
let falhaAutoDados: { versao: string; em: number } | null = null

function mensagem(err: unknown): string {
  if (typeof err === 'string') return err
  if (err && typeof err === 'object' && 'message' in err) return String((err as Error).message)
  return String(err)
}

function limparToastTimer() {
  if (toastTimerId !== null) {
    clearTimeout(toastTimerId)
    toastTimerId = null
  }
}

function fecharToastDados() {
  limparToastTimer()
  toastDadosAtualizados.value = null
}

function mostrarToastDados(versao: string | null) {
  limparToastTimer()
  toastDadosAtualizados.value = versao
    ? `Dados atualizados para a versão ${versao}`
    : 'Dados atualizados com sucesso'
  toastTimerId = setTimeout(() => {
    toastDadosAtualizados.value = null
    toastTimerId = null
  }, DURACAO_TOAST_DADOS_MS)
}

function pararContagemReinicio() {
  if (contagemTimerId !== null) {
    clearInterval(contagemTimerId)
    contagemTimerId = null
  }
  segundosParaReinicio.value = null
}

function garantirWatchChat() {
  if (chatWatchScope) return
  const { isLoading: chatOcupado } = useChatApi()
  chatWatchScope = effectScope(true)
  chatWatchScope.run(() => {
    watch(chatOcupado, (ocupado) => {
      if (ocupado) {
        if (segundosParaReinicio.value !== null) {
          pararContagemReinicio()
        }
      } else if (autoAtualizar.value) {
        void orquestrarAutoUpdate()
      }
    })
  })
}

async function carregarStatus() {
  try {
    status.value = await dadosStatus()
  } catch {
    status.value = null
  }
}

async function verificarAgora(): Promise<void> {
  if (verificacaoEmCurso) return verificacaoEmCurso

  verificando.value = true
  erroVerificacao.value = null
  verificacaoEmCurso = (async () => {
    await carregarStatus()
    const emDesenvolvimento = Boolean(status.value?.desenvolvimento)
    const [remoto, update] = await Promise.allSettled([
      dadosVerificar(),
      emDesenvolvimento ? Promise.resolve(null) : appVerificar(),
    ])
    dadosRemoto.value = remoto.status === 'fulfilled' ? remoto.value : null
    if (remoto.status === 'rejected') {
      erroVerificacao.value = mensagem(remoto.reason)
    } else if (!emDesenvolvimento && update.status === 'rejected') {
      erroVerificacao.value = mensagem(update.reason)
    }

    const appAnterior = app.value
    const appAnteriorEmUsoOuBaixado = Boolean(
      appAnterior &&
      (appBaixadoVersao.value === appAnterior.version ||
        baixandoAppEmSegundoPlano.value ||
        instalandoApp.value)
    )

    if (update.status === 'rejected') {
      if (!appAnteriorEmUsoOuBaixado) {
        appBaixadoVersao.value = null
        pararContagemReinicio()
        if (appAnterior) {
          void appAnterior.close?.().catch(() => {})
        }
        app.value = null
      }
    } else {
      const proximoApp = update.value
      if (appAnterior && proximoApp && proximoApp.version === appAnterior.version) {
        if (appAnteriorEmUsoOuBaixado) {
          if (proximoApp !== appAnterior) {
            void proximoApp.close?.().catch(() => {})
          }
        } else {
          if (proximoApp !== appAnterior) {
            void appAnterior.close?.().catch(() => {})
          }
          app.value = proximoApp
        }
      } else {
        if (appAnterior) {
          if (appBaixadoVersao.value === appAnterior.version) {
            appBaixadoVersao.value = null
          }
          pararContagemReinicio()
          if (appAnterior !== proximoApp) {
            void appAnterior.close?.().catch(() => {})
          }
        }
        if (!proximoApp) {
          appBaixadoVersao.value = null
          pararContagemReinicio()
        }
        app.value = proximoApp
      }
    }
    ultimaVerificacaoEm = Date.now()
  })().finally(() => {
    verificacaoEmCurso = null
    verificando.value = false
  })

  await verificacaoEmCurso

  if (autoAtualizar.value) {
    void orquestrarAutoUpdate()
  }
}

/** Confere uma vez por sessão; passe `{ forcar: true }` para forçar nova conferência. */
function verificar(opcoes?: { forcar?: boolean }): Promise<void> {
  if (opcoes?.forcar) {
    verificacao = verificarAgora().catch(() => {})
    return verificacao
  }
  verificacao ??= verificarAgora().catch(() => {})
  return verificacao
}

/** Executa nova verificação sem concorrência (usado pelo ciclo de 30 min e retorno de foco). */
function verificarNovamente(opcoes?: { forcar?: boolean }): Promise<void> {
  if (verificacaoEmCurso) return verificacaoEmCurso
  if (instalandoDados.value || instalandoApp.value || baixandoAppEmSegundoPlano.value) {
    return Promise.resolve()
  }
  if (!opcoes?.forcar && ultimaVerificacaoEm > 0 && Date.now() - ultimaVerificacaoEm < cooldownFocoAtualMs) {
    return Promise.resolve()
  }
  const p = verificarAgora().catch(() => {})
  verificacao = p
  return p
}

/** Primeiro uso: o app está rodando como app (status conhecido) e ainda não tem dados. */
const precisaPrimeiraCarga = computed(() => status.value !== null && !status.value.instalado)

const dadosNovos = computed(() => {
  const s = status.value
  const r = dadosRemoto.value
  // Em desenvolvimento o núcleo usa o dados.db do repositório: não oferece troca.
  if (!s || !r || !s.instalado || s.desenvolvimento) return null
  return r.atualizacao ? r : null
})

const temAtualizacao = computed(() => !!app.value || !!dadosNovos.value)

const appProntoParaReinicio = computed(
  () => !!app.value && appBaixadoVersao.value === app.value.version
)

function emBackoff(falha: { versao: string; em: number } | null, versao: string): boolean {
  if (!falha || falha.versao !== versao) return false
  return Date.now() - falha.em < INTERVALO_VERIFICACAO_MS
}

function iniciarContagemReinicio() {
  if (contagemTimerId !== null || !app.value) return
  segundosParaReinicio.value = CONTAGEM_REINICIO_SEGUNDOS
  contagemTimerId = setInterval(() => {
    const { isLoading: chatOcupado } = useChatApi()
    if (!autoAtualizar.value || !app.value || chatOcupado.value || versaoAdiada.value === app.value.version) {
      pararContagemReinicio()
      return
    }
    const proximo = (segundosParaReinicio.value ?? 1) - 1
    if (proximo <= 0) {
      pararContagemReinicio()
      void reiniciarAgora()
      return
    }
    segundosParaReinicio.value = proximo
  }, 1000)
}

async function orquestrarAutoUpdate(): Promise<void> {
  if (!autoAtualizar.value || precisaPrimeiraCarga.value) return
  garantirWatchChat()

  const { isLoading: chatOcupado } = useChatApi()

  // Prioridade 1 (FR05): executável antes de dados.db.
  if (app.value) {
    const updateAtual = app.value
    const versao = updateAtual.version

    if (versaoAdiada.value === versao) return
    if (instalandoApp.value || baixandoAppEmSegundoPlano.value) return
    if (emBackoff(falhaAutoApp, versao)) return

    const suportaDownloadSeparado = typeof updateAtual.download === 'function'

    if (suportaDownloadSeparado && appBaixadoVersao.value !== versao) {
      baixandoAppEmSegundoPlano.value = true
      progressoApp.value = 0
      try {
        const baixou = await appBaixar(updateAtual, (f) => {
          progressoApp.value = f
        })
        if (baixou && app.value?.version === versao) {
          appBaixadoVersao.value = versao
          falhaAutoApp = null
        }
      } catch {
        falhaAutoApp = { versao, em: Date.now() }
        return
      } finally {
        baixandoAppEmSegundoPlano.value = false
      }
    }

    // Revalida estado após o await do download.
    if (!autoAtualizar.value || app.value?.version !== versao || versaoAdiada.value === versao) return
    if (chatOcupado.value) return

    iniciarContagemReinicio()
    return
  }

  // Prioridade 2 (FR06): atualização automática de dados.db quando sem update de executável.
  const novos = dadosNovos.value
  if (!novos || novos.precisa_chave) return
  if (instalandoDados.value) return
  if (emBackoff(falhaAutoDados, novos.versao)) return
  if (chatOcupado.value) return

  const ok = await instalarDados(undefined, { silencioso: true })
  if (ok) {
    falhaAutoDados = null
  } else {
    falhaAutoDados = { versao: novos.versao, em: Date.now() }
  }
}

async function instalarDados(chave?: string, opcoes?: { silencioso?: boolean }): Promise<boolean> {
  if (instalandoDados.value) return false
  instalandoDados.value = true
  if (!opcoes?.silencioso) erro.value = null
  try {
    const versaoInstalada = await dadosInstalar(chave)
    await carregarStatus()
    const versaoFinal = versaoInstalada || status.value?.versao || dadosRemoto.value?.versao || null
    if (dadosRemoto.value) {
      dadosRemoto.value = { ...dadosRemoto.value, atualizacao: false, precisa_chave: false }
    }
    ultimaVersaoDadosAtualizada.value = versaoFinal
    dadosReloadSeq.value += 1
    mostrarToastDados(versaoFinal)
    return true
  } catch (err) {
    if (!opcoes?.silencioso) {
      erro.value = mensagem(err)
    }
    // Pode ter sido a chave que mudou: volta a perguntar ao Rust o que falta.
    try {
      dadosRemoto.value = await dadosVerificar()
    } catch {
      /* sem rede: mantém o que já sabia */
    }
    return false
  } finally {
    instalandoDados.value = false
  }
}

async function instalarApp(): Promise<void> {
  if (!app.value || instalandoApp.value || baixandoAppEmSegundoPlano.value) return
  const updateAtual = app.value
  const jaBaixado = appBaixadoVersao.value === updateAtual.version && typeof updateAtual.install === 'function'
  pararContagemReinicio()
  instalandoApp.value = true
  if (!jaBaixado) progressoApp.value = 0
  erro.value = null
  try {
    if (jaBaixado) {
      await appAplicarEReiniciar(updateAtual, true, (f) => {
        progressoApp.value = f
      })
    } else {
      await appInstalar(updateAtual, (f) => {
        progressoApp.value = f
      })
    }
  } catch (err) {
    if (jaBaixado) {
      appBaixadoVersao.value = null
    }
    falhaAutoApp = { versao: updateAtual.version, em: Date.now() }
    erro.value = `Não foi possível atualizar o app: ${mensagem(err)}`
    instalandoApp.value = false
  }
}

function adiarReinicio(): void {
  if (app.value) {
    versaoAdiada.value = app.value.version
  }
  pararContagemReinicio()
}

async function reiniciarAgora(): Promise<void> {
  await instalarApp()
}

function setAutoAtualizar(ativo: boolean): void {
  autoAtualizar.value = ativo
  salvarPreferenciaAutoAtualizar(ativo)
  if (!ativo) {
    pararContagemReinicio()
  } else {
    void orquestrarAutoUpdate()
  }
}

function aoVoltarFoco() {
  if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return
  void verificarNovamente({ forcar: false })
}

function iniciarMonitoramento(opcoes?: { intervaloMs?: number; cooldownFocoMs?: number }): void {
  garantirWatchChat()
  if (monitorando) return
  monitorando = true

  const intervaloMs = opcoes?.intervaloMs ?? INTERVALO_VERIFICACAO_MS
  cooldownFocoAtualMs = opcoes?.cooldownFocoMs ?? COOLDOWN_FOCO_MS

  void verificar()

  intervaloVerificacaoId = setInterval(() => {
    void verificarNovamente({ forcar: true })
  }, intervaloMs)

  if (typeof document !== 'undefined') {
    document.addEventListener('visibilitychange', aoVoltarFoco)
  }
  if (typeof window !== 'undefined') {
    window.addEventListener('focus', aoVoltarFoco)
  }
}

function pararMonitoramento(): void {
  monitorando = false
  if (intervaloVerificacaoId !== null) {
    clearInterval(intervaloVerificacaoId)
    intervaloVerificacaoId = null
  }
  if (typeof document !== 'undefined') {
    document.removeEventListener('visibilitychange', aoVoltarFoco)
  }
  if (typeof window !== 'undefined') {
    window.removeEventListener('focus', aoVoltarFoco)
  }
  pararContagemReinicio()
  fecharToastDados()
}

export function useAtualizacoes() {
  return {
    status,
    dadosRemoto,
    app,
    dadosNovos,
    temAtualizacao,
    precisaPrimeiraCarga,
    autoAtualizar,
    instalandoDados,
    instalandoApp,
    verificando,
    erroVerificacao,
    baixandoAppEmSegundoPlano,
    appProntoParaReinicio,
    segundosParaReinicio,
    versaoAdiada,
    progressoApp,
    erro,
    dadosReloadSeq,
    ultimaVersaoDadosAtualizada,
    toastDadosAtualizados,
    verificar,
    verificarNovamente,
    iniciarMonitoramento,
    pararMonitoramento,
    setAutoAtualizar,
    instalarDados,
    instalarApp,
    adiarReinicio,
    reiniciarAgora,
    fecharToastDados,
    limparErro: () => (erro.value = null),
  }
}

/** Só para testes: volta ao estado de app recém-aberto. */
export function _resetAtualizacoes(opcoes?: { preservarPreferencia?: boolean }) {
  pararMonitoramento()
  if (chatWatchScope) {
    chatWatchScope.stop()
    chatWatchScope = null
  }
  status.value = null
  dadosRemoto.value = null
  app.value = null
  instalandoDados.value = false
  instalandoApp.value = false
  verificando.value = false
  erroVerificacao.value = null
  baixandoAppEmSegundoPlano.value = false
  progressoApp.value = 0
  erro.value = null
  appBaixadoVersao.value = null
  segundosParaReinicio.value = null
  versaoAdiada.value = null
  dadosReloadSeq.value = 0
  ultimaVersaoDadosAtualizada.value = null
  toastDadosAtualizados.value = null
  verificacao = null
  verificacaoEmCurso = null
  ultimaVerificacaoEm = 0
  cooldownFocoAtualMs = COOLDOWN_FOCO_MS
  falhaAutoApp = null
  falhaAutoDados = null
  if (!opcoes?.preservarPreferencia) {
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem(AUTO_UPDATE_STORAGE_KEY)
      }
    } catch {
      /* ignore */
    }
    autoAtualizar.value = false
  } else {
    autoAtualizar.value = lerPreferenciaAutoAtualizar()
  }
}
