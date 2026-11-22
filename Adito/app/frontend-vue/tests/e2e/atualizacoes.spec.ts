import { expect, test } from '@playwright/test'
import { installTauriMock, trackPageErrors } from './helpers/tauriMock'

test.describe('Distribuição: primeiro uso e atualizações', () => {
  test('sem nada novo, o aviso do canto não aparece', async ({ page }) => {
    await installTauriMock(page)
    await page.goto('/#/chat')
    await expect(page.getByLabel('Pergunta sobre pesquisa e extensão')).toBeVisible()
    await expect(page.getByTestId('atualizacao-disponivel')).toHaveCount(0)
    await expect(page.getByTestId('primeiro-uso-dados')).toHaveCount(0)
  })

  test('dados novos: aviso discreto no canto, abre o painel e atualiza', async ({ page }) => {
    const errors = trackPageErrors(page)
    await installTauriMock(page, { dadosNovos: true })
    await page.goto('/#/chat')

    const aviso = page.getByRole('button', { name: 'Atualização disponível' })
    await expect(aviso).toBeVisible()
    // Não bloqueia o uso: o chat continua acessível.
    await expect(page.getByLabel('Pergunta sobre pesquisa e extensão')).toBeEnabled()

    await aviso.click()
    const painel = page.getByRole('dialog', { name: 'Atualizações do Adito' })
    await expect(painel.getByText('Dados novos')).toBeVisible()
    await expect(painel.getByText(/2026-11-22/)).toBeVisible()

    await painel.getByRole('button', { name: 'Atualizar os dados' }).click()
    await expect(page.getByTestId('atualizacao-disponivel')).toHaveCount(0)
    expect(errors()).toEqual([])
  })

  test('"Depois" fecha o painel e mantém o aviso', async ({ page }) => {
    await installTauriMock(page, { dadosNovos: true })
    await page.goto('/#/chat')
    await page.getByRole('button', { name: 'Atualização disponível' }).click()
    await page.getByRole('button', { name: 'Depois' }).click()
    await expect(page.getByRole('dialog', { name: 'Atualizações do Adito' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: 'Atualização disponível' })).toBeVisible()
  })

  test('primeiro uso pede a chave, recusa a errada e aceita a certa', async ({ page }) => {
    await installTauriMock(page, { semDados: true })
    await page.goto('/#/chat')

    const tela = page.getByTestId('primeiro-uso-dados')
    await expect(tela).toBeVisible()
    const campo = tela.getByLabel('Chave dos dados')

    await campo.fill('b'.repeat(64))
    await tela.getByRole('button', { name: 'Baixar os dados' }).click()
    await expect(tela.getByText('Essa chave não abre esta versão dos dados.')).toBeVisible()

    await campo.fill('a'.repeat(64))
    await tela.getByRole('button', { name: 'Baixar os dados' }).click()
    await expect(tela).toHaveCount(0)
  })
})
