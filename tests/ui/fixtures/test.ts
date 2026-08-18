import { test as base } from "@playwright/test";
import { BasePage } from "../pages/base.page";
import { DeskPage } from "../pages/desk.page";
import { FormPage } from "../pages/form.page";

type Fixtures = {
	desk: DeskPage;
	form: FormPage;
	fonts: void;
};

export const test = base.extend<Fixtures>({
	desk: async ({ page }, use) => {
		await use(new DeskPage(page));
	},
	form: async ({ page }, use) => {
		await use(new FormPage(page));
	},
	fonts: [
		async ({ page }, use) => {
			await new BasePage(page).installFonts();
			await use();
		},
		{ auto: true },
	],
});

export { expect } from "@playwright/test";
