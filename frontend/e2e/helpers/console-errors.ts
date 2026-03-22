import { Page } from '@playwright/test';

/**
 * Attaches a console-error collector to a page.
 * Returns a function that retrieves accumulated errors.
 */
export function trackConsoleErrors(page: Page): () => string[] {
  const errors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });
  return () => errors;
}
