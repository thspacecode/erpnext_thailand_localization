import { test as base } from "@playwright/test";
import { DeskPage } from "../pages/desk.page";

export const test = base.extend<{ desk: DeskPage }>({
	desk: async ({ page }, use) => {
		await use(new DeskPage(page));
	},
});

export { expect } from "@playwright/test";
