import { expect, test } from '@playwright/test'
import { installTauriMock } from './helpers/tauriMock'

test.describe('Configurações e Administração', () => {
  test('permite testar, salvar e remover provedor de IA em Configurações', async ({ page }) => {
    await installTauriMock(page, { llmConfigured: false })
    await page.goto('/#/configuracoes')

    await expect(page.getByRole('heading', { name: 'Configurações' })).toBeVisible()
    await expect(page.getByText('Não configurada')).toBeVisible()

    const keyInput = page.getByLabel(/Chave API/i)
    await keyInput.fill('chave-valida-e2e')
    await page.getByRole('button', { name: /Testar e salvar|Salvar/i }).click()

    await expect(page.getByText(/Chave válida e guardada/i)).toBeVisible()
    await expect(page.getByText('Configurada', { exact: true })).toBeVisible()

    // Alterna para Ollama local sem chave via dropdown customizado e confirma privacidade 100% local
    await page.getByRole('combobox', { name: 'Provedor' }).click()
    await page.getByRole('option', { name: /Ollama \(Local\)/i }).click()
    await expect(page.getByText(/100% local — nenhum dado sai do seu computador/i)).toBeVisible()
    await page.getByRole('button', { name: /Testar e salvar/i }).click()
    await expect(page.getByText(/provedor local/i)).toBeVisible()
  })

  test('exibe abas principais, lista contextos e aviso de reindexação na Administração', async ({ page }) => {
    await installTauriMock(page, { llmProvider: 'openai', embeddingsNeedsRetrain: true })
    await page.goto('/#/admin')

    await expect(page.getByRole('button', { name: 'Base de conhecimento' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Auditoria SQL' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Contextos de dados' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sistema' })).toBeVisible()

    await expect(page.getByText(/Reindexação recomendada \(Wipe & Retrain\)/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /Wipe & Retrain/i })).toBeEnabled()

    await page.getByRole('button', { name: /Contextos de dados/i }).click()
    await expect(page.getByText('Contextos carregados')).toBeVisible()
    await expect(page.getByText('pesquisa-extensao-ifes')).toBeVisible()
  })
})
