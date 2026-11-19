import { expect, test } from '@playwright/test'
import { installLiveBridge, trackPageErrors } from './helpers/tauriMock'

const bridgeUrl = process.env.E2E_BRIDGE_URL || 'http://127.0.0.1:18765'

test.describe('E2E Live — Frontend + Núcleo Python real (dados.db)', () => {
  test('carrega Dashboard e Explorar Dados com registros reais e busca no dados.db sem erros JS', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installLiveBridge(page, bridgeUrl)

    await page.goto('/#/dashboard')
    await expect(page.getByText('Investimento estimado')).toBeVisible()
    await expect(page.getByText('Top 10 projetos por investimento')).toBeVisible()
    await expect(page.locator('table tbody tr').first()).toBeVisible()

    await page.goto('/#/explorar')
    await expect(page.locator('table tbody tr').first()).toBeVisible()

    const searchInput = page.locator('input[type="search"], input[placeholder*="Buscar"], input[placeholder*="Filtrar"]').first()
    await searchInput.fill('Serra')
    await expect(page.locator('table tbody tr').first()).toBeVisible()

    expect(getErrors()).toEqual([])
  })

  test('filtra Dashboard por ano real do dados.db e atualiza KPIs', async ({ page }) => {
    // Bug conhecido em DashboardView.vue (`v-model:filtros` + `@update:filtros="fetchData"`).
    // Quando o PR de fix resolver o problema, o Playwright sinalizará para remover `test.fail()`.
    test.fail(true, 'Bug conhecido em DashboardView.vue: filtro de ano não altera KPIs contra dados.db')

    await installLiveBridge(page, bridgeUrl)
    await page.goto('/#/dashboard')
    await expect(page.locator('table tbody tr').first()).toBeVisible()

    const projetosCard = page.locator('.premium-card', { hasText: 'Projetos distintos no filtro' })
    await expect(projetosCard).not.toContainText('...')
    const projetosAntes = (await projetosCard.textContent()) || ''

    const anoSelect = page.locator('select').first()
    await expect.poll(async () => anoSelect.locator('option').count()).toBeGreaterThan(2)
    const firstRealYear = await anoSelect.locator('option').nth(1).getAttribute('value')
    expect(firstRealYear).toBeTruthy()
    await anoSelect.selectOption(firstRealYear!)
    await expect.poll(async () => {
      const txt = (await projetosCard.textContent()) || ''
      return txt.includes('...') ? projetosAntes : txt
    }, { timeout: 2500 }).not.toBe(projetosAntes)
  })
})
