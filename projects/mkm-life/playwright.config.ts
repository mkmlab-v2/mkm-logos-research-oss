import { defineConfig, devices } from '@playwright/test'

/** E2E 전용 포트 — 3000에 다른 앱이 떠 있어도 mkm-life만 기동·재사용 판정 */
const E2E_PORT = Number(process.env.PLAYWRIGHT_PORT || '3333')
const E2E_ORIGIN = `http://localhost:${E2E_PORT}`

/**
 * E2E: `npm run test:e2e` 또는 `npm run test:e2e:one-question`
 * 동일 포트(E2E_ORIGIN)에서 이미 `next dev` 중이면 webServer 재사용.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? 'github' : 'list',
  timeout: 60_000,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || E2E_ORIGIN,
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
    ? undefined
    : {
        command: `npm run dev -- -p ${E2E_PORT}`,
        url: E2E_ORIGIN,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
})

