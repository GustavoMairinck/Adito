import { expect, test } from '@playwright/test'
import { installTauriMock } from './helpers/tauriMock'

test.describe('Configurações e Administração', () => {
  test('permite testar, salvar e remover a chave do Gemini em Configurações', async ({ page }) => {
    await installTauriMock(page, { llmConfigured: false })
    await page.goto('/#/configuracoes')

    await expect(page.getByRole('heading', { name: 'Configurações' })).toBeVisible()
    await expect(page.getByText('Não configurada')).toBeVisible()

    const keyInput = page.locator('input[type="password"], input[placeholder*="AIza"], input').first()
    await keyInput.fill('chave-valida-e2e')
    await page.getByRole('button', { name: /Testar e salvar|Salvar/i }).click()

    await expect(page.getByText(/Chave válida e guardada/i)).toBeVisible()
    await expect(page.getByText('Configurada', { exact: true })).toBeVisible()
  })

  test('exibe abas principais e lista contextos carregados na tela de Administração', async ({ page }) => {
    await installTauriMock(page)
    await page.goto('/#/admin')

    await expect(page.getByText('Base de conhecimento')).toBeVisible()
    await expect(page.getByText('Auditoria SQL')).toBeVisible()
    await expect(page.getByText('Contextos de dados')).toBeVisible()
    await expect(page.getByText('Sistema')).toBeVisible()

    await page.getByRole('button', { name: /Contextos de dados/i }).click()
    await expect(page.getByText('Contextos carregados')).toBeVisible()
    await expect(page.getByText('pesquisa-extensao-ifes')).toBeVisible()
  })
})
