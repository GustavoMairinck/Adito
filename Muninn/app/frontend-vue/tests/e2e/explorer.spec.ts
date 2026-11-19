import { expect, test } from '@playwright/test'
import { installTauriMock, trackPageErrors } from './helpers/tauriMock'

test.describe('Explorar dados', () => {
  test('lista views fato, filtra por busca textual e troca de tabela exibindo novo schema', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installTauriMock(page)
    await page.goto('/#/explorar')

    await expect(page.getByText('Monitoramento Inteligente de Redes')).toBeVisible()
    await expect(page.getByText('Plataforma de Dados Educacionais')).toBeVisible()
    await expect(page.getByText('Projeto Página 2 Exclusivo')).toBeHidden()

    // Paginação: avança para página 2 e confirma registro exclusivo da página 2
    await expect(page.getByText('Página 1 de 2')).toBeVisible()
    await page.getByRole('button', { name: 'Próxima página' }).click()
    await expect(page.getByText('Página 2 de 2')).toBeVisible()
    await expect(page.getByText('Projeto Página 2 Exclusivo')).toBeVisible()
    await page.getByRole('button', { name: 'Página anterior' }).click()
    await expect(page.getByText('Página 1 de 2')).toBeVisible()

    // Ordenação: clica na coluna `ano` (inverte ordem de asc para desc, trazendo registro de 2026 primeiro)
    const anoHeader = page.getByRole('columnheader', { name: 'ano' })
    await expect(anoHeader).toHaveAttribute('aria-sort', 'ascending')
    await anoHeader.getByRole('button', { name: 'ano' }).click()
    await expect(anoHeader).toHaveAttribute('aria-sort', 'descending')
    await expect(page.locator('tbody tr').first()).toContainText('Projeto Página 2 Exclusivo')

    const searchInput = page.locator('input[type="search"], input[placeholder*="Buscar"], input[placeholder*="Filtrar"]').first()
    await searchInput.fill('Robótica')
    await expect(page.getByText('Robótica Aplicada à Indústria')).toBeVisible()
    await expect(page.getByText('Plataforma de Dados Educacionais')).toBeHidden()

    await page.getByRole('button', { name: /Projetos de Pesquisa/i }).click()
    await expect(page.getByText('Visão Computacional no Campus Serra')).toBeVisible()
    await expect(page.getByText('Análise de Séries Temporais Acadêmicas')).toBeVisible()
    await expect(page.getByText('Robótica Aplicada à Indústria')).toBeHidden()

    expect(getErrors()).toEqual([])
  })

  test('exibe erro amigável quando o banco está indisponível (503) sem tela branca', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installTauriMock(page, { explorerError503: true })
    await page.goto('/#/explorar')

    await expect(page.getByText(/Não foi possível ler os dados/i)).toBeVisible()
    expect(getErrors()).toEqual([])
  })
})
