<script setup lang="ts">
/**
 * AdminView.vue
 * Pagina principal de Administracao do ORACULO-ESX (US-010 / US-023 / US-025 / US-DT-09)
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

import httpClient from '@/common/api/httpClient'
import TrainingItemCard from '@/modules/admin/components/TrainingItemCard.vue'
import AddTrainingModal from '@/modules/admin/components/AddTrainingModal.vue'
import ConfirmModal from '@/common/components/feedback/ConfirmModal.vue'
import type { TrainingItem } from '@/modules/admin/components/TrainingItemCard.vue'
// ─── Active Tab ───
const activeTab = ref<'governance' | 'etl' | 'audit' | 'system'>('governance')

const tabs = [
  { key: 'governance' as const, label: 'Governanca IA', icon: Brain },
  { key: 'audit' as const, label: 'Auditoria SQL', icon: Code2 },
  { key: 'etl' as const, label: 'Preparar Dados', icon: RefreshCw },
  { key: 'system' as const, label: 'Sistema', icon: Server }
]

// ════════════════════════════════════════════════════
// TAB 1: GOVERNANCA IA (US-010 + US-025)
// ════════════════════════════════════════════════════

const trainingItems = ref<TrainingItem[]>([
  {
    id: 'ddl-001',
    type: 'ddl',
    name: 'vfactvendasresolved',
    content: `CREATE OR REPLACE VIEW public.vfactvendasresolved AS
SELECT *
FROM fapes.vfactvendasresolved`,
    created_at: '2026-01-15T10:05:00Z'
  },
  {
    id: 'ddl-002',
    type: 'ddl',
    name: 'FactVendas',
    content: `CREATE TABLE fact_vendas (
id_venda INT PRIMARY KEY,
id_tempo INT,
id_produto INT,
id_cliente INT,
id_regiao INT,
id_canal INT,
id_vendedor INT,
quantidade_vendida INT,
valor_bruto DECIMAL(12,2),
desconto DECIMAL(12,2),
receita_liquida DECIMAL(12,2),
custo DECIMAL(12,2),
lucro DECIMAL(12,2)
)`,
    created_at: '2026-01-15T10:05:00Z'
  },
  {
    id: 'sql-001',
    type: 'sql',
    name: 'Receita liquida por ano',
    question: 'Qual a receita liquida total por ano?',
    content: `SELECT ano, SUM(receita_liquida) AS receita_liquida_total
FROM vfactvendasresolved
GROUP BY ano
ORDER BY ano`,
    created_at: '2026-02-01T14:30:00Z'
  },
  {
    id: 'sql-002',
    type: 'sql',
    name: 'Top produtos por receita',
    question: 'Quais sao os 10 produtos com maior receita liquida?',
    content: `SELECT produto, SUM(receita_liquida) AS receita_liquida_total
FROM vfactvendasresolved
GROUP BY produto
ORDER BY receita_liquida_total DESC
LIMIT 10`,
    created_at: '2026-02-01T14:35:00Z'
  },
  {
    id: 'sql-003',
    type: 'sql',
    name: 'Lucro por categoria',
    question: 'Qual o lucro por categoria de produto?',
    content: `SELECT categoria_produto, SUM(lucro) AS lucro_total
FROM vfactvendasresolved
GROUP BY categoria_produto
ORDER BY lucro_total DESC`,
    created_at: '2026-02-05T09:00:00Z'
  },
  {
    id: 'sql-004',
    type: 'sql',
    name: 'Receita por canal',
    question: 'Qual a receita liquida por canal de venda?',
    content: `SELECT canal, SUM(receita_liquida) AS receita_liquida_total, COUNT(id_venda) AS qtd_vendas
FROM vfactvendasresolved
GROUP BY canal
ORDER BY receita_liquida_total DESC`,
    created_at: '2026-02-10T11:20:00Z'
  },
  {
    id: 'sql-005',
    type: 'sql',
    name: 'Evolucao mensal de receita',
    question: 'Como foi a evolucao mensal da receita em 2025?',
    content: `SELECT mes, SUM(receita_liquida) AS receita_liquida_total
FROM vfactvendasresolved
WHERE ano = 2025
GROUP BY mes
ORDER BY mes`,
    created_at: '2026-02-12T16:45:00Z'
  },
  {
    id: 'sql-006',
    type: 'sql',
    name: 'Clientes por porte',
    question: 'Quantos clientes existem em cada porte?',
    content: `SELECT porte_cliente, COUNT(DISTINCT cliente) AS qtd_clientes
FROM vfactvendasresolved
GROUP BY porte_cliente
ORDER BY qtd_clientes DESC`,
    created_at: '2026-02-15T08:00:00Z'
  },
  {
    id: 'doc-001',
    type: 'documentation',
    name: 'Glossario - Receita',
    content: `GLOSSARIO COMERCIAL - Receita
Sinonimos: receita liquida, vendas liquidas, faturamento liquido
Coluna: receita_liquida
Regra: SUM(receita_liquida)
Cuidado: nao usar valor_bruto quando a pergunta pedir receita`,
    created_at: '2026-02-20T10:00:00Z'
  },
  {
    id: 'doc-002',
    type: 'documentation',
    name: 'Glossario - Produto',
    content: `GLOSSARIO COMERCIAL - Produto
Sinonimos: item, SKU, solucao, oferta
Coluna: produto
Use categoria_produto e segmento_produto para agrupamentos comerciais`,
    created_at: '2026-02-20T10:05:00Z'
  },
  {
    id: 'doc-003',
    type: 'documentation',
    name: 'Ontologia - Margem',
    content: `CONCEITO DERIVADO - Margem
Definicao: percentual de lucro sobre a receita liquida
Regra: (SUM(lucro) / NULLIF(SUM(receita_liquida), 0)) * 100
Uso: analises de rentabilidade por produto, cliente, canal ou vendedor`,
    created_at: '2026-02-22T14:00:00Z'
  },
  {
    id: 'doc-004',
    type: 'documentation',
    name: 'Sinonimos do SemanticDictionary',
    content: `SINONIMOS (Term -> TargetRef)
- produto -> produto
- categoria -> categoria_produto
- segmento -> segmento_produto
- cliente -> cliente
- porte -> porte_cliente
- setor -> setor_cliente
- canal -> canal
- vendedor -> vendedor
- receita -> receita_liquida
- margem -> lucro / receita_liquida`,
    created_at: '2026-02-25T09:30:00Z'
  }
])

const expandedId = ref<string | null>(null)
const filterType = ref<'all' | 'ddl' | 'sql' | 'documentation'>('all')
const searchQuery = ref('')
const showAddModal = ref(false)
const confirmWipe = ref(false)
const wipingInProgress = ref(false)
const itemToDelete = ref<TrainingItem | null>(null)

const filteredItems = computed(() => {
  let items = trainingItems.value
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

const stats = computed(() => ({
  ddl: trainingItems.value.filter(i => i.type === 'ddl').length,
  sql: trainingItems.value.filter(i => i.type === 'sql').length,
  doc: trainingItems.value.filter(i => i.type === 'documentation').length,
  total: trainingItems.value.length
}))

function handleToggle(id: string) {
  expandedId.value = expandedId.value === id ? null : id
}

function handleRemove(id: string) {
  trainingItems.value = trainingItems.value.filter(i => i.id !== id)
  if (expandedId.value === id) expandedId.value = null
}

function requestRemove(item: TrainingItem) {
  itemToDelete.value = item
}

function confirmRemoveItem() {
  if (!itemToDelete.value) return
  handleRemove(itemToDelete.value.id)
  itemToDelete.value = null
}

function handleAdd(data: { type: string; question: string; content: string }) {
  const newItem: TrainingItem = {
    id: `${data.type}-${Date.now()}`,
    type: data.type as TrainingItem['type'],
    name: data.type === 'sql'
      ? data.question.substring(0, 60)
      : data.content.substring(0, 60),
    content: data.content,
    question: data.type === 'sql' ? data.question : undefined,
    created_at: new Date().toISOString()
  }
  trainingItems.value.unshift(newItem)
  showAddModal.value = false
}

async function handleWipeRetrain() {
  wipingInProgress.value = true
  // Simulate wipe & retrain
  await new Promise(resolve => setTimeout(resolve, 2500))
  wipingInProgress.value = false
  confirmWipe.value = false
}

// ════════════════════════════════════════════════════
// TAB 2: PREPARAR DADOS (US-023)
// ════════════════════════════════════════════════════

// Todos os campos de vFactPagamentoResolved
interface FactPagamentoRow {
  FatoPagamentoKey: string
  IdPagamentoOriginalFK: string
  ValorAgendado: string
  ValorPago: string
  ValorBonus: string
  ValorOriginal: string
  IdPessoaNK: string
  Sexo: string
  Raca: string
  Bairro: string
  Municipio: string
  UfLocalidade: string
  Sigla: string
  DescricaoModalidade: string
  IdProjetoNK: string
  NomeProjeto: string
  OrcamentoTotal: string
  OrcamentoBolsa: string
  NomeEdital: string
  AreaTecnica: string
  DescricaoStatus: string
  DataPagamento: string
  Ano: string
  Mes: string
  NomeMes: string
  Trimestre: string
}

interface EtlDiffRow {
  tableName: string
  rowId: string
  type: 'updated' | 'inserted' | 'deleted'
  changedFields: string[]
  before: FactPagamentoRow | null
  after: FactPagamentoRow | null
}

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
  rows: EtlDiffRow[]
  runs: EtlTriggeredRun[]
}

const etlSyncing = ref(false)
const etlDispatchLocked = ref(false)
const etlPollingHandle = ref<number | null>(null)
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

// Campos exibidos na comparacao (label: chave)
const factFields: { label: string; key: keyof FactPagamentoRow }[] = [
  { label: 'FatoPagamentoKey',      key: 'FatoPagamentoKey' },
  { label: 'IdPagamentoOriginalFK', key: 'IdPagamentoOriginalFK' },
  { label: 'ValorAgendado',         key: 'ValorAgendado' },
  { label: 'ValorPago',             key: 'ValorPago' },
  { label: 'ValorBonus',            key: 'ValorBonus' },
  { label: 'ValorOriginal',         key: 'ValorOriginal' },
  { label: 'IdPessoaNK',            key: 'IdPessoaNK' },
  { label: 'Sexo',                  key: 'Sexo' },
  { label: 'Raca',                  key: 'Raca' },
  { label: 'Bairro',                key: 'Bairro' },
  { label: 'Municipio',             key: 'Municipio' },
  { label: 'UfLocalidade',          key: 'UfLocalidade' },
  { label: 'Sigla',                 key: 'Sigla' },
  { label: 'DescricaoModalidade',   key: 'DescricaoModalidade' },
  { label: 'IdProjetoNK',           key: 'IdProjetoNK' },
  { label: 'NomeProjeto',           key: 'NomeProjeto' },
  { label: 'OrcamentoTotal',        key: 'OrcamentoTotal' },
  { label: 'OrcamentoBolsa',        key: 'OrcamentoBolsa' },
  { label: 'NomeEdital',            key: 'NomeEdital' },
  { label: 'AreaTecnica',           key: 'AreaTecnica' },
  { label: 'DescricaoStatus',       key: 'DescricaoStatus' },
  { label: 'DataPagamento',         key: 'DataPagamento' },
  { label: 'Ano',                   key: 'Ano' },
  { label: 'Mes',                   key: 'Mes' },
  { label: 'NomeMes',               key: 'NomeMes' },
  { label: 'Trimestre',             key: 'Trimestre' },
]

const etlLogs = ref<EtlLog[]>((() => {
  try {
    const saved = localStorage.getItem('oraculo_esx_etl_logs')
    return saved ? JSON.parse(saved) : []
  } catch {
    return []
  }
})())

watch(etlLogs, (newVal) => {
  localStorage.setItem('oraculo_esx_etl_logs', JSON.stringify(newVal))
}, { deep: true })

function releaseEtlLock() {
  etlDispatchLocked.value = false
  etlSyncing.value = false
}

function stopEtlPolling() {
  if (etlPollingHandle.value !== null) {
    window.clearTimeout(etlPollingHandle.value)
    etlPollingHandle.value = null
  }
}

async function handleSync() {
  if (etlDispatchLocked.value || hasRunningEtl.value) {
    return
  }

  etlDispatchLocked.value = true
  stopEtlPolling()
  etlSyncing.value = true
  try {
    const response = await httpClient.post(
      '/api/admin/data/bootstrap',
      {},
      { timeout: 1000 * 900 }
    )

    // Desktop: uma etapa por contexto da pasta de dados (validação no dados.db e indexação do RAG).
    const data = response.data || {}
    const contextos: any[] = data.contextos || []
    const triggeredAt = new Date().toISOString()
    const stages: EtlTriggeredRun[] = contextos.map((ctx) => ({
      dagId: ctx.slug || ctx.pasta,
      label: ctx.nome || ctx.pasta,
      dagRunId: !ctx.ativo
        ? (ctx.erros || []).join(' ')
        : ctx.indexado
          ? `${ctx.rag_itens} itens de RAG, ${ctx.valores} valores`
          : 'válido; sem indexação (falta a chave da Mistral)',
      state: ctx.ativo && ctx.indexado ? 'success' : ctx.ativo ? 'pending' : 'failed',
      triggeredAt
    }))
    const validos = contextos.filter((ctx) => ctx.ativo).length

    etlLogs.value.unshift({
      id: Date.now(),
      timestamp: triggeredAt,
      message: data.chave_configurada
        ? `${validos} de ${contextos.length} contexto(s) válidos e indexados.`
        : `${validos} de ${contextos.length} contexto(s) válidos. Configure a chave da Mistral para indexar o RAG.`,
      status: validos === contextos.length ? 'success' : 'error',
      totalRecords: contextos.length,
      changedRecords: validos,
      rows: [],
      runs: stages
    })

    releaseEtlLock()
  } catch (error: any) {
    const newLog: EtlLog = {
      id: Date.now(),
      timestamp: new Date().toISOString(),
      message: error?.response?.data?.detail || error?.response?.data?.error || error?.message || 'Falha ao preparar dados',
      status: 'error',
      totalRecords: 0,
      changedRecords: 0,
      rows: [],
      runs: []
    }
    etlLogs.value.unshift(newLog)
    releaseEtlLock()
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
    const res = await httpClient.get('/api/admin/system-status')
    if (res.data) {
      services.value = (res.data.services || []).map((s: any) => ({
        name: s.name,
        status: s.status,
        url: s.url,
        latency: s.latency_ms ? `${s.latency_ms}ms` : '-'
      }))
      systemStats.value = res.data.systemStats || systemStats.value
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
    const response = await httpClient.get('/api/chat/query-executions', { params })
    queryExecutions.value = Array.isArray(response.data) ? response.data : []
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
    const { data } = await httpClient.post('/api/admin/trainings', {
      type: 'sql',
      question: row.question_original || 'Consulta auditada',
      content: row.generated_sql
    })
    trainingItems.value.unshift(data)
    filterType.value = 'sql'
    expandedId.value = data.id
    activeTab.value = 'governance'
  } catch (err) {
    auditError.value = 'Não foi possível promover a consulta para treinamento.'
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
}, { immediate: true })

onBeforeUnmount(() => {
  stopEtlPolling()
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
            Gerencie o modelo de inteligência artificial, prepare dados analíticos e monitore a integridade do ecossistema ORACULO-ESX.
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
              <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-elevated border border-border-standard">
                <Brain class="h-6 w-6 text-text-muted" stroke-width="1.5" />
              </div>
            </div>
          </div>

          <div class="premium-card p-6">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">Estruturas DDL</p>
                <p class="mt-2 text-4xl font-semibold tracking-[-0.04em] text-text-primary">{{ stats.ddl }}</p>
              </div>
              <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-elevated border border-border-standard">
                <Database class="h-6 w-6 text-text-muted" stroke-width="1.5" />
              </div>
            </div>
          </div>

          <div class="premium-card p-6">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">Queries SQL</p>
                <p class="mt-2 text-4xl font-semibold tracking-[-0.04em] text-text-primary">{{ stats.sql }}</p>
              </div>
              <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-elevated border border-border-standard">
                <Code2 class="h-6 w-6 text-text-muted" stroke-width="1.5" />
              </div>
            </div>
          </div>

          <div class="premium-card p-6">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">Documentação</p>
                <p class="mt-2 text-4xl font-semibold tracking-[-0.04em] text-text-primary">{{ stats.doc }}</p>
              </div>
              <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-elevated border border-border-standard">
                <FileText class="h-6 w-6 text-text-muted" stroke-width="1.5" />
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
                class="w-full rounded-lg border border-border-subtle bg-surface/30 py-2.5 pl-10 pr-4 text-sm text-text-primary placeholder-text-muted transition-all focus:border-accent/50 focus:bg-surface/50 focus:outline-none focus:ring-4 focus:ring-accent/5"
              />
            </div>

            <!-- Filter -->
            <div class="flex items-center gap-1 rounded-lg bg-surface/30 p-1 border border-border-subtle">
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
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface/20'
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
              @click="showAddModal = true"
            >
              <Plus class="h-4 w-4" stroke-width="2.5" />
              Novo Treinamento
            </button>
            <button
              :disabled="wipingInProgress"
              class="btn-secondary flex items-center gap-2 text-red-400 border-red-900/30 hover:border-red-500/50 hover:bg-red-500/5"
              @click="confirmWipe = true"
            >
              <Zap class="h-4 w-4" />
              Wipe & Retrain
            </button>
          </div>
        </div>

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
            v-if="filteredItems.length === 0"
            class="premium-card flex flex-col items-center justify-center gap-3 py-16 text-center"
          >
            <Brain class="h-12 w-12 text-text-muted opacity-40" />
            <p class="text-sm font-medium text-text-secondary">Nenhum item de treinamento encontrado</p>
            <p class="text-xs text-text-muted">Ajuste os filtros ou adicione um novo treinamento</p>
          </div>
        </div>

        <!-- Add Training Modal -->
        <AddTrainingModal
          :open="showAddModal"
          @close="showAddModal = false"
          @submit="handleAdd"
        />

        <!-- Wipe Confirmation Modal -->
        <ConfirmModal
          :is-open="confirmWipe"
          title="Atenção Crítica: Wipe & Retrain"
          message="Esta ação irá reconstruir os dados vetoriais no pgvector a partir dos arquivos base. Treinamentos manuais não persistidos serão perdidos. Deseja continuar?"
          confirm-text="Wipe & Retrain"
          @confirm="handleWipeRetrain"
          @close="confirmWipe = false"
        />

        <!-- Item Delete Confirmation Modal -->
        <ConfirmModal
          :is-open="!!itemToDelete"
          title="Excluir treinamento"
          :message="itemToDelete ? `Tem certeza que deseja remover '${itemToDelete.name}'? Esta ação não pode ser desfeita.` : ''"
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
              <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-elevated border border-border-standard">
                <Code2 class="h-6 w-6 text-text-muted" stroke-width="1.5" />
              </div>
            </div>
          </div>

          <div class="premium-card p-6">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">Consultas Válidas</p>
                <p class="mt-2 text-4xl font-semibold tracking-[-0.04em] text-text-primary">{{ auditStats.valid }}</p>
              </div>
              <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-elevated border border-border-standard">
                <CheckCircle2 class="h-6 w-6 text-text-muted" stroke-width="1.5" />
              </div>
            </div>
          </div>

          <div class="premium-card p-6">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted">Consultas Inválidas</p>
                <p class="mt-2 text-4xl font-semibold tracking-[-0.04em] text-text-primary">{{ auditStats.invalid }}</p>
              </div>
              <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-elevated border border-border-standard">
                <XCircle class="h-6 w-6 text-text-muted" stroke-width="1.5" />
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
                class="w-full rounded-lg border border-border-subtle bg-surface/30 py-2.5 pl-10 pr-4 text-sm text-text-primary placeholder-text-muted transition-all focus:border-accent/50 focus:bg-surface/50 focus:outline-none focus:ring-4 focus:ring-accent/5"
              />
            </div>

            <!-- Filter -->
            <div class="flex items-center gap-1 rounded-lg bg-surface/30 p-1 border border-border-subtle">
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
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface/20'
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
                <h2 class="text-xl font-semibold text-text-primary">Carregar Contextos</h2>
                <p class="max-w-xl text-sm text-text-secondary leading-relaxed">
                  Valida os contextos da pasta de dados contra o dados.db e, com a chave da Mistral configurada,
                  gera o RAG (esquema, regras e exemplos) e o índice de valores de cada um.
                </p>
              </div>
            </div>
            <button
              :disabled="hasRunningEtl"
              :class="[
                'btn-primary flex shrink-0 items-center gap-3 px-10 py-4 text-base shadow-xl active:scale-95',
                hasRunningEtl ? 'opacity-50 cursor-not-allowed' : ''
              ]"
              @click="handleSync"
            >
              <Loader2 v-if="hasRunningEtl" class="h-5 w-5 animate-spin" />
              <RefreshCw v-else class="h-5 w-5" stroke-width="2.5" />
              {{ hasRunningEtl ? 'Preparando...' : 'Preparar Dados' }}
            </button>
          </div>
        </div>

        <!-- Reports accordion -->
        <div class="premium-card overflow-hidden">
          <div class="flex flex-col gap-6 border-b border-border-subtle bg-surface/20 px-8 py-6 md:flex-row md:items-center md:justify-between backdrop-blur-sm">
            <div class="flex items-center gap-3">
              <div class="p-2 bg-accent/10 rounded-lg">
                <Clock class="h-5 w-5 text-accent" stroke-width="2" />
              </div>
              <h2 class="text-lg font-semibold text-text-primary">Logs de Preparação</h2>
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
                  <span v-if="log.changedRecords > 0" class="text-xs text-slate-400 dark:text-slate-500">
                    {{ log.changedRecords.toLocaleString('pt-BR') }} linhas na view
                  </span>
                  <span v-else-if="log.runs.length > 0" class="text-xs text-slate-400 dark:text-slate-500">
                    {{ log.runs.length }} etapa{{ log.runs.length > 1 ? 's' : '' }}
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
                    A preparação falhou. Verifique a conectividade com o PostgreSQL e a configuração do Gemini.
                  </div>

                  <!-- Sucesso -->
                  <template v-else>
                    <div v-if="log.runs.length > 0" class="mb-4 space-y-3">
                      <div class="rounded-lg border border-border-subtle bg-white/80 p-4 dark:bg-slate-900/60">
                        <p class="text-sm font-semibold text-slate-900 dark:text-white">
                          {{ log.status === 'running' ? 'Preparação em andamento' : 'Preparação concluída' }}
                        </p>
                        <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          {{ log.status === 'running'
                            ? 'Aguarde a conclusão das etapas de schema, dados, treinamento e embeddings.'
                            : 'As etapas abaixo registram o que foi aplicado no banco e na base de conhecimento.'
                          }}
                        </p>
                      </div>

                      <div
                        v-for="run in log.runs"
                        :key="run.dagRunId"
                        class="rounded-lg border border-border-subtle bg-white px-4 py-3 dark:bg-slate-900"
                      >
                        <div class="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                          <div>
                            <p class="text-sm font-semibold text-slate-900 dark:text-white">{{ run.label }}</p>
                            <p class="mt-1 font-mono text-xs text-slate-500 dark:text-slate-400">{{ run.dagId }}</p>
                          </div>
                          <span class="text-xs font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400">
                            {{ run.state }}
                          </span>
                        </div>
                        <div class="mt-3 grid gap-2 text-xs text-slate-500 dark:text-slate-400 md:grid-cols-2">
                          <p><span class="font-semibold text-slate-700 dark:text-slate-200">Detalhe:</span> <span class="font-mono">{{ run.dagRunId }}</span></p>
                          <p><span class="font-semibold text-slate-700 dark:text-slate-200">Executado em:</span> <span class="font-mono">{{ run.triggeredAt || '-' }}</span></p>
                        </div>
                      </div>
                    </div>

                    <div v-if="log.rows.length > 0" class="mb-4 flex flex-wrap gap-8 text-sm">
                      <div class="flex items-center gap-2">
                        <span class="text-slate-500 dark:text-slate-400">Total de registros analisados:</span>
                        <span class="font-bold text-slate-900 dark:text-white">{{ log.totalRecords.toLocaleString('pt-BR') }}</span>
                      </div>
                      <div class="flex items-center gap-2">
                        <span class="text-slate-500 dark:text-slate-400">Linhas alteradas:</span>
                        <span class="font-bold text-slate-900 dark:text-white">{{ log.changedRecords }}</span>
                      </div>
                    </div>

                    <div v-if="log.rows.length > 0" class="max-h-[480px] space-y-3 overflow-y-auto pr-1">
                      <div
                        v-for="diffRow in log.rows"
                        :key="diffRow.tableName + diffRow.rowId"
                        class="overflow-hidden rounded border border-gray-200 bg-white dark:border-white/10 dark:bg-slate-900"
                      >
                        <!-- Cabecalho da linha -->
                        <div
                          :class="[
                            'flex items-center justify-between border-b px-4 py-2.5',
                            diffRow.type === 'inserted'
                              ? 'border-emerald-200 bg-emerald-50 dark:border-emerald-900/50 dark:bg-emerald-950/40'
                              : diffRow.type === 'deleted'
                                ? 'border-red-200 bg-red-50 dark:border-red-900/50 dark:bg-red-950/40'
                                : 'border-gray-200 bg-gray-50 dark:border-white/10 dark:bg-slate-800'
                          ]"
                        >
                          <div class="flex items-center gap-3">
                            <span class="rounded bg-slate-200 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                              {{ diffRow.tableName }}
                            </span>
                            <span class="font-mono text-sm font-semibold text-slate-700 dark:text-slate-100">{{ diffRow.rowId }}</span>
                          </div>
                          <span
                            :class="[
                              'text-xs font-semibold uppercase tracking-wider',
                              diffRow.type === 'inserted'
                                ? 'text-emerald-700 dark:text-emerald-400'
                                : diffRow.type === 'deleted'
                                  ? 'text-red-700 dark:text-red-400'
                                  : 'text-slate-500 dark:text-slate-400'
                            ]"
                          >
                            {{ diffRow.type === 'inserted' ? '+ Inserido' : diffRow.type === 'deleted' ? '− Removido' : 'Atualizado' }}
                            <span v-if="diffRow.changedFields.length > 0"> &middot; {{ diffRow.changedFields.length }} campo(s)</span>
                          </span>
                        </div>

                        <!-- Comparacao lado a lado -->
                        <div class="grid grid-cols-2 divide-x divide-gray-200 dark:divide-white/10">
                          <!-- ANTES -->
                          <div>
                            <div class="border-b border-gray-200 bg-gray-100/60 px-4 py-2 dark:border-white/10 dark:bg-slate-800/80">
                              <span class="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-300">Antes</span>
                            </div>
                            <div class="divide-y divide-gray-100 dark:divide-white/5">
                              <template v-if="diffRow.before">
                                <div
                                  v-for="field in factFields"
                                  :key="'b-' + field.key"
                                  :class="[
                                    'flex items-center gap-4 px-4 py-2',
                                    diffRow.type === 'deleted'
                                      ? 'bg-red-50/60 dark:bg-red-900/10'
                                      : (diffRow.type === 'updated' && diffRow.changedFields.includes(field.key))
                                        ? 'border-l-2 border-amber-400 bg-amber-100 dark:bg-amber-900/30'
                                        : ''
                                  ]"
                                >
                                  <span
                                    :class="[
                                      'w-44 shrink-0 text-xs',
                                      diffRow.type === 'deleted'
                                        ? 'font-medium text-red-700 dark:text-red-400'
                                        : (diffRow.type === 'updated' && diffRow.changedFields.includes(field.key))
                                          ? 'font-semibold text-amber-800 dark:text-amber-300'
                                          : 'text-slate-500 dark:text-slate-400'
                                    ]"
                                  >{{ field.label }}</span>
                                  <span
                                    :class="[
                                      'text-xs',
                                      diffRow.type === 'deleted'
                                        ? 'font-medium text-red-900 dark:text-red-300'
                                        : (diffRow.type === 'updated' && diffRow.changedFields.includes(field.key))
                                          ? 'font-semibold text-slate-900 dark:text-white'
                                          : 'text-slate-700 dark:text-slate-200'
                                    ]"
                                  >{{ diffRow.before[field.key] }}</span>
                                </div>
                              </template>
                              <div v-else class="px-4 py-4 text-sm italic text-slate-400 dark:text-slate-500">Registro novo &mdash; sem estado anterior.</div>
                            </div>
                          </div>

                          <!-- DEPOIS -->
                          <div>
                            <div class="border-b border-gray-200 bg-gray-100/60 px-4 py-2 dark:border-white/10 dark:bg-slate-800/80">
                              <span class="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-300">Depois</span>
                            </div>
                            <div class="divide-y divide-gray-100 dark:divide-white/5">
                              <template v-if="diffRow.after">
                                <div
                                  v-for="field in factFields"
                                  :key="'a-' + field.key"
                                  :class="[
                                    'flex items-center gap-4 px-4 py-2',
                                    diffRow.type === 'inserted'
                                      ? 'bg-emerald-50/60 dark:bg-emerald-900/10'
                                      : (diffRow.type === 'updated' && diffRow.changedFields.includes(field.key))
                                        ? 'border-l-2 border-amber-400 bg-amber-100 dark:bg-amber-900/30'
                                        : ''
                                  ]"
                                >
                                  <span
                                    :class="[
                                      'w-44 shrink-0 text-xs',
                                      diffRow.type === 'inserted'
                                        ? 'font-medium text-emerald-700 dark:text-emerald-400'
                                        : (diffRow.type === 'updated' && diffRow.changedFields.includes(field.key))
                                          ? 'font-semibold text-amber-800 dark:text-amber-300'
                                          : 'text-slate-500 dark:text-slate-400'
                                    ]"
                                  >{{ field.label }}</span>
                                  <span
                                    :class="[
                                      'text-xs',
                                      diffRow.type === 'inserted'
                                        ? 'font-medium text-emerald-900 dark:text-emerald-300'
                                        : (diffRow.type === 'updated' && diffRow.changedFields.includes(field.key))
                                          ? 'font-semibold text-slate-900 dark:text-white'
                                          : 'text-slate-700 dark:text-slate-200'
                                    ]"
                                  >{{ diffRow.after[field.key] }}</span>
                                </div>
                              </template>
                              <div v-else class="px-4 py-4 text-sm italic text-slate-400 dark:text-slate-500">Registro removido.</div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <p v-if="log.rows.length === 0" class="rounded border border-dashed border-border-subtle bg-white/70 px-4 py-3 text-sm text-slate-500 dark:bg-slate-900/50 dark:text-slate-400">
                      O detalhamento por registros ainda nao esta disponivel nesta tela. Quando necessario, ele sera obtido por consultas ao banco.
                    </p>

                    <p v-if="log.changedRecords > log.rows.length" class="mt-3 text-center text-xs text-slate-400">
                      Exibindo {{ log.rows.length }} de {{ log.changedRecords }} linhas registradas.
                    </p>
                  </template>
                </div>
              </Transition>
            </div>
          </div>
          <div v-else class="flex flex-col items-center justify-center py-12 text-center text-slate-500">
            <Calendar class="mb-3 h-10 w-10 text-slate-300 dark:text-slate-600" />
            <p>Nenhum preparo de dados encontrado para o filtro aplicado.</p>
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
            <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-elevated border border-border-standard mb-6">
              <Server class="h-6 w-6 text-text-muted" stroke-width="1.5" />
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
            <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-elevated border border-border-standard mb-6">
              <HardDrive class="h-6 w-6 text-text-muted" stroke-width="1.5" />
            </div>
            <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-text-muted mb-2">pgvector</p>
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
            <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-elevated border border-border-standard mb-6">
              <Brain class="h-6 w-6 text-text-muted" stroke-width="1.5" />
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
                <span class="text-text-primary">Gemini 3.5 Flash-Lite</span>
              </div>
              <div class="flex items-center justify-between text-xs">
                <span class="text-text-secondary">Vector Store</span>
                <span class="text-text-primary">pgvector</span>
              </div>
            </div>
          </div>
        </div>
      </template>

    </div>
  </div>
</template>
