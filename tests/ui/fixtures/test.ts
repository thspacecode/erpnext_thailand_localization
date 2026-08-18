import {
	expect,
	test as base,
	type PageAssertionsToHaveScreenshotOptions,
} from "@playwright/test";
import path from "node:path";
import { BasePage } from "../pages/base.page";
import { DeskPage } from "../pages/desk.page";
import { FormPage } from "../pages/form.page";
import { FrappeApi } from "./frappe-api";

type Fixtures = {
	api: FrappeApi;
	desk: DeskPage;
	expectScreenshot: (
		name: string,
		options?: PageAssertionsToHaveScreenshotOptions,
	) => Promise<void>;
	form: FormPage;
	fonts: void;
};

export const test = base.extend<Fixtures>({
	api: async ({ page, request }, use) => {
		await use(new FrappeApi(request, page));
	},
	desk: async ({ page }, use) => {
		await use(new DeskPage(page));
	},
	expectScreenshot: async ({ page }, use) => {
		await use(async (name, options = {}) => {
			await expect(page).toHaveScreenshot(name, {
				animations: "disabled",
				maskColor: "#ffffff",
				maxDiffPixelRatio: 0.005,
				stylePath: path.resolve(__dirname, "../styles/screenshot.css"),
				...options,
			});
		});
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

export { expect };
