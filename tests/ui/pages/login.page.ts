import { expect, type Locator, type Page } from "@playwright/test";
import { BasePage } from "./base.page";

export class LoginPage extends BasePage {
	readonly email: Locator;
	readonly password: Locator;
	readonly submit: Locator;

	constructor(page: Page) {
		super(page);
		this.email = page.locator("#login_email");
		this.password = page.locator("#login_password");
		this.submit = page.locator(".btn-login:not(.btn-login-with-email-link)");
	}

	async goto() {
		await this.page.goto("/login");
		await expect(this.email).toBeVisible();
	}

	async login(user: string, password: string) {
		await this.email.fill(user);
		await this.password.fill(password);
		await this.submit.click();
		await this.page.waitForURL(/\/desk/, { timeout: 30_000 });
	}
}
