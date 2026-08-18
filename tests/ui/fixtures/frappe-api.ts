import type { APIRequestContext, Page } from "@playwright/test";

export type FrappeDocument = {
	doctype: string;
	name: string;
	docstatus: number;
	[key: string]: unknown;
};

type MethodArgs = Record<string, boolean | number | string>;

export class FrappeApi {
	private csrfToken?: string;

	constructor(
		private readonly request: APIRequestContext,
		private readonly page: Page,
	) {}

	async call<T>(method: string, args: MethodArgs): Promise<T> {
		const csrfToken = await this.getCsrfToken();
		const response = await this.request.post(`/api/method/${method}`, {
			form: args,
			headers: { "X-Frappe-CSRF-Token": csrfToken },
		});
		if (!response.ok()) {
			throw new Error(`${method} failed (${response.status()}): ${await response.text()}`);
		}

		const result = (await response.json()) as { message: T };
		return result.message;
	}

	async createFromFactory<T extends FrappeDocument>(
		doctype: string,
		overrides: Record<string, unknown> = {},
		submit = false,
	): Promise<T> {
		return this.call<T>("erpnext_thailand_localization.tests.utils.run_factory_method", {
			doctype,
			method: "create",
			args: JSON.stringify({ ...overrides, submit }),
		});
	}

	async insert<T extends FrappeDocument>(doc: Record<string, unknown>): Promise<T> {
		return this.call<T>("frappe.client.insert", { doc: JSON.stringify(doc) });
	}

	async submit<T extends FrappeDocument>(doc: T): Promise<T> {
		return this.call<T>("frappe.client.submit", { doc: JSON.stringify(doc) });
	}

	async cancel(doctype: string, name: string): Promise<void> {
		await this.call("frappe.client.cancel", { doctype, name });
	}

	async delete(doctype: string, name: string): Promise<void> {
		await this.call("frappe.client.delete", { doctype, name });
	}

	private async getCsrfToken(): Promise<string> {
		if (!this.csrfToken) {
			await this.page.goto("/desk");
			await this.page.waitForFunction(
				() => Boolean((window as unknown as { frappe?: { csrf_token?: string } }).frappe?.csrf_token),
			);
			this.csrfToken = await this.page.evaluate(
				() => (window as unknown as { frappe: { csrf_token: string } }).frappe.csrf_token,
			);
		}
		return this.csrfToken;
	}
}
