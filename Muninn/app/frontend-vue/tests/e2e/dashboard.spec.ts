import { expect, test } from '@playwright/test'
import { installTauriMock, trackPageErrors } from './helpers/tauriMock'

test.describe('Dashboard analítico', () => {
  test('renderiza KPIs acadêmicos e Top 10 projetos sem erros JS', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installTauriMock(page)
    await page.goto('/#/dashboard')

    await expect(page.getByText('Investimento estimado')).toBeVisible()
    await expect(page.getByText('R$ 320.000,00')).toBeVisible()
    await expect(page.getByText('236')).toBeVisible()
    await expect(page.getByText('Top 10 projetos por investimento')).toBeVisible()
    await expect(page.getByText('Monitoramento Inteligente de Redes')).toBeVisible()

    expect(getErrors()).toEqual([])
  })

  test('aplica filtro de ano e recalcula KPIs', async ({ page }) => {
    // Bug real exposto pela suíte E2E (Issue #71): em DashboardView.vue,
    // `v-model:filtros="filtros"` + `@update:filtros="fetchData"` não atualiza o
    // objeto reactive de `useDashboardData()` (deveria usar `@update:filtros="updateFilters"`).
    // Quando o PR de fix corrigir o bug, o Playwright avisará para remover este `test.fail()`.
    test.fail(true, 'Bug conhecido em DashboardView.vue: FilterBar não propaga filtros ao useDashboardData()')

    await installTauriMock(page)
    await page.goto('/#/dashboard')

    await expect(page.getByText('R$ 320.000,00')).toBeVisible()
    await page.locator('select').first().selectOption('2023')
    await expect(page.getByText('R$ 84.000,00')).toBeVisible({ timeout: 2500 })
    await expect(page.getByText('48', { exact: true })).toBeVisible({ timeout: 2500 })
  })
})
