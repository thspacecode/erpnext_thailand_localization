import { expect, type Locator } from "@playwright/test";
import { BasePage } from "./base.page";

export class FormPage extends BasePage {
	field(fieldname: string): Locator {
		return this.page.locator(`.frappe-control[data-fieldname="${fieldname}"]`).first();
	}

	async openTab(label: string) {
		const tab = this.page.locator(".form-tabs").getByText(label, { exact: true });
		await expect(tab).toBeVisible();
		await tab.click();
	}

	async expectDocumentName(name: string) {
		const pageTitle = this.page.locator(".page-title");
		await expect(pageTitle).toBeVisible();
		await expect(pageTitle).toContainText(name);
	}

	async expectValue(fieldname: string, value: string) {
		const field = this.field(fieldname);
		await expect(field).toBeAttached();
		if (await field.isVisible()) {
			await field.scrollIntoViewIfNeeded();
		}
		await expect(
			field.locator('input:not([type="hidden"]), select, textarea').first(),
		).toHaveValue(value);
	}

	async expectChecked(fieldname: string) {
		const field = this.field(fieldname);
		await field.scrollIntoViewIfNeeded();
		await expect(field).toBeVisible();
		await expect(field.locator('input[type="checkbox"][data-fieldname]').first()).toBeChecked();
	}

	async expectTableRow(fieldname: string, values: string[]) {
		const field = this.field(fieldname);
		await field.scrollIntoViewIfNeeded();
		await expect(field).toBeVisible();

		const row = field.locator(".grid-row").filter({ hasText: values[0] }).first();
		await expect(row).toBeVisible();
		for (const value of values) {
			await expect(row).toContainText(value);
		}
	}
}
