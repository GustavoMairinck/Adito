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
    await expect(page.getByText(/SELECT grande_area/i).last()).toBeVisible()

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

    await expect(page.getByText(/Chave do Gemini não configurada/i).first()).toBeVisible()
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

  test('exporta todos os registros da resposta do chat para CSV e Excel (.xlsx) com toast de confirmação', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    const rows15 = Array.from({ length: 15 }, (_, i) => ({
      grande_area: `Área ${i + 1}`,
      total_projetos: (i + 1) * 10,
    }))
    await installTauriMock(page, { chatData: rows15 })
    await page.goto('/#/chat')

    const input = page.getByLabel('Pergunta sobre pesquisa e extensão')
    await input.fill('Listar projetos por área')
    await input.press('Enter')

    // Padrão na tabela mostra 10 de 15 registros
    await expect(page.getByText('Mostrando 10 de 15 registros')).toBeVisible()

    // Exportar CSV (.csv) — garante que o menu fica 100% visível dentro da viewport
    const exportBtn = page.getByTestId('chat-export-btn').last()
    await expect(exportBtn).toBeVisible()
    await exportBtn.click()
    const menu = page.getByTestId('chat-export-menu')
    await expect(menu).toBeVisible()
    const box = await menu.boundingBox()
    const viewport = page.viewportSize()!
    expect(box).not.toBeNull()
    expect(box!.y).toBeGreaterThanOrEqual(0)
    expect(box!.y + box!.height).toBeLessThanOrEqual(viewport.height)
    expect(box!.x).toBeGreaterThanOrEqual(0)
    expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width)

    await page.getByRole('menuitem', { name: /Exportar CSV/i }).click()

    await expect(page.getByTestId('chat-toast')).toContainText(/Arquivo salvo em Documentos:.*\.csv/)

    // Exportar Excel (.xlsx)
    await exportBtn.click()
    await page.getByRole('menuitem', { name: /Exportar Excel/i }).click()

    await expect(page.getByTestId('chat-toast')).toContainText(/Arquivo salvo em Documentos:.*\.xlsx/)

    const exports = await page.evaluate(
      () => (window as unknown as Record<string, Array<{ nome: string; bytes: number[] }>>).__TAURI_MOCK_EXPORTS__
    )
    expect(exports).toHaveLength(2)

    // Valida CSV completo (UTF-8 BOM + separador ';' + todas as 15 linhas)
    const csvExport = exports[0]
    expect(csvExport.nome).toMatch(/^adito-listar-projetos-por-area-\d{8}-\d{6}\.csv$/)
    expect(csvExport.bytes.slice(0, 3)).toEqual([0xef, 0xbb, 0xbf])
    const csvText = new TextDecoder().decode(new Uint8Array(csvExport.bytes))
    expect(csvText).toContain('grande area;total projetos')
    expect(csvText).toContain('Área 15;150')

    // Valida assinatura PKZIP do .xlsx
    const xlsxExport = exports[1]
    expect(xlsxExport.nome).toMatch(/^adito-listar-projetos-por-area-\d{8}-\d{6}\.xlsx$/)
    expect(xlsxExport.bytes.slice(0, 4)).toEqual([0x50, 0x4b, 0x03, 0x04])

    expect(getErrors()).toEqual([])
  })

  test('cancelar o diálogo "Salvar como..." na exportação não exibe erro nem grava arquivo', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installTauriMock(page, { exportCancel: true })
    await page.goto('/#/chat')

    const input = page.getByLabel('Pergunta sobre pesquisa e extensão')
    await input.fill('Projetos por área')
    await input.press('Enter')

    const exportBtn = page.getByTestId('chat-export-btn').last()
    await expect(exportBtn).toBeVisible()
    await exportBtn.click()
    await page.getByRole('menuitem', { name: /Exportar Excel/i }).click()

    await expect(page.getByTestId('chat-toast')).toHaveCount(0)
    const exports = await page.evaluate(
      () => (window as unknown as Record<string, Array<{ nome: string; bytes: number[] }>>).__TAURI_MOCK_EXPORTS__
    )
    expect(exports).toHaveLength(0)
    expect(getErrors()).toEqual([])
  })
})
