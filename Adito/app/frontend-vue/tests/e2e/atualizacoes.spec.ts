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

    await painel.getByRole('button', { name: 'Baixar agora' }).click()
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

  test('opt-in em Configurações: baixa executável em segundo plano, exibe contagem de 10s e permite Adiar', async ({ page }) => {
    const errors = trackPageErrors(page)
    await installTauriMock(page, { appNovaVersao: '0.2.0' })
    await page.goto('/#/configuracoes')

    const toggle = page.getByRole('switch', { name: 'Atualização automática (app e dados)' })
    await expect(toggle).toBeVisible()
    await expect(toggle).not.toBeChecked()
    await expect(page.getByTestId('banner-reinicio-atualizacao')).toHaveCount(0)

    await toggle.click()
    await expect(toggle).toBeChecked()

    const banner = page.getByTestId('banner-reinicio-atualizacao')
    await expect(banner).toBeVisible()
    await expect(banner).toContainText('Nova versão v0.2.0 pronta')
    await expect(banner).toContainText(/reiniciando em \d+s/)

    await banner.getByRole('button', { name: 'Adiar' }).click()
    await expect(banner).toHaveCount(0)

    const telemetry = await page.evaluate(
      () => (window as unknown as Record<string, { downloads: number; installs: number; relaunches: number }>).__TAURI_MOCK_UPDATER__
    )
    expect(telemetry.downloads).toBe(1)
    expect(telemetry.installs).toBe(0)
    expect(telemetry.relaunches).toBe(0)

    // Botão manual na barra lateral continua disponível indicando pronto para reiniciar.
    await page.getByRole('button', { name: 'Atualização disponível' }).click()
    await expect(page.getByRole('button', { name: 'Reiniciar para atualizar' })).toBeVisible()
    expect(errors()).toEqual([])
  })

  test('opt-in ativo: clicar em "Reiniciar agora" no banner instala e reinicia o executável', async ({ page }) => {
    const errors = trackPageErrors(page)
    await installTauriMock(page, { appNovaVersao: '0.2.0', autoUpdateEnabled: true })
    await page.goto('/#/chat')

    const banner = page.getByTestId('banner-reinicio-atualizacao')
    await expect(banner).toBeVisible()
    await banner.getByRole('button', { name: 'Reiniciar agora' }).click()

    await expect.poll(async () => {
      return page.evaluate(
        () => (window as unknown as Record<string, { installs: number; relaunches: number }>).__TAURI_MOCK_UPDATER__
      )
    }).toMatchObject({ installs: 1, relaunches: 1 })
    expect(errors()).toEqual([])
  })

  test('atualização manual de dados.db dispara auto-reload no Dashboard e exibe toast discreto', async ({ page }) => {
    const errors = trackPageErrors(page)
    await installTauriMock(page, { dadosNovos: true })
    await page.goto('/#/dashboard')

    await expect(page.getByText('236')).toBeVisible()

    await page.getByRole('button', { name: 'Atualização disponível' }).click()
    await page.getByRole('button', { name: 'Baixar agora' }).click()

    await expect(page.getByTestId('toast-dados-atualizados')).toContainText('Dados atualizados para a versão 2026-11-22')
    await expect(page.getByText('310')).toBeVisible()
    expect(errors()).toEqual([])
  })

  test('opt-in ativo atualiza dados.db automaticamente em segundo plano e recarrega o Dashboard', async ({ page }) => {
    const errors = trackPageErrors(page)
    await installTauriMock(page, { dadosNovos: true, autoUpdateEnabled: true })
    await page.goto('/#/dashboard')

    await expect(page.getByTestId('toast-dados-atualizados')).toContainText('Dados atualizados para a versão 2026-11-22')
    await expect(page.getByText('310')).toBeVisible()
    await expect(page.getByTestId('atualizacao-disponivel')).toHaveCount(0)
    expect(errors()).toEqual([])
  })
})
