<script setup lang="ts">
import { computed } from 'vue'
import ChatResultChart from '@/modules/chat/components/ChatResultChart.vue'
import ChatResultTable from '@/modules/chat/components/ChatResultTable.vue'
import type { ChatReport } from '@/modules/chat/types'
import { SECTION_EMPTY_TEXT, formatDateTime, type SectionView } from '@/modules/chat/utils/report'

/**
 * Página de impressão do relatório (FR12–FR18). Fica fora da tela até a impressão; ao imprimir,
 * `html.adito-printing` esconde o app e mostra só esta página, sempre em tema claro.
 * Visual de documento formal (fonte Arial, margens ABNT): marca pequena do Adito no topo de toda
 * página (thead repetido), número da página no canto superior direito (`@page`), sem rodapé.
 * Cada pergunta vira uma seção com Tabela N e Figura N (ou Quadro N para número único), com a fonte.
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

const baseLabel = computed(() => {
  const nome = props.report.contextoNome || 'base do Adito'
  return props.dataVersion ? `${nome}, versão ${props.dataVersion}` : nome
})
const sourceText = computed(() => `Fonte: Adito, ${baseLabel.value}.`)

/** Numeração própria de tabelas, figuras e quadros, como em documento formal. */
const entries = computed(() => {
  let table = 0
  let figure = 0
  let quadro = 0
  return props.report.sections.map((section, index) => {
    const view = props.views[index]
    const isData = view.kind === 'data'
    const hasChart = isData && !!view.chart && !!view.chartType
    return {
      section,
      view,
      number: index + 1,
      table: isData ? ++table : null,
      figure: hasChart ? ++figure : null,
      quadro: view.kind === 'scalar' ? ++quadro : null,
    }
  })
})
</script>

<template>
  <Teleport to="body">
    <div class="report-print-root" :data-report-print="messageId" aria-hidden="true">
      <table class="rp-layout">
        <thead>
          <tr>
            <td>
              <div class="rp-header">
                <img src="/brand/adito-light.png" alt="" class="rp-header-logo">
                <span class="rp-header-name">Adito</span>
              </div>
            </td>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <!-- Abertura: título, dados do relatório e conteúdo -->
              <section class="rp-cover">
                <p v-if="report.contextoNome" class="rp-org">{{ report.contextoNome }}</p>
                <h1 class="rp-cover-title">{{ report.title }}</h1>
                <table class="rp-info">
                  <tbody>
                    <tr><th>Base de dados</th><td>{{ baseLabel }}</td></tr>
                    <tr><th>Gerado em</th><td>{{ generatedAt }}</td></tr>
                    <tr v-if="appVersion"><th>Versão do Adito</th><td>{{ appVersion }}</td></tr>
                    <tr><th>Identificador</th><td>{{ shortId }}</td></tr>
                  </tbody>
                </table>

                <section class="rp-toc">
                  <p class="rp-toc-title">Conteúdo</p>
                  <ol>
                    <li v-for="entry in entries" :key="`toc-${entry.number}`">
                      <span class="rp-toc-number">{{ entry.number }}</span>
                      <span>{{ entry.section.title }}</span>
                    </li>
                    <li>
                      <span class="rp-toc-number">A</span>
                      <span>Consultas utilizadas</span>
                    </li>
                  </ol>
                </section>
              </section>

              <!-- Uma seção por pergunta -->
              <section v-for="entry in entries" :key="`sec-${entry.number}`" class="rp-section">
                <h2 class="rp-h2">{{ entry.number }} {{ entry.section.title }}</h2>

                <p v-if="entry.view.kind === 'error'" class="rp-note rp-note-warn">{{ entry.view.message }}</p>
                <p v-else-if="entry.view.kind === 'empty'" class="rp-note">{{ SECTION_EMPTY_TEXT }}</p>

                <div v-else-if="entry.view.kind === 'scalar'" class="rp-float">
                  <p class="rp-caption">Quadro {{ entry.quadro }} – {{ entry.section.title }}</p>
                  <table class="rp-quadro">
                    <thead><tr><th>Indicador</th><th class="rp-num">Valor</th></tr></thead>
                    <tbody>
                      <tr>
                        <td class="rp-quadro-label">{{ entry.view.label }}</td>
                        <td class="rp-num rp-card-value">{{ entry.view.value }}</td>
                      </tr>
                    </tbody>
                  </table>
                  <p class="rp-source">{{ sourceText }}</p>
                </div>

                <template v-else-if="entry.view.kind === 'data'">
                  <div class="rp-float">
                    <p class="rp-caption">Tabela {{ entry.table }} – {{ entry.section.title }}</p>
                    <ChatResultTable :rows="entry.view.rows" :field-formats="entry.section.fieldFormats" print />
                    <p class="rp-source">{{ sourceText }}</p>
                    <p v-if="entry.view.total > entry.view.rows.length" class="rp-source rp-table-note">
                      Nota: mostrando {{ entry.view.rows.length }} de {{ entry.view.total }} registros.
                    </p>
                  </div>
                  <figure v-if="entry.view.chart && entry.view.chartType" class="rp-float rp-figure">
                    <figcaption class="rp-caption">Figura {{ entry.figure }} – {{ entry.section.title }}</figcaption>
                    <ChatResultChart :chart="entry.view.chart" :type="entry.view.chartType" :row-limit="10" print />
                    <p class="rp-source">{{ sourceText }}</p>
                  </figure>
                </template>
              </section>

              <!-- Apêndice com o SQL de cada seção -->
              <section class="rp-method">
                <h2 class="rp-h2">Apêndice A – Consultas utilizadas</h2>
                <div v-for="entry in entries" :key="`sql-${entry.number}`" class="rp-sql">
                  <p class="rp-sql-title">{{ entry.number }} {{ entry.section.title }}</p>
                  <pre>{{ entry.section.sql }}</pre>
                </div>
                <p class="rp-method-note">Números calculados diretamente da base, sem uso de IA.</p>
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
  width: 160mm;
  background: #ffffff;
  color: #000000;
  font-family: Arial, 'Liberation Sans', Helvetica, sans-serif;
  font-size: 12pt;
  line-height: 1.5;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

@media print {
  /* Margens no padrão ABNT (3 cm em cima e à esquerda, 2 cm embaixo e à direita). */
  @page {
    size: A4;
    margin: 3cm 2cm 2cm 3cm;

    @top-right {
      content: counter(page);
      font-family: Arial, 'Liberation Sans', Helvetica, sans-serif;
      font-size: 10pt;
      color: #000000;
      vertical-align: bottom;
      padding-bottom: 8mm;
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

/* Fonte única do documento (o app usa outra fonte nos títulos). */
.report-print-root,
.report-print-root :where(h1, h2, p, span, th, td, li, figcaption, div) {
  font-family: Arial, 'Liberation Sans', Helvetica, sans-serif;
}

/* Marca pequena do Adito no topo de toda página (thead se repete no Chromium e no WebKit). */
.report-print-root .rp-layout { width: 100%; border-collapse: collapse; }
.report-print-root .rp-layout > thead > tr > td,
.report-print-root .rp-layout > tbody > tr > td { padding: 0; }
.report-print-root .rp-header { display: flex; align-items: center; gap: 1.5mm; margin-bottom: 6mm; }
.report-print-root .rp-header-logo { width: 4.5mm; height: auto; }
.report-print-root .rp-header-name { font-size: 9pt; font-weight: 700; color: #1f5f3a; }

/* Abertura */
.report-print-root .rp-cover { break-after: page; page-break-after: always; padding-top: 12mm; }
.report-print-root .rp-org { margin: 0; font-size: 10pt; letter-spacing: 0.04em; text-transform: uppercase; color: #333333; }
.report-print-root .rp-cover-title {
  margin: 2mm 0 6mm;
  padding-bottom: 3.5mm;
  border-bottom: 0.5mm solid #1f5f3a;
  font-size: 18pt;
  line-height: 1.25;
  font-weight: 700;
}
.report-print-root .rp-info { border-collapse: collapse; font-size: 11pt; margin-bottom: 10mm; }
.report-print-root .rp-info th { text-align: left; font-weight: 700; padding: 0.6mm 6mm 0.6mm 0; vertical-align: top; }
.report-print-root .rp-info td { padding: 0.6mm 0; }
.report-print-root .rp-toc-title { margin: 0 0 1.5mm; font-weight: 700; }
.report-print-root .rp-toc ol { list-style: none; margin: 0; padding: 0; }
.report-print-root .rp-toc li { display: flex; gap: 6mm; padding: 1mm 0; border-bottom: 0.25mm solid #dddddd; }
.report-print-root .rp-toc-number { width: 6mm; }

/* Seções: uma por página */
.report-print-root .rp-section + .rp-section { break-before: page; page-break-before: always; }
.report-print-root .rp-h2 {
  margin: 0 0 4mm;
  padding-bottom: 1.5mm;
  border-bottom: 0.3mm solid #1f5f3a;
  font-size: 13pt;
  font-weight: 700;
  break-after: avoid;
}
.report-print-root .rp-float { margin: 0 0 8mm; break-inside: avoid; page-break-inside: avoid; }
.report-print-root .rp-caption { margin: 0 0 1.5mm; font-size: 10pt; line-height: 1.2; text-align: center; }
.report-print-root .rp-source { margin: 1.5mm 0 0; font-size: 10pt; line-height: 1.2; }
.report-print-root .rp-table-note { margin-top: 0.5mm; color: #444444; }
.report-print-root .rp-figure figcaption { font-style: normal; color: #000000; }

/* Tabelas no padrão IBGE: traço grosso em cima e embaixo, sem linhas verticais */
.report-print-root .report-print-table table,
.report-print-root .rp-quadro { width: 100%; border-collapse: collapse; font-size: 10pt; line-height: 1.3; }
.report-print-root .report-print-table thead { display: table-header-group; }
.report-print-root .report-print-th,
.report-print-root .rp-quadro th {
  background: transparent;
  color: #000000;
  font-size: 10pt;
  font-weight: 700;
  text-transform: none;
  letter-spacing: normal;
  padding: 1.4mm 2mm;
  border-top: 0.5mm solid #000000;
  border-bottom: 0.3mm solid #000000;
}
.report-print-root .report-print-th::first-letter,
.report-print-root .rp-quadro-label::first-letter { text-transform: uppercase; }
.report-print-root .report-print-tr { break-inside: avoid; page-break-inside: avoid; background: transparent; }
.report-print-root .report-print-td,
.report-print-root .rp-quadro td { padding: 1mm 2mm; border-bottom: none; color: #000000; }
.report-print-root .report-print-table tbody tr:last-child td,
.report-print-root .rp-quadro tbody tr:last-child td { border-bottom: 0.5mm solid #000000; }
.report-print-root .rp-num { text-align: right !important; }
.report-print-root .rp-card-value { font-size: 16pt; font-weight: 700; }

.report-print-root .rp-note { padding: 3mm 4mm; background: #f5f5f5; color: #333333; font-size: 11pt; }
.report-print-root .rp-note-warn { background: #fff7e6; color: #8a5a00; border: 0.3mm solid #f2d39a; }

/* Apêndice */
.report-print-root .rp-method { margin-top: 12mm; }
.report-print-root .rp-sql { margin-bottom: 3mm; break-inside: avoid; }
.report-print-root .rp-sql-title { margin: 0 0 1mm; font-size: 11pt; font-weight: 700; }
.report-print-root .rp-sql pre {
  margin: 0;
  padding: 2mm 3mm;
  white-space: pre-wrap;
  word-break: break-word;
  background: #f4f4f4;
  font-family: 'DejaVu Sans Mono', Consolas, ui-monospace, monospace;
  font-size: 8.5pt;
  line-height: 1.35;
  color: #000000;
}
.report-print-root .rp-method-note { margin: 4mm 0 0; font-size: 10pt; color: #444444; }
</style>
