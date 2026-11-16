<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import axios from 'axios'
import { AlertCircle, BarChart2, ChevronLeft, ChevronRight, Database, Layers, Loader2, RefreshCw, Table2 } from 'lucide-vue-next'
import httpClient from '@/common/api/httpClient'
import { useContextos } from '@/common/composables/useContextos'
import FilterPanel from '../components/FilterPanel.vue'
import DataTable from '../components/DataTable.vue'
import DataChart from '../components/DataChart.vue'
import type { DataRelation, ExplorerResult } from '../types'

const { contextos, selectedId, selected, loadContextos, select } = useContextos()
const ready = ref(false)
const catalog = ref<DataRelation[]>([])
const catalogLoading = ref(true)
const catalogError = ref('')
const rowsError = ref('')
const loading = ref(false)
const tableName = ref('')
const kind = ref('all')
const search = ref('')
const filterColumn = ref('')
const filterValue = ref('')
const sort = ref('')
const direction = ref<'asc' | 'desc'>('asc')
const page = ref(1)
const pageSize = ref(25)
const mode = ref<'table' | 'chart'>('table')
const groupBy = ref('')
const shownColumns = ref<string[]>([])
const result = ref<ExplorerResult | null>(null)
let catalogController: AbortController | undefined
let rowsController: AbortController | undefined
let timer: ReturnType<typeof setTimeout> | undefined
let disposed = false

const categories = [
  { key: 'all', label: 'Todas' },
  { key: 'fact', label: 'Fatos' },
  { key: 'dimension', label: 'Dimensões' },
  { key: 'entity', label: 'Entidades' }
]
const kindLabels = { fact: 'Fato', dimension: 'Dimensão', entity: 'Entidade' }
const filteredTables = computed(() => catalog.value.filter(table => kind.value === 'all' || table.kind === kind.value))
const currentTable = computed(() => catalog.value.find(table => table.name === tableName.value))
const visibleColumns = computed(() => currentTable.value?.columns.filter(column => shownColumns.value.includes(column.name)) ?? [])
const pages = computed(() => Math.max(1, Math.ceil((result.value?.total ?? 0) / pageSize.value)))
const firstRecord = computed(() => result.value?.total ? (result.value.page - 1) * result.value.page_size + 1 : 0)
const lastRecord = computed(() => firstRecord.value + (result.value?.rows.length ?? 0) - (firstRecord.value ? 1 : 0))
const controlClass = 'rounded-lg border border-border-standard bg-surface px-3 py-2 text-sm text-primary outline-none focus:border-accent focus:ring-1 focus:ring-accent'

function errorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error) && typeof error.response?.data?.detail === 'string') return error.response.data.detail
  return fallback
}

async function fetchCatalog() {
  catalogController?.abort()
  rowsController?.abort()
  const controller = new AbortController()
  catalogController = controller
  catalog.value = []
  tableName.value = ''
  kind.value = 'all'
  catalogError.value = ''
  catalogLoading.value = true
  try {
    if (!selectedId.value) return
    const { data } = await httpClient.get<{ tables: DataRelation[] }>('/api/explorer/tables', {
      params: { contexto_id: selectedId.value }, signal: controller.signal
    })
    if (controller.signal.aborted) return
    catalog.value = data.tables
    tableName.value = data.tables.find(table => table.available)?.name ?? ''
  } catch (error) {
    if (!controller.signal.aborted) catalogError.value = errorMessage(error, 'Não foi possível carregar as tabelas. Verifique a conexão com o backend local.')
  } finally {
    if (!controller.signal.aborted) catalogLoading.value = false
  }
}

async function initialize() {
  catalogLoading.value = true
  catalogError.value = ''
  try {
    await loadContextos()
    if (disposed) return
    ready.value = true
    await fetchCatalog()
  } catch (error) {
    catalogError.value = errorMessage(error, 'Não foi possível carregar os contextos. Verifique a conexão com o backend local.')
    catalogLoading.value = false
  }
}

async function fetchRows() {
  if (!selectedId.value || !currentTable.value?.available) return
  const controller = new AbortController()
  rowsController = controller
  loading.value = true
  rowsError.value = ''
  try {
    const { data } = await httpClient.get<ExplorerResult>('/api/explorer/rows', {
      params: {
        contexto_id: selectedId.value, table: tableName.value,
        search: search.value, filter_column: filterColumn.value, filter_value: filterValue.value,
        sort: sort.value, direction: direction.value, page: page.value, page_size: pageSize.value,
        group_by: mode.value === 'chart' ? groupBy.value : ''
      },
      signal: controller.signal
    })
    if (!controller.signal.aborted) {
      result.value = data
      page.value = data.page
    }
  } catch (error) {
    if (!controller.signal.aborted) rowsError.value = errorMessage(error, 'Não foi possível consultar os registros. Tente novamente.')
  } finally {
    if (!controller.signal.aborted) loading.value = false
  }
}

function scheduleRows() {
  clearTimeout(timer)
  rowsController?.abort()
  result.value = null
  rowsError.value = ''
  loading.value = !!currentTable.value?.available
  if (loading.value) timer = setTimeout(fetchRows, 250)
}

function clearFilters() {
  search.value = ''
  filterColumn.value = ''
  filterValue.value = ''
}

function toggleColumn(name: string) {
  if (shownColumns.value.includes(name)) {
    if (shownColumns.value.length > 1) shownColumns.value = shownColumns.value.filter(column => column !== name)
  } else shownColumns.value = [...shownColumns.value, name]
}

function changeSort(column: string) {
  direction.value = sort.value === column && direction.value === 'asc' ? 'desc' : 'asc'
  sort.value = column
}

watch(selectedId, () => { if (ready.value) void fetchCatalog() }, { flush: 'sync' })
watch(kind, () => {
  if (!filteredTables.value.some(table => table.name === tableName.value)) {
    tableName.value = filteredTables.value.find(table => table.available)?.name ?? ''
  }
})
watch(currentTable, table => {
  clearFilters()
  sort.value = table?.columns[0]?.name ?? ''
  direction.value = 'asc'
  groupBy.value = table?.columns.find(column => /TEXT|CHAR/i.test(column.type))?.name ?? table?.columns[0]?.name ?? ''
  shownColumns.value = table?.columns.map(column => column.name) ?? []
  page.value = 1
})
watch(filterColumn, () => { filterValue.value = '' })
watch([search, filterColumn, filterValue, sort, direction, pageSize], () => { page.value = 1 })
watch([tableName, search, filterColumn, filterValue, sort, direction, page, pageSize, mode, groupBy], scheduleRows, { flush: 'post' })

onMounted(initialize)
onBeforeUnmount(() => {
  disposed = true
  clearTimeout(timer)
  catalogController?.abort()
  rowsController?.abort()
})
</script>

<template>
  <div class="min-h-full bg-primary p-4 md:p-8 lg:p-10">
    <div class="mx-auto max-w-[1600px] space-y-6">
      <header class="flex flex-wrap items-end justify-between gap-5">
        <div>
          <h1 class="text-3xl font-semibold text-primary">
            Explorar dados
          </h1>
          <p class="mt-2 max-w-2xl text-sm text-text-secondary">
            Consulte fatos, dimensões e entidades de pesquisa e extensão do Campus Serra.
          </p>
        </div>
        <div class="flex w-full items-end gap-2 sm:w-auto">
          <div class="min-w-0 flex-1 sm:w-64">
            <label for="explorer-context" class="mb-1.5 block text-xs font-medium text-text-secondary">
              Contexto de dados
            </label>
            <select
              id="explorer-context"
              :value="selectedId ?? ''"
              :class="[controlClass, 'w-full']"
              @change="select(($event.target as HTMLSelectElement).value || null)"
            >
              <option value="">
                Selecione um contexto
              </option>
              <option v-for="context in contextos" :key="context.id" :value="context.id">
                {{ context.name }}
              </option>
            </select>
          </div>
          <button
            class="btn-secondary p-2.5 disabled:opacity-50"
            aria-label="Recarregar contextos e tabelas"
            title="Recarregar contextos e tabelas"
            :disabled="catalogLoading"
            @click="initialize"
          >
            <RefreshCw :size="18" :class="{ 'animate-spin': catalogLoading }" aria-hidden="true" />
          </button>
        </div>
      </header>
      <div
        v-if="catalogError"
        role="alert"
        class="rounded-xl border border-red-300 bg-surface p-5 text-sm text-error"
      >
        <AlertCircle :size="18" class="mb-2" aria-hidden="true" />
        <p>
          {{ catalogError }}
        </p>
        <button class="btn-secondary mt-3" @click="initialize">
          Tentar novamente
        </button>
      </div>
      <div
        v-else-if="catalogLoading"
        role="status"
        class="flex items-center gap-3 rounded-xl border border-border-subtle bg-surface p-8 text-sm text-text-secondary"
      >
        <Loader2 :size="20" class="animate-spin" aria-hidden="true" />
        Carregando tabelas…
      </div>
      <div v-else-if="!selectedId" class="rounded-xl border border-border-subtle bg-surface p-8">
        <Database :size="32" class="mb-4 text-accent" aria-hidden="true" />
        <h2 class="text-lg">
          {{ contextos.length ? 'Selecione um contexto para consultar os dados' : 'Nenhum contexto carregado' }}
        </h2>
        <p class="mt-2 text-sm text-text-secondary">
          {{ contextos.length ? 'Escolha o conjunto de dados no seletor acima.' : 'Carregue os contextos do modelo unificado em Administração para disponibilizar as tabelas.' }}
        </p>
        <RouterLink v-if="!contextos.length" to="/admin" class="btn-primary mt-5 inline-block">
          Abrir Administração
        </RouterLink>
      </div>
      <template v-else>
        <p v-if="selected?.description" class="text-sm text-text-secondary">
          {{ selected.description }}
        </p>
        <div class="grid items-start gap-5 xl:grid-cols-[240px_minmax(0,1fr)]">
          <aside
            class="overflow-hidden rounded-xl border border-border-subtle bg-surface"
            aria-label="Catálogo de tabelas"
          >
            <div class="border-b border-border-subtle p-4">
              <h2 class="flex items-center gap-2 text-sm font-semibold">
                <Layers :size="17" class="text-accent" aria-hidden="true" />
                Tabelas do contexto
              </h2>
              <div class="mt-4 flex flex-wrap gap-1.5" role="group" aria-label="Tipo de tabela">
                <button
                  v-for="category in categories"
                  :key="category.key"
                  :aria-pressed="kind === category.key"
                  :class="['rounded-md border px-2 py-1.5 text-xs transition-colors', kind === category.key ? 'border-accent bg-accent/10 text-accent' : 'border-border-subtle text-text-secondary hover:bg-surface-elevated']"
                  @click="kind = category.key"
                >
                  {{ category.label }}
                  <span class="ml-1 opacity-70">
                    {{ catalog.filter(table => category.key === 'all' || table.kind === category.key).length }}
                  </span>
                </button>
              </div>
            </div>
            <div class="max-h-[520px] space-y-1 overflow-y-auto p-2">
              <p v-if="!filteredTables.length" class="p-4 text-sm text-text-muted">
                Nenhuma tabela deste tipo no contexto.
              </p>
              <button
                v-for="table in filteredTables"
                :key="table.name"
                :disabled="!table.available"
                :aria-pressed="tableName === table.name"
                :class="['w-full rounded-lg border p-3 text-left transition-colors disabled:opacity-50', tableName === table.name ? 'border-accent/30 bg-accent/10' : 'border-transparent hover:bg-surface-elevated']"
                @click="tableName = table.name"
              >
                <span class="block break-words text-sm font-medium text-primary">
                  {{ table.label }}
                </span>
                <span class="mt-1 block text-xs text-text-muted">
                  {{ kindLabels[table.kind] }}
                  ·
                  {{ table.columns.length }}
                  colunas
                </span>
                <span v-if="!table.available" class="mt-1 block text-xs text-error">
                  Indisponível. Recarregue o contexto.
                </span>
              </button>
            </div>
          </aside>
          <section v-if="currentTable" class="min-w-0 space-y-4" aria-label="Consulta da tabela">
            <div>
              <h2 class="break-words text-xl font-semibold">
                {{ currentTable.label }}
              </h2>
              <p v-if="currentTable.description" class="mt-1.5 text-sm text-text-secondary">
                {{ currentTable.description }}
              </p>
              <p
                v-if="currentTable.label !== currentTable.name"
                class="mt-2 break-all font-mono text-xs text-text-muted"
              >
                {{ currentTable.name }}
              </p>
            </div>
            <details class="rounded-xl border border-border-subtle bg-surface p-4">
              <summary class="cursor-pointer text-sm font-medium text-text-secondary">
                Estrutura e colunas visíveis
              </summary>
              <div class="mt-4 flex flex-wrap gap-2">
                <label
                  v-for="column in currentTable.columns"
                  :key="column.name"
                  class="flex min-w-0 cursor-pointer items-center gap-2 rounded-lg border border-border-subtle px-3 py-2 text-xs"
                >
                  <input
                    type="checkbox"
                    class="accent-accent"
                    :checked="shownColumns.includes(column.name)"
                    :disabled="shownColumns.length === 1 && shownColumns.includes(column.name)"
                    @change="toggleColumn(column.name)"
                  />
                  <span class="break-all text-primary">
                    {{ column.name }}
                    <span class="text-text-muted">
                      {{ column.type || 'tipo não declarado' }}
                    </span>
                  </span>
                </label>
              </div>
            </details>
            <div class="overflow-hidden rounded-xl border border-border-subtle bg-surface shadow-sm">
              <div
                class="flex flex-wrap items-center justify-between gap-3 border-b border-border-subtle p-4"
              >
                <p class="text-sm text-text-secondary" role="status" aria-live="polite">
                  {{ loading ? 'Consultando registros…' : result ? `${result.total.toLocaleString('pt-BR')} registros encontrados` : 'Consulta de registros' }}
                </p>
                <div
                  class="flex gap-1 rounded-lg bg-surface-elevated p-1"
                  role="group"
                  aria-label="Visualização dos dados"
                >
                  <button
                    :aria-pressed="mode === 'table'"
                    :class="['flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs', mode === 'table' ? 'bg-surface text-accent shadow-sm' : 'text-text-secondary']"
                    @click="mode = 'table'"
                  >
                    <Table2 :size="15" aria-hidden="true" />
                    Tabela
                  </button>
                  <button
                    :aria-pressed="mode === 'chart'"
                    :class="['flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs', mode === 'chart' ? 'bg-surface text-accent shadow-sm' : 'text-text-secondary']"
                    @click="mode = 'chart'"
                  >
                    <BarChart2 :size="15" aria-hidden="true" />
                    Gráfico
                  </button>
                </div>
              </div>
              <FilterPanel
                v-model:search="search"
                v-model:column="filterColumn"
                v-model:value="filterValue"
                :columns="currentTable.columns"
                @clear="clearFilters"
              />
              <div v-if="mode === 'chart'" class="border-b border-border-subtle p-4">
                <label for="explorer-group" class="mr-3 text-sm text-text-secondary">
                  Agrupar por
                </label>
                <select id="explorer-group" v-model="groupBy" :class="[controlClass, 'max-w-full']">
                  <option v-for="column in currentTable.columns" :key="column.name" :value="column.name">
                    {{ column.name }}
                  </option>
                </select>
              </div>
              <div v-if="rowsError" role="alert" class="p-6 text-sm text-error">
                <p>
                  {{ rowsError }}
                </p>
                <button class="btn-secondary mt-3" @click="scheduleRows">
                  Tentar novamente
                </button>
              </div>
              <div
                v-else-if="loading"
                class="flex min-h-56 items-center justify-center gap-2 text-sm text-text-muted"
                role="status"
              >
                <Loader2 :size="20" class="animate-spin" aria-hidden="true" />
                Carregando dados…
              </div>
              <template v-else-if="result">
                <DataTable
                  v-if="mode === 'table'"
                  :rows="result.rows"
                  :columns="visibleColumns"
                  :sort="sort"
                  :direction="direction"
                  @sort="changeSort"
                />
                <DataChart v-else :distribution="result.distribution" :total="result.total" />
                <div
                  v-if="mode === 'table'"
                  class="flex flex-wrap items-center justify-between gap-3 border-t border-border-subtle p-4 text-xs text-text-secondary"
                >
                  <span>
                    {{ firstRecord.toLocaleString('pt-BR') }}
                    –
                    {{ lastRecord.toLocaleString('pt-BR') }}
                    de
                    {{ result.total.toLocaleString('pt-BR') }}
                  </span>
                  <div class="flex flex-wrap items-center gap-3">
                    <label for="explorer-page-size">
                      Por página
                    </label>
                    <select id="explorer-page-size" v-model.number="pageSize" :class="[controlClass, 'py-1']">
                      <option :value="25">
                        25
                      </option>
                      <option :value="50">
                        50
                      </option>
                      <option :value="100">
                        100
                      </option>
                    </select>
                    <span>
                      Página
                      {{ result.page }}
                      de
                      {{ pages }}
                    </span>
                    <button
                      class="rounded-md border border-border-subtle p-1.5 hover:bg-surface-elevated disabled:opacity-35"
                      aria-label="Página anterior"
                      :disabled="page <= 1"
                      @click="page--"
                    >
                      <ChevronLeft :size="16" aria-hidden="true" />
                    </button>
                    <button
                      class="rounded-md border border-border-subtle p-1.5 hover:bg-surface-elevated disabled:opacity-35"
                      aria-label="Próxima página"
                      :disabled="page >= pages"
                      @click="page++"
                    >
                      <ChevronRight :size="16" aria-hidden="true" />
                    </button>
                  </div>
                </div>
              </template>
            </div>
          </section>
          <div
            v-else
            class="rounded-xl border border-border-subtle bg-surface p-8 text-sm text-text-secondary"
          >
            Selecione uma tabela disponível no catálogo para iniciar a consulta.
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
