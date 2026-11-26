<script setup lang="ts">
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import {
  AreaChart,
  BarChart2,
  BarChartHorizontal,
  Check,
  ChevronDown,
  Code,
  Copy,
  Database,
  Download,
  FileSpreadsheet,
  FileText,
  Lightbulb,
  PieChart,
  Pin,
  Square,
  TrendingUp
} from 'lucide-vue-next'
import BrandIcon from '@/common/components/BrandIcon.vue'
import type { ChatMessage } from '@/modules/chat/types'
import type { ExportFormat } from '@/common/utils/exportData'
import { renderMarkdown } from '@/modules/chat/utils/markdown'
import { CHAT_CHART_TYPES, canUsePie, initialChartType, type ChatChartType } from '@/modules/chat/utils/chartType'
import { formatFieldValue } from '@/modules/chat/utils/format'
import ChatResultChart from '@/modules/chat/components/ChatResultChart.vue'
import ChatResultTable from '@/modules/chat/components/ChatResultTable.vue'

const props = defineProps<{
  message: ChatMessage
}>()

const emit = defineEmits<{
  (e: 'toggle-sql', id: string): void
  (e: 'pin', message: ChatMessage): void
  (e: 'export', payload: { message: ChatMessage; format: ExportFormat }): void
  (e: 'suggest', question: string): void
  (e: 'chart-type', payload: { id: string; type: ChatChartType }): void
}>()

const hasRenderableTable = computed(() => {
  return !!(props.message.table && props.message.table.length > 0 && Object.values(props.message.table[0])[0] !== 'null')
})

const canExportTable = computed(() => hasRenderableTable.value && !props.message.isScalarResult)

const exportMenuOpen = ref(false)
const exportMenuRef = ref<HTMLElement | null>(null)
const exportButtonRef = ref<HTMLButtonElement | null>(null)
const exportDropdownRef = ref<HTMLElement | null>(null)
const exportMenuStyle = ref<Record<string, string>>({})
let exportListenersAttached = false

function updateExportMenuPosition() {
  if (typeof window === 'undefined' || !exportMenuRef.value) return
  const rect = exportMenuRef.value.getBoundingClientRect()
  const dropdownRect = exportDropdownRef.value?.getBoundingClientRect()
  const menuWidth = dropdownRect && dropdownRect.width > 0 ? Math.ceil(dropdownRect.width) : 212
  const menuHeight = dropdownRect && dropdownRect.height > 0 ? Math.ceil(dropdownRect.height) : 96
  const margin = 8
  const left = Math.max(margin, Math.min(rect.left, window.innerWidth - menuWidth - margin))
  const spaceBelow = window.innerHeight - rect.bottom

  if (spaceBelow < menuHeight + 16 && rect.top > spaceBelow) {
    exportMenuStyle.value = {
      left: `${left}px`,
      bottom: `${window.innerHeight - rect.top + 6}px`,
      minWidth: '212px',
    }
  } else {
    exportMenuStyle.value = {
      left: `${left}px`,
      top: `${rect.bottom + 6}px`,
      minWidth: '212px',
    }
  }
}

function attachExportListeners() {
  if (exportListenersAttached || typeof document === 'undefined' || typeof window === 'undefined') return
  document.addEventListener('mousedown', handleExportOutsideClick)
  document.addEventListener('keydown', handleExportKeydown, true)
  window.addEventListener('resize', handleExportViewportChange)
  window.addEventListener('scroll', handleExportViewportChange, true)
  exportListenersAttached = true
}

function detachExportListeners() {
  if (!exportListenersAttached || typeof document === 'undefined' || typeof window === 'undefined') return
  document.removeEventListener('mousedown', handleExportOutsideClick)
  document.removeEventListener('keydown', handleExportKeydown, true)
  window.removeEventListener('resize', handleExportViewportChange)
  window.removeEventListener('scroll', handleExportViewportChange, true)
  exportListenersAttached = false
}

watch(exportMenuOpen, (open) => {
  if (open) {
    updateExportMenuPosition()
    attachExportListeners()
    nextTick(() => updateExportMenuPosition())
  } else {
    detachExportListeners()
  }
})

function toggleExportMenu() {
  exportMenuOpen.value = !exportMenuOpen.value
}

function closeExportMenu() {
  exportMenuOpen.value = false
}

function triggerExport(format: ExportFormat) {
  exportMenuOpen.value = false
  emit('export', { message: props.message, format })
}

function handleExportOutsideClick(event: MouseEvent) {
  if (!exportMenuOpen.value) return
  const target = event.target as Node | null
  if (target && (exportMenuRef.value?.contains(target) || exportDropdownRef.value?.contains(target))) return
  closeExportMenu()
}

function handleExportViewportChange() {
  if (!exportMenuOpen.value || !exportMenuRef.value) return
  const rect = exportMenuRef.value.getBoundingClientRect()
  if (rect.bottom < 0 || rect.top > window.innerHeight) {
    closeExportMenu()
    return
  }
  updateExportMenuPosition()
}

function handleExportKeydown(event: KeyboardEvent) {
  if (!exportMenuOpen.value || event.key !== 'Escape') return
  event.preventDefault()
  event.stopPropagation()
  closeExportMenu()
  exportButtonRef.value?.focus()
}
const rowLimit = ref<number | 'all'>(10)
const rowLimitOptions: Array<number | 'all'> = [5, 10, 15, 'all']
const isCopied = ref(false)
const isSqlCopied = ref(false)

const bubbleRef = ref<HTMLElement | null>(null)
const isVisible = ref(false)
let scrollObserver: IntersectionObserver | null = null


const copyToClipboard = async () => {
  if (isCopied.value || !props.message.text) return
  
  let content = props.message.text
  
  // Adicionar interpretação se houver
  if (props.message.explanation) {
    content += `\n\nInterpretação: ${props.message.explanation}`
  }

  // Adicionar resultado escalar se houver
  if (props.message.isScalarResult && props.message.table?.[0]) {
    const [key, value] = Object.entries(props.message.table[0])[0]
    content += `\n\nResultado: ${formatTableValue(key, value)}`
  }

  // Adicionar dados da tabela se houver
  if (hasRenderableTable.value && !props.message.isScalarResult && props.message.table?.length) {
    const table = props.message.table
    const headers = Object.keys(table[0])
    const headerRow = `| ${headers.join(' | ')} |`
    const divider = `| ${headers.map(() => '---').join(' | ')} |`
    const rows = table
      .map(r => `| ${Object.entries(r).map(([key, value]) => formatTableValue(key, value)).join(' | ')} |`)
      .join('\n')
    content += `\n\nDados:\n${headerRow}\n${divider}\n${rows}`
  }

  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(content)
    } else {
      const textArea = document.createElement('textarea')
      textArea.value = content
      textArea.style.position = 'absolute'
      textArea.style.left = '-999999px'
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      textArea.remove()
    }
    isCopied.value = true
    setTimeout(() => {
      isCopied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy text:', err)
  }
}

const copySqlToClipboard = async () => {
  if (isSqlCopied.value || !props.message.sql) return
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(props.message.sql)
    } else {
      const textArea = document.createElement('textarea')
      textArea.value = props.message.sql
      textArea.style.position = 'absolute'
      textArea.style.left = '-999999px'
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      textArea.remove()
    }
    isSqlCopied.value = true
    setTimeout(() => {
      isSqlCopied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy SQL:', err)
  }
}

const formatTableValue = (key: string | number, value: unknown) =>
  formatFieldValue(props.message.fieldFormats, key, value)

const renderedText = computed(() => renderMarkdown(props.message.text || ''))

const tableRowCount = computed(() => props.message.table?.length || 0)

const displayedRowLimit = computed(() => {
  return rowLimit.value === 'all' ? tableRowCount.value : rowLimit.value
})

const displayedRows = computed(() => {
  return (props.message.table || []).slice(0, displayedRowLimit.value)
})

const chartTypeIcons = {
  bar: BarChart2,
  horizontal_bar: BarChartHorizontal,
  line: TrendingUp,
  area: AreaChart,
  pie: PieChart
} as const

// Tipo escolhido pelo usuário. Até ele escolher, vale a sugestão do agente de painéis e, sem
// sugestão, o formato dos dados (as linhas de uma conversa antiga só chegam depois de abri-la).
const selectedChartType = ref<ChatChartType | null>(props.message.chartType ?? null)
const isPieAvailable = computed(() => canUsePie(props.message.chart?.series))
const pieUnavailableReason = 'Pizza só funciona com uma única série de valores, sem números negativos'

const chartType = computed<ChatChartType>(() => {
  const type = selectedChartType.value ?? initialChartType(props.message.suggestedChartType, props.message.table)
  return type === 'pie' && !isPieAvailable.value ? 'bar' : type
})

const selectChartType = (type: ChatChartType) => {
  if (type === 'pie' && !isPieAvailable.value) return
  selectedChartType.value = type
  // O relatório usa o tipo que está na tela (FR08).
  emit('chart-type', { id: props.message.id, type })
}

const chartTypeTitle = (type: ChatChartType, label: string) => {
  if (type === 'pie' && !isPieAvailable.value) return pieUnavailableReason
  return `Mostrar em ${label.toLowerCase()}`
}

const pinMessage = () => {
  emit('pin', { ...props.message, chartType: chartType.value })
}

onMounted(() => {
  if (typeof document !== 'undefined') {
    // Setup scroll reveal animation observer
    scrollObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          isVisible.value = entry.isIntersecting
        })
      },
      {
        rootMargin: '0px',
        threshold: 0
      }
    )
    if (bubbleRef.value) {
      scrollObserver.observe(bubbleRef.value)
    }
  }
})

onBeforeUnmount(() => {
  scrollObserver?.disconnect()
  detachExportListeners()
})
</script>

<template>
  <div
    ref="bubbleRef"
    :class="[
      'flex w-full ease-out-premium transform-gpu',
      message.type === 'user' ? 'justify-end' : 'justify-start',
      isVisible ? 'opacity-100 translate-y-0 scale-100 filter-none' : 'opacity-0 translate-y-6 scale-[0.97] blur-[2px] pointer-events-none'
    ]"
  >
    <div :class="[
      (message.chart?.series?.length || (hasRenderableTable && !message.isScalarResult) ? 'w-full' : 'max-w-full md:max-w-3xl'),
      message.type === 'user' ? 'ml-4 md:ml-12 mr-4 md:mr-0' : 'mr-4 md:mr-0'
    ]">
      <div v-if="message.type === 'ai'" class="flex items-center justify-between gap-2 mb-3 pr-1">
        <div class="flex items-center gap-2">
          <div class="w-10 h-10 flex items-center justify-center relative">
            <div v-if="message.isLoading" class="loading-brand-wrapper">
              <BrandIcon alt="" class="relative z-10 h-8 w-8" />
              <div class="loading-brand-ring" />
            </div>
            <BrandIcon v-else alt="" class="h-9 w-9" />
          </div>
          <span class="font-semibold tracking-[-0.03em] text-primary dark:text-white">Adito</span>
        </div>

        <!-- Botão Copiar para AI -->
        <button
          v-if="message.text && !message.isLoading"
          type="button"
          @click="copyToClipboard"
          class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all hover:bg-surface-elevated text-primary dark:text-slate-300 hover:text-accent dark:hover:text-white border border-transparent hover:border-border-subtle"
          :title="isCopied ? 'Copiado!' : 'Copiar resposta completa'"
        >
          <transition mode="out-in">
            <Check v-if="isCopied" class="w-3.5 h-3.5 text-emerald-500" />
            <Copy v-else class="w-3.5 h-3.5" />
          </transition>
          <span class="hidden sm:inline">{{ isCopied ? 'Copiado' : 'Copiar' }}</span>
        </button>
      </div>

      <div
        :class="[
          'relative group rounded-2xl p-4 transition-all',
          message.type === 'user'
            ? 'rounded-tr-sm bg-[var(--brand-dark)] text-white border border-transparent shadow-xs dark:bg-[#1E5E3A] dark:border-[rgba(54,146,81,0.35)]'
            : message.isFallback
              ? 'bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-500/30'
              : 'border border-border-subtle bg-surface shadow-premium'
        ]"
      >
        <template v-if="message.isFallback">
          <div class="flex items-start gap-2">
            <div class="flex-1">
              <div class="flex items-center gap-2 mb-1.5">
                <BrandIcon alt="" class="h-4 w-4" />
                <span class="text-sm font-semibold text-amber-800 dark:text-amber-500">Adito · Exploração</span>
              </div>
              <p class="text-sm text-amber-700 dark:text-amber-400/90 mb-3 leading-relaxed">
                {{ message.fallbackMessage || 'Nao encontrei os dados exatos para esta pergunta. Que tal tentar uma das opcoes abaixo?' }}
              </p>

              <div v-if="message.suggestions?.length" class="space-y-1.5">
                <div class="grid grid-cols-1 gap-1.5">
                  <button
                    v-for="(suggestion, index) in message.suggestions"
                    :key="`fallback-${index}`"
                    class="text-left w-full p-2.5 text-sm bg-white dark:bg-slate-900 border border-amber-200/50 dark:border-amber-900/40 rounded-lg hover:border-amber-400 hover:shadow-sm hover:bg-amber-50/50 transition-all text-slate-700 dark:text-slate-300"
                    @click="emit('suggest', suggestion.question)"
                  >
                    <div class="flex justify-between items-center text-xs">
                      <span class="line-clamp-2 pr-2">"{{ suggestion.question }}"</span>
                      <span class="shrink-0 text-[10px] text-amber-600/50 dark:text-amber-500/40">Sugerido</span>
                    </div>
                  </button>
                </div>
              </div>

              <div
                v-if="message.related_attributes?.length"
                class="mt-4 pt-4 border-t border-amber-200/50 dark:border-amber-900/40"
              >
                <div class="flex items-center gap-1.5 mb-2.5">
                  <Database class="w-3.5 h-3.5 text-amber-600 dark:text-amber-500" />
                  <span class="text-xs font-semibold text-amber-800 dark:text-amber-400">
                    Atributos de Banco Disponiveis Neste Dominio:
                  </span>
                </div>
                <div class="flex flex-wrap gap-2">
                  <div
                    v-for="(attribute, index) in message.related_attributes"
                    :key="`attr-fallback-${index}`"
                    class="group relative"
                  >
                    <span class="inline-flex items-center px-2 py-1 bg-amber-100/50 dark:bg-amber-900/30 border border-amber-200/60 dark:border-amber-700/50 text-amber-800 dark:text-amber-300 text-[11px] font-medium rounded-md cursor-help transition-colors hover:bg-amber-200/50">
                      {{ attribute.coluna }}
                    </span>
                    <div class="absolute bottom-full left-0 mb-1 hidden group-hover:block w-48 p-2 bg-slate-800 text-white text-[10px] rounded shadow-lg z-10">
                      {{ attribute.descricao }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>

        <p v-if="message.type === 'user'" class="text-white">
          {{ message.text }}
        </p>

        <template v-else-if="!message.isFallback">
          <div>
            <div
              v-if="message.text"
              class="chat-markdown text-gray-700 dark:text-gray-300"
              v-html="renderedText"
            />

            <div v-if="message.isLoading" :class="['chat-loading-container', message.text ? 'mt-4' : '']" aria-live="polite">
              <div class="chat-loading-status">
                <div class="status-indicator">
                  <span class="status-dot" />
                  <span class="status-dot delay-100" />
                  <span class="status-dot delay-200" />
                </div>
                <span class="status-text">{{ message.loadingStatus || 'Consultando base de dados' }}</span>
              </div>
              <div v-if="!message.text" class="skeleton-group">
                <div class="skeleton-line w-full" />
                <div class="skeleton-line w-[92%] [animation-delay:0.1s]" />
                <div class="skeleton-line w-[68%] [animation-delay:0.2s]" />
              </div>
            </div>

            <div
              v-else-if="message.interrupted"
              :class="[
                'flex items-center gap-1.5 text-xs text-text-muted italic',
                message.text ? 'mt-3 pt-2 border-t border-border-subtle/60 dark:border-white/[0.08]' : ''
              ]"
              role="status"
            >
              <Square class="h-2.5 w-2.5 shrink-0 opacity-70" />
              <span>Resposta interrompida</span>
            </div>
          </div>
        </template>

        <div
          v-if="message.explanation && !message.isFallback"
          class="mt-3 rounded-lg border border-border-subtle bg-surface-elevated/50 px-3 py-2 text-xs leading-relaxed text-text-secondary dark:border-white/[0.06]"
        >
          <span class="font-semibold text-primary dark:text-slate-100">Interpretação:</span>
          {{ message.explanation }}
        </div>

        <div
          v-if="message.isScalarResult && hasRenderableTable && message.table?.[0]"
          class="mt-4 text-3xl font-semibold text-primary dark:text-slate-100"
        >
          {{ formatTableValue(Object.keys(message.table[0])[0], Object.values(message.table[0])[0]) }}
        </div>

        <div
          v-if="hasRenderableTable && !message.isScalarResult && tableRowCount > 5"
          class="mt-4 flex flex-wrap items-center gap-2 text-xs text-text-secondary"
        >
          <span class="font-medium">Mostrar:</span>
          <button
            v-for="option in rowLimitOptions"
            :key="String(option)"
            type="button"
            :class="[
              'rounded-full border px-3 py-1 font-semibold transition-colors cursor-pointer',
              rowLimit === option
                ? 'border-[var(--brand-primary)] bg-[var(--brand-primary)] text-white'
                : 'border-border-subtle bg-surface-elevated hover:border-accent/50'
            ]"
            @click="rowLimit = option"
          >
            {{ option === 'all' ? `Todas (${tableRowCount})` : option }}
          </button>
        </div>

        <div
          v-if="message.chart?.series?.length && hasRenderableTable && tableRowCount > 1"
          class="mt-4 flex justify-end px-1"
        >
          <div
            class="flex items-center gap-1 rounded-lg border border-border-subtle bg-surface-elevated/45 p-1 dark:border-white/[0.06] dark:bg-white/5"
            role="group"
            aria-label="Tipo de gráfico"
          >
            <button
              v-for="option in CHAT_CHART_TYPES"
              :key="option.value"
              type="button"
              :class="[
                'rounded-md p-1.5 transition-all',
                chartType === option.value
                  ? 'border border-border-subtle bg-surface text-primary shadow-premium dark:bg-slate-700 dark:text-white'
                  : 'border border-transparent text-text-secondary hover:bg-surface/60 hover:text-primary dark:hover:text-white',
                option.value === 'pie' && !isPieAvailable ? 'cursor-not-allowed opacity-40 hover:bg-transparent hover:text-text-secondary' : 'cursor-pointer'
              ]"
              :title="chartTypeTitle(option.value, option.label)"
              :aria-label="option.label"
              :aria-pressed="chartType === option.value"
              :aria-disabled="option.value === 'pie' && !isPieAvailable ? 'true' : undefined"
              :data-chart-type="option.value"
              @click="selectChartType(option.value)"
            >
              <component :is="chartTypeIcons[option.value]" class="w-4 h-4" />
            </button>
          </div>
        </div>

        <ChatResultChart
          v-if="message.chart?.series?.length && hasRenderableTable && tableRowCount > 1"
          :chart="message.chart"
          :type="chartType"
          :row-limit="rowLimit"
        />

        <ChatResultTable
          v-if="hasRenderableTable && !message.isScalarResult"
          :rows="displayedRows"
          :field-formats="message.fieldFormats"
        />
        <div v-if="hasRenderableTable && !message.isScalarResult && tableRowCount > 1" class="mt-2 flex items-center justify-between px-1">
          <p class="text-[11px] text-text-muted font-medium">
            Mostrando {{ displayedRows.length }} de {{ tableRowCount }} registros
          </p>
        </div>

        <div v-if="message.sql || canExportTable" class="mt-4 flex flex-wrap gap-2">
          <button
            v-if="message.sql"
            class="flex items-center gap-2 rounded-lg border border-border-subtle bg-surface-elevated px-3 py-2 text-xs font-semibold text-primary transition-colors hover:border-accent/30 hover:text-accent dark:text-slate-200"
            @click="emit('toggle-sql', message.id)"
          >
            <Code class="w-4 h-4" />
            {{ message.showSQL ? 'Ocultar SQL' : 'Ver SQL Gerado' }}
          </button>

          <button
            v-if="message.sql && hasRenderableTable"
            class="flex items-center gap-2 rounded-lg border border-border-subtle bg-surface-elevated px-3 py-2 text-xs font-semibold text-primary transition-colors hover:border-accent/30 hover:text-accent dark:text-slate-200"
            @click="pinMessage"
          >
            <Pin class="w-4 h-4" />
            Fixar no Dashboard
          </button>

          <div v-if="canExportTable" ref="exportMenuRef" class="relative">
            <button
              ref="exportButtonRef"
              type="button"
              data-testid="chat-export-btn"
              aria-haspopup="menu"
              :aria-expanded="exportMenuOpen"
              class="flex items-center gap-1.5 rounded-lg border border-border-subtle bg-surface-elevated px-3 py-2 text-xs font-semibold text-primary transition-colors hover:border-accent/30 hover:text-accent dark:text-slate-200"
              @click="toggleExportMenu"
            >
              <Download class="w-4 h-4" aria-hidden="true" />
              <span>Exportar</span>
              <ChevronDown
                class="w-3.5 h-3.5 transition-transform duration-150"
                :class="{ 'rotate-180': exportMenuOpen }"
                aria-hidden="true"
              />
            </button>

            <Teleport to="body">
              <div
                v-if="exportMenuOpen"
                ref="exportDropdownRef"
                role="menu"
                aria-label="Opções de exportação"
                data-testid="chat-export-menu"
                :style="exportMenuStyle"
                class="fixed z-[75] rounded-xl border border-border-subtle bg-surface p-1.5 shadow-premium dark:border-white/10"
              >
                <button
                  type="button"
                  role="menuitem"
                  class="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-xs font-medium text-text-primary transition-colors hover:bg-surface-elevated hover:text-accent"
                  @click="triggerExport('csv')"
                >
                  <FileText class="h-4 w-4 shrink-0 text-text-secondary" aria-hidden="true" />
                  <span>Exportar CSV (.csv)</span>
                </button>
                <button
                  type="button"
                  role="menuitem"
                  class="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-xs font-medium text-text-primary transition-colors hover:bg-surface-elevated hover:text-accent"
                  @click="triggerExport('xlsx')"
                >
                  <FileSpreadsheet class="h-4 w-4 shrink-0 text-emerald-600 dark:text-[#68d388]" aria-hidden="true" />
                  <span>Exportar Excel (.xlsx)</span>
                </button>
              </div>
            </Teleport>
          </div>
        </div>

        <div v-if="message.sql && message.showSQL" class="mt-3 rounded-lg border border-border-subtle bg-surface-elevated overflow-hidden dark:border-white/[0.06] dark:bg-black/20">
          <div class="flex items-center justify-between px-3 py-2 border-b border-border-subtle/50 bg-surface/30">
            <span class="text-[10px] font-bold uppercase tracking-wider text-text-muted">Query SQL</span>
            <button
              type="button"
              @click="copySqlToClipboard"
              class="flex items-center gap-1 px-2 py-1 rounded text-[10px] font-bold uppercase transition-all text-primary dark:text-slate-300 hover:text-accent dark:hover:text-white hover:bg-surface/50"
            >
              <transition mode="out-in">
                <Check v-if="isSqlCopied" class="w-3 h-3 text-emerald-500" />
                <Copy v-else class="w-3 h-3" />
              </transition>
              {{ isSqlCopied ? 'Copiado' : 'Copiar' }}
            </button>
          </div>
          <div class="p-4 overflow-x-auto">
            <pre class="text-sm text-accent font-mono whitespace-pre-wrap">{{ message.sql }}</pre>
          </div>
        </div>

        <div
          v-if="!message.isFallback && message.suggestions?.length"
          class="mt-4 pt-4 border-t border-border-subtle dark:border-white/[0.06]"
        >
          <div class="flex items-center gap-2 mb-3">
            <Lightbulb class="w-4 h-4 text-text-muted" />
            <p class="text-sm font-medium text-text-secondary">
              Sugestão: envie uma nova pergunta ou explore as opções abaixo.
            </p>
          </div>
          <div class="grid grid-cols-1 gap-1.5">
            <button
              v-for="(suggestion, index) in message.suggestions"
              :key="`normal-${index}`"
              class="group w-full rounded-lg border border-border-subtle bg-surface-elevated/40 px-3 py-2.5 text-left text-sm text-text-secondary transition-all hover:border-border-standard hover:bg-surface dark:border-white/[0.05] dark:hover:bg-surface-elevated"
              @click="emit('suggest', suggestion.question)"
            >
              <div class="flex justify-between items-center text-xs">
                <span class="line-clamp-2 pr-2 font-medium">"{{ suggestion.question }}"</span>
                <span class="shrink-0 text-[10px] text-text-muted transition-colors group-hover:text-accent">Executar →</span>
              </div>
            </button>
          </div>

          <div
            v-if="message.related_attributes?.length"
            class="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/50"
          >
            <div class="flex items-center gap-1.5 mb-2">
              <Database class="w-3.5 h-3.5 text-slate-500" />
              <span class="text-xs font-semibold text-slate-600 dark:text-slate-400">
                Atributos Relacionados Disponiveis:
              </span>
            </div>
            <div class="flex flex-wrap gap-2">
              <div
                v-for="(attribute, index) in message.related_attributes"
                :key="`attr-normal-${index}`"
                class="group relative"
              >
                <span class="inline-flex items-center px-2 py-1 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-white/5 text-slate-600 dark:text-slate-300 text-[11px] font-medium rounded-md cursor-help transition-colors hover:bg-slate-200 dark:hover:bg-slate-700">
                  {{ attribute.coluna }}
                </span>
                <div class="absolute bottom-full left-0 mb-1 hidden group-hover:block w-48 p-2 bg-slate-800 text-white text-[10px] rounded shadow-lg z-10">
                  {{ attribute.descricao }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Ações para mensagem do usuário -->
      <div v-if="message.type === 'user'" class="flex justify-end mt-1.5 pr-1">
        <button
          type="button"
          @click="copyToClipboard"
          class="flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all text-primary dark:text-slate-400 hover:text-accent dark:hover:text-white hover:bg-surface-elevated/50"
          :title="isCopied ? 'Copiado!' : 'Copiar pergunta'"
        >
          <transition mode="out-in">
            <Check v-if="isCopied" class="w-3 h-3 text-emerald-500" />
            <Copy v-else class="w-3 h-3" />
          </transition>
          <span>{{ isCopied ? 'Copiado' : 'Copiar' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ease-out-premium {
  transition: opacity 0.8s cubic-bezier(0.16, 1, 0.3, 1),
              transform 0.8s cubic-bezier(0.16, 1, 0.3, 1),
              filter 0.8s cubic-bezier(0.16, 1, 0.3, 1);
  will-change: transform, opacity, filter;
}

.chat-markdown :deep(p) {
  margin: 0 0 0.875rem;
  font-size: 0.9375rem;
  line-height: 1.7;
}

.chat-markdown :deep(p:last-child) {
  margin-bottom: 0;
}

.chat-markdown :deep(ul) {
  margin: 0.5rem 0 0.75rem 1.25rem;
  list-style: disc;
}

.chat-markdown :deep(ol) {
  margin: 0.5rem 0 0.75rem 1.25rem;
  list-style: decimal;
}

.chat-markdown :deep(li) {
  margin: 0.3rem 0;
  font-size: 0.9375rem;
  line-height: 1.65;
}

.chat-markdown :deep(strong) {
  font-weight: 700;
  color: rgb(var(--color-primary));
}

.chat-markdown :deep(em) {
  font-style: italic;
}

.chat-markdown :deep(code) {
  border-radius: 0.375rem;
  background: rgba(15, 25, 35, 0.06);
  padding: 0.1rem 0.35rem;
  font-size: 0.9em;
}

.chat-markdown :deep(hr) {
  margin: 1rem 0;
  border: 0;
  border-top: 1px solid rgb(var(--color-border-subtle));
}

.chat-markdown :deep(h1),
.chat-markdown :deep(h2),
.chat-markdown :deep(h3) {
  margin: 0.75rem 0 0.5rem;
  font-weight: 700;
  color: rgb(var(--color-primary));
  letter-spacing: -0.02em;
}

.chat-markdown :deep(h1) {
  font-size: 1.125rem;
}

.chat-markdown :deep(h2) {
  font-size: 1rem;
}

.chat-markdown :deep(h3) {
  font-size: 0.9375rem;
}

/* Loading state */
/* Nova animação de carregamento — Estilo Profissional/Marca */
.loading-brand-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-brand-ring {
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 2px solid var(--accent);
  border-top-color: transparent;
  border-right-color: transparent;
  animation: brand-spin 0.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
  opacity: 0.8;
}

@keyframes brand-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.chat-loading-container {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.chat-loading-status {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-indicator {
  display: flex;
  gap: 3px;
}

.status-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background-color: var(--accent);
  opacity: 0.4;
  animation: pulse-dot 1.2s ease-in-out infinite;
}

.delay-100 { animation-delay: 0.2s; }
.delay-200 { animation-delay: 0.4s; }

@keyframes pulse-dot {
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.2); }
}

.status-text {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: 0.01em;
  text-transform: uppercase;
  font-family: var(--font-mono);
}

.skeleton-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skeleton-line {
  height: 11px;
  border-radius: 4px;
  background: var(--bg-surface-elevated);
  position: relative;
  overflow: hidden;
}

.skeleton-line::after {
  content: "";
  position: absolute;
  inset: 0;
  transform: translateX(-100%);
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.15),
    transparent
  );
  animation: shimmer 1.8s infinite;
}

.dark .skeleton-line::after {
  background: linear-gradient(
    90deg,
    transparent,
    rgba(255, 255, 255, 0.04),
    transparent
  );
}

@keyframes shimmer {
  100% { transform: translateX(100%); }
}

@media (prefers-reduced-motion: reduce) {
  .loading-brand-ring,
  .status-dot,
  .skeleton-line::after {
    animation: none;
  }
}
</style>

<style scoped>
:deep(.apexcharts-tooltip) {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(155, 155, 155, 0.2);
  border-radius: 10px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(155, 155, 155, 0.4);
}

.dark .custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
}

.dark .custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}

.custom-scrollbar::-webkit-scrollbar-corner {
  background: transparent;
}
</style>
