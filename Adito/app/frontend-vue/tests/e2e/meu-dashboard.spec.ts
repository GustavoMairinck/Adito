import { expect, test } from '@playwright/test'
import { installTauriMock, trackPageErrors } from './helpers/tauriMock'

test.describe('Meu painel — Pinning e gestão de widgets', () => {
  test('fixa análise do chat no painel, visualiza gráfico salvo e exclui widget sem erros JS', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installTauriMock(page)
    await page.goto('/#/chat')

    // Envia pergunta e fixa a resposta no painel
    const input = page.getByLabel('Pergunta sobre pesquisa e extensão')
    await input.fill('Quantos projetos existem por grande área?')
    await input.press('Enter')

    await expect(page.getByText(/existem 236 projetos de pesquisa ativos no Campus Serra/i)).toBeVisible()
    await page.getByRole('button', { name: /Fixar no Dashboard/i }).last().click()

    await expect(page.getByRole('heading', { name: 'Fixar no Dashboard' })).toBeVisible()
    const titleInput = page.getByPlaceholder('Ex: Evolução de Pagamentos')
    await titleInput.fill('Projetos por Grande Área (E2E)')
    await page.getByRole('button', { name: /Salvar no Painel/i }).click()

    // Navega para Meu painel e confirma que tanto o widget inicial quanto o recém-fixado aparecem
    await page.getByRole('link', { name: 'Meu painel' }).click()
    await expect(page).toHaveURL(/#\/meu-dashboard/)
    await expect(page.getByText('Bolsas por Ano', { exact: true })).toBeVisible()
    await expect(page.getByText('Projetos por Grande Área (E2E)', { exact: true })).toBeVisible()

    // Exclui o widget recém-criado e valida que desaparece da tela
    await page.getByRole('button', { name: 'Excluir Painel' }).last().click()
    const confirmBtn = page.getByRole('button', { name: /Confirmar|Excluir|Remover/i }).last()
    if (await confirmBtn.isVisible().catch(() => false)) {
      await confirmBtn.click()
    }
    await expect(page.getByText('Projetos por Grande Área (E2E)', { exact: true })).toBeHidden()

    expect(getErrors()).toEqual([])
  })
})
