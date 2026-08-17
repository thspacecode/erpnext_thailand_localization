import { test as setup, expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { STORAGE_STATE } from "./playwright.config";
import { CREDENTIALS } from "./fixtures/credentials";

setup("authenticate", async ({ page }) => {
	const response = await page.request.post("/api/method/login", {
		form: {
			usr: CREDENTIALS.user,
			pwd: CREDENTIALS.password,
		},
	});

	expect(
		response.ok(),
		`Login failed (${response.status()}). Check FRAPPE_TEST_USER and FRAPPE_TEST_PASSWORD.`,
	).toBeTruthy();

	await page.goto("/desk");
	await expect(page).toHaveURL(/\/desk/);

	fs.mkdirSync(path.dirname(STORAGE_STATE), { recursive: true });
	await page.context().storageState({ path: STORAGE_STATE });
});
