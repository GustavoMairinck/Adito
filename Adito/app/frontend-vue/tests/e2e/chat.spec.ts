import { expect, test } from '@playwright/test'
import { installTauriMock, trackPageErrors } from './helpers/tauriMock'

test.describe('Chat estratégico', () => {
  test('envia pergunta, recebe streaming, exibe SQL gerado e inicia novo chat sem erros JS', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installTauriMock(page)
    await page.goto('/#/chat')

    const input = page.getByLabel('Pergunta sobre pesquisa e extensão')
    await expect(input).toBeVisible()
    await input.fill('Quantos projetos existem por grande área?')
    await input.press('Enter')

    await expect(page.getByText(/existem 236 projetos de pesquisa ativos no Campus Serra/i)).toBeVisible()
    await expect(page.getByText('Engenharias').first()).toBeVisible()

    // Abre o SQL gerado da resposta recém-recebida
    await page.getByRole('button', { name: /Ver SQL Gerado/i }).last().click()
    await expect(page.getByText(/SELECT grande_area/i)).toBeVisible()

    // Cria novo chat e confirma que o painel volta ao estado inicial limpo
    await page.getByRole('button', { name: /Novo chat/i }).click()
    await expect(page.getByText(/existem 236 projetos de pesquisa ativos no Campus Serra/i)).toBeHidden()

    expect(getErrors()).toEqual([])
  })

  test('exibe aviso e link para Configurações quando a chave LLM não está configurada', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installTauriMock(page, { llmConfigured: false })
    await page.goto('/#/chat')

    const banner = page.getByRole('link', { name: /falta a chave do Gemini/i })
    await expect(banner).toBeVisible()
    await banner.click()
    await expect(page).toHaveURL(/#\/configuracoes/)

    expect(getErrors()).toEqual([])
  })

  test('exibe erro amigável quando o núcleo devolve 503 no stream do chat', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installTauriMock(page, { llmConfigured: true, chatError503: true })
    await page.goto('/#/chat')

    const input = page.getByLabel('Pergunta sobre pesquisa e extensão')
    await input.fill('Quantas bolsas existem?')
    await input.press('Enter')

    await expect(page.getByText(/Chave do Gemini não configurada/i)).toBeVisible()
    expect(getErrors()).toEqual([])
  })
})
