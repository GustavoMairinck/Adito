import { computed, ref, shallowRef } from 'vue'
import {
  appInstalar,
  appVerificar,
  dadosInstalar,
  dadosStatus,
  dadosVerificar,
  type AppUpdate,
  type DadosRemoto,
  type DadosStatus,
} from '@/common/api/atualizacoes'

/**
 * Estado único (compartilhado entre a barra lateral e a tela de primeiro uso) das atualizações.
 * Ao abrir, confere uma vez se há versão nova do app ou dos dados; nunca instala sem o usuário pedir.
 * Sem internet, ou sem release publicado, não mostra nada.
 */

const status = ref<DadosStatus | null>(null)
const dadosRemoto = ref<DadosRemoto | null>(null)
const app = shallowRef<AppUpdate | null>(null)

const instalandoDados = ref(false)
const instalandoApp = ref(false)
const progressoApp = ref(0)
const erro = ref<string | null>(null)

let verificacao: Promise<void> | null = null

function mensagem(err: unknown): string {
  if (typeof err === 'string') return err
  if (err && typeof err === 'object' && 'message' in err) return String((err as Error).message)
  return String(err)
}

async function carregarStatus() {
  try {
    status.value = await dadosStatus()
  } catch {
    status.value = null
  }
}

async function verificarAgora() {
  await carregarStatus()
  const [remoto, update] = await Promise.allSettled([dadosVerificar(), appVerificar()])
  dadosRemoto.value = remoto.status === 'fulfilled' ? remoto.value : null
  app.value = update.status === 'fulfilled' ? update.value : null
}

/** Confere uma vez por sessão; chamadas seguintes reaproveitam a mesma conferência. */
function verificar(): Promise<void> {
  verificacao ??= verificarAgora().catch(() => {})
  return verificacao
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

async function instalarDados(chave?: string): Promise<boolean> {
  instalandoDados.value = true
  erro.value = null
  try {
    await dadosInstalar(chave)
    await carregarStatus()
    if (dadosRemoto.value) dadosRemoto.value = { ...dadosRemoto.value, atualizacao: false, precisa_chave: false }
    return true
  } catch (err) {
    erro.value = mensagem(err)
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
  if (!app.value) return
  instalandoApp.value = true
  progressoApp.value = 0
  erro.value = null
  try {
    await appInstalar(app.value, (f) => (progressoApp.value = f))
  } catch (err) {
    erro.value = `Não foi possível atualizar o app: ${mensagem(err)}`
    instalandoApp.value = false
  }
}

export function useAtualizacoes() {
  return {
    status,
    dadosRemoto,
    app,
    dadosNovos,
    temAtualizacao,
    precisaPrimeiraCarga,
    instalandoDados,
    instalandoApp,
    progressoApp,
    erro,
    verificar,
    instalarDados,
    instalarApp,
    limparErro: () => (erro.value = null),
  }
}

/** Só para testes: volta ao estado de app recém-aberto. */
export function _resetAtualizacoes() {
  status.value = null
  dadosRemoto.value = null
  app.value = null
  instalandoDados.value = false
  instalandoApp.value = false
  progressoApp.value = 0
  erro.value = null
  verificacao = null
}
