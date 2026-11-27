import { expect, test } from '@playwright/test'
import { installTauriMock, trackPageErrors } from './helpers/tauriMock'

test.describe('Explorar dados', () => {
  test('abre pelo menu, lista as tabelas do contexto e pagina, busca, filtra e agrupa', async ({ page }) => {
    const getErrors = trackPageErrors(page)
    await installTauriMock(page)
    await page.goto('/#/chat')

    await page.getByRole('link', { name: 'Explorar dados' }).click()
    await expect(page).toHaveURL(/#\/explorar/)
    await expect(page.getByRole('heading', { name: 'Explorar dados' })).toBeVisible()

    // Catálogo do contexto; a tabela sem colunas aparece indisponível.
    const catalogo = page.getByRole('complementary', { name: 'Catálogo de tabelas' })
    await expect(catalogo.getByRole('button', { name: /Orientações e Bolsas/ })).toBeVisible()
    await expect(catalogo.getByRole('button', { name: /Ações de Extensão/ })).toBeDisabled()

    await catalogo.getByRole('button', { name: /Projetos de Pesquisa/ }).click()
    const consulta = page.getByRole('region', { name: 'Consulta da tabela' })
    await expect(consulta.getByText('1 – 25 de 33')).toBeVisible()
    await expect(consulta.getByText('Página 1 de 2')).toBeVisible()

    await consulta.getByRole('button', { name: 'Próxima página' }).click()
    await expect(consulta.getByText('26 – 33 de 33')).toBeVisible()

    // Busca textual
    await page.getByPlaceholder('Digite um termo…').fill('Robótica')
    await expect(consulta.getByText('1 – 1 de 1')).toBeVisible()
    await expect(consulta.getByText('Robótica educacional 100%')).toBeVisible()
    await page.getByPlaceholder('Digite um termo…').fill('')

    // Filtro por valor exato de uma coluna
    await page.locator('#explorer-filter-column').selectOption('ano')
    await page.getByPlaceholder('Informe o valor').fill('2024')
    await expect(consulta.getByText('1 – 16 de 16')).toBeVisible()

    // Gráfico: conta os registros filtrados por valor da coluna
    await consulta.getByRole('button', { name: /Gráfico/ }).click()
    await page.locator('#explorer-group').selectOption('grande_area')
    await expect(consulta.getByText('Ciências Exatas e da Terra')).toBeVisible()

    expect(getErrors()).toEqual([])
  })
})
