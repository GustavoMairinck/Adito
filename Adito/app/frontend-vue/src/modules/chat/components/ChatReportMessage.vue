<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { AlertTriangle, Check, Code, Copy, FileDown, FileText, Inbox, Loader2 } from 'lucide-vue-next'
import BrandIcon from '@/common/components/BrandIcon.vue'
import ChatResultChart from '@/modules/chat/components/ChatResultChart.vue'
import ChatResultTable from '@/modules/chat/components/ChatResultTable.vue'
import ChatReportPrint from '@/modules/chat/components/ChatReportPrint.vue'
import type { ChatMessage, ChatReport } from '@/modules/chat/types'
import {
  SECTION_EMPTY_TEXT,
  formatDateTime,
  reportFileName,
  reportToMarkdown,
  sectionView,
} from '@/modules/chat/utils/report'
import { dadosStatus } from '@/common/api/atualizacoes'
import { useAtualizacoes } from '@/common/composables/useAtualizacoes'

const props = defineProps<{
  message: ChatMessage
  report: ChatReport
}>()

const report = computed(() => props.report)
const views = computed(() => report.value.sections.map(section => sectionView(section, report.value.loaded)))
const entries = computed(() => report.value.sections.map((section, index) => ({ section, view: views.value[index], index })))
const openSql = ref<Record<number, boolean>>({})
const dataVersion = ref<string | null>(null)
const appVersion = ref<string | null>(null)
const isCopied = ref(false)
const printing = ref(false)

const loadDataVersion = async () => {
  try {
    dataVersion.value = (await dadosStatus())?.versao ?? null
  } catch {
    dataVersion.value = null
  }
}

// A versão dos dados acompanha a atualização do dados.db em segundo plano (os números são
// recarregados pela tela do chat).
const { dadosReloadSeq } = useAtualizacoes()
watch(dadosReloadSeq, (seq) => { if (seq > 0) void loadDataVersion() })

onMounted(async () => {
  await loadDataVersion()
  try {
    const { getVersion } = await import('@tauri-apps/api/app')
    const version = await getVersion()
    appVersion.value = typeof version === 'string' && version ? version : null
  } catch {
    appVersion.value = null
  }
})

const copyReport = async () => {
  if (isCopied.value) return
  const content = reportToMarkdown(report.value, dataVersion.value)
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
    setTimeout(() => { isCopied.value = false }, 2000)
  } catch (err) {
    console.error('Falha ao copiar o relatório:', err)
  }
}

/** Espera os gráficos da página de impressão aparecerem (sem animação) antes de abrir a impressão. */
const waitForPrintCharts = async () => {
  const expected = views.value.filter(view => view.kind === 'data' && view.chartType).length
  const started = Date.now()
  while (Date.now() - started < 3000) {
    const root = document.querySelector(`[data-report-print="${props.message.id}"]`)
    const rendered = root?.querySelectorAll('.apexcharts-canvas').length ?? 0
    if (rendered >= expected) break
    await new Promise(resolve => setTimeout(resolve, 50))
  }
  await new Promise(resolve => setTimeout(resolve, 250))
}

// PDF pela impressão do webview ("Salvar como PDF" do sistema), sem dependência nova (KD04).
// A limpeza (classe `adito-printing`, título da janela e estado do botão) roda uma vez só, no que vier
// primeiro: `afterprint`, a janela voltar a ter foco depois da impressão (o WebKitGTK nem sempre
// dispara `afterprint` ao cancelar), um tempo limite de segurança ou a mensagem sair da tela.
const PRINT_SAFETY_TIMEOUT_MS = 120_000
let disposed = false
let finishPrint: (() => void) | null = null

const exportPdf = async () => {
  if (printing.value || !report.value.loaded) return
  printing.value = true
  await nextTick()
  await waitForPrintCharts()
  if (disposed) return
  const previousTitle = document.title
  document.title = reportFileName(report.value.title, report.value.generatedAt)
  document.documentElement.classList.add('adito-printing')

  let safetyTimer: ReturnType<typeof setTimeout> | null = null
  const onFocus = () => setTimeout(() => finishPrint?.(), 300)
  finishPrint = () => {
    finishPrint = null
    if (safetyTimer) clearTimeout(safetyTimer)
    window.removeEventListener('afterprint', onAfterPrint)
    window.removeEventListener('focus', onFocus)
    document.documentElement.classList.remove('adito-printing')
    document.title = previousTitle
    printing.value = false
  }
  const onAfterPrint = () => finishPrint?.()
  window.addEventListener('afterprint', onAfterPrint)
  safetyTimer = setTimeout(() => finishPrint?.(), PRINT_SAFETY_TIMEOUT_MS)
  window.print()
  // Só escuta o foco depois de abrir a impressão, para não limpar antes da janela do sistema aparecer.
  window.addEventListener('focus', onFocus)
}

onBeforeUnmount(() => {
  disposed = true
  finishPrint?.()
})
</script>

<template>
  <div class="flex w-full justify-start" data-testid="report-message">
    <div class="w-full mr-4 md:mr-0">
      <div class="flex items-center justify-between gap-2 mb-3 pr-1">
        <div class="flex items-center gap-2">
          <div class="w-10 h-10 flex items-center justify-center">
            <BrandIcon alt="" class="h-9 w-9" />
          </div>
          <span class="font-semibold tracking-[-0.03em] text-primary dark:text-white">Adito</span>
        </div>
        <div class="flex items-center gap-1">
          <button
            type="button"
            class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all hover:bg-surface-elevated text-primary dark:text-slate-300 hover:text-accent border border-transparent hover:border-border-subtle disabled:opacity-50"
            :disabled="!report.loaded"
            :title="isCopied ? 'Copiado!' : 'Copiar o relatório em texto'"
            @click="copyReport"
          >
            <Check v-if="isCopied" class="w-3.5 h-3.5 text-emerald-500" />
            <Copy v-else class="w-3.5 h-3.5" />
            <span>{{ isCopied ? 'Copiado' : 'Copiar' }}</span>
          </button>
          <button
            type="button"
            class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all bg-[var(--brand-primary)] text-white hover:bg-[var(--brand-dark)] disabled:opacity-50"
            :disabled="!report.loaded || printing"
            title="Exportar o relatório em PDF"
            @click="exportPdf"
          >
            <Loader2 v-if="printing" class="w-3.5 h-3.5 animate-spin" />
            <FileDown v-else class="w-3.5 h-3.5" />
            Exportar PDF
          </button>
        </div>
      </div>

      <article class="rounded-2xl border border-border-subtle bg-surface shadow-premium overflow-hidden" :aria-label="`Relatório: ${report.title}`">
        <header class="border-b border-border-subtle bg-surface-elevated/50 px-5 py-4 dark:border-white/[0.06]">
          <span class="inline-flex items-center gap-1.5 rounded-full bg-accent/10 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wider text-accent">
            <FileText class="h-3.5 w-3.5" />
            Relatório
          </span>
          <h3 class="mt-2 text-lg font-semibold text-primary dark:text-white">{{ report.title }}</h3>
          <p class="mt-1 text-xs text-text-secondary">
            Gerado em {{ formatDateTime(report.generatedAt) }}
            <template v-if="report.contextoNome"> · {{ report.contextoNome }}</template>
            <template v-if="dataVersion"> · Dados de {{ dataVersion }}</template>
            · {{ report.sections.length }} {{ report.sections.length === 1 ? 'seção' : 'seções' }}
          </p>
          <p class="mt-1 text-[11px] text-text-muted">Números calculados diretamente dos dados atuais, sem uso de IA.</p>
        </header>

        <section
          v-for="{ section, view, index } in entries"
          :key="`${section.sourceMessageId}-${index}`"
          class="border-b border-border-subtle px-5 py-5 last:border-b-0 dark:border-white/[0.06]"
          :aria-label="`Seção ${index + 1}: ${section.title}`"
          data-testid="report-section"
        >
          <h4 class="flex items-start gap-3 text-sm font-semibold text-primary dark:text-white">
            <span class="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-[var(--brand-primary)] text-xs font-bold text-white">{{ index + 1 }}</span>
            <span class="pt-0.5">{{ section.title }}</span>
          </h4>

          <div v-if="view.kind === 'loading'" class="mt-4 flex items-center gap-2 text-xs text-text-muted" role="status">
            <Loader2 class="h-4 w-4 animate-spin" />
            Carregando os dados da seção…
          </div>

          <div
            v-else-if="view.kind === 'error'"
            role="alert"
            class="mt-4 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-500/20 dark:bg-amber-500/10 dark:text-amber-300"
          >
            <AlertTriangle class="h-4 w-4 shrink-0" />
            {{ view.message }}
          </div>

          <div v-else-if="view.kind === 'empty'" class="mt-4 flex items-center gap-2 text-xs text-text-muted">
            <Inbox class="h-4 w-4" />
            {{ SECTION_EMPTY_TEXT }}
          </div>

          <div
            v-else-if="view.kind === 'scalar'"
            class="mt-4 inline-flex flex-col rounded-xl border border-border-subtle bg-surface-elevated/50 px-5 py-3"
          >
            <span class="text-[11px] font-semibold uppercase tracking-wider text-text-muted">{{ view.label }}</span>
            <span class="text-3xl font-semibold text-primary dark:text-slate-100">{{ view.value }}</span>
          </div>

          <template v-else-if="view.kind === 'data'">
            <ChatResultChart
              v-if="view.chart && view.chartType"
              :chart="view.chart"
              :type="view.chartType"
              :row-limit="10"
            />
            <ChatResultTable :rows="view.rows" :field-formats="section.fieldFormats" />
            <p class="mt-2 px-1 text-[11px] font-medium text-text-muted">
              Mostrando {{ view.rows.length }} de {{ view.total }} registros
            </p>
          </template>

          <button
            type="button"
            class="mt-3 flex items-center gap-1.5 text-xs font-medium text-text-secondary hover:text-accent"
            :aria-expanded="!!openSql[index]"
            @click="openSql[index] = !openSql[index]"
          >
            <Code class="h-3.5 w-3.5" />
            {{ openSql[index] ? 'Ocultar SQL' : 'Ver SQL da seção' }}
          </button>
          <pre
            v-if="openSql[index]"
            class="mt-2 overflow-x-auto whitespace-pre-wrap rounded-lg border border-border-subtle bg-surface-elevated p-3 font-mono text-xs text-accent dark:border-white/[0.06] dark:bg-black/20"
          >{{ section.sql }}</pre>
        </section>
      </article>
    </div>

    <ChatReportPrint
      v-if="printing"
      :message-id="message.id"
      :report="report"
      :views="views"
      :data-version="dataVersion"
      :app-version="appVersion"
    />
  </div>
</template>
