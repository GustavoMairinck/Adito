<script setup lang="ts">
import { computed } from 'vue'
import ChatResultChart from '@/modules/chat/components/ChatResultChart.vue'
import ChatResultTable from '@/modules/chat/components/ChatResultTable.vue'
import type { ChatReport } from '@/modules/chat/types'
import { SECTION_EMPTY_TEXT, formatDateTime, type SectionView } from '@/modules/chat/utils/report'
import { formatFieldValue } from '@/modules/chat/utils/format'

/**
 * Página de impressão do relatório (FR12–FR18). Fica fora da tela até a impressão; ao imprimir,
 * `html.adito-printing` esconde o app e mostra só esta página, sempre em tema claro.
 * Capa sem cabeçalho/rodapé; nas demais páginas, cabeçalho e rodapé repetidos (thead/tfoot) e
 * "Página X de Y" na margem da página (`@page`).
 */
const props = defineProps<{
  messageId: string
  report: ChatReport
  views: SectionView[]
  dataVersion?: string | null
  appVersion?: string | null
}>()

const generatedAt = computed(() => formatDateTime(props.report.generatedAt))
const shortId = computed(() => props.messageId.replace(/-/g, '').slice(0, 12).toUpperCase())

const entries = computed(() => {
  let figure = 0
  return props.report.sections.map((section, index) => {
    const view = props.views[index]
    const hasChart = view.kind === 'data' && !!view.chart && !!view.chartType
    if (hasChart) figure += 1
    return { section, view, number: index + 1, figure: hasChart ? figure : null }
  })
})

/** Destaques da seção: total de registros e a maior categoria da primeira série (sem somar médias). */
const highlights = (view: SectionView, formats: Record<string, any>) => {
  if (view.kind !== 'data') return []
  const cards = [{ label: 'Registros', value: view.total.toLocaleString('pt-BR') }]
  const chart = view.chart
  const serie = chart?.series?.[0]
  if (chart && serie && serie.data.length) {
    let best = 0
    serie.data.forEach((value, i) => { if (Number(value) > Number(serie.data[best])) best = i })
    const metricKey = Object.keys(view.rows[0] || {}).find(key => key.replace(/_/g, ' ').toLowerCase() === serie.name.toLowerCase())
    const value = metricKey ? formatFieldValue(formats, metricKey, serie.data[best]) : Number(serie.data[best]).toLocaleString('pt-BR')
    cards.push({ label: `Maior ${serie.name.toLowerCase()}`, value: `${chart.categories[best]} · ${value}` })
  }
  return cards
}
</script>

<template>
  <Teleport to="body">
    <div class="report-print-root" :data-report-print="messageId" aria-hidden="true">
      <!-- Capa -->
      <section class="rp-cover">
        <div class="rp-cover-band" />
        <img src="/brand/adito-light.png" alt="Adito" class="rp-cover-logo">
        <p class="rp-kicker">Relatório</p>
        <h1 class="rp-cover-title">{{ report.title }}</h1>
        <p v-if="report.contextoNome" class="rp-cover-context">{{ report.contextoNome }}</p>

        <dl class="rp-cover-meta">
          <div><dt>Gerado em</dt><dd>{{ generatedAt }}</dd></div>
          <div v-if="dataVersion"><dt>Versão dos dados</dt><dd>{{ dataVersion }}</dd></div>
          <div v-if="appVersion"><dt>Versão do Adito</dt><dd>{{ appVersion }}</dd></div>
          <div><dt>Seções</dt><dd>{{ report.sections.length }}</dd></div>
          <div><dt>Identificador</dt><dd class="rp-mono">{{ shortId }}</dd></div>
        </dl>

        <div class="rp-seal">
          <img src="/brand/adito-light.png" alt="" class="rp-seal-logo">
          <div>
            <strong>Documento gerado pelo Adito</strong>
            <p>Números calculados diretamente dos dados de pesquisa e extensão do Ifes, sem uso de IA. A metodologia e o SQL de cada seção estão no anexo.</p>
          </div>
        </div>
      </section>

      <table class="rp-layout">
        <thead>
          <tr>
            <td>
              <div class="rp-header">
                <img src="/brand/adito-light.png" alt="" class="rp-header-logo">
                <span class="rp-header-title">{{ report.title }}</span>
                <span class="rp-header-tag">Relatório · Adito</span>
              </div>
            </td>
          </tr>
        </thead>
        <tfoot>
          <tr>
            <td>
              <div class="rp-footer">
                <span class="rp-footer-seal">Gerado pelo Adito</span>
                <span>{{ generatedAt }}</span>
                <span class="rp-mono">ID {{ shortId }}</span>
              </div>
            </td>
          </tr>
        </tfoot>
        <tbody>
          <tr>
            <td>
              <!-- Sumário -->
              <section class="rp-toc">
                <h2 class="rp-h2">Sumário</h2>
                <ol>
                  <li v-for="entry in entries" :key="`toc-${entry.number}`">
                    <span class="rp-toc-number">{{ entry.number }}</span>
                    <span class="rp-toc-title">{{ entry.section.title }}</span>
                  </li>
                  <li>
                    <span class="rp-toc-number">A</span>
                    <span class="rp-toc-title">Metodologia</span>
                  </li>
                </ol>
              </section>

              <!-- Seções -->
              <section v-for="entry in entries" :key="`sec-${entry.number}`" class="rp-section">
                <div class="rp-section-divider">
                  <span class="rp-section-number">{{ String(entry.number).padStart(2, '0') }}</span>
                  <h2 class="rp-section-title">{{ entry.section.title }}</h2>
                </div>

                <p v-if="entry.view.kind === 'error'" class="rp-note rp-note-warn">{{ entry.view.message }}</p>
                <p v-else-if="entry.view.kind === 'empty'" class="rp-note">{{ SECTION_EMPTY_TEXT }}</p>
                <div v-else-if="entry.view.kind === 'scalar'" class="rp-cards">
                  <div class="rp-card rp-card-main">
                    <span class="rp-card-label">{{ entry.view.label }}</span>
                    <span class="rp-card-value">{{ entry.view.value }}</span>
                  </div>
                </div>
                <template v-else-if="entry.view.kind === 'data'">
                  <div class="rp-cards">
                    <div v-for="card in highlights(entry.view, entry.section.fieldFormats)" :key="card.label" class="rp-card">
                      <span class="rp-card-label">{{ card.label }}</span>
                      <span class="rp-card-value rp-card-value-sm">{{ card.value }}</span>
                    </div>
                  </div>
                  <figure v-if="entry.view.chart && entry.view.chartType" class="rp-figure">
                    <ChatResultChart :chart="entry.view.chart" :type="entry.view.chartType" :row-limit="10" print />
                    <figcaption>Figura {{ entry.figure }} — {{ entry.section.title }}</figcaption>
                  </figure>
                  <ChatResultTable :rows="entry.view.rows" :field-formats="entry.section.fieldFormats" print />
                  <p class="rp-table-note">Mostrando {{ entry.view.rows.length }} de {{ entry.view.total }} registros.</p>
                </template>
              </section>

              <!-- Metodologia -->
              <section class="rp-method">
                <div class="rp-section-divider">
                  <span class="rp-section-number">A</span>
                  <h2 class="rp-section-title">Metodologia</h2>
                </div>
                <ul class="rp-method-list">
                  <li v-if="report.contextoNome"><strong>Contexto de dados:</strong> {{ report.contextoNome }}</li>
                  <li v-if="dataVersion"><strong>Versão dos dados:</strong> {{ dataVersion }}</li>
                  <li><strong>Gerado em:</strong> {{ generatedAt }}</li>
                  <li><strong>Identificador do relatório:</strong> <span class="rp-mono">{{ messageId }}</span></li>
                  <li>Cada seção corresponde a uma pergunta feita no chat do Adito. O SQL abaixo foi reexecutado sobre os dados na geração deste documento; os números, gráficos e tabelas foram calculados diretamente dos dados, sem uso de IA.</li>
                </ul>
                <div v-for="entry in entries" :key="`sql-${entry.number}`" class="rp-sql">
                  <p class="rp-sql-title">{{ entry.number }}. {{ entry.section.title }}</p>
                  <pre>{{ entry.section.sql }}</pre>
                </div>
              </section>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </Teleport>
</template>

<style>
/* Fora da tela até imprimir; os gráficos precisam de largura real para renderizar. */
.report-print-root {
  position: fixed;
  left: -10000px;
  top: 0;
  width: 182mm;
  background: #ffffff;
  color: #1f2a24;
  font-family: var(--font-sans, 'IBM Plex Sans', system-ui, sans-serif);
  font-size: 10pt;
  line-height: 1.45;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

@media print {
  @page {
    size: A4;
    margin: 14mm 14mm 16mm;

    @bottom-right {
      content: "Página " counter(page) " de " counter(pages);
      font-size: 8pt;
      color: #6b7a70;
    }
  }

  @page :first {
    margin: 0;

    @bottom-right {
      content: none;
    }
  }

  html.adito-printing,
  html.adito-printing body {
    background: #ffffff !important;
    height: auto !important;
    overflow: visible !important;
  }

  html.adito-printing body > :not(.report-print-root) {
    display: none !important;
  }

  html.adito-printing .report-print-root {
    position: static;
    left: auto;
    width: auto;
  }
}

.report-print-root .rp-mono { font-family: var(--font-mono, ui-monospace, monospace); }

/* Capa: página inteira, sem cabeçalho nem rodapé */
.report-print-root .rp-cover {
  position: relative;
  box-sizing: border-box;
  height: 297mm;
  padding: 38mm 22mm 24mm;
  break-after: page;
  page-break-after: always;
  display: flex;
  flex-direction: column;
}
.report-print-root .rp-cover-band {
  position: absolute;
  inset: 0 0 auto 0;
  height: 14mm;
  background: linear-gradient(90deg, #16462b 0%, #2b7a42 60%, #749e30 100%);
}
.report-print-root .rp-cover-logo { width: 34mm; height: auto; }
.report-print-root .rp-kicker {
  margin-top: 26mm;
  font-size: 10pt;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #2b7a42;
}
.report-print-root .rp-cover-title {
  margin: 4mm 0 0;
  font-size: 26pt;
  line-height: 1.15;
  font-weight: 700;
  color: #16462b;
  border-left: 3mm solid #749e30;
  padding-left: 5mm;
}
.report-print-root .rp-cover-context { margin-top: 4mm; font-size: 12pt; color: #465249; }
.report-print-root .rp-cover-meta {
  margin: 14mm 0 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4mm 10mm;
  border-top: 0.4mm solid #d9e3db;
  padding-top: 6mm;
}
.report-print-root .rp-cover-meta dt { font-size: 8pt; text-transform: uppercase; letter-spacing: 0.1em; color: #6b7a70; }
.report-print-root .rp-cover-meta dd { margin: 1mm 0 0; font-size: 11pt; font-weight: 600; color: #1f2a24; }
.report-print-root .rp-seal {
  margin-top: auto;
  display: flex;
  gap: 5mm;
  align-items: center;
  border: 0.4mm solid #2b7a42;
  border-radius: 3mm;
  padding: 5mm 6mm;
  background: #f3f8f4;
}
.report-print-root .rp-seal-logo { width: 14mm; height: auto; }
.report-print-root .rp-seal strong { font-size: 11pt; color: #16462b; }
.report-print-root .rp-seal p { margin: 1mm 0 0; font-size: 9pt; color: #465249; }

/* Cabeçalho e rodapé repetidos em todas as páginas depois da capa */
.report-print-root .rp-layout { width: 100%; border-collapse: collapse; }
.report-print-root .rp-layout > thead > tr > td,
.report-print-root .rp-layout > tfoot > tr > td,
.report-print-root .rp-layout > tbody > tr > td { padding: 0; }
.report-print-root .rp-header {
  display: flex;
  align-items: center;
  gap: 3mm;
  padding-bottom: 2.5mm;
  margin-bottom: 6mm;
  border-bottom: 0.6mm solid #2b7a42;
}
.report-print-root .rp-header-logo { width: 8mm; height: auto; }
.report-print-root .rp-header-title { flex: 1; font-size: 9pt; font-weight: 600; color: #16462b; }
.report-print-root .rp-header-tag { font-size: 8pt; color: #6b7a70; text-transform: uppercase; letter-spacing: 0.08em; }
.report-print-root .rp-footer {
  display: flex;
  justify-content: space-between;
  gap: 4mm;
  margin-top: 6mm;
  padding-top: 2mm;
  border-top: 0.3mm solid #d9e3db;
  font-size: 8pt;
  color: #6b7a70;
}
.report-print-root .rp-footer-seal { font-weight: 700; color: #2b7a42; }

.report-print-root .rp-h2 { font-size: 14pt; color: #16462b; margin: 0 0 4mm; }
.report-print-root .rp-toc { break-after: page; page-break-after: always; }
.report-print-root .rp-toc ol { list-style: none; margin: 0; padding: 0; }
.report-print-root .rp-toc li {
  display: flex;
  gap: 4mm;
  padding: 2.5mm 0;
  border-bottom: 0.3mm dashed #d9e3db;
  font-size: 11pt;
}
.report-print-root .rp-toc-number { width: 8mm; font-weight: 700; color: #2b7a42; }

/* Seções */
.report-print-root .rp-section { margin-bottom: 10mm; }
.report-print-root .rp-section + .rp-section { break-before: page; page-break-before: always; }
.report-print-root .rp-section-divider {
  display: flex;
  align-items: stretch;
  margin-bottom: 5mm;
  background: #f3f8f4;
  border-left: 2mm solid #2b7a42;
  break-after: avoid;
}
.report-print-root .rp-section-number {
  display: flex;
  align-items: center;
  padding: 0 4mm;
  font-size: 16pt;
  font-weight: 700;
  color: #ffffff;
  background: #2b7a42;
}
.report-print-root .rp-section-title { margin: 0; padding: 3mm 4mm; font-size: 13pt; color: #16462b; }
.report-print-root .rp-cards { display: flex; gap: 4mm; margin-bottom: 5mm; break-inside: avoid; }
.report-print-root .rp-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1mm;
  border: 0.3mm solid #d9e3db;
  border-top: 1mm solid #749e30;
  border-radius: 2mm;
  padding: 3mm 4mm;
}
.report-print-root .rp-card-main { flex: 0 0 auto; min-width: 60mm; }
.report-print-root .rp-card-label { font-size: 8pt; text-transform: uppercase; letter-spacing: 0.08em; color: #6b7a70; }
.report-print-root .rp-card-value { font-size: 20pt; font-weight: 700; color: #16462b; }
.report-print-root .rp-card-value-sm { font-size: 12pt; }
.report-print-root .rp-figure { margin: 0 0 5mm; break-inside: avoid; page-break-inside: avoid; }
.report-print-root .rp-figure figcaption { margin-top: 1.5mm; font-size: 8.5pt; font-style: italic; color: #6b7a70; text-align: center; }
.report-print-root .report-print-chart { border: 0.3mm solid #e2e8df; border-radius: 2mm; padding: 2mm; }
.report-print-root .report-print-table table { width: 100%; }
.report-print-root .report-print-table thead { display: table-header-group; }
.report-print-root .report-print-th {
  background: #16462b;
  color: #ffffff;
  font-size: 8pt;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 2mm 3mm;
}
.report-print-root .report-print-tr { break-inside: avoid; page-break-inside: avoid; }
.report-print-root .report-print-tr:nth-child(even) { background: #f3f8f4; }
.report-print-root .report-print-td { padding: 1.6mm 3mm; border-bottom: 0.2mm solid #e2e8df; color: #1f2a24; }
.report-print-root .rp-table-note { margin-top: 1.5mm; font-size: 8pt; color: #6b7a70; }
.report-print-root .rp-note { padding: 3mm 4mm; border-radius: 2mm; background: #f5f6f5; color: #465249; }
.report-print-root .rp-note-warn { background: #fff7e6; color: #8a5a00; border: 0.3mm solid #f2d39a; }

/* Metodologia */
.report-print-root .rp-method { break-before: page; page-break-before: always; }
.report-print-root .rp-method-list { margin: 0 0 5mm; padding-left: 5mm; }
.report-print-root .rp-method-list li { margin-bottom: 1.5mm; }
.report-print-root .rp-sql { margin-bottom: 4mm; break-inside: avoid; }
.report-print-root .rp-sql-title { margin: 0 0 1mm; font-weight: 600; color: #16462b; }
.report-print-root .rp-sql pre {
  margin: 0;
  padding: 3mm;
  white-space: pre-wrap;
  word-break: break-word;
  background: #f5f6f5;
  border: 0.3mm solid #e2e8df;
  border-radius: 2mm;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 8pt;
  color: #1f2a24;
}
</style>
