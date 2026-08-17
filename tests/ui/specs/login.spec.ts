import { expect, test } from "@playwright/test";
import { CREDENTIALS } from "../fixtures/credentials";
import { LoginPage } from "../pages/login.page";

test.describe("Login page", () => {
	test.use({ storageState: { cookies: [], origins: [] } });

	test("logs in through the UI and lands on the Desk", async ({ page }) => {
		const login = new LoginPage(page);
		await login.goto();
		await login.login(CREDENTIALS.user, CREDENTIALS.password);

		await expect(page).toHaveURL(/\/desk/);
	});

	test("rejects invalid credentials", async ({ page }) => {
		const login = new LoginPage(page);
		await login.goto();
		await login.email.fill("Administrator");
		await login.password.fill("definitely-the-wrong-password");
		await login.submit.click();

		await expect(page).toHaveURL(/\/login/);
		await expect(login.email).toBeVisible();
	});
});
