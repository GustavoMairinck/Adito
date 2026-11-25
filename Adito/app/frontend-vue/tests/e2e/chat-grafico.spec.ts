import { expect, test, type Page } from '@playwright/test'
import { installTauriMock, trackPageErrors } from './helpers/tauriMock'

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

// 12 áreas, 5 pequenas: passa do limite de 10 linhas e agrupa as pequenas em "Outros".
const COM_OUTROS = [
  { grande_area: 'Área 01', total: 300 },
  { grande_area: 'Área 02', total: 250 },
  { grande_area: 'Área 03', total: 200 },
  { grande_area: 'Área 04', total: 180 },
  { grande_area: 'Área 05', total: 150 },
  { grande_area: 'Área 06', total: 120 },
  { grande_area: 'Área 07', total: 100 },
  { grande_area: 'Área 08', total: 5 },
  { grande_area: 'Área 09', total: 4 },
  { grande_area: 'Área 10', total: 3 },
  { grande_area: 'Área 11', total: 2 },
  { grande_area: 'Área 12', total: 1 },
]

async function ask(page: Page, question = 'Quantos projetos existem por grande área?') {
  await page.goto('/#/chat')
  const input = page.getByLabel('Pergunta sobre pesquisa e extensão')
  await input.fill(question)
  await input.press('Enter')
  await expect(page.locator('.apexcharts-canvas').last()).toBeVisible()
}

const typeButton = (page: Page, label: string) =>
  page.getByRole('group', { name: 'Tipo de gráfico' }).last().getByRole('button', { name: label, exact: true })

async function barBoxes(page: Page) {
  const bars = page.locator('.apexcharts-bar-series path.apexcharts-bar-area')
  await expect(bars).toHaveCount(POR_AREA.length)
  // Espera a animação de entrada terminar antes de medir.
  await page.waitForTimeout(900)
  return Promise.all([bars.nth(0).boundingBox(), bars.nth(1).boundingBox()])
}

test.describe('Chat — tipos de gráfico', () => {
  test('desenha cada tipo do Meu painel e marca o botão escolhido', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installTauriMock(page, { chatData: POR_AREA })
    await ask(page)

    // Categoria que não é tempo abre em barras verticais.
    await expect(typeButton(page, 'Barras verticais')).toHaveAttribute('aria-pressed', 'true')
    await expect(page.locator('.apexcharts-bar-series')).toBeVisible()
    const [vertical1, vertical2] = await barBoxes(page)
    // Colunas em pé: lado a lado, com a mesma base.
    expect(Math.abs(vertical1!.x - vertical2!.x)).toBeGreaterThan(20)
    expect(Math.abs(vertical1!.y + vertical1!.height - (vertical2!.y + vertical2!.height))).toBeLessThan(2)

    await typeButton(page, 'Barras horizontais').click()
    await expect(typeButton(page, 'Barras horizontais')).toHaveAttribute('aria-pressed', 'true')
    await expect(typeButton(page, 'Barras verticais')).toHaveAttribute('aria-pressed', 'false')
    const [horizontal1, horizontal2] = await barBoxes(page)
    // Barras deitadas: uma embaixo da outra, saindo do mesmo ponto à esquerda.
    expect(Math.abs(horizontal1!.y - horizontal2!.y)).toBeGreaterThan(20)
    expect(Math.abs(horizontal1!.x - horizontal2!.x)).toBeLessThan(2)
    expect(horizontal1!.width).toBeGreaterThan(horizontal2!.width)
    await expect(page.locator('.apexcharts-yaxis-texts-g')).toContainText('Engenharias')

    await typeButton(page, 'Linhas').click()
    await expect(page.locator('.apexcharts-line-series')).toBeVisible()
    await expect(page.locator('.apexcharts-bar-series')).toHaveCount(0)

    await typeButton(page, 'Área').click()
    await expect(page.locator('.apexcharts-area-series')).toBeVisible()

    await typeButton(page, 'Pizza').click()
    await expect(typeButton(page, 'Pizza')).toHaveAttribute('aria-pressed', 'true')
    await expect(page.locator('.apexcharts-pie-series')).toHaveCount(POR_AREA.length)
    const legend = page.locator('.apexcharts-legend')
    await expect(legend).toBeVisible()
    for (const row of POR_AREA) {
      await expect(legend).toContainText(row.grande_area)
    }
    // Rótulos de porcentagem nas fatias.
    await expect(page.locator('.apexcharts-pie .apexcharts-datalabels').first()).toContainText('%')

    expect(getErrors()).toEqual([])
  })

  test('série no tempo abre em linhas', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installTauriMock(page, { chatData: POR_ANO })
    await ask(page, 'Quantos projetos por ano?')

    await expect(typeButton(page, 'Linhas')).toHaveAttribute('aria-pressed', 'true')
    await expect(page.locator('.apexcharts-line-series')).toBeVisible()
    expect(getErrors()).toEqual([])
  })

  test('pizza fica desativada, com o motivo, quando há mais de uma série', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installTauriMock(page, {
      chatData: POR_AREA.map(row => ({ ...row, valor: row.total * 1000 })),
    })
    await ask(page)

    const pie = typeButton(page, 'Pizza')
    await expect(pie).toBeDisabled()
    await expect(pie).toHaveAttribute('title', /uma única série/)
    await pie.click({ force: true })
    await expect(typeButton(page, 'Barras verticais')).toHaveAttribute('aria-pressed', 'true')
    await expect(page.locator('.apexcharts-pie-series')).toHaveCount(0)
    expect(getErrors()).toEqual([])
  })

  test('clicar em "Outros" na pizza expande as categorias agrupadas', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installTauriMock(page, { chatData: COM_OUTROS })
    await ask(page)

    await typeButton(page, 'Pizza').click()
    const legend = page.locator('.apexcharts-legend')
    await expect(legend).toContainText('Outros')
    await expect(page.getByText(/Clique na fatia ou na palavra/)).toBeVisible()

    await legend.locator('.apexcharts-legend-series', { hasText: 'Outros' }).click()
    await expect(page.getByRole('button', { name: /Reagrupar 'Outros'/ })).toBeVisible()
    await expect(legend).toContainText('Área 08')
    await expect(legend).not.toContainText('Outros')
    expect(getErrors()).toEqual([])
  })

  test('fixar no painel leva o tipo de gráfico escolhido', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installTauriMock(page)
    await ask(page)

    await typeButton(page, 'Pizza').click()
    await expect(page.locator('.apexcharts-pie-series').first()).toBeVisible()

    await page.getByRole('button', { name: /Fixar no Dashboard/i }).last().click()
    await page.getByPlaceholder('Ex: Evolução de Pagamentos').fill('Projetos por área em pizza (E2E)')
    await page.getByRole('button', { name: /Salvar no Painel/i }).click()
    await expect(page.getByText('Fixado com sucesso')).toBeVisible()

    const created = await page.evaluate(() => {
      const widgets = (window as any).__TAURI_MOCK_WIDGETS__ as Array<Record<string, unknown>>
      return widgets[widgets.length - 1]
    })
    expect(created.chart_type).toBe('pie')

    await page.getByRole('link', { name: 'Meu painel' }).click()
    await expect(page.getByText('Projetos por área em pizza (E2E)', { exact: true })).toBeVisible()
    await expect(page.locator('.apexcharts-pie-series').first()).toBeVisible()
    expect(getErrors()).toEqual([])
  })
})
