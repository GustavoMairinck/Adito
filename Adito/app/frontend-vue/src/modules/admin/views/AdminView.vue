<script setup lang="ts">
/**
 * AdminView.vue
 * Pagina principal de Administracao do Adito (US-010 / US-023 / US-025 / US-DT-09)
 */
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import {
  Settings,
  Brain,
  RefreshCw,
  Server,
  Plus,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  Loader2,
  Database,
  FileText,
  Code2,
  Zap,
  HardDrive,
  Activity,
  Clock,
  Search,
  Calendar,
  ChevronLeft,
  ChevronRight
} from 'lucide-vue-next'

import { call } from '@/common/api/core'
import TrainingItemCard from '@/modules/admin/components/TrainingItemCard.vue'
import AddTrainingModal from '@/modules/admin/components/AddTrainingModal.vue'
import type { TrainingSubmit } from '@/modules/admin/components/AddTrainingModal.vue'
import ConfirmModal from '@/common/components/feedback/ConfirmModal.vue'
import type { TrainingItem } from '@/modules/admin/components/TrainingItemCard.vue'
// ─── Active Tab ───
const activeTab = ref<'governance' | 'etl' | 'audit' | 'system'>('governance')

const tabs = [
  { key: 'governance' as const, label: 'Base de conhecimento', icon: Brain },
  { key: 'audit' as const, label: 'Auditoria SQL', icon: Code2 },
  { key: 'etl' as const, label: 'Contextos de dados', icon: RefreshCw },
  { key: 'system' as const, label: 'Sistema', icon: Server }
]

// ════════════════════════════════════════════════════
// TAB 1: GOVERNANCA IA (US-010 + US-025)
// ════════════════════════════════════════════════════

// Itens do RAG no app.db (knowledge_knowledgeitem): os gerados dos arquivos de cada contexto
// (esquema das views, rules.md, examples.json) e os postos à mão aqui ou pela Auditoria SQL.
const trainingItems = ref<TrainingItem[]>([])
const loadingTrainings = ref(false)
const trainingsError = ref('')

async function fetchTrainings() {
  loadingTrainings.value = true
  trainingsError.value = ''
  try {
    trainingItems.value = await call<TrainingItem[]>('admin.trainings.list')
  } catch (error: any) {
    trainingsError.value = error?.message || 'Não foi possível ler a base de conhecimento.'
  } finally {
    loadingTrainings.value = false
  }
}

const expandedId = ref<string | null>(null)
const filterType = ref<'all' | 'ddl' | 'sql' | 'documentation'>('all')
/** 'all', 'global' (itens sem contexto) ou o id de um contexto. */
const filterContexto = ref<string>('all')
const searchQuery = ref('')
const showAddModal = ref(false)
const addingTraining = ref(false)
const addTrainingError = ref('')
const confirmWipe = ref(false)
const wipingInProgress = ref(false)
const wipeResult = ref<{ ok: boolean; text: string } | null>(null)
const itemToDelete = ref<TrainingItem | null>(null)
const removingItem = ref(false)

/** Contextos que aparecem no filtro e no modal: os do app.db mais os citados por algum item. */
const contextOptions = computed(() => {
  const map = new Map<string, string>()
  for (const c of contextosCarregados.value) map.set(c.id, c.nome)
  for (const i of trainingItems.value) {
    if (i.contexto && !map.has(i.contexto)) map.set(i.contexto, i.contexto_nome || i.contexto_slug || i.contexto)
  }
  return [...map].map(([id, nome]) => ({ id, nome })).sort((x, y) => x.nome.localeCompare(y.nome, 'pt-BR'))
})

const itemsDoContexto = computed(() => {
  if (filterContexto.value === 'all') return trainingItems.value
  if (filterContexto.value === 'global') return trainingItems.value.filter(i => !i.contexto)
  return trainingItems.value.filter(i => i.contexto === filterContexto.value)
})

const filteredItems = computed(() => {
  let items = itemsDoContexto.value
  if (filterType.value !== 'all') {
    items = items.filter(i => i.type === filterType.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    items = items.filter(i =>
      i.name.toLowerCase().includes(q) ||
      i.content.toLowerCase().includes(q) ||
      (i.question && i.question.toLowerCase().includes(q))
    )
  }
  return items
})

// Contagens do contexto escolhido no filtro (com "Todos", batem com o app.db inteiro).
const stats = computed(() => ({
  ddl: itemsDoContexto.value.filter(i => i.type === 'ddl').length,
  sql: itemsDoContexto.value.filter(i => i.type === 'sql').length,
  doc: itemsDoContexto.value.filter(i => i.type === 'documentation').length,
  total: itemsDoContexto.value.length
}))

function handleToggle(id: string) {
  expandedId.value = expandedId.value === id ? null : id
}

function requestRemove(item: TrainingItem) {
  itemToDelete.value = item
}

const removeMessage = computed(() => {
  const item = itemToDelete.value
  if (!item) return ''
  const base = `Tem certeza que deseja remover '${item.name}'?`
  return item.origem === 'contexto'
    ? `${base} Ele foi gerado dos arquivos do contexto e volta no próximo Wipe & Retrain.`
    : `${base} Esta ação não pode ser desfeita.`
})

async function confirmRemoveItem() {
  const item = itemToDelete.value
  if (!item || removingItem.value) return
  removingItem.value = true
  try {
    await call('admin.trainings.delete', { id: item.id })
    trainingItems.value = trainingItems.value.filter(i => i.id !== item.id)
    if (expandedId.value === item.id) expandedId.value = null
  } catch (error: any) {
    trainingsError.value = error?.message || 'Não foi possível remover o item.'
  } finally {
    removingItem.value = false
    itemToDelete.value = null
  }
}

function openAddModal() {
  addTrainingError.value = ''
  showAddModal.value = true
}

async function handleAdd(data: TrainingSubmit) {
  addingTraining.value = true
  addTrainingError.value = ''
  try {
    const created = await call<TrainingItem>('admin.trainings.create', {
      type: data.type,
      question: data.question,
      content: data.content,
      contexto: data.contexto
    })
    trainingItems.value.unshift(created)
    // Se o filtro atual esconderia o item recém-criado, ajusta para ele aparecer.
    if (filterType.value !== 'all' && filterType.value !== created.type) filterType.value = 'all'
    if (filterContexto.value !== 'all' && filterContexto.value !== (created.contexto || 'global')) {
      filterContexto.value = created.contexto || 'global'
    }
    expandedId.value = created.id
    showAddModal.value = false
  } catch (error: any) {
    const d = error?.data
    addTrainingError.value = d?.message || d?.detail || d?.question?.[0] || d?.contexto?.[0]
      || error?.message || 'Não foi possível salvar o treinamento.'
  } finally {
    addingTraining.value = false
  }
}

/** Contexto que o Wipe & Retrain vai refazer: o do filtro, ou todos os ativos. */
const wipeAlvo = computed(() => {
  const id = filterContexto.value
  if (id === 'all' || id === 'global') return null
  return contextOptions.value.find(c => c.id === id) ?? null
})

const wipeMessage = computed(() => {
  const alvo = wipeAlvo.value
  const itens = alvo ? trainingItems.value.filter(i => i.contexto === alvo.id) : trainingItems.value.filter(i => i.contexto)
  const gerados = itens.filter(i => i.origem === 'contexto').length
  const manuais = itens.filter(i => i.origem === 'manual').length
  const onde = alvo ? `do contexto "${alvo.nome}"` : 'de todos os contextos ativos'
  return `Os ${gerados} itens gerados dos arquivos ${onde} serão apagados e refeitos a partir do esquema das views, do rules.md e do examples.json (usa a chave do Gemini). `
    + (manuais
      ? `Os ${manuais} itens adicionados à mão (Novo Treinamento ou Auditoria SQL) serão mantidos. `
      : '')
    + 'Itens sem contexto não são tocados. Deseja continuar?'
})

async function handleWipeRetrain() {
  if (wipingInProgress.value) return
  confirmWipe.value = false
  wipingInProgress.value = true
  wipeResult.value = null
  try {
    // Sem limite de tempo: o reindex roda no núcleo local e pode levar minutos.
    const res = await call<{ contextos: { nome: string; indexado: boolean; erros: string[]; rag_itens?: number }[] }>(
      'admin.trainings.retrain',
      wipeAlvo.value ? { contexto: wipeAlvo.value.id } : {}
    )
    const falhas = res.contextos.filter(c => !c.indexado)
    const ok = res.contextos.filter(c => c.indexado)
    const partes = ok.map(c => `${c.nome}: ${c.rag_itens ?? 0} itens`)
    for (const f of falhas) partes.push(`${f.nome}: ${f.erros.join(' ')}`)
    wipeResult.value = {
      ok: falhas.length === 0 && ok.length > 0,
      text: res.contextos.length ? partes.join(' · ') : 'Nenhum contexto ativo para reindexar.'
    }
  } catch (error: any) {
    wipeResult.value = { ok: false, text: error?.data?.detail || error?.message || 'O reindex falhou.' }
  } finally {
    wipingInProgress.value = false
    await Promise.all([fetchTrainings(), fetchContextos()])
  }
}

// ════════════════════════════════════════════════════
// TAB 2: PREPARAR DADOS (US-023)
// ════════════════════════════════════════════════════

interface EtlTriggeredRun {
  dagId: string
  label: string
  dagRunId: string
  state: string
  triggeredAt: string | null
}

interface EtlLog {
  id: number
  timestamp: string
  message: string
  status: 'running' | 'success' | 'error'
  totalRecords: number
  changedRecords: number
  rows?: unknown[]  // históricos antigos (versão web) tinham linhas aqui
  runs: EtlTriggeredRun[]
}

const etlSyncing = ref(false)
const etlDispatchLocked = ref(false)
const expandedLog = ref<number | null>(null)

// ─── Data Bootstrap Pagination & Filters ───
const etlSearchQuery = ref('')
const etlCurrentPage = ref(1)
const etlItemsPerPage = ref(3)

const filteredEtlLogs = computed(() => {
  let logs = etlLogs.value

  // Filtro por termo (pesquisa na mensagem ou data)
  if (etlSearchQuery.value.trim()) {
    const q = etlSearchQuery.value.toLowerCase()
    logs = logs.filter(log =>
      log.message.toLowerCase().includes(q) ||
      new Date(log.timestamp).toLocaleDateString('pt-BR').includes(q)
    )
  }

  return logs
})

const hasRunningEtl = computed(() => (
  etlDispatchLocked.value || etlSyncing.value || etlLogs.value.some(log => log.status === 'running')
))

const totalEtlPages = computed(() => Math.ceil(filteredEtlLogs.value.length / etlItemsPerPage.value))

const paginatedEtlLogs = computed(() => {
  const start = (etlCurrentPage.value - 1) * etlItemsPerPage.value
  const end = start + etlItemsPerPage.value
  return filteredEtlLogs.value.slice(start, end)
})

function nextPage() {
  if (etlCurrentPage.value < totalEtlPages.value) etlCurrentPage.value++
}

function prevPage() {
  if (etlCurrentPage.value > 1) etlCurrentPage.value--
}

// Reseta a pagina quando o filtro muda
watch(etlSearchQuery, () => {
  etlCurrentPage.value = 1
})

const etlLogs = ref<EtlLog[]>((() => {
  try {
    const saved = localStorage.getItem('adito_etl_logs')
    return saved ? JSON.parse(saved) : []
  } catch {
    return []
  }
})())

watch(etlLogs, (newVal) => {
  localStorage.setItem('adito_etl_logs', JSON.stringify(newVal))
}, { deep: true })

function releaseEtlLock() {
  etlDispatchLocked.value = false
  etlSyncing.value = false
}

// ─── Contextos carregados no app.db (situação atual) ───
interface ContextoCarregado {
  id: string
  slug: string
  nome: string
  descricao: string
  ativo: boolean
  tabelas: string[]
  rag_itens: number
  valores: number
  atualizado_em: string | null
  erros: string[]
}

const contextosCarregados = ref<ContextoCarregado[]>([])
const loadingContextos = ref(false)
const contextosError = ref('')

async function fetchContextos() {
  loadingContextos.value = true
  contextosError.value = ''
  try {
    contextosCarregados.value = await call<ContextoCarregado[]>('admin.contextos')
  } catch (error: any) {
    contextosError.value = error?.message || 'Não foi possível ler os contextos.'
  } finally {
    loadingContextos.value = false
  }
}

/** Resultado de um contexto numa carga, em português e com a cor do estado. */
function runStateLabel(state: string) {
  if (state === 'success') return { text: 'Indexado', cls: 'text-emerald-600 dark:text-emerald-400' }
  if (state === 'pending') return { text: 'Válido, sem indexação', cls: 'text-amber-600 dark:text-amber-400' }
  return { text: 'Com erro', cls: 'text-red-600 dark:text-red-400' }
}

async function handleSync() {
  if (etlDispatchLocked.value || hasRunningEtl.value) {
    return
  }

  etlDispatchLocked.value = true
  etlSyncing.value = true
  try {
    // Sem limite de tempo: a indexação roda no núcleo local e pode levar minutos.
    const response = await call('admin.bootstrap')

    // Desktop: uma etapa por contexto da pasta de dados (validação no dados.db e indexação do RAG).
    const data = response || {}
    const contextos: any[] = data.contextos || []
    const triggeredAt = new Date().toISOString()
    const stages: EtlTriggeredRun[] = contextos.map((ctx) => ({
      dagId: ctx.slug || ctx.pasta,
      label: ctx.nome || ctx.pasta,
      dagRunId: !ctx.ativo || ctx.erros?.length
        ? (ctx.erros || []).join(' ')
        : ctx.indexado
          ? `${ctx.rag_itens} itens de RAG, ${ctx.valores} valores`
          : 'válido; sem indexação (falta a chave do Gemini)',
      state: ctx.erros?.length || !ctx.ativo ? 'failed' : ctx.indexado ? 'success' : 'pending',
      triggeredAt
    }))
    const validos = contextos.filter((ctx) => ctx.ativo).length
    const indexados = contextos.filter((ctx) => ctx.ativo && ctx.indexado).length
    const falhou = contextos.some((ctx) => !ctx.ativo || ctx.erros?.length)

    etlLogs.value.unshift({
      id: Date.now(),
      timestamp: triggeredAt,
      message: data.chave_configurada
        ? `${validos} de ${contextos.length} contexto(s) válidos; ${indexados} indexado(s).`
        : `${validos} de ${contextos.length} contexto(s) válidos. Configure a chave do Gemini para indexar o RAG.`,
      status: falhou ? 'error' : 'success',
      totalRecords: contextos.length,
      changedRecords: validos,
      runs: stages
    })

    releaseEtlLock()
    fetchContextos()
  } catch (error: any) {
    const newLog: EtlLog = {
      id: Date.now(),
      timestamp: new Date().toISOString(),
      message: error?.response?.data?.detail || error?.response?.data?.error || error?.message || 'Falha ao preparar dados',
      status: 'error',
      totalRecords: 0,
      changedRecords: 0,
      runs: []
    }
    etlLogs.value.unshift(newLog)
    releaseEtlLock()
    fetchContextos()
  }
}

const services = ref<{ name: string; status: 'online' | 'offline'; url: string; latency?: string | number }[]>([])

const systemStats = ref({
  version: '...',
  uptime: '...',
  vectorRows: 0,
  trainedDdl: 0,
  trainedDoc: 0,
  trainedExamples: 0,
  lastTraining: ''
})

const loadingSystem = ref(true)

async function fetchSystemStatus() {
  try {
    const res = await call('admin.system_status')
    if (res) {
      services.value = (res.services || []).map((s: any) => ({
        name: s.name,
        status: s.status,
        url: s.url,
        latency: s.latency_ms ? `${s.latency_ms}ms` : '-'
      }))
      systemStats.value = res.systemStats || systemStats.value
    }
  } catch (error) {
    console.error('Erro ao buscar status do sistema:', error)
  } finally {
    loadingSystem.value = false
  }
}

// ─── TAB 3: AUDITORIA SQL (US-DT-09) ───
const queryExecutions = ref<any[]>([])
const loadingExecutions = ref(false)
const auditError = ref('')
const auditFilter = ref<'all' | 'valid' | 'invalid'>('all')
const auditSearchQuery = ref('')
const auditCurrentPage = ref(1)
const auditItemsPerPage = ref(10)
const expandedAuditId = ref<string | null>(null)

async function fetchQueryExecutions() {
  loadingExecutions.value = true
  auditError.value = ''
  try {
    const params: Record<string, string> = { limit: '100' }
    if (auditFilter.value === 'valid') params.is_valid = 'true'
    if (auditFilter.value === 'invalid') params.is_valid = 'false'
    const response = await call('admin.query_executions', params)
    queryExecutions.value = Array.isArray(response) ? response : []
  } catch (error) {
    queryExecutions.value = []
    auditError.value = 'Não foi possível carregar o histórico de SQL.'
    console.error('Erro ao buscar auditoria de SQL:', error)
  } finally {
    loadingExecutions.value = false
  }
}

async function promoteAuditRow(row: any) {
  if (!row.generated_sql) return
  auditError.value = ''
  try {
    const data = await call<TrainingItem>('admin.trainings.create', {
      type: 'sql',
      question: row.question_original || 'Consulta auditada',
      content: row.generated_sql,
      // A consulta foi feita num contexto: o exemplo vale para as perguntas desse contexto.
      contexto: row.contexto || null
    })
    trainingItems.value.unshift(data)
    filterType.value = 'sql'
    filterContexto.value = data.contexto || 'global'
    expandedId.value = data.id
    activeTab.value = 'governance'
  } catch (err: any) {
    auditError.value = err?.data?.detail || err?.data?.message || err?.message
      || 'Não foi possível promover a consulta para treinamento.'
  }
}

const filteredAuditLogs = computed(() => {
  let logs = queryExecutions.value
  if (auditSearchQuery.value.trim()) {
    const q = auditSearchQuery.value.toLowerCase()
    logs = logs.filter(log =>
      log.question_original && log.question_original.toLowerCase().includes(q)
    )
  }
  return logs
})

const auditStats = computed(() => {
  const total = queryExecutions.value.length
  const valid = queryExecutions.value.filter(log => log.is_valid).length
  const invalid = total - valid
  return { total, valid, invalid }
})

watch(auditFilter, fetchQueryExecutions)

const totalAuditPages = computed(() => Math.ceil(filteredAuditLogs.value.length / auditItemsPerPage.value))

const paginatedAuditLogs = computed(() => {
  const start = (auditCurrentPage.value - 1) * auditItemsPerPage.value
  const end = start + auditItemsPerPage.value
  return filteredAuditLogs.value.slice(start, end)
})

function nextAuditPage() {
  if (auditCurrentPage.value < totalAuditPages.value) auditCurrentPage.value++
}

function prevAuditPage() {
  if (auditCurrentPage.value > 1) auditCurrentPage.value--
}

watch(auditSearchQuery, () => {
  auditCurrentPage.value = 1
})

let sysPolling: number | null = null

watch(activeTab, (val) => {
  if (val === 'system') {
    fetchSystemStatus()
    sysPolling = window.setInterval(fetchSystemStatus, 10000)
  } else if (sysPolling) {
    clearInterval(sysPolling)
    sysPolling = null
  }
  
  if (val === 'audit') {
    fetchQueryExecutions()
  }

  if (val === 'etl') {
    fetchContextos()
  }

  if (val === 'governance') {
    fetchTrainings()
    fetchContextos()
  }
}, { immediate: true })

onBeforeUnmount(() => {
  if (sysPolling) clearInterval(sysPolling)
})
</script>

<template>
  <div class="min-h-screen bg-primary p-4 md:p-8">
    <div class="space-y-8">

      <!-- ═══ Header ═══ -->
      <div class="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
        <div class="space-y-2">
          <h1 class="flex items-center gap-4 text-4xl font-bold tracking-[-0.03em] text-text-primary">
            <Settings class="h-9 w-9 text-accent" stroke-width="1.5" />
            Administração
          </h1>
          <p class="max-w-2xl text-base text-text-secondary">
            Carregue os contextos de pesquisa e extensão, gerencie o modelo de inteligência artificial e acompanhe os dados locais do Adito.
          </p>
        </div>
      </div>

      <!-- ═══ Tab Navigation ═══ -->
      <div class="flex w-fit items-center gap-1 rounded-lg bg-surface-elevated/60 p-1 border border-border-subtle">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :class="[
            'flex items-center gap-2 rounded-md px-5 py-2 text-sm font-medium transition-all duration-150',
            activeTab === tab.key
              ? 'bg-surface text-text-primary border border-border-subtle'
              : 'text-text-secondary hover:text-text-primary hover:bg-surface/50'
          ]"
          @click="activeTab = tab.key"
        >
          <component :is="tab.icon" class="h-4 w-4" stroke-width="2" />
          {{ tab.label }}
        </button>
      </div>

      <!-- ════════════════════════════════════════════ -->
      <!-- TAB 1: GOVERNANCA IA                        -->
      <!-- ════════════════════════════════════════════ -->
      <template v-if="activeTab === 'governance'">

        <!-- Stats Cards -->
        <div class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <div class="premium-card p-6">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">Total de Itens</p>
                <p class="mt-2 text-4xl font-semibold tracking-[-0.04em] text-text-primary">{{ stats.total }}</p>
              </div>
              <div class="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--brand-primary)]/10 border border-[var(--brand-primary)]/20">
                <Brain class="h-6 w-6 text-[var(--brand-primary)] dark:text-[#68d388]" stroke-width="1.75" />
              </div>
            </div>
          </div>

          <div class="premium-card p-6">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">Estruturas DDL</p>
                <p class="mt-2 text-4xl font-semibold tracking-[-0.04em] text-text-primary">{{ stats.ddl }}</p>
              </div>
              <div class="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--brand-primary)]/10 border border-[var(--brand-primary)]/20">
                <Database class="h-6 w-6 text-[var(--brand-primary)] dark:text-[#68d388]" stroke-width="1.75" />
              </div>
            </div>
          </div>

          <div class="premium-card p-6">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">Queries SQL</p>
                <p class="mt-2 text-4xl font-semibold tracking-[-0.04em] text-text-primary">{{ stats.sql }}</p>
              </div>
              <div class="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--brand-primary)]/10 border border-[var(--brand-primary)]/20">
                <Code2 class="h-6 w-6 text-[var(--brand-primary)] dark:text-[#68d388]" stroke-width="1.75" />
              </div>
            </div>
          </div>

          <div class="premium-card p-6">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">Documentação</p>
                <p class="mt-2 text-4xl font-semibold tracking-[-0.04em] text-text-primary">{{ stats.doc }}</p>
              </div>
              <div class="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--brand-primary)]/10 border border-[var(--brand-primary)]/20">
                <FileText class="h-6 w-6 text-[var(--brand-primary)] dark:text-[#68d388]" stroke-width="1.75" />
              </div>
            </div>
          </div>
        </div>

        <!-- Toolbar -->
        <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div class="flex flex-1 flex-wrap items-center gap-4">
            <!-- Search -->
            <div class="relative flex-1 md:max-w-md">
              <Search class="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" stroke-width="2" />
              <input
                v-model="searchQuery"
                type="text"
                placeholder="Pesquisar em treinamentos..."
                class="w-full rounded-lg border border-border-subtle bg-surface py-2.5 pl-10 pr-4 text-sm text-text-primary placeholder-text-muted transition-all focus:border-[var(--brand-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--brand-primary)]/20"
              />
            </div>

            <!-- Contexto -->
            <select
              v-model="filterContexto"
              title="Contexto dos itens"
              class="rounded-lg border border-border-subtle bg-surface px-3 py-2.5 text-sm text-text-primary focus:border-[var(--brand-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--brand-primary)]/20"
            >
              <option value="all">Todos os contextos</option>
              <option v-for="c in contextOptions" :key="c.id" :value="c.id">{{ c.nome }}</option>
              <option value="global">Sem contexto (vale para todos)</option>
            </select>

            <!-- Filter -->
            <div class="flex items-center gap-1 rounded-lg bg-surface p-1 border border-border-subtle">
              <button
                v-for="f in [
                  { key: 'all' as const, label: 'Todos' },
                  { key: 'ddl' as const, label: 'DDL' },
                  { key: 'sql' as const, label: 'SQL' },
                  { key: 'documentation' as const, label: 'Docs' }
                ]"
                :key="f.key"
                :class="[
                  'rounded-md px-4 py-1.5 text-xs font-semibold transition-all duration-200',
                  filterType === f.key
                    ? 'bg-surface-elevated text-text-primary shadow-sm'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface-elevated/50'
                ]"
                @click="filterType = f.key"
              >
                {{ f.label }}
              </button>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-3">
            <button
              class="btn-primary flex items-center gap-2"
              @click="openAddModal"
            >
              <Plus class="h-4 w-4" stroke-width="2.5" />
              Novo Treinamento
            </button>
            <button
              :disabled="wipingInProgress"
              class="btn-secondary flex items-center gap-2 text-[#C50707] border-[#C50707]/30 hover:border-[#C50707]/60 hover:bg-[#C50707]/8 dark:text-red-300 dark:border-red-400/40 dark:bg-red-500/10 dark:hover:bg-red-500/20 dark:hover:border-red-400/60"
              :title="wipeAlvo ? `Refazer o índice de ${wipeAlvo.nome}` : 'Refazer o índice de todos os contextos ativos'"
              @click="confirmWipe = true"
            >
              <Loader2 v-if="wipingInProgress" class="h-4 w-4 animate-spin" />
              <Zap v-else class="h-4 w-4" />
              {{ wipingInProgress ? 'Reindexando...' : 'Wipe & Retrain' }}
            </button>
          </div>
        </div>

        <p
          v-if="wipeResult"
          :class="[
            'rounded-lg border px-4 py-3 text-sm',
            wipeResult.ok
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
              : 'border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-300'
          ]"
        >
          {{ wipeResult.ok ? 'Índice refeito.' : 'O reindex não terminou em todos os contextos.' }} {{ wipeResult.text }}
        </p>
        <p
          v-if="trainingsError"
          class="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-300"
        >
          {{ trainingsError }}
        </p>

        <!-- Training Items List -->
        <div class="space-y-3">
          <TrainingItemCard
            v-for="item in filteredItems"
            :key="item.id"
            :item="item"
            :expanded="expandedId === item.id"
            @toggle="handleToggle(item.id)"
            @remove="requestRemove"
          />

          <div
            v-if="loadingTrainings && trainingItems.length === 0"
            class="premium-card flex items-center justify-center gap-3 py-16 text-sm text-text-secondary"
          >
            <Loader2 class="h-5 w-5 animate-spin" /> Lendo a base de conhecimento...
          </div>
          <div
            v-else-if="filteredItems.length === 0"
            class="premium-card flex flex-col items-center justify-center gap-3 py-16 text-center"
          >
            <Brain class="h-12 w-12 text-text-muted opacity-40" />
            <template v-if="trainingItems.length === 0">
              <p class="text-sm font-medium text-text-secondary">A base de conhecimento está vazia</p>
              <p class="text-xs text-text-muted">Carregue os contextos na aba "Contextos de dados" ou use o Wipe &amp; Retrain para indexá-los</p>
            </template>
            <template v-else>
              <p class="text-sm font-medium text-text-secondary">Nenhum item de treinamento encontrado</p>
              <p class="text-xs text-text-muted">Ajuste os filtros ou adicione um novo treinamento</p>
            </template>
          </div>
        </div>

        <!-- Add Training Modal -->
        <AddTrainingModal
          :open="showAddModal"
          :contextos="contextOptions"
          :default-contexto="wipeAlvo?.id ?? null"
          :submitting="addingTraining"
          :error="addTrainingError"
          @close="showAddModal = false"
          @submit="handleAdd"
        />

        <!-- Wipe Confirmation Modal -->
        <ConfirmModal
          :is-open="confirmWipe"
          :title="wipeAlvo ? `Wipe & Retrain: ${wipeAlvo.nome}` : 'Wipe & Retrain: todos os contextos'"
          :message="wipeMessage"
          confirm-text="Wipe & Retrain"
          @confirm="handleWipeRetrain"
          @close="confirmWipe = false"
        />

        <!-- Item Delete Confirmation Modal -->
        <ConfirmModal
          :is-open="!!itemToDelete"
          title="Excluir treinamento"
          :message="removeMessage"
          confirm-text="Remover item"
          @confirm="confirmRemoveItem"
          @close="itemToDelete = null"
        />
      </template>

      <!-- ════════════════════════════════════════════ -->
      <!-- TAB 2: AUDITORIA SQL (US-DT-09)             -->
      <!-- ════════════════════════════════════════════ -->
      <template v-else-if="activeTab === 'audit'">

        <!-- Stats Cards -->
        <div class="grid grid-cols-1 gap-6 sm:grid-cols-3">
          <div class="premium-card p-6">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">Total de Consultas</p>
                <p class="mt-2 text-4xl font-semibold tracking-[-0.04em] text-text-primary">{{ auditStats.total }}</p>
              </div>
              <div class="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--brand-primary)]/10 border border-[var(--brand-primary)]/20">
                <Code2 class="h-6 w-6 text-[var(--brand-primary)] dark:text-[#68d388]" stroke-width="1.75" />
              </div>
            </div>
          </div>

          <div class="premium-card p-6">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">Consultas Válidas</p>
                <p class="mt-2 text-4xl font-semibold tracking-[-0.04em] text-text-primary">{{ auditStats.valid }}</p>
              </div>
              <div class="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--brand-primary)]/10 border border-[var(--brand-primary)]/20">
                <CheckCircle2 class="h-6 w-6 text-[var(--brand-primary)] dark:text-[#68d388]" stroke-width="1.75" />
              </div>
            </div>
          </div>

          <div class="premium-card p-6">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">Consultas Inválidas</p>
                <p class="mt-2 text-4xl font-semibold tracking-[-0.04em] text-text-primary">{{ auditStats.invalid }}</p>
              </div>
              <div class="flex h-12 w-12 items-center justify-center rounded-full bg-[#C50707]/10 border border-[#C50707]/20 dark:bg-red-500/15 dark:border-red-400/25">
                <XCircle class="h-6 w-6 text-[#C50707] dark:text-red-300" stroke-width="1.75" />
              </div>
            </div>
          </div>
        </div>

        <!-- Toolbar -->
        <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div class="flex flex-1 flex-wrap items-center gap-4">
            <!-- Search -->
            <div class="relative flex-1 md:max-w-md">
              <Search class="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" stroke-width="2" />
              <input
                v-model="auditSearchQuery"
                type="text"
                placeholder="Pesquisar por pergunta..."
                class="w-full rounded-lg border border-border-subtle bg-surface py-2.5 pl-10 pr-4 text-sm text-text-primary placeholder-text-muted transition-all focus:border-[var(--brand-primary)] focus:outline-none focus:ring-2 focus:ring-[var(--brand-primary)]/20"
              />
            </div>

            <!-- Filter -->
            <div class="flex items-center gap-1 rounded-lg bg-surface p-1 border border-border-subtle">
              <button
                v-for="f in [
                  { key: 'all' as const, label: 'Todos' },
                  { key: 'valid' as const, label: 'Válidos' },
                  { key: 'invalid' as const, label: 'Inválidos' }
                ]"
                :key="f.key"
                :class="[
                  'rounded-md px-4 py-1.5 text-xs font-semibold transition-all duration-200',
                  auditFilter === f.key
                    ? 'bg-surface-elevated text-text-primary shadow-sm'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface-elevated/50'
                ]"
                @click="auditFilter = f.key"
              >
                {{ f.label }}
              </button>
            </div>
          </div>

          <button
            class="btn-secondary flex items-center gap-2 text-xs"
            @click="fetchQueryExecutions"
            :disabled="loadingExecutions"
          >
            <RefreshCw class="h-3.5 w-3.5" />
            Atualizar
          </button>
        </div>

        <div v-if="auditError" class="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400">
          {{ auditError }}
        </div>

        <!-- Audit List -->
        <div class="space-y-3">
          <div v-if="loadingExecutions" class="premium-card flex items-center justify-center py-16">
            <Loader2 class="h-6 w-6 animate-spin text-text-muted" />
          </div>

          <template v-else-if="paginatedAuditLogs.length > 0">
            <div
              v-for="log in paginatedAuditLogs"
              :key="log.id"
              :class="[
                'overflow-hidden rounded-xl border transition-all duration-300 backdrop-blur-md',
                expandedAuditId === log.id
                  ? 'border-accent/30 bg-surface-elevated/40'
                  : 'border-border-subtle bg-surface/30 hover:border-border-standard hover:bg-surface/50'
              ]"
            >
              <!-- Header -->
              <button
                class="flex w-full items-center gap-5 px-6 py-5 text-left transition-all group"
                @click="expandedAuditId = expandedAuditId === log.id ? null : log.id"
              >
                <div class="min-w-0 flex-1">
                  <p class="truncate text-sm font-semibold text-text-primary group-hover:text-accent transition-colors">
                    {{ log.question_original || 'Pergunta não registrada' }}
                  </p>
                  <div class="mt-1 flex flex-wrap items-center gap-3 text-xs text-text-muted">
                    <span class="flex items-center gap-1">
                      <Clock class="h-3 w-3" />
                      {{ new Date(log.created_at).toLocaleString('pt-BR') }}
                    </span>
                    <span v-if="log.execution_time_ms != null">{{ log.execution_time_ms }}ms</span>
                  </div>
                </div>

                <div class="flex shrink-0 items-center gap-3">
                  <span
                    :class="[
                      'inline-flex shrink-0 items-center gap-1.5 rounded-md border px-3 py-1 text-[10px] font-bold uppercase tracking-widest',
                      log.is_valid
                        ? 'border-emerald-500/20 bg-emerald-500/5 text-emerald-500'
                        : 'border-red-500/20 bg-red-500/5 text-red-400'
                    ]"
                  >
                    {{ log.is_valid ? 'Válida' : 'Inválida' }}
                  </span>
                  <div class="p-1.5 rounded-md bg-surface/50 border border-border-subtle">
                    <ChevronUp v-if="expandedAuditId === log.id" class="h-4 w-4 text-text-muted" />
                    <ChevronDown v-else class="h-4 w-4 text-text-muted" />
                  </div>
                </div>
              </button>

              <!-- Expanded Detail -->
              <div v-if="expandedAuditId === log.id" class="border-t border-border-subtle bg-background/40">
                <div class="px-6 py-6 space-y-4">
                  <div class="flex items-center justify-between px-1">
                    <p class="text-[11px] font-bold uppercase tracking-[0.2em] text-text-muted">SQL Gerado</p>
                    <button
                      v-if="log.generated_sql"
                      class="btn-secondary flex items-center gap-2 px-3 py-1.5 text-xs"
                      @click="promoteAuditRow(log)"
                    >
                      <Plus class="h-3.5 w-3.5" />
                      Promover para Treinamento
                    </button>
                  </div>
                  <div class="relative overflow-hidden rounded-xl border border-border-subtle bg-primary dark:bg-black/20">
                    <pre class="font-mono text-sm leading-relaxed text-sky-700 dark:text-sky-400 overflow-x-auto p-6 whitespace-pre-wrap">{{ log.generated_sql }}</pre>
                  </div>

                  <div v-if="log.error_message" class="rounded-lg border border-red-500/20 bg-red-500/5 p-3">
                    <p class="text-xs font-semibold text-red-400">Erro: {{ log.error_message }}</p>
                  </div>
                </div>
              </div>
            </div>
          </template>

          <div v-else class="premium-card flex flex-col items-center gap-3 py-16 text-center">
            <Code2 class="h-10 w-10 text-text-muted opacity-40" />
            <p class="text-sm text-text-secondary">Nenhuma consulta encontrada.</p>
            <p class="text-xs text-text-muted">Perguntas feitas no chat que geram consultas serão listadas aqui.</p>
          </div>

          <!-- Pagination -->
          <div v-if="totalAuditPages > 1" class="flex items-center justify-between pt-2">
            <span class="text-sm text-text-secondary">
              Página {{ auditCurrentPage }} de {{ totalAuditPages }} ({{ filteredAuditLogs.length }} registros)
            </span>
            <div class="flex gap-2">
              <button
                :disabled="auditCurrentPage === 1"
                class="flex items-center gap-1 rounded-lg border border-border-subtle px-3 py-1.5 text-sm text-text-primary transition-colors hover:bg-surface-elevated/40 disabled:opacity-50"
                @click="prevAuditPage"
              >
                <ChevronLeft class="h-4 w-4" /> Anterior
              </button>
              <button
                :disabled="auditCurrentPage === totalAuditPages"
                class="flex items-center gap-1 rounded-lg border border-border-subtle px-3 py-1.5 text-sm text-text-primary transition-colors hover:bg-surface-elevated/40 disabled:opacity-50"
                @click="nextAuditPage"
              >
                Próxima <ChevronRight class="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </template>

      <!-- ════════════════════════════════════════════ -->
      <!-- TAB 3: PREPARAR DADOS                       -->
      <!-- ════════════════════════════════════════════ -->
      <template v-else-if="activeTab === 'etl'">

        <!-- Sync Action Card (full-width horizontal) -->
        <div class="premium-card overflow-hidden">
          <div class="flex flex-col gap-8 p-8 md:flex-row md:items-center md:justify-between">
            <div class="flex items-center gap-6">
              <div class="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-accent/10 border border-accent/20">
                <Database class="h-8 w-8 text-accent" stroke-width="1.5" />
              </div>
              <div class="space-y-1">
                <h2 class="text-xl font-semibold text-text-primary">Contextos de dados</h2>
                <p class="max-w-xl text-sm text-text-secondary leading-relaxed">
                  Lê os contextos do app e da sua pasta de dados, confere se as tabelas existem no dados.db e,
                  com a chave do Gemini configurada, gera o RAG (esquema, regras e exemplos) e o índice de valores de cada um.
                </p>
              </div>
            </div>
            <button
              :disabled="hasRunningEtl"
              :class="[
                'btn-primary flex shrink-0 items-center gap-3 px-5 py-3 text-sm',
                hasRunningEtl ? 'opacity-50 cursor-not-allowed' : ''
              ]"
              @click="handleSync"
            >
              <Loader2 v-if="hasRunningEtl" class="h-5 w-5 animate-spin" />
              <RefreshCw v-else class="h-5 w-5" stroke-width="2.5" />
              {{ hasRunningEtl ? 'Indexando contextos…' : 'Carregar e indexar contextos' }}
            </button>
          </div>
          <p v-if="hasRunningEtl" class="mt-4 text-sm text-text-muted">
            Pode levar alguns minutos: o Gemini limita os pedidos por minuto e o Adito espera quando precisa.
            Se parar no meio, o que já foi indexado fica salvo e a próxima carga continua de onde parou.
          </p>
        </div>

        <!-- Contextos carregados -->
        <div class="premium-card overflow-hidden">
          <div class="flex items-center justify-between gap-4 border-b border-border-subtle bg-surface/20 px-8 py-6">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-accent/10 rounded-lg">
                <Database class="h-5 w-5 text-accent" stroke-width="2" />
              </div>
              <h2 class="text-lg font-semibold text-text-primary">Contextos carregados</h2>
            </div>
            <button
              class="flex items-center gap-2 rounded-lg border border-border-subtle px-3 py-1.5 text-sm text-text-secondary transition-colors hover:text-text-primary"
              :disabled="loadingContextos"
              @click="fetchContextos"
            >
              <RefreshCw :class="['h-4 w-4', loadingContextos ? 'animate-spin' : '']" />
              Atualizar
            </button>
          </div>

          <p v-if="contextosError" class="px-8 py-6 text-sm text-red-600 dark:text-red-400">{{ contextosError }}</p>
          <p v-else-if="!loadingContextos && contextosCarregados.length === 0" class="px-8 py-6 text-sm text-text-muted">
            Nenhum contexto no app ainda. Use "Carregar e indexar contextos".
          </p>
          <ul v-else class="divide-y divide-border-subtle">
            <li v-for="ctx in contextosCarregados" :key="ctx.id" class="flex flex-col gap-3 px-8 py-5">
              <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
                <p class="text-base font-semibold text-text-primary">{{ ctx.nome }}</p>
                <span class="font-mono text-xs text-text-muted">{{ ctx.slug }}</span>
                <span
                  :class="[
                    'rounded-full px-2.5 py-0.5 text-xs font-semibold',
                    ctx.ativo && ctx.erros.length === 0
                      ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                      : 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'
                  ]"
                >{{ ctx.ativo && ctx.erros.length === 0 ? 'Ativo' : 'Inativo' }}</span>
              </div>
              <p v-if="ctx.descricao" class="max-w-3xl text-sm text-text-secondary">{{ ctx.descricao }}</p>
              <div class="flex flex-wrap gap-x-6 gap-y-1 text-sm text-text-secondary">
                <span><b class="font-semibold text-text-primary">{{ ctx.tabelas.length }}</b> tabela{{ ctx.tabelas.length === 1 ? '' : 's' }}</span>
                <span><b class="font-semibold text-text-primary">{{ ctx.rag_itens.toLocaleString('pt-BR') }}</b> itens de RAG</span>
                <span><b class="font-semibold text-text-primary">{{ ctx.valores.toLocaleString('pt-BR') }}</b> valores indexados</span>
                <span v-if="ctx.atualizado_em">Atualizado em {{ new Date(ctx.atualizado_em).toLocaleString('pt-BR') }}</span>
              </div>
              <p v-if="ctx.ativo && ctx.erros.length === 0 && ctx.rag_itens === 0" class="text-xs text-amber-700 dark:text-amber-400">
                Ainda sem RAG: o chat funciona, mas com menos exemplos. Configure a chave do Gemini e use "Carregar e indexar contextos".
              </p>
              <ul v-if="ctx.erros.length" class="space-y-1 rounded-lg border border-red-100 bg-red-50/60 px-4 py-3 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300">
                <li v-for="erro in ctx.erros" :key="erro">{{ erro }}</li>
              </ul>
              <details class="text-xs text-text-muted">
                <summary class="cursor-pointer select-none">Tabelas do contexto</summary>
                <p class="mt-2 font-mono leading-relaxed">{{ ctx.tabelas.join(' · ') }}</p>
              </details>
            </li>
          </ul>
        </div>

        <!-- Reports accordion -->
        <div class="premium-card overflow-hidden">
          <div class="flex flex-col gap-6 border-b border-border-subtle bg-surface/20 px-8 py-6 md:flex-row md:items-center md:justify-between backdrop-blur-sm">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-accent/10 rounded-lg">
                <Clock class="h-5 w-5 text-accent" stroke-width="2" />
              </div>
              <h2 class="text-lg font-semibold text-text-primary">Histórico de carregamento</h2>
            </div>

            <!-- Filtro de Busca -->
            <div class="relative max-w-md w-full">
              <Search class="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" stroke-width="2" />
              <input
                v-model="etlSearchQuery"
                type="text"
                placeholder="Filtrar por mensagem ou data..."
                class="w-full rounded-lg border border-border-subtle bg-surface/30 py-2.5 pl-10 pr-4 text-sm text-text-primary placeholder-text-muted outline-none transition-all focus:border-accent/50 focus:ring-4 focus:ring-accent/5"
              />
            </div>
          </div>

          <div v-if="paginatedEtlLogs.length > 0" class="divide-y divide-gray-100 dark:divide-white/5">
            <div
              v-for="log in paginatedEtlLogs"
              :key="log.id"
            >
              <!-- Header clicavel -->
              <button
                class="flex w-full items-center justify-between px-6 py-4 text-left transition-colors hover:bg-gray-50 dark:hover:bg-white/[0.02]"
                @click="expandedLog = expandedLog === log.id ? null : log.id"
              >
                <div class="flex items-center gap-3">
                  <CheckCircle2 v-if="log.status === 'success'" class="h-4 w-4 shrink-0 text-emerald-500" />
                  <Loader2      v-else-if="log.status === 'running'" class="h-4 w-4 shrink-0 animate-spin text-amber-500" />
                  <XCircle      v-else class="h-4 w-4 shrink-0 text-red-400" />
                  <div>
                    <p class="text-sm text-slate-700 dark:text-slate-200">{{ log.message }}</p>
                    <p class="mt-0.5 text-xs text-slate-400 dark:text-slate-500">
                      {{ new Date(log.timestamp).toLocaleString('pt-BR') }}
                    </p>
                  </div>
                </div>
                <div class="flex shrink-0 items-center gap-3">
                  <span v-if="log.runs.length > 0" class="text-xs text-slate-400 dark:text-slate-500">
                    {{ log.changedRecords }} de {{ log.runs.length }} contexto{{ log.runs.length > 1 ? 's' : '' }} válido{{ log.changedRecords === 1 ? '' : 's' }}
                  </span>
                  <span v-else-if="log.status === 'running'" class="text-xs font-semibold text-amber-600 dark:text-amber-400">Em execucao</span>
                  <span v-else-if="log.status === 'error'" class="text-xs text-red-500 font-semibold">Falha na preparação</span>
                  <ChevronUp   v-if="expandedLog === log.id" class="h-4 w-4 text-slate-400" />
                  <ChevronDown v-else                        class="h-4 w-4 text-slate-400" />
                </div>
              </button>

              <!-- Painel expandido -->
              <Transition
                enter-active-class="transition-all duration-200 ease-out"
                enter-from-class="opacity-0"
                enter-to-class="opacity-100"
              >
                <div v-if="expandedLog === log.id" class="border-t border-gray-100 bg-gray-50/50 px-6 pb-6 pt-4 dark:border-white/5 dark:bg-slate-900/30">

                  <!-- Erro -->
                  <div
                    v-if="log.status === 'error'"
                    class="rounded border border-red-100 bg-white px-4 py-3 text-sm text-red-600 dark:border-red-900/40 dark:bg-slate-900 dark:text-red-400"
                  >
                    {{ log.message }}
                    <ul v-if="log.runs.length" class="mt-2 space-y-1">
                      <li v-for="(run, i) in log.runs.filter(item => item.state === 'failed')" :key="run.dagId + i">
                        {{ run.label }} — {{ run.dagRunId }}
                      </li>
                    </ul>
                  </div>

                  <!-- Sucesso -->
                  <template v-else>
                    <div v-if="log.runs.length > 0" class="mb-4 space-y-3">
                      <div class="rounded-lg border border-border-subtle bg-white/80 p-4 dark:bg-slate-900/60">
                        <p class="text-sm font-semibold text-slate-900 dark:text-white">
                          {{ log.status === 'running' ? 'Carga em andamento' : 'Carga concluída' }}
                        </p>
                        <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          {{ log.status === 'running'
                            ? 'O núcleo está validando e indexando os contextos.'
                            : 'Resultado de cada contexto nesta carga.'
                          }}
                        </p>
                      </div>

                      <div
                        v-for="(run, i) in log.runs"
                        :key="run.dagId + i"
                        class="rounded-lg border border-border-subtle bg-white px-4 py-3 dark:bg-slate-900"
                      >
                        <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                          <div>
                            <p class="text-sm font-semibold text-slate-900 dark:text-white">{{ run.label }}</p>
                            <p class="mt-1 font-mono text-xs text-slate-500 dark:text-slate-400">{{ run.dagId }}</p>
                          </div>
                          <span :class="['text-xs font-semibold', runStateLabel(run.state).cls]">
                            {{ runStateLabel(run.state).text }}
                          </span>
                        </div>
                        <div class="mt-3 grid gap-2 text-xs text-slate-500 dark:text-slate-400 md:grid-cols-2">
                          <p><span class="font-semibold text-slate-700 dark:text-slate-200">Detalhe:</span> <span class="font-mono">{{ run.dagRunId }}</span></p>
                          <p><span class="font-semibold text-slate-700 dark:text-slate-200">Executado em:</span> <span class="font-mono">{{ run.triggeredAt || '-' }}</span></p>
                        </div>
                      </div>
                    </div>

                  </template>
                </div>
              </Transition>
            </div>
          </div>
          <div v-else class="flex flex-col items-center justify-center py-12 text-center text-slate-500">
            <Calendar class="mb-3 h-10 w-10 text-slate-300 dark:text-slate-600" />
            <p>Nenhuma carga de contextos encontrada para o filtro aplicado.</p>
          </div>

          <!-- Paginacao -->
          <div v-if="totalEtlPages > 1" class="flex items-center justify-between border-t border-gray-100 px-6 py-4 dark:border-white/5">
            <span class="text-sm text-slate-500">
              Pagina {{ etlCurrentPage }} de {{ totalEtlPages }} ({{ filteredEtlLogs.length }} registros)
            </span>
            <div class="flex gap-2">
              <button
                :disabled="etlCurrentPage === 1"
                class="flex items-center gap-1 rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-slate-600 transition-colors hover:bg-gray-50 disabled:opacity-50 dark:border-white/10 dark:text-slate-300 dark:hover:bg-white/5"
                @click="prevPage"
              >
                <ChevronLeft class="h-4 w-4" /> Anterior
              </button>
              <button
                :disabled="etlCurrentPage === totalEtlPages"
                class="flex items-center gap-1 rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-slate-600 transition-colors hover:bg-gray-50 disabled:opacity-50 dark:border-white/10 dark:text-slate-300 dark:hover:bg-white/5"
                @click="nextPage"
              >
                Proxima <ChevronRight class="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </template>

      <!-- ════════════════════════════════════════════ -->
      <!-- TAB 4: SISTEMA                              -->
      <!-- ════════════════════════════════════════════ -->
      <template v-else-if="activeTab === 'system'">

        <!-- Service Status -->
        <div class="premium-card overflow-hidden">
          <div class="flex items-center gap-3 border-b border-border-subtle bg-surface/20 px-8 py-5">
            <div class="p-2 bg-accent/10 rounded-lg">
              <Activity class="h-5 w-5 text-accent" stroke-width="2" />
            </div>
            <h2 class="text-lg font-semibold text-text-primary">Status do Ecossistema</h2>
          </div>
          <div class="divide-y divide-border-subtle">
            <div
              v-for="svc in services"
              :key="svc.name"
              class="flex items-center justify-between px-8 py-5 hover:bg-surface/10 transition-colors group"
            >
              <div class="flex items-center gap-4">
                <span class="flex h-2.5 w-2.5">
                  <span
                    :class="[
                      'inline-flex h-2.5 w-2.5 rounded-full',
                      svc.status === 'online' ? 'bg-emerald-500' : 'bg-red-500'
                    ]"
                  />
                </span>
                <div>
                  <p class="text-sm font-semibold text-text-primary group-hover:text-accent transition-colors">{{ svc.name }}</p>
                  <p class="font-mono text-[11px] text-text-muted mt-0.5">{{ svc.url }}</p>
                </div>
              </div>
              <div class="flex items-center gap-6">
                <span class="font-mono text-xs text-text-muted">{{ svc.latency }}</span>
                <span
                  :class="[
                    'text-[10px] font-bold uppercase tracking-wider',
                    svc.status === 'online'
                      ? 'text-emerald-500'
                      : 'text-red-500'
                  ]"
                >
                  {{ svc.status === 'online' ? 'Operacional' : 'Indisponível' }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- System Info Cards -->
        <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <div class="premium-card p-6">
            <div class="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--brand-primary)]/10 border border-[var(--brand-primary)]/20 mb-6">
              <Server class="h-6 w-6 text-[var(--brand-primary)] dark:text-[#68d388]" stroke-width="1.75" />
            </div>
            <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted mb-2">Versão do Sistema</p>
            <p class="text-2xl font-semibold text-text-primary mb-6">v{{ systemStats.version }}</p>

            <div class="space-y-2.5 pt-4 border-t border-border-subtle">
              <div class="flex items-center justify-between text-xs">
                <span class="text-text-secondary">Tempo de Atividade</span>
                <span class="font-mono text-text-primary">{{ systemStats.uptime }}</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-text-secondary">Ambiente</span>
                <span class="text-text-primary">Produção</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-text-secondary">Status do Core</span>
                <span class="text-text-primary">Saudável</span>
              </div>
            </div>
          </div>

          <div class="premium-card p-6">
            <div class="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--brand-primary)]/10 border border-[var(--brand-primary)]/20 mb-6">
              <HardDrive class="h-6 w-6 text-[var(--brand-primary)] dark:text-[#68d388]" stroke-width="1.75" />
            </div>
            <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted mb-2">SQLite Vec (RAG)</p>
            <p class="text-2xl font-semibold text-text-primary mb-6">{{ systemStats.vectorRows.toLocaleString('pt-BR') }} <span class="text-sm font-normal text-text-secondary">vetores</span></p>

            <div class="space-y-2.5 pt-4 border-t border-border-subtle">
              <div class="flex items-center justify-between text-xs">
                <span class="text-text-secondary">DDLs Indexadas</span>
                <span class="font-mono text-text-primary">{{ systemStats.trainedDdl }}</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-text-secondary">Documentação</span>
                <span class="font-mono text-text-primary">{{ systemStats.trainedDoc }}</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-text-secondary">Exemplos SQL</span>
                <span class="font-mono text-text-primary">{{ systemStats.trainedExamples }}</span>
              </div>
            </div>
          </div>

          <div class="premium-card p-6">
            <div class="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--brand-primary)]/10 border border-[var(--brand-primary)]/20 mb-6">
              <Brain class="h-6 w-6 text-[var(--brand-primary)] dark:text-[#68d388]" stroke-width="1.75" />
            </div>
            <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted mb-2">Inteligência Artificial</p>
            <p class="text-2xl font-semibold text-text-primary mb-6">Operacional</p>

            <div class="space-y-2.5 pt-4 border-t border-border-subtle">
              <div class="flex items-center justify-between text-xs">
                <span class="text-text-secondary">Último Treino</span>
                <span class="text-text-primary">{{ new Date(systemStats.lastTraining).toLocaleDateString('pt-BR') }}</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-text-secondary">Motor LLM</span>
                <span class="text-text-primary">Gemini AI</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-text-secondary">Vector Store</span>
                <span class="text-text-primary">SQLite BLOB (numpy)</span>
              </div>
            </div>
          </div>
        </div>
      </template>

    </div>
  </div>
</template>
