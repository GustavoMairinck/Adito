<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { BarChart2, Table2, Check, LayoutGrid } from 'lucide-vue-next'

import FilterPanel from '@/modules/dataExplorer/components/FilterPanel.vue'
import ProjectsTable from '@/modules/dataExplorer/components/ProjectsTable.vue'
import ProjectsChart from '@/modules/dataExplorer/components/ProjectsChart.vue'
import httpClient from '@/common/api/httpClient'

const viewMode = ref<'tabela' | 'grafico'>('tabela')
const filtros = reactive({ ano: '', modalidade: '', status: '', area: '', instituicao: '' })
const filtrosDisponiveis = reactive<{ anos: string[]; modalidades: string[]; status: string[]; areas: string[]; instituicoes: string[] }>({
  anos: [],
  modalidades: [],
  status: [],
  areas: [],
  instituicoes: []
})
const projetos = ref<any[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref<string | null>(null)
const debounceTimer = ref<number | undefined>(undefined)

const columns = ref([
  { id: 'projeto', label: 'Produto', visible: true, locked: true },
  { id: 'edital', label: 'Cliente', visible: true, locked: false },
  { id: 'modalidade', label: 'Canal', visible: true, locked: false },
  { id: 'valor', label: 'Receita', visible: true, locked: true },
  { id: 'status', label: 'Porte', visible: true, locked: false },
  { id: 'area', label: 'Categoria', visible: true, locked: false }
])

const toggleColumn = (col: any) => {
  if (!col.locked) col.visible = !col.visible
}

const fetchProjects = async () => {
  loading.value = true
  error.value = null
  try {
    const params = new URLSearchParams()
    Object.entries(filtros).forEach(([k, v]) => {
      if (v) params.append(k, v)
    })
    const { data } = await httpClient.get('/api/projects', { params })
    projetos.value = data?.data || []
    total.value = data?.total || 0
    if (data?.filtros_disponiveis) {
      Object.assign(filtrosDisponiveis, data.filtros_disponiveis)
    }
  } catch {
    error.value = 'Não foi possível carregar os produtos. Verifique o backend.'
  } finally {
    loading.value = false
  }
}

onMounted(fetchProjects)

watch(
  () => ({ ...filtros }),
  () => {
    if (debounceTimer.value) window.clearTimeout(debounceTimer.value)
    debounceTimer.value = window.setTimeout(fetchProjects, 300)
  },
  { deep: true }
)

const handleClear = () => {
  Object.assign(filtros, { ano: '', modalidade: '', status: '', area: '', instituicao: '' })
}

const totalLabel = computed(() =>
  loading.value
    ? 'Carregando...'
    : `${total.value} Produto${total.value !== 1 ? 's' : ''} Encontrado${total.value !== 1 ? 's' : ''}`
)
</script>

<template>
  <div class="min-h-screen bg-primary p-4 md:p-8 lg:p-10">
    <div
      v-motion
      :initial="{ opacity: 0, y: 20 }"
      :enter="{ opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } }"
      class="mx-auto w-full space-y-6"
    >
      <div class="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 class="mb-2 text-3xl font-semibold tracking-[-0.04em] text-primary">Explorar Dados</h1>
          <p class="mb-3 max-w-2xl text-sm leading-relaxed text-text-secondary">
            Utilize os filtros e controles interativos abaixo para realizar buscas aprofundadas ou refinar as análises nos atributos de produtos, clientes, canais e categorias.
          </p>
          <p class="text-sm font-medium text-accent">
            {{ totalLabel }}
          </p>
        </div>

        <div class="flex gap-1 rounded-lg border border-border-subtle bg-surface p-1 shadow-sm">
          <button
            v-for="item in [
              { key: 'tabela', icon: Table2, label: 'Tabela' },
              { key: 'grafico', icon: BarChart2, label: 'Gráfico' }
            ]"
            :key="item.key"
            :class="[
              'flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-all',
              viewMode === item.key
                ? 'bg-white text-accent shadow-sm border border-border-subtle dark:bg-white/[0.08] dark:border-white/[0.05]'
                : 'text-text-secondary hover:bg-black/[0.03] hover:text-text-primary dark:hover:bg-white/[0.03]'
            ]"
            @click="viewMode = item.key as 'tabela' | 'grafico'"
          >
            <component :is="item.icon" :size="16" />
            {{ item.label }}
          </button>
        </div>
      </div>

      <div v-if="viewMode === 'tabela'" class="relative w-full rounded-xl border border-border-subtle bg-surface p-4 shadow-sm">
        <div class="flex flex-col gap-4">
          <div class="flex items-center gap-2 text-text-secondary">
            <LayoutGrid :size="16" />
            <span class="eyebrow">Configurar colunas</span>
          </div>

          <div class="flex flex-wrap gap-2.5">
            <button
              v-for="col in columns"
              :key="col.id"
              :disabled="col.locked"
              :class="[
                'group flex select-none items-center gap-2 rounded-lg border px-4 py-2 text-sm font-semibold transition-all duration-200',
                col.visible
                  ? col.locked
                     ? 'cursor-not-allowed border-gray-100 bg-gray-50 text-gray-400 dark:border-gray-700 dark:bg-gray-800/50 dark:text-gray-500'
                     : 'cursor-pointer border-accent/30 bg-accent/10 text-accent hover:bg-accent/14'
                  : 'cursor-pointer border-gray-200 bg-white text-gray-400 hover:border-gray-300 hover:text-gray-600 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-500 dark:hover:border-gray-600 dark:hover:text-gray-400'
              ]"
              @click="toggleColumn(col)"
            >
              <div
                v-if="!col.locked"
                :class="[
                  'flex h-4 w-4 items-center justify-center rounded transition-colors',
                  col.visible ? 'bg-accent text-white' : 'bg-gray-100 dark:bg-gray-800'
                ]"
              >
                <Check v-if="col.visible" :size="12" stroke-width="3" />
              </div>
              {{ col.label }}
            </button>
          </div>
        </div>
      </div>

      <div class="flex min-h-0 flex-1 flex-col gap-4 lg:flex-row">
        <div class="w-full self-start lg:w-fit">
          <FilterPanel
            :filters="filtros"
            :filters-available="filtrosDisponiveis"
            @update:filters="(val) => Object.assign(filtros, val)"
            @clear="handleClear"
          />
        </div>

        <div v-motion :initial="{ opacity: 0 }" :enter="{ opacity: 1, transition: { delay: 0.1 } }" class="min-w-0 flex-1 space-y-4">
          <div
            v-if="error"
            class="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-600 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400"
          >
            {{ error }}
          </div>

          <ProjectsTable v-if="viewMode === 'tabela'" :projetos="projetos" :loading="loading" :columns="columns" />
          <ProjectsChart v-else :projetos="projetos" :loading="loading" />
        </div>
      </div>
    </div>
  </div>
</template>
