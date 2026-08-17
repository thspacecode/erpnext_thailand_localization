import { expect, test } from "../fixtures/test";

test.describe("ERPNext Thailand Localization Desk", () => {
	test("boots the Desk for a logged-in user", async ({ desk, page }) => {
		await page.goto("/desk");
		await desk.awaitReady();

		await expect(page.locator("#navbar-search, .navbar")).toBeVisible();
	});

	test("opens the Thai Withholding Tax Category list", async ({ desk, page }) => {
		await desk.goToList("Thai Withholding Tax Category");

		await expect(page.locator(".page-head")).toBeVisible();
		const route = await desk.currentRoute();
		expect(route).toEqual(["List", "Thai Withholding Tax Category", "List"]);
	});
});
