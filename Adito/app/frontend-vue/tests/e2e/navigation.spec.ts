import { expect, test } from '@playwright/test'
import { installTauriMock } from './helpers/tauriMock'

test.describe('Navegação principal e layout', () => {
  test('navega entre todas as seções do menu lateral sem erros', async ({ page }) => {
    await installTauriMock(page)
    await page.goto('/#/chat')

    await expect(page.getByRole('heading', { name: 'Adito' })).toBeVisible()
    await expect(page.getByLabel('Pergunta sobre pesquisa e extensão')).toBeVisible()

    await page.getByRole('link', { name: 'Meu painel' }).click()
    await expect(page).toHaveURL(/#\/meu-dashboard/)

    await page.getByRole('link', { name: 'Explorar dados' }).click()
    await expect(page).toHaveURL(/#\/explorar/)
    await expect(page.getByRole('heading', { name: 'Explorar dados' })).toBeVisible()

    await page.getByRole('link', { name: 'Administração' }).click()
    await expect(page).toHaveURL(/#\/admin/)
    await expect(page.getByRole('button', { name: 'Base de conhecimento' })).toBeVisible()

    await page.getByRole('link', { name: 'Configurações' }).click()
    await expect(page).toHaveURL(/#\/configuracoes/)
    await expect(page.getByRole('heading', { name: 'Configurações' })).toBeVisible()
  })
})
