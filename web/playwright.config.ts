import { defineConfig, devices } from '@playwright/test'
import { fileURLToPath } from 'node:url'

const executablePath = process.env.CREDIT_REVIEW_BROWSER_PATH
const testDir = fileURLToPath(new URL('./tests/e2e', import.meta.url))
const reportDir = fileURLToPath(new URL('../artifacts/playwright-report', import.meta.url))

export default defineConfig({
  testDir,
  fullyParallel: false,
  workers: 1,
  timeout: 120_000,
  expect: { timeout: 15_000 },
  reporter: [['list'], ['html', { outputFolder: reportDir, open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    launchOptions: executablePath ? { executablePath } : undefined,
    ...devices['Desktop Chrome'],
  },
})
