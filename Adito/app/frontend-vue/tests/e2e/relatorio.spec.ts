import fs from 'node:fs'
import { expect, test, type Page } from '@playwright/test'
import { installTauriMock, trackPageErrors } from './helpers/tauriMock'

// Dados sintéticos, sem nomes de pessoas.
const POR_AREA = [
  { grande_area: 'Engenharias', total: 120 },
  { grande_area: 'Ciências Exatas e da Terra', total: 80 },
  { grande_area: 'Ciências Humanas', total: 45 },
  { grande_area: 'Ciências Biológicas', total: 30 },
]
const POR_ANO = [
  { ano: 2021, total: 30 },
  { ano: 2022, total: 45 },
  { ano: 2023, total: 60 },
  { ano: 2024, total: 52 },
]
const TOTAL = [{ total_projetos: 236 }]

async function ask(page: Page, question: string) {
  const input = page.getByLabel('Pergunta sobre pesquisa e extensão')
  await input.fill(question)
  await input.press('Enter')
  await expect(page.getByText(`Resposta para "${question}"`, { exact: false })).toBeVisible()
}

async function setup(page: Page) {
  await installTauriMock(page, {
    chatDataByQuestion: { 'por área': POR_AREA, 'por ano': POR_ANO, 'quantos': TOTAL, 'quebrado': POR_AREA },
  })
  await page.addInitScript(() => {
    ;(window as any).__printed = 0
    window.print = () => { (window as any).__printed += 1 }
    ;(window as any).__copied = ''
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: async (text: string) => { (window as any).__copied = text } },
    })
  })
  await page.goto('/#/chat')
  // Começa uma conversa nova (o núcleo simulado já tem uma conversa salva com resposta).
  await page.getByRole('button', { name: /Novo chat/i }).click()
}

async function createReport(page: Page) {
  await page.getByRole('button', { name: 'Mais opções' }).click()
  await page.getByRole('menuitem', { name: 'Criar relatório' }).click()
  return page.getByRole('region', { name: 'Criar relatório' })
}

test.describe('Relatório a partir das respostas do chat', () => {
  test('só aparece depois de uma resposta com dados e gera o relatório na conversa', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await setup(page)

    // Sem resposta, sem botão "Mais"
    await expect(page.getByRole('button', { name: 'Mais opções' })).toHaveCount(0)

    await ask(page, 'Projetos por área')
    await ask(page, 'Projetos por ano')
    await ask(page, 'Quantos projetos existem?')

    // O usuário deixa a primeira resposta em barras horizontais: o relatório usa o tipo da tela.
    await page.getByRole('group', { name: 'Tipo de gráfico' }).first().getByRole('button', { name: 'Barras horizontais', exact: true }).click()

    const form = await createReport(page)
    await expect(form).toBeVisible()
    await expect(form.getByText('3 de 3')).toBeVisible()
    await expect(form.getByLabel('Título do relatório')).not.toHaveValue('')

    // Desmarca, reordena e renomeia
    await form.getByLabel('Incluir a seção: Quantos projetos existem?').uncheck()
    await expect(form.getByText('2 de 3')).toBeVisible()
    await form.getByRole('button', { name: 'Descer a seção 1' }).click()
    await form.getByLabel('Título da seção 2').fill('Projetos por grande área')
    await form.getByLabel('Título do relatório').fill('Panorama de projetos de pesquisa')

    // Título vazio bloqueia
    await form.getByLabel('Título da seção 1').fill('')
    await expect(form.getByRole('button', { name: 'Gerar relatório' })).toBeDisabled()
    await form.getByLabel('Título da seção 1').fill('Evolução anual de projetos')

    await form.getByRole('button', { name: 'Gerar relatório' }).click()
    await expect(form).toBeHidden()

    const sent = await page.evaluate(() => (window as any).__TAURI_MOCK_LAST_REPORT__.params)
    expect(sent.title).toBe('Panorama de projetos de pesquisa')
    expect(sent.sections.map((s: any) => s.title)).toEqual(['Evolução anual de projetos', 'Projetos por grande área'])
    expect(sent.sections[1].chart_type).toBe('horizontal_bar')

    const report = page.getByTestId('report-message')
    await expect(report.getByRole('heading', { name: 'Panorama de projetos de pesquisa' })).toBeVisible()
    const sections = report.getByTestId('report-section')
    await expect(sections).toHaveCount(2)
    await expect(sections.nth(0)).toContainText('Evolução anual de projetos')
    await expect(sections.nth(0).locator('.apexcharts-line-series')).toBeVisible()
    await expect(sections.nth(1).locator('.apexcharts-bar-series')).toBeVisible()
    await expect(sections.nth(1)).toContainText('Mostrando 4 de 4 registros')
    await expect(report).toContainText('sem uso de IA')

    // SQL da seção
    await sections.nth(0).getByRole('button', { name: 'Ver SQL da seção' }).click()
    await expect(sections.nth(0).locator('pre')).toContainText('SELECT')

    // Copiar em Markdown
    await report.getByRole('button', { name: /Copiar/ }).click()
    const copied = await page.evaluate(() => (window as any).__copied as string)
    expect(copied).toContain('# Panorama de projetos de pesquisa')
    expect(copied).toContain('## 1. Evolução anual de projetos')
    expect(copied).toContain('| grande area | total |')
    expect(copied).not.toContain('Resposta para')

    expect(getErrors()).toEqual([])
  })

  test('seção com SQL quebrado mostra aviso sem derrubar o relatório; resultado escalar vira cartão', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await setup(page)
    await ask(page, 'Projeto quebrado')
    await ask(page, 'Quantos projetos existem?')

    const form = await createReport(page)
    await form.getByRole('button', { name: 'Gerar relatório' }).click()

    const sections = page.getByTestId('report-message').getByTestId('report-section')
    await expect(sections).toHaveCount(2)
    await expect(sections.nth(0).getByRole('alert')).toContainText('os dados mudaram desde a pergunta')
    await expect(sections.nth(1)).toContainText('total projetos')
    await expect(sections.nth(1)).toContainText('236')
    expect(getErrors()).toEqual([])
  })

  test('exporta o PDF com abertura, seções, tabelas, figuras e apêndice com o SQL', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await setup(page)
    await ask(page, 'Projetos por área')
    await ask(page, 'Projetos por ano')
    await ask(page, 'Quantos projetos existem?')

    const form = await createReport(page)
    await form.getByLabel('Título do relatório').fill('Panorama de projetos de pesquisa')
    await form.getByRole('button', { name: 'Gerar relatório' }).click()

    const report = page.getByTestId('report-message')
    await expect(report.getByTestId('report-section')).toHaveCount(3)
    await report.getByRole('button', { name: 'Exportar PDF' }).click()
    await expect.poll(() => page.evaluate(() => (window as any).__printed)).toBe(1)

    expect(await page.evaluate(() => document.title)).toMatch(/^Relatório - Panorama de projetos de pesquisa - \d{4}-\d{2}-\d{2}$/)
    expect(await page.evaluate(() => document.documentElement.classList.contains('adito-printing'))).toBe(true)

    const root = page.locator('.report-print-root')
    await expect(root.locator('.rp-cover-title')).toHaveText('Panorama de projetos de pesquisa')
    await expect(root.locator('.rp-cover')).toContainText('Base de dados')
    await expect(root.locator('.rp-header')).toHaveText('Adito')
    await expect(root).not.toContainText('Gerado pelo Adito')
    await expect(root.locator('.rp-toc li')).toHaveCount(4)
    await expect(root.locator('.rp-section')).toHaveCount(3)
    await expect(root.locator('figcaption')).toHaveText(['Figura 1 – Projetos por área', 'Figura 2 – Projetos por ano'])
    await expect(root.locator('.rp-caption').filter({ hasText: /^Tabela/ })).toHaveText(['Tabela 1 – Projetos por área', 'Tabela 2 – Projetos por ano'])
    await expect(root.locator('.rp-caption').filter({ hasText: /^Quadro/ })).toHaveCount(1)
    await expect(root.locator('.rp-card-value').first()).toBeVisible()
    await expect(root.locator('.rp-method')).toContainText('sem uso de IA')
    await expect(root.locator('.rp-sql')).toHaveCount(3)
    await expect(root.locator('.apexcharts-canvas')).toHaveCount(2)

    // PDF de verdade pelo Chromium (mesmo motor do WebView2): mídia de impressão e A4.
    await page.emulateMedia({ media: 'print' })
    const pdf = await page.pdf({ format: 'A4', preferCSSPageSize: true, printBackground: true })
    const out = process.env.REPORT_PDF_OUT
    if (out) fs.writeFileSync(out, pdf)
    const pages = (pdf.toString('latin1').match(/\/Type\s*\/Page[^s]/g) || []).length
    // abertura + 3 seções (uma por página; o apêndice com o SQL segue a última)
    expect(pages).toBeGreaterThanOrEqual(4)

    // Fechar a impressão devolve o app ao normal
    await page.evaluate(() => window.dispatchEvent(new Event('afterprint')))
    expect(await page.evaluate(() => document.documentElement.classList.contains('adito-printing'))).toBe(false)
    await expect(root).toHaveCount(0)
    expect(getErrors()).toEqual([])
  })

  test('libera o "Exportar PDF" quando a impressão fecha sem afterprint ou a conversa muda', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await setup(page)
    await ask(page, 'Projetos por área')
    const form = await createReport(page)
    await form.getByRole('button', { name: 'Gerar relatório' }).click()

    const report = page.getByTestId('report-message')
    const exportButton = report.getByRole('button', { name: 'Exportar PDF' })
    const printingClass = () => page.evaluate(() => document.documentElement.classList.contains('adito-printing'))

    // WebKitGTK: cancelar a janela de impressão pode não disparar afterprint; a volta do foco limpa.
    await exportButton.click()
    await expect.poll(() => page.evaluate(() => (window as any).__printed)).toBe(1)
    expect(await printingClass()).toBe(true)
    await page.evaluate(() => window.dispatchEvent(new Event('focus')))
    await expect.poll(printingClass).toBe(false)
    await expect(exportButton).toBeEnabled()

    // Sair da conversa com a impressão aberta também limpa
    await exportButton.click()
    await expect.poll(() => page.evaluate(() => (window as any).__printed)).toBe(2)
    expect(await printingClass()).toBe(true)
    await page.getByRole('button', { name: /Novo chat/i }).click()
    await expect.poll(printingClass).toBe(false)
    await expect(page.locator('.report-print-root')).toHaveCount(0)
    expect(getErrors()).toEqual([])
  })
})
