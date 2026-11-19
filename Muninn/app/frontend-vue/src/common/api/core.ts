/**
 * Chamadas ao núcleo local do Muninn (Python), via Tauri, sem servidor HTTP.
 *
 * O front chama `call('dashboard.kpis', {...})`; o Tauri escreve o pedido no stdin do núcleo
 * e devolve a resposta que volta pelo stdout (ver src-tauri/src/lib.rs e backend/nucleo/rpc/server.py).
 * `stream` faz o mesmo e entrega os eventos (token, status, result, error) antes do fim.
 *
 * Erros chegam como CoreError, com `status` e `data` iguais ao que o servidor HTTP devolvia;
 * `error.response.{status,data}` continua existindo para o tratamento que as telas já fazem.
 */
import { Channel, invoke } from '@tauri-apps/api/core'

export class CoreError extends Error {
  status: number
  data: any
  response: { status: number; data: any }

  constructor(status: number, data: any, message?: string) {
    const fromData = data && typeof data === 'object'
      ? data.detail ?? data.error ?? data.message
      : undefined
    super(message ?? (typeof fromData === 'string' ? fromData : `status ${status}`))
    this.name = 'CoreError'
    this.status = status
    this.data = data
    this.response = { status, data }
  }
}

export interface CallOptions {
  /** Abortar rejeita na hora com `name === 'CanceledError'` e pede ao núcleo para cancelar. */
  signal?: AbortSignal
}

// Começa num ponto aleatório: se a página recarregar (Ctrl+R, Vite) com pedidos ainda abertos no
// Rust, os ids novos não colidem com os antigos ("Pedido já está em andamento").
let lastId = Math.floor(Math.random() * 2 ** 40)
const nextId = () => ++lastId

function canceled(): CoreError {
  const error = new CoreError(499, { detail: 'canceled' }, 'canceled')
  error.name = 'CanceledError'
  return error
}

function toCoreError(err: unknown): CoreError {
  if (err instanceof CoreError) return err
  if (err && typeof err === 'object' && 'status' in err) {
    const { status, data } = err as { status: number; data: any }
    return new CoreError(status, data)
  }
  return new CoreError(503, { detail: String(err) })
}

/** Rejeita assim que o signal abortar e avisa o núcleo para parar o pedido. */
function withAbort<T>(id: number, promise: Promise<T>, signal?: AbortSignal): Promise<T> {
  if (!signal) return promise
  if (signal.aborted) return Promise.reject(canceled())
  return new Promise<T>((resolve, reject) => {
    const onAbort = () => {
      invoke('core_cancel', { id }).catch(() => {})
      reject(canceled())
    }
    signal.addEventListener('abort', onAbort, { once: true })
    promise.then(resolve, reject).finally(() => signal.removeEventListener('abort', onAbort))
  })
}

/** Espera o núcleo ficar pronto (ao abrir o app e depois de trocar a chave). */
export async function coreReady(): Promise<void> {
  await invoke('core_ready')
}

export function call<T = any>(method: string, params: Record<string, unknown> = {}, options: CallOptions = {}): Promise<T> {
  const id = nextId()
  const request = invoke<T>('core_call', { id, method, params }).catch((err) => {
    throw toCoreError(err)
  })
  return withAbort(id, request, options.signal)
}

type StreamEnd = { event: '$end'; ok: boolean; result?: any; error?: { status: number; data: any } }
type StreamMessage = { event: string; data: any } | StreamEnd

/**
 * Pedido com eventos. Os eventos chegam em ordem pelo Channel, e o fim também (`$end`),
 * então nenhum evento chega depois de a Promise resolver.
 */
export function stream<T = any>(
  method: string,
  params: Record<string, unknown>,
  onEvent: (event: string, data: any) => void,
  options: CallOptions = {},
): Promise<T> {
  const id = nextId()
  const request = new Promise<T>((resolve, reject) => {
    let settled = false
    const channel = new Channel<StreamMessage>()
    channel.onmessage = (message) => {
      if (settled) return
      if (message.event === '$end') {
        settled = true
        const end = message as StreamEnd
        if (end.ok) resolve(end.result as T)
        else reject(new CoreError(end.error?.status ?? 500, end.error?.data))
        return
      }
      onEvent(message.event, (message as { data: any }).data)
    }
    invoke('core_stream', { id, method, params, onEvent: channel }).catch((err) => {
      if (!settled) {
        settled = true
        reject(toCoreError(err))
      }
    })
  })
  return withAbort(id, request, options.signal)
}
