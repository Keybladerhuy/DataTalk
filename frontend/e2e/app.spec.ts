import { test, expect } from '@playwright/test';
import path from 'path';
import { trackConsoleErrors } from './helpers/console-errors';

const CSV_PATH = path.join(__dirname, 'fixtures', 'test-data.csv');

test.describe('DataTalk', () => {
  let getConsoleErrors: () => string[];

  test.beforeEach(async ({ page }) => {
    getConsoleErrors = trackConsoleErrors(page);
    await page.goto('/');
  });

  test.afterEach(async () => {
    const errors = getConsoleErrors();
    expect(errors, 'Browser console errors detected').toEqual([]);
  });

  test('page loads without console errors', async ({ page }) => {
    await expect(page.locator('h1')).toHaveText('DataTalk');
  });

  test('shows upload section on load', async ({ page }) => {
    await expect(page.locator('input[type="file"]')).toBeVisible();
    await expect(page.locator('h2').first()).toContainText('Upload a CSV');
  });

  test('query section is hidden before upload', async ({ page }) => {
    await expect(page.locator('input[type="text"]')).toHaveCount(0);
  });

  test('upload CSV and see preview table', async ({ page }) => {
    // Skip if backend is not reachable
    try {
      const res = await page.request.get('http://localhost:8000/docs');
      if (!res.ok()) test.skip();
    } catch {
      test.skip();
    }

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles(CSV_PATH);

    // Wait for preview table
    await expect(page.locator('table').first()).toBeVisible({ timeout: 10_000 });
    await expect(page.locator('.badge')).toHaveCount(3);

    // Check table headers
    const headers = page.locator('table thead th');
    await expect(headers).toHaveCount(3);
    await expect(headers.nth(0)).toHaveText('name');
    await expect(headers.nth(1)).toHaveText('age');
    await expect(headers.nth(2)).toHaveText('city');

    // Check 3 data rows
    await expect(page.locator('table tbody tr')).toHaveCount(3);

    // Query section should now be visible
    await expect(page.locator('input[type="text"]')).toBeVisible();
  });

  test('submit query and see results', async ({ page }) => {
    // Skip if backend is not reachable
    try {
      const res = await page.request.get('http://localhost:8000/docs');
      if (!res.ok()) test.skip();
    } catch {
      test.skip();
    }

    // Upload first
    await page.locator('input[type="file"]').setInputFiles(CSV_PATH);
    await expect(page.locator('table').first()).toBeVisible({ timeout: 10_000 });

    // Submit a query
    const queryInput = page.locator('input[type="text"]');
    await queryInput.fill('What is the average age?');
    await page.locator('button').filter({ hasText: 'Ask' }).click();

    // Wait for result (generated query or error)
    await expect(
      page.locator('.generated-query, .error').first()
    ).toBeVisible({ timeout: 30_000 });
  });
});
