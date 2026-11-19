import { defineConfig } from '@playwright/test'
import fs from 'node:fs'

const systemChrome = ['/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'].find((p) =>
  fs.existsSync(p),
)

const isLive = process.env.E2E_LIVE === '1'
const port = Number(process.env.E2E_VITE_PORT || 5174)

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: !isLive,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    headless: true,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    launchOptions: systemChrome ? { executablePath: systemChrome } : undefined,
  },
  projects: [
    {
      name: 'mock',
      testIgnore: /live-.*\.spec\.ts/,
    },
    {
      name: 'live',
      testMatch: /live-.*\.spec\.ts/,
    },
  ],
  webServer: {
    command: `npx vite --port ${port} --host 127.0.0.1 --strictPort`,
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
})
