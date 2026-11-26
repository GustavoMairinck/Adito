import { expect, test } from '@playwright/test'
import { installTauriMock, trackPageErrors } from './helpers/tauriMock'

test.describe('Sidebar unificada', () => {
  test('mantém largura expandida de 360px, alterna busca pela lupa e permite fixar/renomear conversas', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installTauriMock(page)
    await page.setViewportSize({ width: 1280, height: 800 })
    await page.goto('/#/chat')

    const sidebar = page.getByTestId('sidebar-nav')
    await expect(sidebar).toBeVisible()
    const box = await sidebar.boundingBox()
    expect(Math.round(box?.width || 0)).toBe(360)

    await expect(page.getByTestId('theme-toggle-btn')).toBeVisible()
    await expect(page.getByText('Powered by LEDS & SmartIdea')).toBeVisible()

    const searchBtn = page.getByRole('button', { name: 'Buscar conversas' })
    await searchBtn.click()
    await expect(page.getByLabel('Filtrar conversas')).toBeVisible()
    await searchBtn.click()
    await expect(page.getByLabel('Filtrar conversas')).toBeHidden()

    const convItem = page.locator('.conv-item', { hasText: 'Panorama de Projetos' }).first()
    await convItem.hover()
    await convItem.getByRole('button', { name: 'Fixar conversa' }).click()
    await expect(page.getByText('Fixadas')).toBeVisible()

    await convItem.hover()
    await convItem.getByRole('button', { name: 'Renomear conversa' }).click()
    const renameInput = page.getByLabel('Renomear conversa')
    await renameInput.fill('Projetos Renomeado')
    await renameInput.press('Enter')
    await expect(page.locator('.conv-item', { hasText: 'Projetos Renomeado' })).toBeVisible()

    expect(getErrors()).toEqual([])
  })
})
