# End-to-End (e2e) Tests

## What is e2e testing?

End-to-end tests simulate a real user interacting with the app in an actual browser. Instead of testing individual functions (unit tests) or API endpoints (integration tests), e2e tests verify the whole system works together — frontend, backend, and everything in between.

For example, an e2e test might: open the app, upload a CSV file, check that a preview table appears, type a question, and verify that results show up. If any part of that chain breaks, the test fails.

## How it works

We use [Playwright](https://playwright.dev/) — a tool that launches a real Chromium browser, navigates to the app, and interacts with it programmatically (clicking buttons, filling inputs, reading text from the page).

### Key files

```
e2e/
├── README.md                    # This file
├── app.spec.ts                  # The test file (all test cases live here)
├── fixtures/
│   └── test-data.csv            # A small CSV file used by tests for uploads
└── helpers/
    └── console-errors.ts        # Utility that catches browser console errors
```

- **app.spec.ts** — Contains all the test cases. Each `test(...)` block is one scenario.
- **fixtures/** — Static test data. The CSV here is a tiny 3-row file so tests run fast and produce predictable results.
- **helpers/** — Reusable utilities. `console-errors.ts` listens for browser errors (like the NG0908 error we caught) and fails the test if any occur.

## Running the tests

Make sure the frontend dev server is running first (`npm start` from the `frontend/` folder).

```bash
# Run all tests (headless — no browser window)
npm run e2e

# Run tests with a visible browser (useful for debugging)
npm run e2e:headed
```

Some tests require the backend to be running on port 8000. If the backend is down, those tests are automatically skipped (not failed).

## What the tests check

| Test | Needs backend? | What it verifies |
|------|---------------|------------------|
| Page loads without console errors | No | No runtime errors in the browser console |
| Shows upload section on load | No | The file input and heading are visible |
| Query section is hidden before upload | No | The question input only appears after a CSV is uploaded |
| Upload CSV and see preview table | Yes | Uploading a file shows column info and a data table |
| Submit query and see results | Yes | Asking a question returns a result from the LLM |

## Adding a new test

Add a new `test(...)` block inside `app.spec.ts`. The `afterEach` hook automatically checks for browser console errors, so every test gets that check for free. Example:

```typescript
test('my new test', async ({ page }) => {
  // page.locator() finds elements on the page
  // expect() makes assertions about what you find
  await expect(page.locator('h1')).toHaveText('DataTalk');
});
```

See the [Playwright docs](https://playwright.dev/docs/writing-tests) for more on writing tests.
