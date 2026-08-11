import { expect, test } from '@playwright/test'
import path from 'node:path'

test.describe.configure({ mode: 'serial' })

test('normal demo path reaches report review', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '授信智能合规审查工作台' })).toBeVisible()
  await page.getByRole('button', { name: '创建正常演示' }).click()
  await expect(page).toHaveURL(/\/cases\//)
  await expect(page.getByText('星海演示科技有限公司')).toBeVisible()
  await expect(page.getByText('等待报告确认')).toBeVisible({ timeout: 90_000 })

  await page.getByRole('combobox').click({ force: true })
  await page.getByText('Reviewer · 审查员').click()
  await page.getByRole('button', { name: '报告', exact: true }).first().click()
  await expect(page.getByRole('heading', { name: '报告复核与导出' })).toBeVisible()
  await expect(page.getByText('AWAITING_REVIEW')).toBeVisible()
})

test('high-risk demo path resolves conflict and exposes R07 failure', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '创建高风险演示' }).click()
  await expect(page).toHaveURL(/\/cases\//)
  await expect(page.getByText('远山演示制造有限公司')).toBeVisible()
  await expect(page.getByText('等待事实复核')).toBeVisible({ timeout: 90_000 })

  await page.getByRole('combobox').click({ force: true })
  await page.getByText('Reviewer · 审查员').click()
  await page.getByRole('button', { name: '事实复核' }).click()
  await expect(page.getByRole('heading', { name: '事实冲突裁定' })).toBeVisible()
  await page.getByRole('radio', { name: /48 due-diligence/ }).click()
  await page.locator('textarea').first().fill('尽调报告为最新审查材料，采用其期限值。')
  await page.getByRole('button', { name: '提交事实裁定并继续' }).click()
  await expect(page).toHaveURL(/\/runs\/.*\/facts/)
  await page.getByRole('button', { name: '规则与风险' }).click()
  await expect(page.getByText('R07')).toBeVisible({ timeout: 90_000 })
  await expect(page.getByText('FAIL').first()).toBeVisible()
  await expect(page.getByText('NON_COMPLIANT')).toBeVisible()

  await page.getByRole('button', { name: '报告复核', exact: true }).click()
  await expect(page.getByText('AWAITING_REVIEW')).toBeVisible()
  await page.getByRole('button', { name: '确认报告', exact: true }).click()
  await page.getByRole('dialog').getByRole('button', { name: '确认报告', exact: true }).click()
  await expect(page.getByText('CONFIRMED')).toBeVisible()
})

test('RM manual upload path creates a real review run', async ({ page }) => {
  const materialsRoot = path.resolve(process.cwd(), '../artifacts/e2e-materials')
  await page.goto('/cases/new')
  await expect(page.getByRole('heading', { name: '创建一次可追溯的授信审查' })).toBeVisible()

  const formItems = page.locator('form .el-form-item')
  await formItems.nth(0).locator('input').fill('CASE-MANUAL-E2E-001')
  await formItems.nth(2).locator('input').fill('星海演示科技有限公司')
  await formItems.nth(3).locator('input').fill('SYNTH-MANUAL-E2E-001')

  const fileInputs = page.locator('input[type="file"]')
  await fileInputs.nth(0).setInputFiles(path.join(materialsRoot, 'business-license.pdf'))
  await fileInputs.nth(1).setInputFiles(path.join(materialsRoot, 'credit-application.docx'))
  await fileInputs.nth(2).setInputFiles(path.join(materialsRoot, 'due-diligence.pdf'))
  await fileInputs.nth(3).setInputFiles(path.join(materialsRoot, 'financial-statements.xlsx'))
  await page.getByRole('button', { name: '创建并启动审查' }).click()

  await expect(page).toHaveURL(/\/cases\//)
  await expect(page.getByText('星海演示科技有限公司')).toBeVisible()
  await expect(page.getByText('business-license.pdf')).toBeVisible()
  await expect(page.getByText('credit-application.docx')).toBeVisible()
  await expect(page.getByText('等待报告确认')).toBeVisible({ timeout: 90_000 })
})
