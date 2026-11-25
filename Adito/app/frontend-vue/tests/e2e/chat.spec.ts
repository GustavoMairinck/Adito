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

  test('aborta prompt pelo botão Parar, preserva texto digitado e permite enviar nova pergunta imediatamente', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installTauriMock(page, { chatStreamDelayMs: 600 })
    await page.goto('/#/chat')

    const input = page.getByLabel('Pergunta sobre pesquisa e extensão')
    await input.fill('Pergunta lenta para abortar')
    await input.press('Enter')

    // Botão Parar aparece e texto parcial começa a chegar
    const stopBtn = page.getByRole('button', { name: 'Parar geração' })
    await expect(stopBtn).toBeVisible()
    await expect(page.getByText(/Parcial para "Pergunta lenta para abortar"/i)).toBeVisible()

    // Usuário já digita a próxima pergunta enquanto a anterior carrega
    await input.fill('Nova pergunta imediata')
    await stopBtn.click()

    // Mostra aviso discreto mantendo o texto parcial e sem apagar o que foi digitado
    await expect(page.getByText('Resposta interrompida')).toBeVisible()
    await expect(page.getByText(/Parcial para "Pergunta lenta para abortar"/i)).toBeVisible()
    await expect(input).toHaveValue('Nova pergunta imediata')

    // Confirma que core_cancel foi chamado no Tauri
    const canceledCount = await page.evaluate(() => ((window as any).__TAURI_MOCK_CANCELED_IDS__ || []).length)
    expect(canceledCount).toBeGreaterThanOrEqual(1)

    // Envia a nova pergunta imediatamente e recebe a resposta completa
    await page.getByRole('button', { name: 'Enviar mensagem' }).click()
    await expect(page.getByText(/Resposta para "Nova pergunta imediata"/i)).toBeVisible()
    expect(getErrors()).toEqual([])
  })

  test('aborta prompt pela tecla Esc mantendo o texto digitado no campo', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installTauriMock(page, { chatStreamDelayMs: 800 })
    await page.goto('/#/chat')

    const input = page.getByLabel('Pergunta sobre pesquisa e extensão')
    await input.fill('Consulta com Esc')
    await input.press('Enter')

    await expect(page.getByRole('button', { name: 'Parar geração' })).toBeVisible()
    await input.fill('Rascunho preservado')
    await input.press('Escape')

    await expect(page.getByText('Resposta interrompida')).toBeVisible()
    await expect(input).toHaveValue('Rascunho preservado')
    await expect(page.getByRole('button', { name: 'Enviar mensagem' })).toBeVisible()
    expect(getErrors()).toEqual([])
  })

  test('mantém geração em segundo plano ao trocar de conversa e navegar para Meu painel e voltar', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installTauriMock(page, { chatStreamDelayMs: 500 })
    await page.goto('/#/chat')

    // Inicia geração numa conversa nova
    await page.getByRole('button', { name: /Novo chat/i }).click()
    const input = page.getByLabel('Pergunta sobre pesquisa e extensão')
    await input.fill('Consulta em segundo plano')
    await input.press('Enter')
    await expect(page.getByRole('button', { name: 'Parar geração' })).toBeVisible()

    // Troca para outra conversa na sidebar: botão volta a Enviar e resposta não vaza para cá
    await page.getByText('Panorama de Projetos').click()
    await expect(page.getByRole('button', { name: 'Enviar mensagem' })).toBeVisible()

    // Navega para Meu painel enquanto a geração ainda roda e volta para o Chat
    await page.getByRole('link', { name: 'Meu painel' }).click()
    await expect(page).toHaveURL(/#\/meu-dashboard/)
    await page.getByRole('link', { name: 'Chat' }).click()
    await expect(page).toHaveURL(/#\/chat/)

    // Volta na conversa original e confirma que a resposta concluiu em segundo plano
    await page.getByText('Consulta em segundo plano').first().click()
    await expect(page.getByText(/Resposta para "Consulta em segundo plano"/i)).toBeVisible()
    expect(getErrors()).toEqual([])
  })

  test('excluir conversa em geração dispara core_cancel automaticamente', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installTauriMock(page, { chatStreamDelayMs: 1200 })
    await page.goto('/#/chat')

    await page.getByRole('button', { name: /Novo chat/i }).click()
    const input = page.getByLabel('Pergunta sobre pesquisa e extensão')
    await input.fill('Conversa para excluir gerando')
    await input.press('Enter')

    await expect(page.getByRole('button', { name: 'Parar geração' })).toBeVisible()

    // Abre o modal de exclusão da conversa em geração na sidebar e confirma
    const convItem = page.locator('.conv-item', { hasText: 'Conversa para excluir gerando' }).first()
    await convItem.hover()
    await convItem.getByTitle('Excluir chat').click()
    await page.getByRole('button', { name: 'Excluir conversa' }).click()

    const canceledCount = await page.evaluate(() => ((window as any).__TAURI_MOCK_CANCELED_IDS__ || []).length)
    expect(canceledCount).toBeGreaterThanOrEqual(1)
    await expect(page.locator('.conv-item', { hasText: 'Conversa para excluir gerando' })).toHaveCount(0)
    expect(getErrors()).toEqual([])
  })
})
