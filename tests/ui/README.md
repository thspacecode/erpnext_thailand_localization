# UI tests (Playwright)

End-to-end browser tests for **ERPNext Thailand Localization**, following the
Playwright structure used by `erp_summit`.

## Layout

```text
apps/erpnext_thailand_localization/tests/ui/
├── .env.example
├── package.json
├── playwright.config.ts
├── tsconfig.json
├── yarn.lock
├── auth.setup.ts
├── fixtures/
│   ├── credentials.ts
│   └── test.ts
├── pages/
│   ├── desk.page.ts
│   └── login.page.ts
└── specs/
    ├── desk-navigation.spec.ts
    └── login.spec.ts
```

The `setup` project signs in through Frappe's login API and writes the browser
state to `playwright/.auth/user.json`. The Chromium project depends on setup and
reuses that state. Tests that cover the login page explicitly start logged out.

## Run locally

From `apps/erpnext_thailand_localization/tests/ui`:

```bash
yarn install
yarn playwright install --with-deps chromium
yarn test:ui
```

The config reuses a server already listening on the configured URL. Otherwise,
it starts `bench serve --port 8000` from the bench root.

Additional commands:

```bash
yarn test:ui:headed
yarn test:ui:ui
yarn test:ui:debug
yarn test:ui:report
yarn test:ui:codegen
```

Copy `.env.example` to `.env` to override the site URL or credentials.

## Write a test

Import the extended fixture when a test needs Desk helpers:

```ts
import { expect, test } from "../fixtures/test";

test("opens a localization list", async ({ desk, page }) => {
	await desk.goToList("Thai Withholding Tax Category");
	await expect(page.locator(".page-head")).toBeVisible();
});
```

## CI

`.github/workflows/ui-tests.yml` creates a Frappe/ERPNext site, installs this
app, bootstraps its test master data, and runs the Chromium suite. The HTML
report is uploaded as a workflow artifact.
