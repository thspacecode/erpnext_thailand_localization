import { expect, type Page } from "@playwright/test";

export const DESK_ROOT = "/desk";

export class DeskPage {
	constructor(readonly page: Page) {}

	async awaitReady() {
		await this.page.waitForFunction(
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			() => Boolean((window as any).frappe?.router?.current_route),
			null,
			{ timeout: 30_000 },
		);
	}

	async goToList(doctype: string) {
		await this.page.goto(`${DESK_ROOT}/${slug(doctype)}`);
		await this.awaitReady();

		const route = await this.currentRoute();
		expect(route[0]).toBe("List");
		expect(route[1]).toBe(doctype);
	}

	async goToNew(doctype: string) {
		await this.page.goto(`${DESK_ROOT}/${slug(doctype)}/new`);
		await this.awaitReady();
	}

	async goToDoc(doctype: string, name: string) {
		await this.page.goto(`${DESK_ROOT}/${slug(doctype)}/${encodeURIComponent(name)}`);
		await this.awaitReady();
	}

	async currentRoute(): Promise<string[]> {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		return this.page.evaluate(() => (window as any).frappe.router.current_route as string[]);
	}
}

export function slug(doctype: string): string {
	return doctype.trim().toLowerCase().replace(/\s+/g, "-");
}
