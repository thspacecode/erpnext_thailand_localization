import path from "node:path";

import { THAI_WHT_SETUP } from "../../test-data/thai-wht-setup";
import { expect, test } from "../../fixtures/test";

test.describe("Set up Thai withholding tax", () => {
	test("Reviews the Thai WHT setup created by the test master-data bootstrap", async ({
		desk,
		form,
		page,
	}, testInfo) => {
		testInfo.annotations.push({
			type: "prerequisite",
			description: "Install ERPNext Thailand Localization and bootstrap the test master data.",
		});
		const screenshotOptions = {
			animations: "disabled" as const,
			mask: [page.locator(".frappe-timestamp")],
			maskColor: "#ffffff",
			maxDiffPixelRatio: 0.002,
			stylePath: path.resolve(__dirname, "../../styles/screenshot.css"),
		};

		await test.step("Configure the main settings", async () => {
			await page.setViewportSize({ width: 1440, height: 720 });
			await desk.goToSingle("Thai Localization Settings");
			await form.expectValue("revenue_department", THAI_WHT_SETUP.revenueDepartment);
			await expect(page).toHaveScreenshot("thai-localization-settings.png", screenshotOptions);
		});

		await test.step("Configure the Company's tax accounts", async () => {
			await page.setViewportSize({ width: 1440, height: 900 });
			await desk.goToDoc("Company", THAI_WHT_SETUP.company.name);
			await form.openTab("Thai Tax");
			await form.expectChecked("enable_sales_withholding_tax");
			await form.expectValue(
				"sales_withholding_tax_account",
				THAI_WHT_SETUP.company.salesAccount,
			);
			await form.expectChecked("enable_purchase_withholding_tax");
			await form.expectValue(
				"purchase_withholding_tax_pnd3_account",
				THAI_WHT_SETUP.company.purchasePnd3Account,
			);
			await form.expectValue(
				"purchase_withholding_tax_pnd53_account",
				THAI_WHT_SETUP.company.purchasePnd53Account,
			);
			await expect(page).toHaveScreenshot("company-thai-tax.png", screenshotOptions);
		});

		await test.step("Set the Item income type and rate", async () => {
			await page.setViewportSize({ width: 1440, height: 1200 });
			await desk.goToDoc("Item", THAI_WHT_SETUP.item.name);
			await form.openTab("Tax");
			await form.expectValue(
				"custom_thai_withholding_tax_income_type",
				THAI_WHT_SETUP.item.incomeType,
			);
			await form.expectValue("custom_thai_withholding_tax_rate", "");
			await expect(form.field("custom_thai_withholding_tax_rate_by_category")).toBeVisible();
			await expect(page).toHaveScreenshot("item-thai-withholding-tax.png", screenshotOptions);
		});

		await test.step("Set the Supplier's tax category", async () => {
			await page.setViewportSize({ width: 1440, height: 1000 });
			await desk.goToDoc("Supplier", THAI_WHT_SETUP.supplier.name);
			await form.openTab("Tax");
			await form.expectValue("tax_id", "0105555000003");
			await form.expectValue(
				"custom_thai_withholding_tax_category",
				THAI_WHT_SETUP.supplier.category,
			);
			await expect(page).toHaveScreenshot("supplier-tax.png", screenshotOptions);
		});

		await test.step("Set the Company's tax category", async () => {
			await page.setViewportSize({ width: 1440, height: 900 });
			await desk.goToDoc("Company", THAI_WHT_SETUP.company.name);
			await form.openTab("Details");
			await form.expectValue("tax_id", "0105555000001");
			await form.expectValue(
				"custom_thai_withholding_tax_category",
				THAI_WHT_SETUP.company.category,
			);
			await expect(page).toHaveScreenshot(
				"company-details-tax-category.png",
				screenshotOptions,
			);
		});
	});
});
